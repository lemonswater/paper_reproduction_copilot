"""Chat Service：编排 context、prompt、provider 和 citation 校验。"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections.abc import Callable

from app.chat.context import ChatContextBuilder
from app.chat.errors import (
    ChatConflictError,
    ChatUnavailableError,
)
from app.chat.memory import (
    ConversationMemoryCompactor,
    MemoryCompactionOutcome,
    build_memory_draft_invoker,
    validate_memory_hash,
)
from app.chat.prompt import build_budgeted_chat_prompt
from app.chat.schemas import (
    ChatAskResponse,
    ChatDraft,
    ChatMemoryStatus,
    ChatMessagePage,
    ChatToolTraceSummary,
    ConversationMemoryView,
)
from app.chat.store import ChatRepository
from app.config import settings
from app.interaction.service import InteractionService
from app.secrets.redaction import SecretRedactor
from app.tool_calling.loop import (
    BoundedToolCallingLoop,
    merge_grounding_sources,
    public_trace_summary,
)

logger = logging.getLogger(__name__)

ChatDraftInvoker = Callable[[str, str], ChatDraft]


def _request_sha256(job_id: str, question: str) -> str:
    payload = json.dumps(
        {
            "job_id": job_id,
            "question": question,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _idempotency_key(value: str) -> str:
    key = value.strip()
    if not key or len(key) > 300:
        raise ChatConflictError(
            "Idempotency-Key 长度必须为 1..300"
        )
    return key


def build_chat_draft_invoker() -> ChatDraftInvoker:
    """Chat Provider adapter；只允许结构化回答，不绑定 Tool。"""

    def invoke(prompt: str, job_id: str) -> ChatDraft:
        from app.model_routing.factory import build_model_gateway

        result = build_model_gateway().invoke_structured(
            task_kind="chat_answer",
            schema=ChatDraft,
            prompt=prompt,
            node_name="chat_answer",
            job_id=job_id,
            quality_tier="balanced",
            requested_max_output_tokens=4096,
        )
        if result.value is None:
            statuses = ",".join(
                item.status for item in result.attempts
            )
            raise ChatUnavailableError(
                f"Chat structured output failed: {statuses}"
            )
        return result.value

    return invoke


class ChatService:
    def __init__(
        self,
        *,
        repository: ChatRepository,
        interaction: InteractionService,
        context_builder: ChatContextBuilder,
        draft_invoker: ChatDraftInvoker,
        memory_compactor: ConversationMemoryCompactor,
        recent_messages: int,
        history_max_chars: int,
        memory_max_chars: int,
        prompt_max_chars: int,
        # 默认空 Redactor 只为旧单元测试兼容；生产装配必须传真实实例。
        redactor: SecretRedactor | None = None,
        tool_loop: BoundedToolCallingLoop | None = None,
        source_limit: int = 8,
        total_context_chars: int = 48000,
    ):
        self.repository = repository
        self.interaction = interaction
        self.context_builder = context_builder
        self.draft_invoker = draft_invoker
        self.memory_compactor = memory_compactor
        self.recent_messages = recent_messages
        self.history_max_chars = history_max_chars
        self.memory_max_chars = memory_max_chars
        self.prompt_max_chars = prompt_max_chars
        self.redactor = redactor or SecretRedactor.empty()
        self.tool_loop = tool_loop
        self.source_limit = source_limit
        self.total_context_chars = total_context_chars
        # 单 Uvicorn Worker 中同时序列化 compaction、answer 和 append。
        self._ask_lock = threading.Lock()

    def ping(self) -> None:
        self.repository.ping()

    def list_messages(
        self,
        *,
        job_id: str,
        after_sequence: int,
        limit: int,
    ) -> ChatMessagePage:
        self.interaction.get_job(job_id)
        items = self.repository.list_messages(
            job_id=job_id,
            after_sequence=after_sequence,
            limit=limit,
        )
        return ChatMessagePage(
            items=items,
            next_after=(
                items[-1].sequence
                if items
                else after_sequence
            ),
        )

    def list_recent_messages(
        self,
        *,
        job_id: str,
        limit: int,
    ) -> ChatMessagePage:
        """给 Web 首屏返回 newest N 条，响应内仍按时间正序。"""

        self.interaction.get_job(job_id)
        items = self.repository.list_recent_messages(
            job_id=job_id,
            limit=limit,
        )
        return ChatMessagePage(
            items=items,
            next_after=(items[-1].sequence if items else 0),
        )

    def get_memory(
        self,
        *,
        job_id: str,
    ) -> ConversationMemoryView | None:
        self.interaction.get_job(job_id)
        memory = self.repository.get_latest_memory(job_id)
        if memory is None:
            return None
        try:
            validate_memory_hash(memory)
        except Exception as exc:
            raise ChatUnavailableError(
                "Chat Memory integrity check failed"
            ) from exc
        return ConversationMemoryView.from_memory(memory)

    def _memory_status(
        self,
        *,
        outcome: MemoryCompactionOutcome | None = None,
    ) -> ChatMemoryStatus:
        memory = outcome.memory if outcome is not None else None
        return ChatMemoryStatus(
            enabled=self.memory_compactor.enabled,
            available=memory is not None,
            version=(memory.version if memory is not None else None),
            covered_through_sequence=(
                memory.covered_through_sequence
                if memory is not None
                else 0
            ),
            degraded=(outcome.degraded if outcome is not None else False),
            degraded_reason=(
                outcome.reason if outcome is not None else None
            ),
            provider_attempt_count=(
                outcome.provider_attempt_count
                if outcome is not None
                else 0
            ),
        )

    def _current_memory_outcome(
        self,
        job_id: str,
    ) -> MemoryCompactionOutcome:
        try:
            memory = self.repository.get_latest_memory(job_id)
            if memory is not None:
                validate_memory_hash(memory)
            return MemoryCompactionOutcome(memory, False, False)
        except Exception as exc:
            return MemoryCompactionOutcome(
                memory=None,
                created=False,
                degraded=True,
                reason=type(exc).__name__,
            )

    def ask(
        self,
        *,
        job_id: str,
        question: str,
        idempotency_key: str,
    ) -> ChatAskResponse:
        raw_question = question.strip()
        if not raw_question:
            raise ChatConflictError("question 不能为空")

        # 已知 Secret 永远不能进入 request hash 后面的持久化和 Provider 边界。
        normalized_question = self.redactor.redact_text(
            raw_question,
            max_chars=4000,
        )
        key = _idempotency_key(idempotency_key)
        request_hash = _request_sha256(
            job_id,
            normalized_question,
        )

        # get_job 同时阻止对不存在 Job 的孤立 Chat 写入。
        job = self.interaction.get_job(job_id)
        replay = self.repository.find_exchange(
            job_id=job_id,
            idempotency_key=key,
            request_sha256=request_hash,
        )
        if replay is not None:
            memory_outcome = self._current_memory_outcome(job_id)
            return ChatAskResponse(
                user_message=replay[0],
                assistant_message=replay[1],
                replayed=True,
                allowed_operations=job.allowed_operations,
                memory=self._memory_status(outcome=memory_outcome),
            )

        with self._ask_lock:
            # 获取锁后再次检查，避免两个同 key 请求同时越过第一次检查。
            replay = self.repository.find_exchange(
                job_id=job_id,
                idempotency_key=key,
                request_sha256=request_hash,
            )
            if replay is not None:
                memory_outcome = self._current_memory_outcome(job_id)
                return ChatAskResponse(
                    user_message=replay[0],
                    assistant_message=replay[1],
                    replayed=True,
                    allowed_operations=job.allowed_operations,
                    memory=self._memory_status(outcome=memory_outcome),
                )

            memory_outcome = self.memory_compactor.ensure_memory(job_id)
            memory = memory_outcome.memory

            logger.info(
                "chat_memory_compaction",
                extra={
                    "job_id": job_id,
                    "memory_enabled": self.memory_compactor.enabled,
                    "memory_created": memory_outcome.created,
                    "memory_degraded": memory_outcome.degraded,
                    "memory_reason": memory_outcome.reason,
                    "memory_version": (
                        memory_outcome.memory.version
                        if memory_outcome.memory is not None
                        else None
                    ),
                    "covered_through_sequence": (
                        memory_outcome.memory.covered_through_sequence
                        if memory_outcome.memory is not None
                        else 0
                    ),
                },
            )

            recent = self.repository.list_recent_messages(
                job_id=job_id,
                limit=self.recent_messages,
            )
            # 正常 cutoff 会让 recent 全部位于 memory 之后；过滤是额外防线。
            history = [
                item
                for item in recent
                if memory is None
                or item.sequence > memory.covered_through_sequence
            ]
            tool_trace = None
            if self.tool_loop is None:
                # Feature 关闭：完全保持原来的 eager context。
                bundle = self.context_builder.build(
                    job_id=job_id,
                    question=normalized_question,
                )
            else:
                base_bundle = self.context_builder.build_job_only(
                    job_id=job_id,
                    question=normalized_question,
                )
                try:
                    outcome = self.tool_loop.run(
                        job_id=job_id,
                        job_status=base_bundle.job.status,
                        question=normalized_question,
                        request_sha256=request_hash,
                    )
                    tool_trace = public_trace_summary(outcome.trace)

                    if outcome.trace.status in {
                        "planner_unavailable",
                        "policy_blocked",
                    }:
                        # Tool Selection 是优化层，不应成为 Chat 的单点故障。
                        # fallback 只读取 Phase 51 之前本来就允许的证据，不扩大权限。
                        bundle = self.context_builder.build(
                            job_id=job_id,
                            question=normalized_question,
                        )
                    else:
                        bundle = merge_grounding_sources(
                            base=base_bundle,
                            additions=outcome.sources,
                            source_limit=self.source_limit,
                            total_chars=self.total_context_chars,
                        )
                except Exception as exc:
                    logger.warning(
                        "chat_tool_calling_degraded",
                        extra={
                            "job_id": job_id,
                            "error_type": type(exc).__name__,
                        },
                    )
                    # 不记录原始异常 message，避免路径、Provider body 或证据正文泄漏。
                    bundle = self.context_builder.build(
                        job_id=job_id,
                        question=normalized_question,
                    )
            prompt_build = build_budgeted_chat_prompt(
                question=normalized_question,
                history=history,
                memory=memory,
                bundle=bundle,
                prompt_max_chars=self.prompt_max_chars,
                history_max_chars=self.history_max_chars,
                memory_max_chars=self.memory_max_chars,
            )
            # Prompt 已完成 JSON 编码和预算选择；在 Provider 调用前再按已知值脱敏。
            # 不能在这里截断字符串，否则可能得到不完整 JSON。
            safe_prompt = self.redactor.redact_text(prompt_build.prompt)
            if len(safe_prompt) > self.prompt_max_chars:
                raise ChatUnavailableError(
                    "Chat Prompt redaction exceeded configured budget"
                )
            draft = self.draft_invoker(safe_prompt, job_id)

            # 只能引用预算后实际进入 SOURCES_DATA 的 source。
            source_by_id = {
                item.citation.citation_id: item.citation
                for item in prompt_build.sources
            }
            unknown = [
                item
                for item in draft.citation_ids
                if item not in source_by_id
            ]
            citation_ids = list(
                dict.fromkeys(draft.citation_ids)
            )

            # 编造来源或没有任何有效引用都 fail closed。
            # 不信任模型仅靠 insufficient_evidence 字段自我约束。
            if unknown or not citation_ids:
                answer = (
                    "现有可验证证据不足，无法安全回答这个问题。"
                    "请等待相关 Artifact 生成，或查看当前任务日志和报告。"
                )
                citations = []
            else:
                answer = self.redactor.redact_text(
                    draft.answer,
                    max_chars=6000,
                )
                citations = [
                    source_by_id[item]
                    for item in citation_ids
                    if item in source_by_id
                ]

            user, assistant, created = (
                self.repository.append_exchange(
                    job_id=job_id,
                    idempotency_key=key,
                    request_sha256=request_hash,
                    question=normalized_question,
                    answer=answer,
                    citations=citations,
                    tool_trace=tool_trace,
                )
            )
            current_job = self.interaction.get_job(job_id)
            return ChatAskResponse(
                user_message=user,
                assistant_message=assistant,
                replayed=not created,
                allowed_operations=(
                    current_job.allowed_operations
                ),
                memory=self._memory_status(outcome=memory_outcome),
            )


def build_chat_service(
    *,
    repository: ChatRepository,
    interaction: InteractionService,
    context_builder: ChatContextBuilder,
) -> ChatService:
    from app.secrets.factory import build_secret_service

    # build_redactor 只把 active material 短暂加载进当前受信任进程；
    # ChatDraft、Prompt 和响应中都不保存 material。
    redactor = build_secret_service().build_redactor(
        actor="runtime:chat-redactor"
    )

    memory_compactor = ConversationMemoryCompactor(
        repository=repository,
        invoker=build_memory_draft_invoker(),
        enabled=settings.chat_compaction_enabled,
        recent_messages=settings.chat_recent_messages,
        min_messages=settings.chat_compaction_min_messages,
        max_messages=settings.chat_compaction_max_messages,
        max_input_chars=settings.chat_compaction_max_input_chars,
        memory_max_chars=settings.chat_memory_max_chars,
        prompt_version=settings.chat_memory_prompt_version,
        model_name=settings.openai_model,
        structured_method=settings.structured_output_method,
        strict=settings.structured_output_strict,
    )
    tool_loop = None
    if settings.chat_tool_calling_enabled:
        from app.tool_calling.factory import build_chat_tool_calling_loop

        tool_loop = build_chat_tool_calling_loop(
            context_builder=context_builder,
        )

    return ChatService(
        repository=repository,
        interaction=interaction,
        context_builder=context_builder,
        draft_invoker=build_chat_draft_invoker(),
        memory_compactor=memory_compactor,
        recent_messages=settings.chat_recent_messages,
        history_max_chars=settings.chat_history_max_chars,
        memory_max_chars=settings.chat_memory_max_chars,
        prompt_max_chars=settings.chat_prompt_max_chars,
        redactor=redactor,
        tool_loop=tool_loop,
        source_limit=settings.chat_source_limit,
        total_context_chars=settings.chat_total_context_chars,
    )

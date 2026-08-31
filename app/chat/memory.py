"""ConversationMemoryCompactor：增量压缩旧对话成可审计 Memory。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.chat.errors import (
    ChatMemoryConflict,
    ChatMemoryError,
    ChatMemoryUnavailable,
)
from app.chat.memory_prompt import (
    build_memory_prompt,
    memory_message_payload,
)
from app.chat.schemas import (
    ChatCitation,
    ChatMessage,
    ConversationMemory,
    ConversationMemoryBody,
    MemoryDraft,
    MemoryStatement,
)
from app.chat.store import ChatRepository


@dataclass(frozen=True)
class MemoryDraftResult:
    draft: MemoryDraft
    model_name: str
    model_invocation_id: str | None
    provider_attempt_count: int = 1


MemoryDraftInvoker = Callable[[str, str], MemoryDraftResult]


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _messages_sha256(messages: list[ChatMessage]) -> str:
    return _sha256(
        [item.model_dump(mode="json") for item in messages]
    )


def _memory_sha256_payload(
    *,
    memory_id: str,
    job_id: str,
    version: int,
    covered_from_sequence: int,
    covered_through_sequence: int,
    delta_messages_sha256: str,
    parent_memory_id: str | None,
    parent_memory_sha256: str | None,
    body: ConversationMemoryBody,
    prompt_version: str,
    model_name: str,
    structured_method: str,
    strict: bool,
    created_at: str,
) -> dict:
    return {
        "memory_id": memory_id,
        "job_id": job_id,
        "version": version,
        "covered_from_sequence": covered_from_sequence,
        "covered_through_sequence": covered_through_sequence,
        "delta_messages_sha256": delta_messages_sha256,
        "parent_memory_id": parent_memory_id,
        "parent_memory_sha256": parent_memory_sha256,
        "body": _memory_body_hash_payload(body),
        "prompt_version": prompt_version,
        "model_name": model_name,
        "structured_method": structured_method,
        "strict": strict,
        "created_at": created_at,
    }


PHASE38_CITATION_FIELDS = {
    "comparison_id",
    "comparison_hash",
    "base_job_id",
    "target_job_id",
}

PHASE46_CITATION_FIELDS = {
    "project_id",
    "project_fact_id",
    "project_fact_hash",
}

PHASE49_CITATION_FIELDS = {
    "knowledge_pack_hash",
    "knowledge_subject_id",
    "knowledge_subject_hash",
    "knowledge_evidence_ref_ids",
}


def _memory_body_hash_payload(
    body: ConversationMemoryBody,
) -> dict:
    """按 body 创建时的 Citation schema 生成稳定 hash 投影。"""

    payload = body.model_dump(mode="json")
    version = body.citation_schema_version
    if version == "phase36-v1":
        # Phase 36 创建 hash 时不存在 version 和 Comparison 字段。
        payload.pop("citation_schema_version", None)
        removed = (
            PHASE38_CITATION_FIELDS
            | PHASE46_CITATION_FIELDS
            | PHASE49_CITATION_FIELDS
        )
        for citation in payload.get("citation_anchors", []):
            for field_name in removed:
                citation.pop(field_name, None)
    elif version == "phase38-v2":
        removed = PHASE46_CITATION_FIELDS | PHASE49_CITATION_FIELDS
        for citation in payload.get("citation_anchors", []):
            for field_name in removed:
                citation.pop(field_name, None)
    elif version == "phase46-v3":
        removed = PHASE49_CITATION_FIELDS
        for citation in payload.get("citation_anchors", []):
            for field_name in removed:
                citation.pop(field_name, None)
    return payload


def validate_memory_hash(memory: ConversationMemory) -> None:
    payload = _memory_sha256_payload(
        memory_id=memory.memory_id,
        job_id=memory.job_id,
        version=memory.version,
        covered_from_sequence=memory.covered_from_sequence,
        covered_through_sequence=memory.covered_through_sequence,
        delta_messages_sha256=memory.delta_messages_sha256,
        parent_memory_id=memory.parent_memory_id,
        parent_memory_sha256=memory.parent_memory_sha256,
        body=memory.body,
        prompt_version=memory.prompt_version,
        model_name=memory.model_name,
        structured_method=memory.structured_method,
        strict=memory.strict,
        created_at=memory.created_at,
    )
    if _sha256(payload) != memory.memory_sha256:
        raise ChatMemoryConflict("ConversationMemory hash 不一致")


@dataclass(frozen=True)
class MemoryCompactionOutcome:
    memory: ConversationMemory | None
    created: bool
    degraded: bool
    reason: str | None = None
    provider_attempt_count: int = 0


def _complete_exchange_prefix(
    messages: list[ChatMessage],
) -> list[ChatMessage]:
    """只接受连续、原子写入的 user/assistant pairs。"""

    accepted: list[ChatMessage] = []
    index = 0
    while index + 1 < len(messages):
        user = messages[index]
        assistant = messages[index + 1]
        if (
            user.role != "user"
            or assistant.role != "assistant"
            or assistant.reply_to != user.message_id
            or assistant.sequence != user.sequence + 1
        ):
            raise ChatMemoryConflict(
                f"Chat exchange 在 sequence={user.sequence} 处不完整"
            )
        accepted.extend([user, assistant])
        index += 2
    return accepted


def _bounded_delta(
    messages: list[ChatMessage],
    *,
    max_messages: int,
    max_chars: int,
) -> list[ChatMessage]:
    selected: list[ChatMessage] = []
    # 以完整 exchange 为单位增加，不切半条问答。
    for index in range(0, min(len(messages), max_messages), 2):
        pair = messages[index:index + 2]
        if len(pair) < 2:
            break
        candidate = [*selected, *pair]
        encoded = _canonical(
            [memory_message_payload(item) for item in candidate]
        )
        if len(encoded) > max_chars:
            break
        selected = candidate
    return selected


class ConversationMemoryCompactor:
    def __init__(
        self,
        *,
        repository: ChatRepository,
        invoker: MemoryDraftInvoker,
        enabled: bool,
        recent_messages: int,
        min_messages: int,
        max_messages: int,
        max_input_chars: int,
        memory_max_chars: int,
        prompt_version: str,
        model_name: str,
        structured_method: str,
        strict: bool,
    ):
        self.repository = repository
        self.invoker = invoker
        self.enabled = enabled
        self.recent_messages = recent_messages
        self.min_messages = min_messages
        self.max_messages = max_messages
        self.max_input_chars = max_input_chars
        self.memory_max_chars = memory_max_chars
        self.prompt_version = prompt_version
        self.model_name = model_name
        self.structured_method = structured_method
        self.strict = strict

    def _delta(
        self,
        *,
        job_id: str,
        previous: ConversationMemory | None,
    ) -> list[ChatMessage]:
        latest = self.repository.latest_sequence(job_id)
        previous_end = (
            previous.covered_through_sequence
            if previous is not None
            else 0
        )
        compactable_end = latest - self.recent_messages
        if compactable_end <= previous_end:
            return []

        start = previous_end + 1
        rows = self.repository.list_messages_range(
            job_id=job_id,
            start_sequence=start,
            end_sequence=compactable_end,
            limit=self.max_messages,
        )
        if not rows:
            return []
        expected = start
        for item in rows:
            if item.sequence != expected:
                raise ChatMemoryConflict(
                    "Memory delta message sequence 不连续"
                )
            expected += 1
        complete = _complete_exchange_prefix(rows)
        return _bounded_delta(
            complete,
            max_messages=self.max_messages,
            max_chars=self.max_input_chars,
        )

    @staticmethod
    def _citation_map(
        *,
        previous: ConversationMemory | None,
        delta: list[ChatMessage],
    ) -> dict[str, ChatCitation]:
        citations = {
            item.citation_id: item
            for item in (
                previous.body.citation_anchors
                if previous is not None
                else []
            )
        }
        for message in delta:
            for citation in message.citations:
                existing = citations.get(citation.citation_id)
                if existing is not None and existing != citation:
                    raise ChatMemoryConflict(
                        "同一 citation_id 对应不同 citation identity"
                    )
                citations[citation.citation_id] = citation
        return citations

    @staticmethod
    def _validate_statement_sources(
        *,
        draft: MemoryDraft,
        previous: ConversationMemory | None,
        delta: list[ChatMessage],
    ) -> None:
        delta_roles = {item.sequence: item.role for item in delta}
        previous_user_sources: set[int] = set()
        previous_any_sources: set[int] = set()
        if previous is not None:
            for item in [
                *previous.body.user_constraints,
                *previous.body.open_questions,
            ]:
                previous_user_sources.update(item.source_sequences)
            for item in [
                *previous.body.user_constraints,
                *previous.body.decisions,
                *previous.body.open_questions,
            ]:
                previous_any_sources.update(item.source_sequences)

        def validate(
            statements: list[MemoryStatement],
            *,
            user_only: bool,
        ) -> None:
            for statement in statements:
                for sequence in statement.source_sequences:
                    if sequence in delta_roles:
                        if user_only and delta_roles[sequence] != "user":
                            raise ChatMemoryConflict(
                                "constraint/open question 必须引用 user message"
                            )
                        continue
                    allowed_previous = (
                        previous_user_sources
                        if user_only
                        else previous_any_sources
                    )
                    if sequence not in allowed_previous:
                        raise ChatMemoryConflict(
                            f"Memory 使用了未知 source sequence={sequence}"
                        )

        validate(draft.user_constraints, user_only=True)
        validate(draft.open_questions, user_only=True)
        validate(draft.decisions, user_only=False)

    @staticmethod
    def _repair_user_statement_sources(
        *,
        draft: MemoryDraft,
        delta: list[ChatMessage],
    ) -> MemoryDraft:
        """Repair a common provider mistake without broadening provenance.

        Some providers attach a constraint/open-question to the assistant's
        acknowledgement instead of the user's message.  Every assistant
        message in a valid exchange has an unambiguous ``reply_to`` user
        message, so remapping only those local sequences is deterministic and
        keeps the final Memory anchored to the original user statement.
        Unknown sequences are left untouched and still fail closed in the
        validator below.
        """

        message_by_id = {item.message_id: item for item in delta}
        assistant_to_user_sequence = {
            item.sequence: message_by_id[item.reply_to].sequence
            for item in delta
            if (
                item.role == "assistant"
                and item.reply_to is not None
                and item.reply_to in message_by_id
                and message_by_id[item.reply_to].role == "user"
            )
        }

        def repair(items: list[MemoryStatement]) -> list[MemoryStatement]:
            return [
                item.model_copy(
                    update={
                        "source_sequences": [
                            assistant_to_user_sequence.get(
                                sequence,
                                sequence,
                            )
                            for sequence in item.source_sequences
                        ]
                    }
                )
                for item in items
            ]

        return draft.model_copy(
            update={
                "user_constraints": repair(draft.user_constraints),
                "open_questions": repair(draft.open_questions),
            }
        )

    def _project_body(
        self,
        *,
        draft: MemoryDraft,
        previous: ConversationMemory | None,
        delta: list[ChatMessage],
    ) -> ConversationMemoryBody:
        draft = self._repair_user_statement_sources(
            draft=draft,
            delta=delta,
        )
        self._validate_statement_sources(
            draft=draft,
            previous=previous,
            delta=delta,
        )
        citation_map = self._citation_map(
            previous=previous,
            delta=delta,
        )
        unknown = [
            item
            for item in draft.citation_ids_to_preserve
            if item not in citation_map
        ]
        if unknown:
            raise ChatMemoryConflict(
                f"MemoryDraft 返回未知 citation IDs：{unknown[:3]}"
            )
        body = ConversationMemoryBody(
            summary=draft.summary,
            user_constraints=draft.user_constraints,
            decisions=draft.decisions,
            open_questions=draft.open_questions,
            citation_anchors=[
                citation_map[item]
                for item in dict.fromkeys(
                    draft.citation_ids_to_preserve
                )
            ],
            citation_schema_version=(
                "phase49-v4"
                if any(
                    item.source_type == "knowledge"
                    for item in [
                        citation_map[cid]
                        for cid in dict.fromkeys(
                            draft.citation_ids_to_preserve
                        )
                    ]
                )
                else "phase46-v3"
                if any(
                    item.source_type == "project_fact"
                    for item in [
                        citation_map[cid]
                        for cid in dict.fromkeys(
                            draft.citation_ids_to_preserve
                        )
                    ]
                )
                else "phase38-v2"
            ),
        )
        if len(_canonical(body.model_dump(mode="json"))) > self.memory_max_chars:
            raise ChatMemoryConflict("ConversationMemory 超过字符预算")
        return body

    def ensure_memory(self, job_id: str) -> MemoryCompactionOutcome:
        # 读取/解析/hash 任一步失败，都不能让损坏 Memory 进入 Answer Prompt。
        # 同时仍允许 Chat 使用最近原始窗口继续回答。
        try:
            previous = self.repository.get_latest_memory(job_id)
            if previous is not None:
                validate_memory_hash(previous)
        except Exception as exc:
            return MemoryCompactionOutcome(
                memory=None,
                created=False,
                degraded=True,
                reason=type(exc).__name__,
            )
        if not self.enabled:
            return MemoryCompactionOutcome(previous, False, False)

        try:
            delta = self._delta(job_id=job_id, previous=previous)
            if len(delta) < self.min_messages:
                return MemoryCompactionOutcome(previous, False, False)

            prompt = build_memory_prompt(
                previous=previous,
                delta=delta,
            )
            if len(prompt) > self.max_input_chars + self.memory_max_chars + 8000:
                raise ChatMemoryConflict("Memory prompt 超过确定性预算")
            invocation = self.invoker(prompt, job_id)
            draft = invocation.draft
            generated_by_model = invocation.model_name
            body = self._project_body(
                draft=draft,
                previous=previous,
                delta=delta,
            )

            created_at = datetime.now(timezone.utc).isoformat()
            memory_id = f"chat-memory-{uuid4().hex}"
            version = 1 if previous is None else previous.version + 1
            covered_from_sequence = (
                1 if previous is None
                else previous.covered_through_sequence + 1
            )
            covered_through_sequence = delta[-1].sequence
            delta_hash = _messages_sha256(delta)
            parent_id = previous.memory_id if previous is not None else None
            parent_hash = (
                previous.memory_sha256 if previous is not None else None
            )

            payload = _memory_sha256_payload(
                memory_id=memory_id,
                job_id=job_id,
                version=version,
                covered_from_sequence=covered_from_sequence,
                covered_through_sequence=covered_through_sequence,
                delta_messages_sha256=delta_hash,
                parent_memory_id=parent_id,
                parent_memory_sha256=parent_hash,
                body=body,
                prompt_version=self.prompt_version,
                model_name=generated_by_model,
                structured_method=self.structured_method,
                strict=self.strict,
                created_at=created_at,
            )
            memory = ConversationMemory(
                memory_id=memory_id,
                job_id=job_id,
                version=version,
                covered_from_sequence=covered_from_sequence,
                covered_through_sequence=covered_through_sequence,
                delta_messages_sha256=delta_hash,
                parent_memory_id=parent_id,
                parent_memory_sha256=parent_hash,
                body=body,
                memory_sha256=_sha256(payload),
                prompt_version=self.prompt_version,
                model_name=generated_by_model,
                structured_method=self.structured_method,
                strict=self.strict,
                created_at=created_at,
            )

            saved, created = self.repository.save_memory(
                memory=memory,
                expected_parent_memory_id=parent_id,
            )
            validate_memory_hash(saved)
            return MemoryCompactionOutcome(
                memory=saved,
                created=created,
                degraded=False,
                provider_attempt_count=invocation.provider_attempt_count,
            )
        except ChatMemoryError as exc:
            return MemoryCompactionOutcome(
                memory=previous,
                created=False,
                degraded=True,
                reason=getattr(
                    exc,
                    "reason_code",
                    type(exc).__name__,
                ),
                provider_attempt_count=getattr(
                    exc,
                    "attempt_count",
                    0,
                ),
            )
        except Exception as exc:
            # Provider/parse 的内部细节不能进入 API；记录 telemetry 时只记类型。
            return MemoryCompactionOutcome(
                previous,
                False,
                True,
                type(exc).__name__,
            )


def _memory_failure_reason(result: object) -> str:
    """把结构化调用明细归并为可公开、稳定的 Memory 错误码。"""

    attempts = list(getattr(result, "attempts", []))
    if any(getattr(item, "truncated", False) for item in attempts):
        return "ChatMemoryOutputTruncated"

    statuses = {
        str(getattr(item, "status", ""))
        for item in attempts
        if getattr(item, "status", None)
    }
    if "configuration_error" in statuses:
        return "ChatMemoryStructuredConfigurationFailed"
    if statuses and statuses.issubset(
        {"provider_retry", "invoke_error"}
    ):
        return "ChatMemoryProviderInvokeFailed"
    if "validation_error" in statuses:
        return "ChatMemorySchemaValidationFailed"
    return "ChatMemoryStructuredOutputFailed"


def build_memory_draft_invoker() -> MemoryDraftInvoker:
    """Memory Provider adapter；预算失败时由 Compactor 安全降级。"""

    def invoke(prompt: str, job_id: str) -> MemoryDraftResult:
        from app.model_routing.factory import build_model_gateway

        result = build_model_gateway().invoke_structured(
            task_kind="chat_memory_compaction",
            schema=MemoryDraft,
            prompt=prompt,
            node_name="chat_memory_compaction",
            job_id=job_id,
            quality_tier="balanced",
            requested_max_output_tokens=4096,
        )
        if result.value is None:
            raise ChatMemoryUnavailable(
                _memory_failure_reason(result),
                attempt_count=len(result.attempts),
            )
        return MemoryDraftResult(
            draft=result.value,
            model_name=result.decision.executed_model_name,
            model_invocation_id=result.invocation_id,
            provider_attempt_count=len(result.attempts),
        )

    return invoke

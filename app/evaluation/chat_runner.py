from __future__ import annotations

import hashlib
import json
import shutil
import time
from collections.abc import Callable
from pathlib import Path

from app.chat.context import GroundingBundle, GroundingSource
from app.chat.memory import (
    ConversationMemoryCompactor,
    MemoryDraftResult,
    build_memory_draft_invoker,
    validate_memory_hash,
)
from app.chat.schemas import ChatDraft, MemoryDraft
from app.chat.service import (
    ChatService,
    build_chat_draft_invoker,
)
from app.chat.store import SqliteChatRepository
from app.config import settings
from app.evaluation.case_loader import resolve_evaluation_path
from app.evaluation.chat_schemas import (
    ChatEvalMemoryScript,
    ChatEvalObservation,
    ChatEvalScenario,
    ChatMemoryObservation,
    ChatScenarioRunObservation,
    ChatTurnObservation,
)
from app.evaluation.schemas import (
    EvalCase,
    EvalMetrics,
    EvalObservation,
)
from app.interaction.schemas import (
    AllowedOperation,
    JobView,
    PublicJobInput,
)


class _StaticInteraction:
    """Chat Eval 的只读交互替身。

    如果未来有人误把 submit/cancel 接入 ChatService，测试会立即失败，
    而不是在假的 Eval 环境里静默成功。
    """

    def __init__(self, job: JobView):
        self.job = job
        self.mutation_attempts = 0

    def get_job(self, job_id: str) -> JobView:
        if job_id != self.job.job_id:
            raise KeyError(f"Chat Eval unknown job_id={job_id}")
        return self.job

    def _reject_mutation(self, name: str) -> None:
        self.mutation_attempts += 1
        raise AssertionError(
            f"read-only Chat attempted mutation: {name}"
        )

    def submit_decision(self, **_kwargs: object) -> None:
        self._reject_mutation("submit_decision")

    def cancel_job(self, **_kwargs: object) -> None:
        self._reject_mutation("cancel_job")

    def create_rerun_proposal(self, **_kwargs: object) -> None:
        self._reject_mutation("create_rerun_proposal")


class _StaticContextBuilder:
    """返回 Scenario 中的合成 Source，不打开 Artifact 或生产路径。"""

    def __init__(
        self,
        *,
        job: JobView,
        sources: list[GroundingSource],
    ):
        self.job = job
        self.sources = list(sources)

    def build(self, *, job_id: str, question: str) -> GroundingBundle:
        if job_id != self.job.job_id or not question.strip():
            raise ValueError("Chat Eval context identity 不一致")
        return GroundingBundle(
            job=self.job,
            sources=list(self.sources),
        )


class _ScriptedChatInvoker:
    def __init__(self, drafts: list[ChatDraft]):
        self.drafts = list(drafts)
        self.calls = 0
        self.prompts: list[str] = []
        self.returned: list[ChatDraft] = []

    def __call__(self, prompt: str, job_id: str) -> ChatDraft:
        del job_id
        self.prompts.append(prompt)
        if self.calls >= len(self.drafts):
            raise ValueError("Chat scripted drafts 已耗尽")
        draft = self.drafts[self.calls]
        self.calls += 1
        self.returned.append(draft)
        return draft

    def assert_exhausted(self) -> None:
        if self.calls != len(self.drafts):
            raise ValueError(
                "Chat scripted drafts 未全部消费："
                f"{self.calls}/{len(self.drafts)}"
            )


class _ScriptedMemoryInvoker:
    def __init__(self, scripts: list[ChatEvalMemoryScript]):
        self.scripts = list(scripts)
        self.calls = 0
        self.prompts: list[str] = []

    def __call__(self, prompt: str, job_id: str) -> MemoryDraftResult:
        del job_id
        self.prompts.append(prompt)
        if self.calls >= len(self.scripts):
            raise ValueError("Memory scripts 已耗尽")
        item = self.scripts[self.calls]
        self.calls += 1
        if item.error_code is not None:
            # Compactor 只应暴露错误类型，不把内部文本写入 API/Observation。
            raise RuntimeError(item.error_code)
        assert item.draft is not None
        return MemoryDraftResult(
            draft=item.draft,
            model_name="scripted",
            model_invocation_id=None,
        )

    def assert_exhausted(self) -> None:
        if self.calls != len(self.scripts):
            raise ValueError(
                "Memory scripts 未全部消费："
                f"{self.calls}/{len(self.scripts)}"
            )


class _CapturingChatInvoker:
    """包装真实 Provider，只保存有界 Draft 与 Prompt 长度。"""

    def __init__(self, delegate: Callable[[str, str], ChatDraft]):
        self.delegate = delegate
        self.calls = 0
        self.prompts: list[str] = []
        self.returned: list[ChatDraft] = []

    def __call__(self, prompt: str, job_id: str) -> ChatDraft:
        self.calls += 1
        self.prompts.append(prompt)
        draft = self.delegate(prompt, job_id)
        self.returned.append(draft)
        return draft


class _CapturingMemoryInvoker:
    def __init__(
        self,
        delegate: Callable[[str, str], MemoryDraftResult],
    ):
        self.delegate = delegate
        self.calls = 0
        self.prompts: list[str] = []

    def __call__(self, prompt: str, job_id: str) -> MemoryDraftResult:
        self.calls += 1
        self.prompts.append(prompt)
        return self.delegate(prompt, job_id)


def _load_scenario(case: EvalCase) -> ChatEvalScenario:
    path = resolve_evaluation_path(str(case.input.fixture_path))
    scenario = ChatEvalScenario.model_validate_json(
        path.read_text(encoding="utf-8")
    )
    if scenario.scenario_id != case.case_id:
        raise ValueError(
            "Scenario identity 与 Case 不一致："
            f"{scenario.scenario_id} != {case.case_id}"
        )
    return scenario


def _validate_mode(
    *,
    case: EvalCase,
    scenario: ChatEvalScenario,
    provider: bool,
) -> None:
    provider_pairs = {
        ("chat_provider", "chat_provider"),
        ("conversation_decision_provider", "decision_provider"),
    }
    offline_pairs = {
        ("chat_scenario", "chat_offline"),
        ("conversation_decision", "decision_offline"),
    }
    pair = (case.runner, case.suite)

    if provider:
        if pair not in provider_pairs:
            raise ValueError("Provider Chat Eval runner/suite 不一致")
        if any(item.scripted_draft is not None for item in scenario.turns):
            raise ValueError("Provider Chat Eval 禁止 scripted ChatDraft")
        if scenario.memory_scripts:
            raise ValueError("Provider Chat Eval 禁止 scripted MemoryDraft")
        return

    if pair not in offline_pairs:
        raise ValueError("Offline Chat Eval runner/suite 不一致")
    if scenario.repetitions != 1:
        raise ValueError("Offline Chat Eval repetitions 必须为 1")
    if any(item.scripted_draft is None for item in scenario.turns):
        raise ValueError("Offline Chat Eval 每个 Turn 都要求 scripted_draft")


def _job(scenario: ChatEvalScenario, repetition: int) -> JobView:
    timestamp = "2026-08-10T00:00:00+00:00"
    return JobView(
        job_id=f"chat-eval-job-{repetition}",
        thread_id=f"chat-eval-thread-{repetition}",
        run_id=f"chat-eval-run-{repetition}",
        status=scenario.job_status,
        version=scenario.job_version,
        attempt_count=0,
        max_attempts=1,
        wait_generation=scenario.wait_generation,
        interrupt_nodes=[],
        interrupts=[],
        cancel_requested=False,
        input=PublicJobInput(
            paper_name="synthetic-paper",
            repo_name="synthetic-repository",
            experiment_goal="Conversation decision evaluation only",
            execution_profile_id="none",
        ),
        allowed_operations=list(scenario.allowed_operations),
        created_at=timestamp,
        updated_at=timestamp,
    )


def _grounding_sources(
    scenario: ChatEvalScenario,
) -> list[GroundingSource]:
    return [
        GroundingSource(
            citation=item.citation,
            content=item.content,
            score=item.score,
        )
        for item in scenario.sources
    ]


def _operation_availability(
    *,
    draft: ChatDraft,
    allowed_operations: list[AllowedOperation],
) -> str:
    """把模型请求投影到服务端 Capability，但不执行任何操作。"""

    requested = draft.requested_operation
    if requested is None:
        return "not_requested"

    matches = [
        operation
        for operation in allowed_operations
        if operation.kind == requested.kind
        and (
            requested.kind != "submit_decision"
            or operation.decision_kind == requested.decision_kind
        )
    ]
    if not matches:
        return "unavailable"
    if len(matches) == 1:
        return "available"
    return "ambiguous"


def _prompt_source_ids(prompt: str) -> list[str]:
    """只解码 SOURCES_DATA JSON，不保存 Source content。"""

    marker = "SOURCES_DATA:\n"
    if marker not in prompt:
        raise ValueError("Chat Prompt 缺少 SOURCES_DATA")
    tail = prompt.split(marker, 1)[1].lstrip()
    payload, _ = json.JSONDecoder().raw_decode(tail)
    if not isinstance(payload, list):
        raise ValueError("SOURCES_DATA 必须是 JSON list")
    return [
        str(item["citation_id"])
        for item in payload
        if isinstance(item, dict) and "citation_id" in item
    ]


def _memory_observation(
    repository: SqliteChatRepository,
    *,
    job_id: str,
) -> ChatMemoryObservation:
    memory = repository.get_latest_memory(job_id)
    if memory is None:
        return ChatMemoryObservation()

    hash_valid = True
    try:
        validate_memory_hash(memory)
    except Exception:  # noqa: BLE001 - Observation 只投影布尔结果。
        hash_valid = False

    messages = repository.list_messages(
        job_id=job_id,
        after_sequence=0,
        limit=500,
    )
    roles = {item.sequence: item.role for item in messages}
    checks: list[bool] = []
    for statement in memory.body.user_constraints:
        checks.extend(
            roles.get(sequence) == "user"
            for sequence in statement.source_sequences
        )
    for statement in memory.body.open_questions:
        checks.extend(
            roles.get(sequence) == "user"
            for sequence in statement.source_sequences
        )
    for statement in memory.body.decisions:
        checks.extend(
            sequence in roles
            for sequence in statement.source_sequences
        )
    source_ratio = (
        sum(checks) / len(checks)
        if checks
        else 1.0
    )
    compacted_source_chars = sum(
        len(item.content)
        for item in messages
        if item.sequence <= memory.covered_through_sequence
    )
    memory_text_chars = len(memory.body.summary) + sum(
        len(statement.text)
        for statement in [
            *memory.body.user_constraints,
            *memory.body.decisions,
            *memory.body.open_questions,
        ]
    )
    text_compression_ratio = (
        memory_text_chars / compacted_source_chars
        if compacted_source_chars
        else None
    )
    return ChatMemoryObservation(
        available=True,
        version=memory.version,
        covered_through_sequence=memory.covered_through_sequence,
        compacted_source_chars=compacted_source_chars,
        memory_text_chars=memory_text_chars,
        text_compression_ratio=text_compression_ratio,
        summary=memory.body.summary,
        user_constraints=memory.body.user_constraints,
        decisions=memory.body.decisions,
        open_questions=memory.body.open_questions,
        citation_ids=[
            item.citation_id for item in memory.body.citation_anchors
        ],
        hash_valid=hash_valid,
        source_sequence_valid_ratio=source_ratio,
    )


def _seed_history(
    repository: SqliteChatRepository,
    *,
    scenario: ChatEvalScenario,
    job_id: str,
) -> None:
    citation_by_id = {
        item.citation.citation_id: item.citation
        for item in scenario.sources
    }
    for index, exchange in enumerate(scenario.seed_exchanges):
        repository.append_exchange(
            job_id=job_id,
            idempotency_key=f"seed-{index}",
            request_sha256=hashlib.sha256(
                f"{scenario.scenario_id}:{index}".encode("utf-8")
            ).hexdigest(),
            question=exchange.question,
            answer=exchange.answer,
            citations=[
                citation_by_id[item]
                for item in exchange.citation_ids
            ],
        )


def _run_once(
    *,
    scenario: ChatEvalScenario,
    provider: bool,
    repetition: int,
    db_path: Path,
) -> ChatScenarioRunObservation:
    started = time.perf_counter()
    job = _job(scenario, repetition)
    repository = SqliteChatRepository(db_path)
    repository.initialize()
    _seed_history(repository, scenario=scenario, job_id=job.job_id)

    if provider:
        chat_invoker = _CapturingChatInvoker(
            build_chat_draft_invoker()
        )
        memory_invoker = _CapturingMemoryInvoker(
            build_memory_draft_invoker()
        )
    else:
        chat_invoker = _ScriptedChatInvoker(
            [
                item.scripted_draft
                for item in scenario.turns
                if item.scripted_draft is not None
            ]
        )
        memory_invoker = _ScriptedMemoryInvoker(
            scenario.memory_scripts
        )

    compactor = ConversationMemoryCompactor(
        repository=repository,
        invoker=memory_invoker,
        enabled=scenario.compaction_enabled,
        recent_messages=scenario.recent_messages,
        min_messages=scenario.compaction_min_messages,
        max_messages=scenario.compaction_max_messages,
        max_input_chars=scenario.compaction_max_input_chars,
        memory_max_chars=scenario.memory_max_chars,
        prompt_version="phase37-eval-v1",
        model_name=(settings.openai_model if provider else "scripted"),
        structured_method=settings.structured_output_method,
        strict=settings.structured_output_strict,
    )
    interaction = _StaticInteraction(job)
    service = ChatService(
        repository=repository,
        interaction=interaction,
        context_builder=_StaticContextBuilder(
            job=job,
            sources=_grounding_sources(scenario),
        ),
        draft_invoker=chat_invoker,
        memory_compactor=compactor,
        recent_messages=scenario.recent_messages,
        history_max_chars=scenario.history_max_chars,
        memory_max_chars=scenario.memory_max_chars,
        prompt_max_chars=scenario.prompt_max_chars,
    )

    responses = []
    for turn in scenario.turns:
        responses.append(
            service.ask(
                job_id=job.job_id,
                question=turn.question,
                idempotency_key=turn.idempotency_key,
            )
        )

    if not provider:
        chat_invoker.assert_exhausted()
        memory_invoker.assert_exhausted()

    if len(scenario.turns) != len(responses):
        raise ValueError("Turn 与 Response 数量不一致")
    turn_observations: list[ChatTurnObservation] = []
    for index, (turn, response) in enumerate(
        zip(scenario.turns, responses)
    ):
        draft = chat_invoker.returned[index]
        prompt_sources = _prompt_source_ids(chat_invoker.prompts[index])
        requested = list(dict.fromkeys(draft.citation_ids))
        unknown = [item for item in requested if item not in prompt_sources]
        answer = response.assistant_message.content
        requested_operation = draft.requested_operation
        turn_observations.append(
            ChatTurnObservation(
                label=turn.label,
                answer=answer,
                citation_ids=[
                    item.citation_id
                    for item in response.assistant_message.citations
                ],
                requested_citation_ids=requested,
                prompt_source_ids=prompt_sources,
                unknown_requested_citation_ids=unknown,
                model_marked_insufficient=draft.insufficient_evidence,
                # Provider 结构化结果是拒答状态的权威信号；固定文案只
                # 作为未知 Citation/无 Citation 的 fail-closed 兜底。
                refused=(
                    draft.insufficient_evidence
                    or answer.startswith("现有可验证证据不足")
                ),
                replayed=response.replayed,
                memory_available=response.memory.available,
                memory_degraded=response.memory.degraded,
                memory_degraded_reason=response.memory.degraded_reason,
                memory_provider_attempt_count=(
                    response.memory.provider_attempt_count
                ),
                predicted_intent=draft.intent,
                requested_operation_kind=(
                    requested_operation.kind
                    if requested_operation is not None
                    else None
                ),
                requested_decision_kind=(
                    requested_operation.decision_kind
                    if requested_operation is not None
                    else None
                ),
                operation_availability=_operation_availability(
                    draft=draft,
                    allowed_operations=response.allowed_operations,
                ),
            )
        )

    all_prompt_lengths = [
        *[len(item) for item in chat_invoker.prompts],
        *[len(item) for item in memory_invoker.prompts],
    ]
    return ChatScenarioRunObservation(
        repetition=repetition,
        turns=turn_observations,
        memory=_memory_observation(repository, job_id=job.job_id),
        raw_message_count=repository.latest_sequence(job.job_id),
        answer_invocations=chat_invoker.calls,
        memory_invocations=memory_invoker.calls,
        degraded_turns=sum(item.memory.degraded for item in responses),
        max_prompt_chars=max(all_prompt_lengths, default=0),
        duration_ms=(time.perf_counter() - started) * 1000,
        mutation_attempts=interaction.mutation_attempts,
    )


def run_chat_eval_case(
    case: EvalCase,
    *,
    work_dir: Path,
    provider: bool,
) -> EvalObservation:
    """运行完整 Chat Scenario，并只返回有界 Observation。"""

    scenario = _load_scenario(case)
    _validate_mode(case=case, scenario=scenario, provider=provider)
    work_dir.mkdir(parents=True, exist_ok=True)
    scratch = work_dir / "_chat_scratch"
    scratch.mkdir(parents=True, exist_ok=False)

    try:
        runs = [
            _run_once(
                scenario=scenario,
                provider=provider,
                repetition=repetition,
                db_path=(scratch / f"run-{repetition}.sqlite"),
            )
            for repetition in range(1, scenario.repetitions + 1)
        ]
    finally:
        # SQLite/WAL 只用于运行隔离，不作为永久评测 Artifact。
        shutil.rmtree(scratch, ignore_errors=True)

    duration_ms = sum(item.duration_ms for item in runs)
    llm_calls = sum(
        item.answer_invocations + item.memory_invocations
        for item in runs
    )
    return EvalObservation(
        case_id=case.case_id,
        runner=case.runner,
        route=[
            "chat_eval_scenario",
            "conversation_memory",
            "chat_grounding",
            "citation_projection",
        ],
        final_status="succeeded",
        metrics=EvalMetrics(
            duration_ms=duration_ms,
            llm_calls=llm_calls,
        ),
        chat=ChatEvalObservation(
            scenario_id=scenario.scenario_id,
            mode=("provider" if provider else "offline"),
            runs=runs,
        ),
    )

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from app.execution.profile_store import (
    compute_execution_policy_hash,
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.secrets.redaction import SecretRedactor
from app.project_memory.errors import ProjectMemoryConflictError
from app.project_memory.evidence import (
    ProjectChatEvidenceReader,
    ProjectJobEvidenceReader,
    chat_message_sha256,
)
from app.project_memory.identity import (
    canonical_sha256,
    compute_content_hash,
    compute_fact_hash,
    compute_project_hash,
    new_fact_id,
    new_project_id,
)
from app.project_memory.schemas import (
    ChatFactProposalRequest,
    ChatUserMessageFactSource,
    DatasetBindingFactValue,
    ExecutionProfileDraftValue,
    ExecutionProfileFactValue,
    FactConfirmRequest,
    FactCorrectRequest,
    FactTerminalRequest,
    ManualFactProposalRequest,
    ManualUserFactSource,
    ProjectArchiveRequest,
    ProjectBindJobRequest,
    ProjectCreateRequest,
    ProjectFactConfirmation,
    ProjectFactContent,
    ProjectFactCorrectionResponse,
    ProjectFactDraftContent,
    ProjectFactMutationResponse,
    ProjectFactRecord,
    ProjectJobBinding,
    ProjectMutationResponse,
    ProjectRecord,
    TextFactValue,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_key(value: str) -> str:
    key = value.strip()
    if not key or len(key) > 300:
        raise ValueError("Idempotency-Key 长度必须为 1..300")
    return key


def _operation(kind: str, key: str) -> str:
    return f"phase46:{kind}:{_required_key(key)}"


def _request_hash(value) -> str:
    return canonical_sha256(value.model_dump(mode="json"))


def _normalized_expiry(value: str | None, *, now: str) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        current = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("expires_at 必须是 ISO-8601 时间") from exc
    if parsed.tzinfo is None or current.tzinfo is None:
        raise ValueError("expires_at 和 clock 必须包含时区")
    parsed = parsed.astimezone(timezone.utc)
    current = current.astimezone(timezone.utc)
    if parsed <= current:
        raise ValueError("expires_at 必须晚于当前时间")
    # 统一 UTC 格式后，SQLite 文本比较才具有稳定时间顺序。
    return parsed.isoformat()


def _with_project_hash(project: ProjectRecord) -> ProjectRecord:
    raw = project.model_dump(mode="json")
    raw["record_hash"] = "0" * 64
    draft = ProjectRecord.model_validate(raw)
    raw["record_hash"] = compute_project_hash(draft)
    return ProjectRecord.model_validate(raw)


def _with_fact_hash(fact: ProjectFactRecord) -> ProjectFactRecord:
    raw = fact.model_dump(mode="json")
    raw["record_hash"] = "0" * 64
    draft = ProjectFactRecord.model_validate(raw)
    raw["record_hash"] = compute_fact_hash(draft)
    return ProjectFactRecord.model_validate(raw)


class ProjectMemoryService:
    def __init__(
        self,
        *,
        repository,
        jobs: ProjectJobEvidenceReader,
        chats: ProjectChatEvidenceReader,
        retriever,
        redactor: SecretRedactor,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.repository = repository
        self.jobs = jobs
        self.chats = chats
        self.retriever = retriever
        self.redactor = redactor
        self.clock = clock
        self.repository.initialize()

    def ping(self) -> None:
        self.repository.ping()

    def _clean(self, value: str, *, limit: int) -> str:
        cleaned = self.redactor.redact_text(value, max_chars=limit).strip()
        if not cleaned:
            raise ValueError("Project Memory 文本脱敏后不能为空")
        return cleaned

    def _normalize_content(
        self,
        draft: ProjectFactDraftContent,
    ) -> ProjectFactContent:
        value = draft.value
        if isinstance(value, TextFactValue):
            normalized = TextFactValue(
                text=self._clean(value.text, limit=2000)
            )
        elif isinstance(value, DatasetBindingFactValue):
            # required_worker_label 是受信任能力标签，不允许写绝对路径。
            if value.required_worker_label.startswith("/"):
                raise ValueError("dataset_binding 不能保存绝对路径")
            normalized = DatasetBindingFactValue(
                dataset_name=self._clean(value.dataset_name, limit=200),
                required_worker_label=self._clean(
                    value.required_worker_label,
                    limit=200,
                ),
                fingerprint=(
                    self._clean(value.fingerprint, limit=300)
                    if value.fingerprint
                    else None
                ),
            )
        elif isinstance(value, ExecutionProfileDraftValue):
            profile = get_execution_profile(value.profile_id)
            normalized = ExecutionProfileFactValue(
                profile_id=profile.profile_id,
                profile_fingerprint=compute_execution_profile_fingerprint(profile),
                execution_policy_hash=compute_execution_policy_hash(profile),
            )
        else:
            # BooleanFactValue 没有动态文本，也不需要重写。
            normalized = value

        return ProjectFactContent(
            category=draft.category,
            key=draft.key,
            value=normalized,
        )

    def create_project(
        self,
        *,
        request: ProjectCreateRequest,
        idempotency_key: str,
        actor: str,
    ) -> ProjectMutationResponse:
        snapshot = self.jobs.read(request.anchor_job_id)
        anchor = snapshot.anchor
        if anchor.job_version != request.expected_anchor_job_version:
            raise ProjectMemoryConflictError("Anchor Job version 已变化")
        if anchor.workspace_manifest_hash != request.expected_workspace_manifest_hash:
            raise ProjectMemoryConflictError("Anchor Workspace Manifest hash 已变化")

        now = self.clock()
        project = _with_project_hash(
            ProjectRecord(
                project_id=new_project_id(),
                display_name=self._clean(request.display_name, limit=200),
                status="active",
                anchor=anchor,
                version=0,
                record_hash="0" * 64,
                created_by=actor,
                created_at=now,
                updated_at=now,
            )
        )
        binding = ProjectJobBinding(
            project_id=project.project_id,
            job_id=anchor.job_id,
            job_version_at_binding=anchor.job_version,
            run_id=anchor.run_id,
            workspace_manifest_id=anchor.workspace_manifest_id,
            workspace_manifest_hash=anchor.workspace_manifest_hash,
            paper_sha256=anchor.paper_sha256,
            repository_commit=anchor.repository_commit,
            role="anchor",
            bound_by=actor,
            bound_at=now,
        )
        saved, replayed = self.repository.create_project(
            project=project,
            anchor_binding=binding,
            operation_key=_operation("create_project", idempotency_key),
            request_hash=_request_hash(request),
        )
        return ProjectMutationResponse(project=saved, replayed=replayed)

    def archive_project(
        self,
        *,
        project_id: str,
        request: ProjectArchiveRequest,
        idempotency_key: str,
        actor: str,
    ) -> ProjectMutationResponse:
        current = self.repository.get_project(project_id)
        if current.status != "active":
            raise ProjectMemoryConflictError("Project 已经 archived")
        now = self.clock()
        archived = _with_project_hash(
            ProjectRecord.model_validate(
                {
                    **current.model_dump(mode="json"),
                    "status": "archived",
                    "version": current.version + 1,
                    "archived_reason": self._clean(request.reason, limit=1000),
                    "updated_at": now,
                    "record_hash": "0" * 64,
                }
            )
        )
        saved, replayed = self.repository.archive_project(
            project=archived,
            expected_version=request.expected_version,
            expected_hash=request.expected_record_hash,
            operation_key=_operation("archive_project", idempotency_key),
            request_hash=_request_hash(request),
        )
        return ProjectMutationResponse(project=saved, replayed=replayed)

    def bind_job(
        self,
        *,
        project_id: str,
        request: ProjectBindJobRequest,
        expected_project_version: int,
        expected_project_hash: str,
        idempotency_key: str,
        actor: str,
    ) -> ProjectJobBinding:
        project = self.repository.get_project(project_id)
        if project.status != "active":
            raise ProjectMemoryConflictError("不能向 archived project 绑定 Job")
        snapshot = self.jobs.read(request.job_id)
        anchor = snapshot.anchor
        if anchor.job_version != request.expected_job_version:
            raise ProjectMemoryConflictError("待绑定 Job version 已变化")
        if anchor.workspace_manifest_hash != request.expected_workspace_manifest_hash:
            raise ProjectMemoryConflictError("待绑定 Workspace Manifest hash 已变化")
        if anchor.paper_sha256 != project.anchor.paper_sha256:
            raise ProjectMemoryConflictError("待绑定 Job 使用了不同论文内容")

        binding = ProjectJobBinding(
            project_id=project_id,
            job_id=anchor.job_id,
            job_version_at_binding=anchor.job_version,
            run_id=anchor.run_id,
            workspace_manifest_id=anchor.workspace_manifest_id,
            workspace_manifest_hash=anchor.workspace_manifest_hash,
            paper_sha256=anchor.paper_sha256,
            repository_commit=anchor.repository_commit,
            role="member",
            bound_by=actor,
            bound_at=self.clock(),
        )
        saved, _ = self.repository.bind_job(
            binding=binding,
            expected_project_version=expected_project_version,
            expected_project_hash=expected_project_hash,
            operation_key=_operation("bind_job", idempotency_key),
            request_hash=_request_hash(request),
        )
        return saved

    def _proposal(
        self,
        *,
        project_id: str,
        content: ProjectFactContent,
        source,
        expires_at: str | None,
    ) -> ProjectFactRecord:
        project = self.repository.get_project(project_id)
        if project.status != "active":
            raise ProjectMemoryConflictError("archived project 不能新增 fact")
        now = self.clock()
        normalized_expiry = _normalized_expiry(expires_at, now=now)
        return _with_fact_hash(
            ProjectFactRecord(
                fact_id=new_fact_id(),
                project_id=project_id,
                version=0,
                status="proposed",
                authority="unconfirmed_proposal",
                content=content,
                content_hash=compute_content_hash(content),
                source=source,
                expires_at=normalized_expiry,
                created_at=now,
                updated_at=now,
                record_hash="0" * 64,
            )
        )

    def propose_manual(
        self,
        *,
        project_id: str,
        request: ManualFactProposalRequest,
        idempotency_key: str,
        actor: str,
    ) -> ProjectFactMutationResponse:
        content = self._normalize_content(request.content)
        source = ManualUserFactSource(
            actor=actor,
            source_note=self._clean(request.source_note, limit=1000),
            request_sha256=_request_hash(request),
        )
        fact = self._proposal(
            project_id=project_id,
            content=content,
            source=source,
            expires_at=request.expires_at,
        )
        saved, replayed = self.repository.create_fact(
            fact=fact,
            operation_key=_operation("propose_manual", idempotency_key),
            request_hash=_request_hash(request),
        )
        return ProjectFactMutationResponse(fact=saved, replayed=replayed)

    def propose_from_chat(
        self,
        *,
        project_id: str,
        request: ChatFactProposalRequest,
        idempotency_key: str,
        actor: str,
    ) -> ProjectFactMutationResponse:
        bound = self.repository.project_for_job(request.source_job_id)
        if bound is None or bound.project_id != project_id:
            raise ProjectMemoryConflictError("Chat source Job 未绑定当前 Project")
        message = self.chats.message_at(
            job_id=request.source_job_id,
            sequence=request.source_message_sequence,
        )
        if message.role != "user":
            raise ProjectMemoryConflictError("只允许 role=user 消息作为事实来源")
        actual_hash = chat_message_sha256(message)
        if message.message_id != request.expected_message_id:
            raise ProjectMemoryConflictError("Chat message_id 已变化")
        if actual_hash != request.expected_message_sha256:
            raise ProjectMemoryConflictError("Chat message hash 已变化")

        content = self._normalize_content(request.content)
        source = ChatUserMessageFactSource(
            actor=actor,
            job_id=message.job_id,
            message_id=message.message_id,
            message_sequence=message.sequence,
            message_sha256=actual_hash,
        )
        fact = self._proposal(
            project_id=project_id,
            content=content,
            source=source,
            expires_at=request.expires_at,
        )
        saved, replayed = self.repository.create_fact(
            fact=fact,
            operation_key=_operation("propose_chat", idempotency_key),
            request_hash=_request_hash(request),
        )
        return ProjectFactMutationResponse(fact=saved, replayed=replayed)

    def confirm(
        self,
        *,
        fact_id: str,
        request: FactConfirmRequest,
        idempotency_key: str,
        actor: str,
    ) -> ProjectFactMutationResponse:
        current = self.repository.get_fact(fact_id)
        if current.status != "proposed":
            raise ProjectMemoryConflictError("只有 proposed fact 可以 confirm")
        now = self.clock()
        if current.expires_at is not None and current.expires_at <= now:
            raise ProjectMemoryConflictError("已到期 proposal 不能 confirm")
        updated = _with_fact_hash(
            ProjectFactRecord.model_validate(
                {
                    **current.model_dump(mode="json"),
                    "version": current.version + 1,
                    "status": "confirmed",
                    "authority": "explicit_user",
                    "confirmation": {
                        "actor": actor,
                        "reason": self._clean(request.reason, limit=1000),
                        "confirmed_at": now,
                    },
                    "updated_at": now,
                    "record_hash": "0" * 64,
                }
            )
        )
        saved, replayed = self.repository.replace_fact(
            fact=updated,
            expected_version=request.expected_version,
            expected_hash=request.expected_record_hash,
            operation_key=_operation("confirm", idempotency_key),
            request_hash=_request_hash(request),
        )
        return ProjectFactMutationResponse(fact=saved, replayed=replayed)

    def _terminal_transition(
        self,
        *,
        fact_id: str,
        request: FactTerminalRequest,
        target_status: str,
        allowed_from: set[str],
        idempotency_key: str,
        actor: str,
    ) -> ProjectFactMutationResponse:
        current = self.repository.get_fact(fact_id)
        if current.status not in allowed_from:
            raise ProjectMemoryConflictError(
                f"{current.status} 不能转换为 {target_status}"
            )
        now = self.clock()
        raw = current.model_dump(mode="json")
        prior_events = list(raw.get("prior_terminal_events") or [])
        if raw.get("terminal_event") is not None:
            # delete terminal fact 时保留 revoke/expire/supersede 事件。
            prior_events.append(raw["terminal_event"])
        raw.update(
            {
                "version": current.version + 1,
                "status": target_status,
                "terminal_event": {
                    "status": target_status,
                    "actor": actor,
                    "reason": self._clean(request.reason, limit=1000),
                    "occurred_at": now,
                },
                "prior_terminal_events": prior_events,
                "updated_at": now,
                "record_hash": "0" * 64,
            }
        )
        if target_status == "deleted":
            # content_hash 继续证明被删除内容的旧身份，但正文清空。
            raw["content"] = None
        updated = _with_fact_hash(ProjectFactRecord.model_validate(raw))
        saved, replayed = self.repository.replace_fact(
            fact=updated,
            expected_version=request.expected_version,
            expected_hash=request.expected_record_hash,
            operation_key=_operation(target_status, idempotency_key),
            request_hash=_request_hash(request),
        )
        return ProjectFactMutationResponse(fact=saved, replayed=replayed)

    def revoke(self, **kwargs) -> ProjectFactMutationResponse:
        return self._terminal_transition(
            target_status="revoked",
            allowed_from={"proposed", "confirmed"},
            **kwargs,
        )

    def delete(self, **kwargs) -> ProjectFactMutationResponse:
        return self._terminal_transition(
            target_status="deleted",
            allowed_from={"proposed", "superseded", "revoked", "expired"},
            **kwargs,
        )

    def correct(
        self,
        *,
        fact_id: str,
        request: FactCorrectRequest,
        idempotency_key: str,
        actor: str,
    ) -> ProjectFactCorrectionResponse:
        current = self.repository.get_fact(fact_id)
        if current.status != "confirmed" or current.content is None:
            raise ProjectMemoryConflictError("只有 confirmed fact 可以 correct")

        new_content = self._normalize_content(request.content)
        # Correction 必须留在同一个 slot；改 category/key 应新建 proposal。
        if (
            new_content.category != current.content.category
            or new_content.key != current.content.key
        ):
            raise ProjectMemoryConflictError("Correction 不能改变 category/key")

        now = self.clock()
        normalized_expiry = _normalized_expiry(
            request.expires_at,
            now=now,
        )
        successor_id = new_fact_id()
        reason = self._clean(request.reason, limit=1000)

        old_raw = current.model_dump(mode="json")
        old_raw.update(
            {
                "version": current.version + 1,
                "status": "superseded",
                "superseded_by_fact_id": successor_id,
                "terminal_event": {
                    "status": "superseded",
                    "actor": actor,
                    "reason": reason,
                    "occurred_at": now,
                },
                "updated_at": now,
                "record_hash": "0" * 64,
            }
        )
        previous = _with_fact_hash(ProjectFactRecord.model_validate(old_raw))

        successor = _with_fact_hash(
            ProjectFactRecord(
                fact_id=successor_id,
                project_id=current.project_id,
                version=0,
                status="confirmed",
                authority="explicit_user",
                content=new_content,
                content_hash=compute_content_hash(new_content),
                source=ManualUserFactSource(
                    actor=actor,
                    source_note=f"Correction of {current.fact_id}: {reason}",
                    request_sha256=_request_hash(request),
                ),
                confirmation=ProjectFactConfirmation(
                    actor=actor,
                    reason=reason,
                    confirmed_at=now,
                ),
                supersedes_fact_id=current.fact_id,
                supersedes_record_hash=current.record_hash,
                expires_at=normalized_expiry,
                created_at=now,
                updated_at=now,
                record_hash="0" * 64,
            )
        )
        return self.repository.replace_with_successor(
            previous=previous,
            successor=successor,
            expected_version=request.expected_version,
            expected_hash=request.expected_record_hash,
            operation_key=_operation("correct", idempotency_key),
            request_hash=_request_hash(request),
        )

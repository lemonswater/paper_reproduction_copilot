from __future__ import annotations

from pathlib import Path
from typing import Any

from app.interaction.policy import (
    allowed_operations,
    decision_to_resume_value,
    normalize_decision_against_record,
    validate_decision,
)
from app.interaction.schemas import (
    CancelEnvelope,
    DecisionEnvelope,
    EventView,
    JobCreateRequest,
    JobMutationResponse,
    JobView,
    LogTailResponse,
    PublicInterrupt,
    PublicJobInput,
    PublicJobResult,
)
from app.job_runtime.errors import (
    JobConflictError,
)
from app.job_runtime.schemas import (
    JobRecord,
    JobRequest,
)
from app.job_runtime.service import JobService

_REDACTED_KEYS = {
    "absolute_path",
    "claim_token",
    "run_dir",
    "patch_path",
    "worktree_path",
    "input_path",
}

_SECRET_KEY_PARTS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
}


def _public_value(value: Any) -> Any:
    """递归移除运行时内部路径和常见 secret 字段。"""

    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if (
                lowered in _REDACTED_KEYS
                or any(
                    part in lowered
                    for part in _SECRET_KEY_PARTS
                )
            ):
                result[key] = "[redacted]"
            else:
                result[key] = _public_value(
                    raw_value
                )
        return result

    if isinstance(value, list):
        return [
            _public_value(item)
            for item in value
        ]

    return value


def _public_result(
    record: JobRecord,
) -> PublicJobResult | None:
    if record.result is None:
        return None
    return PublicJobResult(
        final_status=record.result.get(
            "final_status"
        ),
        stage_error_count=record.result.get(
            "stage_error_count"
        ),
        output_file_count=record.result.get(
            "output_file_count"
        ),
    )


def _public_input_name(
    *,
    local_path: str | None,
    resource: Any | None,
    fallback: str,
) -> str:
    """Resource Job 允许 local_path=None；避免 Path(None) 报错。

    公开视图只展示稳定 Resource ID，不泄露 object key 或本机物化路径。
    """

    if local_path:
        return Path(local_path).name
    if resource is not None:
        return f"{resource.kind}:{resource.resource_id}"
    return fallback


def _public_job_input(record: JobRecord) -> PublicJobInput:
    """安全投影 Job 输入；派生 Job 只展示 lineage，不泄露父绝对路径。"""

    derived = record.request.derived_run
    if derived is not None:
        parent = derived.source.parent_job_id
        return PublicJobInput(
            paper_name="derived:parent-paper",
            repo_name="derived:parent-repository",
            experiment_goal=record.request.experiment_goal,
            execution_profile_id=record.request.execution_profile_id,
            derived_from_job_id=parent,
        )
    return PublicJobInput(
        paper_name=_public_input_name(
            local_path=record.request.paper_path,
            resource=record.request.paper_resource,
            fallback="paper",
        ),
        repo_name=_public_input_name(
            local_path=record.request.repo_path,
            resource=record.request.repo_resource,
            fallback="repository",
        ),
        experiment_goal=record.request.experiment_goal,
        execution_profile_id=record.request.execution_profile_id,
    )


def _required_idempotency_key(
    value: str,
) -> str:
    """规范化并拒绝空白或过长的写请求幂等键。"""

    key = value.strip()
    if not key or len(key) > 300:
        raise ValueError(
            "Idempotency-Key 长度必须为 1..300"
        )
    return key


def project_job(record: JobRecord) -> JobView:
    """
    JobRecord 是内部模型；JobView 是公开模型。

    禁止使用 record.model_dump() 再排除几个字段，因为以后 JobRecord 新增
    secret 字段时可能被默认暴露。这里采用显式 allowlist。
    """

    return JobView(
        job_id=record.job_id,
        thread_id=record.thread_id,
        run_id=record.run_id,
        status=record.status,
        version=record.version,
        attempt_count=record.attempt_count,
        max_attempts=record.max_attempts,
        wait_generation=record.wait_generation,
        interrupt_nodes=list(
            record.interrupt_nodes
        ),
        interrupts=[
            PublicInterrupt(
                node=item.node,
                interrupt_id=item.interrupt_id,
                value_preview=_public_value(
                    item.value_preview
                ),
            )
            for item in record.interrupts
        ],
        cancel_requested=record.cancel_requested,
        cancellation_reason=(
            record.cancellation_reason
        ),
        result=_public_result(record),
        error=_public_value(record.error),
        reconciliation=_public_value(
            record.reconciliation
        ),
        input=_public_job_input(record),
        allowed_operations=(
            allowed_operations(record)
        ),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class InteractionService:
    """CLI/API 共用的交互用例层，不直接执行 SQL。"""

    def __init__(
        self,
        job_service: JobService,
        *,
        resource_service: Any | None = None,
    ):
        self.job_service = job_service
        self.resource_service = resource_service

    def _resolve_resource(
        self, resource_id: str
    ) -> Any:
        """把 resource_id 解析为 published Resource 的不可变 snapshot。"""

        if self.resource_service is None:
            raise ValueError(
                "Resource 解析未配置：缺少 ResourceService"
            )
        from app.job_runtime.schemas import (
            ResolvedResourceInput,
        )
        from app.resources.errors import (
            ResourceNotFoundError,
        )

        try:
            record = self.resource_service.get(
                resource_id
            )
        except ResourceNotFoundError as exc:
            raise ValueError(
                f"resource 不存在：{resource_id}"
            ) from exc
        if record.status != "published":
            raise ValueError(
                f"resource 未 published：{record.status}"
            )
        manifest = record.manifest
        if manifest is None:
            raise ValueError(
                "published resource 缺少 manifest"
            )
        return ResolvedResourceInput(
            resource_id=record.resource_id,
            manifest_sha256=manifest.manifest_sha256,
            object_key=manifest.object_key,
            content_sha256=manifest.sha256,
            size_bytes=manifest.size_bytes,
            kind=manifest.kind,
            git_commit=manifest.git_commit,
        )

    def create_job(
        self,
        *,
        request: JobCreateRequest,
        idempotency_key: str,
    ) -> JobMutationResponse:
        key = _required_idempotency_key(
            idempotency_key
        )
        paper_resource = (
            self._resolve_resource(request.paper_resource_id)
            if request.paper_resource_id is not None
            else None
        )
        repo_resource = (
            self._resolve_resource(request.repo_resource_id)
            if request.repo_resource_id is not None
            else None
        )
        record, created = self.job_service.submit(
            request=JobRequest(
                paper_path=request.paper_path,
                repo_path=request.repo_path,
                paper_resource=paper_resource,
                repo_resource=repo_resource,
                log_path=request.log_path,
                experiment_goal=(
                    request.experiment_goal
                ),
                execution_profile_id=(
                    request.execution_profile_id
                ),
            ),
            thread_id=request.thread_id,
            idempotency_key=key,
        )
        return JobMutationResponse(
            job=project_job(record),
            replayed=not created,
        )

    def get_job(
        self,
        job_id: str,
    ) -> JobView:
        return project_job(
            self.job_service.get(job_id)
        )

    def list_jobs(
        self,
        *,
        status: str | None,
        limit: int,
    ) -> list[JobView]:
        return [
            project_job(item)
            for item in self.job_service.list(
                status=status,
                limit=limit,
            )
        ]

    def submit_decision(
        self,
        *,
        job_id: str,
        envelope: DecisionEnvelope,
        idempotency_key: str,
        actor: str,
    ) -> JobMutationResponse:
        key = _required_idempotency_key(
            idempotency_key
        )
        current = self.job_service.get(job_id)

        # 第一层：Job、generation 和 node 身份。
        expected_node = validate_decision(
            record=current,
            envelope=envelope,
        )

        # 第二层：需要动态服务端状态的 decision 语义。
        normalized_decision = (
            normalize_decision_against_record(
                record=current,
                decision=envelope.decision,
            )
        )
        value = decision_to_resume_value(
            normalized_decision
        )

        # 只有两层校验都成功才允许 durable resume 入队。
        updated, created = (
            self.job_service.resume(
                job_id=job_id,
                expected_node=expected_node,
                value=value,
                idempotency_key=key,
                expected_job_version=(
                    envelope
                    .expected_job_version
                ),
                expected_wait_generation=(
                    envelope
                    .expected_wait_generation
                ),
                actor=actor,
            )
        )
        return JobMutationResponse(
            job=project_job(updated),
            replayed=not created,
        )

    def cancel_job(
        self,
        *,
        job_id: str,
        envelope: CancelEnvelope,
        idempotency_key: str,
        actor: str,
    ) -> JobMutationResponse:
        key = _required_idempotency_key(
            idempotency_key
        )
        updated = self.job_service.cancel(
            job_id=job_id,
            reason=envelope.reason,
            idempotency_key=key,
            expected_job_version=(
                envelope.expected_job_version
            ),
            actor=actor,
        )
        return JobMutationResponse(
            job=project_job(updated),
        )

    def events_after(
        self,
        *,
        job_id: str,
        after_event_id: int,
        limit: int,
    ) -> list[EventView]:
        return [
            EventView(
                event_id=item.event_id,
                job_id=item.job_id,
                event_type=item.event_type,
                actor=item.actor,
                payload=_public_value(
                    item.payload
                ),
                created_at=item.created_at,
            )
            for item in (
                self.job_service.events_after(
                    job_id,
                    after_event_id=(
                        after_event_id
                    ),
                    limit=limit,
                )
            )
        ]

    def tail_log(
        self,
        *,
        job_id: str,
        lines: int,
        max_bytes: int,
    ) -> LogTailResponse:
        record = self.job_service.get(job_id)
        path, content = (
            self.job_service.tail_log(
                job_id=job_id,
                lines=lines,
                max_bytes=max_bytes,
            )
        )
        if path is None:
            return LogTailResponse(
                lines=lines
            )

        run_root = Path(
            record.run_dir
        ).resolve()
        resolved = Path(path).resolve()
        if run_root not in resolved.parents:
            raise JobConflictError(
                "日志路径逃逸当前 run"
            )

        return LogTailResponse(
            relative_path=(
                resolved.relative_to(
                    run_root
                ).as_posix()
            ),
            content=content,
            lines=lines,
            truncated_by_bytes=(
                resolved.stat().st_size
                > max_bytes
            ),
        )
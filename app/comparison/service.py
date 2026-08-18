from __future__ import annotations

import hashlib
import json
import shlex
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Protocol

from app.comparison.errors import (
    ComparisonConflictError,
    ComparisonIntegrityError,
    ComparisonLimitExceededError,
    ComparisonNotFoundError,
)
from app.comparison.identity import (
    comparison_id_for_hash,
    compute_comparison_hash,
    compute_snapshot_hash,
    sha256_text,
)
from app.comparison.repository import FileComparisonRepository
from app.comparison.schemas import (
    ArtifactIdentity,
    CommandSnapshot,
    ComparisonCreateRequest,
    ComparisonEvidence,
    ComparisonListResponse,
    ComparisonReport,
    ComparisonSummary,
    DatasetIdentity,
    ErrorIdentity,
    ExecutionFacts,
    RunChange,
    RunSnapshot,
)
from app.interaction.schemas import ArtifactView
from app.job_runtime.schemas import JobRecord
from app.run_evidence.errors import (
    RunEvidenceConflictError,
    RunEvidenceIntegrityError,
    RunEvidenceLimitExceededError,
    RunEvidenceNotFoundError,
)
from app.run_evidence.reader import VerifiedRunEvidenceReader
from app.workspace.schemas import WorkspaceManifest


COMPARATOR_VERSION = "phase38-v1"
RUN_MANIFEST_PATH = "reports/run_manifest.json"
VOLATILE_ARTIFACT_PATHS = {
    "reports/run_manifest.json",
    "reports/artifact_index.json",
}
SECRET_NAMES = {
    "api-key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
}


class ComparisonJobReader(Protocol):
    """JobService.store、SqliteJobStore 和 PostgresJobStore 都满足它。"""

    def get(self, job_id: str) -> JobRecord:
        ...

    def get_workspace_manifest(self, manifest_id: str) -> WorkspaceManifest:
        ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_sensitive_option(name: str) -> bool:
    normalized = name.lower().lstrip("-").replace("_", "-")
    return any(part in normalized for part in SECRET_NAMES)


def _redact_token(token: str) -> str:
    """保留参数结构，但移除绝对路径和 option=value 中的敏感值。"""

    if "=" in token:
        name, value = token.split("=", 1)
        if _is_sensitive_option(name):
            return f"{name}=<redacted>"
        if value.startswith("/"):
            return f"{name}=<absolute-path>"
    if token.startswith("/"):
        return "<absolute-path>"
    return token


def build_command_snapshot(raw: Any) -> CommandSnapshot:
    command = str(_safe_dict(raw).get("command") or "").strip()
    if not command:
        return CommandSnapshot()

    item = _safe_dict(raw)
    cwd = str(item.get("cwd") or "")
    degraded = False
    try:
        tokens = shlex.split(command, posix=True)
        projected: list[str] = []
        redact_next = False
        for token in tokens:
            if redact_next:
                projected.append("<redacted>")
                redact_next = False
                continue
            if token.startswith("-") and "=" not in token and _is_sensitive_option(token):
                projected.append(token)
                redact_next = True
                continue
            projected.append(_redact_token(token))
        display = shlex.join(projected)
    except ValueError:
        # 引号不闭合时不尝试展示可能含 secret 的半解析内容。
        display = f"<unparseable-command sha256={sha256_text(command)[:16]}>"
        degraded = True

    return CommandSnapshot(
        present=True,
        display=display,
        command_sha256=sha256_text(command),
        cwd_sha256=sha256_text(cwd),
        source=str(item.get("source") or "unknown"),
        risk_level=str(item.get("risk_level") or "unknown"),
        parse_degraded=degraded,
    )


class ComparisonService:
    def __init__(
        self,
        *,
        evidence_reader: VerifiedRunEvidenceReader,
        repository: FileComparisonRepository,
        max_changes: int,
    ):
        self.evidence_reader = evidence_reader
        self.jobs = evidence_reader.jobs
        self.repository = repository
        self.max_changes = max_changes

    @staticmethod
    def _paper_sha256(manifest: WorkspaceManifest) -> str:
        entries = [item for item in manifest.entries if item.role == "paper"]
        if len(entries) != 1:
            raise ComparisonIntegrityError("Workspace 必须且只能包含一个 paper entry")
        return entries[0].sha256

    @staticmethod
    def _dataset_identities(manifest: WorkspaceManifest) -> list[DatasetIdentity]:
        return sorted(
            [
                DatasetIdentity(
                    name=item.name,
                    uri_sha256=sha256_text(item.uri),
                    fingerprint=item.fingerprint,
                    required_worker_label=item.required_worker_label,
                )
                for item in manifest.external_data
            ],
            key=lambda item: (item.name, item.uri_sha256),
        )

    @staticmethod
    def _error_identities(payload: dict[str, Any]) -> list[ErrorIdentity]:
        errors = _safe_list(_safe_dict(payload.get("errors")).get("items"))
        result: list[ErrorIdentity] = []
        for raw in errors:
            item = _safe_dict(raw)
            result.append(
                ErrorIdentity(
                    code=str(item.get("code") or "UNKNOWN"),
                    category=str(item.get("category") or "unknown"),
                    stage=str(item.get("stage") or "unknown"),
                    terminal=bool(item.get("terminal", True)),
                    message_sha256=sha256_text(str(item.get("message") or "")),
                )
            )
        return sorted(
            result,
            key=lambda item: (
                item.stage,
                item.code,
                item.category,
                item.message_sha256,
            ),
        )

    @staticmethod
    def _artifact_identities(views: list[ArtifactView]) -> list[ArtifactIdentity]:
        result = []
        for item in views:
            if item.relative_path in VOLATILE_ARTIFACT_PATHS:
                continue
            # Catalog 已约束 relative_path；这里额外拒绝绝对路径和 ..。
            path = PurePosixPath(item.relative_path)
            if path.is_absolute() or ".." in path.parts:
                raise ComparisonIntegrityError("Artifact relative_path 非法")
            result.append(
                ArtifactIdentity(
                    artifact_id=item.artifact_id,
                    relative_path=item.relative_path,
                    layer=item.layer,
                    media_type=item.media_type,
                    sha256=item.sha256,
                    size_bytes=item.size_bytes,
                    producer_node=item.producer_node,
                )
            )
        return sorted(result, key=lambda item: item.relative_path)

    def _snapshot(self, job_id: str) -> RunSnapshot:
        try:
            evidence = self.evidence_reader.read(job_id)
        except RunEvidenceNotFoundError as exc:
            raise ComparisonNotFoundError(str(exc)) from exc
        except RunEvidenceConflictError as exc:
            raise ComparisonConflictError(str(exc)) from exc
        except RunEvidenceIntegrityError as exc:
            raise ComparisonIntegrityError(str(exc)) from exc
        except RunEvidenceLimitExceededError as exc:
            raise ComparisonLimitExceededError(str(exc)) from exc
        job = evidence.job
        workspace = evidence.workspace
        views = list(evidence.artifacts)
        run_manifest_view = evidence.run_manifest_artifact
        manifest = evidence.run_manifest

        execution = _safe_dict(manifest.get("execution"))
        execution_result = _safe_dict(execution.get("result"))
        supervision = _safe_dict(manifest.get("execution_supervision"))
        usage = _safe_dict(supervision.get("resource_usage"))
        profile = _safe_dict(manifest.get("execution_profile"))
        smoke = _safe_dict(manifest.get("smoke_test"))
        repair = _safe_dict(manifest.get("repair"))
        file_repair = _safe_dict(manifest.get("file_repair"))

        draft = RunSnapshot(
            snapshot_hash="0" * 64,
            job_id=job.job_id,
            run_id=job.run_id,
            job_status=job.status,
            experiment_goal=job.request.experiment_goal,
            workspace_manifest_id=workspace.manifest_id,
            workspace_manifest_hash=workspace.manifest_hash,
            workspace_manifest_generation=workspace.generation,
            paper_sha256=self._paper_sha256(workspace),
            repository_commit=workspace.repository.commit_sha,
            repository_clean=workspace.repository.clean,
            datasets=self._dataset_identities(workspace),
            execution_profile_id=job.requirements.execution_profile_id,
            execution_policy_hash=job.requirements.execution_policy_hash,
            execution_backend=job.requirements.execution_backend,
            execution_profile_fingerprint=(
                str(profile.get("fingerprint")) if profile.get("fingerprint") else None
            ),
            selected_command=build_command_snapshot(manifest.get("selected_run_command")),
            execution=ExecutionFacts(
                final_status=(
                    str(manifest.get("final_status"))
                    if manifest.get("final_status") is not None
                    else None
                ),
                ok=(
                    bool(execution_result.get("ok"))
                    if execution_result.get("ok") is not None
                    else None
                ),
                returncode=execution_result.get("returncode"),
                end_reason=(
                    str(supervision.get("end_reason"))
                    if supervision.get("end_reason") is not None
                    else None
                ),
                peak_rss_bytes=usage.get("peak_rss_bytes"),
                total_cpu_seconds=usage.get("total_cpu_seconds"),
                peak_process_count=usage.get("peak_process_count"),
                total_write_bytes=usage.get("total_write_bytes"),
            ),
            smoke_test_status=(
                str(smoke.get("status")) if smoke.get("status") is not None else None
            ),
            smoke_test_passed=(
                bool(smoke.get("passed")) if smoke.get("passed") is not None else None
            ),
            repair_attempt_count=int(repair.get("attempt_count") or 0),
            file_repair_attempt_count=int(file_repair.get("attempt_count") or 0),
            errors=self._error_identities(manifest),
            artifacts=self._artifact_identities(views),
            run_manifest_artifact_id=run_manifest_view.artifact_id,
            run_manifest_sha256=run_manifest_view.sha256,
        )
        return draft.model_copy(update={"snapshot_hash": compute_snapshot_hash(draft)})

    @staticmethod
    def _job_evidence(snapshot: RunSnapshot, locator: str) -> ComparisonEvidence:
        return ComparisonEvidence(
            trust="control_plane",
            source_type="job",
            job_id=snapshot.job_id,
            run_id=snapshot.run_id,
            locator=locator,
        )

    @staticmethod
    def _workspace_evidence(snapshot: RunSnapshot, locator: str) -> ComparisonEvidence:
        return ComparisonEvidence(
            trust="control_plane",
            source_type="workspace_manifest",
            job_id=snapshot.job_id,
            run_id=snapshot.run_id,
            locator=locator,
            manifest_id=snapshot.workspace_manifest_id,
            manifest_hash=snapshot.workspace_manifest_hash,
        )

    @staticmethod
    def _manifest_evidence(snapshot: RunSnapshot, locator: str) -> ComparisonEvidence:
        return ComparisonEvidence(
            trust="verified_content",
            source_type="run_manifest",
            job_id=snapshot.job_id,
            run_id=snapshot.run_id,
            locator=locator,
            artifact_id=snapshot.run_manifest_artifact_id,
            relative_path=RUN_MANIFEST_PATH,
            sha256=snapshot.run_manifest_sha256,
        )

    @staticmethod
    def _artifact_evidence(snapshot: RunSnapshot, item: ArtifactIdentity) -> ComparisonEvidence:
        return ComparisonEvidence(
            trust="catalog_identity",
            source_type="artifact_catalog",
            job_id=snapshot.job_id,
            run_id=snapshot.run_id,
            locator=f"artifact:{item.relative_path}",
            artifact_id=item.artifact_id,
            relative_path=item.relative_path,
            sha256=item.sha256,
        )

    def _append_change(self, changes: list[RunChange], change: RunChange) -> None:
        if len(changes) >= self.max_changes:
            raise ComparisonLimitExceededError("结构化变化数量超过上限")
        changes.append(change)

    def _compare_value(
        self,
        changes: list[RunChange],
        *,
        category: str,
        field_path: str,
        base_value: Any,
        target_value: Any,
        importance: str,
        message: str,
        base_evidence: ComparisonEvidence,
        target_evidence: ComparisonEvidence,
    ) -> None:
        if base_value == target_value:
            return
        self._append_change(
            changes,
            RunChange(
                category=category,
                kind="changed",
                importance=importance,
                field_path=field_path,
                base_value=base_value,
                target_value=target_value,
                message=message,
                evidence=[base_evidence, target_evidence],
            ),
        )

    def _compare_artifacts(
        self,
        changes: list[RunChange],
        base: RunSnapshot,
        target: RunSnapshot,
    ) -> tuple[int, int, int]:
        base_map = {item.relative_path: item for item in base.artifacts}
        target_map = {item.relative_path: item for item in target.artifacts}
        added = removed = changed = 0
        for path in sorted(base_map.keys() | target_map.keys()):
            left = base_map.get(path)
            right = target_map.get(path)
            if left is None and right is not None:
                added += 1
                self._append_change(
                    changes,
                    RunChange(
                        category="artifact",
                        kind="added",
                        importance="medium",
                        field_path=f"artifacts.{path}",
                        target_value=right.model_dump(mode="json"),
                        message="Target Run 新增 Artifact。",
                        evidence=[self._artifact_evidence(target, right)],
                    ),
                )
            elif right is None and left is not None:
                removed += 1
                self._append_change(
                    changes,
                    RunChange(
                        category="artifact",
                        kind="removed",
                        importance="medium",
                        field_path=f"artifacts.{path}",
                        base_value=left.model_dump(mode="json"),
                        message="Target Run 缺少 Base Run 中的 Artifact。",
                        evidence=[self._artifact_evidence(base, left)],
                    ),
                )
            elif (
                left is not None
                and right is not None
                # artifact_id 是每个 Run 内的定位身份，不属于跨 Run 内容等价性。
                and left.model_dump(exclude={"artifact_id"})
                != right.model_dump(exclude={"artifact_id"})
            ):
                changed += 1
                self._append_change(
                    changes,
                    RunChange(
                        category="artifact",
                        kind="changed",
                        importance="medium",
                        field_path=f"artifacts.{path}",
                        base_value=left.model_dump(mode="json"),
                        target_value=right.model_dump(mode="json"),
                        message="同一相对路径的 Artifact 内容或生产身份发生变化。",
                        evidence=[
                            self._artifact_evidence(base, left),
                            self._artifact_evidence(target, right),
                        ],
                    ),
                )
        return added, removed, changed

    def create(self, request: ComparisonCreateRequest) -> ComparisonReport:
        base = self._snapshot(request.base_job_id)
        target = self._snapshot(request.target_job_id)
        warnings: list[str] = []
        if base.paper_sha256 != target.paper_sha256:
            if not request.allow_cross_paper:
                raise ComparisonConflictError(
                    "两个 Job 的 paper SHA-256 不同；如确需诊断请显式 allow_cross_paper"
                )
            warnings.append(
                "两个 Run 使用不同论文内容，本报告只能用于运行诊断，不能解释为同一实验的前后变化。"
            )

        changes: list[RunChange] = []
        base_command = base.selected_command.model_dump(mode="json")
        target_command = target.selected_command.model_dump(mode="json")
        # Raw cwd 可能只是 materialized workspace 路径不同；在没有稳定的
        # repo-relative cwd 投影前，不把它升级为用户可见命令差异。
        base_command.pop("cwd_sha256", None)
        target_command.pop("cwd_sha256", None)

        specs = [
            ("input", "paper_sha256", base.paper_sha256, target.paper_sha256, "high", "论文输入身份发生变化。", "workspace"),
            ("input", "experiment_goal", base.experiment_goal, target.experiment_goal, "medium", "实验目标发生变化。", "job"),
            ("input", "datasets", [x.model_dump(mode="json") for x in base.datasets], [x.model_dump(mode="json") for x in target.datasets], "high", "外部数据引用身份发生变化。", "workspace"),
            ("repository", "repository.commit", base.repository_commit, target.repository_commit, "high", "仓库 commit 发生变化。", "workspace"),
            ("repository", "repository.clean", base.repository_clean, target.repository_clean, "medium", "仓库 clean 状态发生变化。", "workspace"),
            ("environment", "execution.profile_id", base.execution_profile_id, target.execution_profile_id, "high", "Execution Profile 发生变化。", "job"),
            ("environment", "execution.policy_hash", base.execution_policy_hash, target.execution_policy_hash, "high", "执行策略身份发生变化。", "job"),
            ("environment", "execution.backend", base.execution_backend, target.execution_backend, "high", "执行后端发生变化。", "job"),
            ("environment", "execution.profile_fingerprint", base.execution_profile_fingerprint, target.execution_profile_fingerprint, "high", "运行环境指纹发生变化。", "manifest"),
            ("command", "selected_command", base_command, target_command, "high", "实际选择命令的脱敏投影或内容 hash 发生变化。", "manifest"),
            ("execution", "job_status", base.job_status, target.job_status, "high", "Job 最终状态发生变化。", "job"),
            ("execution", "execution", base.execution.model_dump(mode="json"), target.execution.model_dump(mode="json"), "high", "执行结果或资源观测发生变化。", "manifest"),
            ("execution", "smoke_test.status", [base.smoke_test_status, base.smoke_test_passed], [target.smoke_test_status, target.smoke_test_passed], "medium", "Smoke Test 结果发生变化。", "manifest"),
            ("repair", "repair.attempt_count", base.repair_attempt_count, target.repair_attempt_count, "medium", "调试修复次数发生变化。", "manifest"),
            ("repair", "file_repair.attempt_count", base.file_repair_attempt_count, target.file_repair_attempt_count, "medium", "文件修复次数发生变化。", "manifest"),
            ("error", "errors", [x.model_dump(mode="json") for x in base.errors], [x.model_dump(mode="json") for x in target.errors], "high", "结构化错误身份集合发生变化。", "manifest"),
        ]
        for category, field_path, left, right, importance, message, source in specs:
            evidence_builder = {
                "job": self._job_evidence,
                "workspace": self._workspace_evidence,
                "manifest": self._manifest_evidence,
            }[source]
            self._compare_value(
                changes,
                category=category,
                field_path=field_path,
                base_value=left,
                target_value=right,
                importance=importance,
                message=message,
                base_evidence=evidence_builder(base, field_path),
                target_evidence=evidence_builder(target, field_path),
            )

        artifact_added, artifact_removed, artifact_changed = self._compare_artifacts(
            changes, base, target
        )
        changes.sort(key=lambda item: (item.category, item.field_path, item.kind))
        summary = ComparisonSummary(
            change_count=len(changes),
            high_count=sum(item.importance == "high" for item in changes),
            medium_count=sum(item.importance == "medium" for item in changes),
            low_count=sum(item.importance == "low" for item in changes),
            changed_categories=sorted({item.category for item in changes}),
            artifact_added=artifact_added,
            artifact_removed=artifact_removed,
            artifact_changed=artifact_changed,
            scope_warnings=warnings,
        )
        draft = ComparisonReport(
            comparator_version=COMPARATOR_VERSION,
            comparison_id="comparison_" + "0" * 24,
            comparison_hash="0" * 64,
            created_at=utc_now(),
            allow_cross_paper=request.allow_cross_paper,
            base=base,
            target=target,
            summary=summary,
            changes=changes,
        )
        comparison_hash = compute_comparison_hash(draft)
        report = draft.model_copy(
            update={
                "comparison_hash": comparison_hash,
                "comparison_id": comparison_id_for_hash(comparison_hash),
            }
        )
        return self.repository.save(report)

    def get(self, comparison_id: str) -> ComparisonReport:
        return self.repository.get(comparison_id)

    def list_for_job(self, job_id: str, *, limit: int = 100) -> ComparisonListResponse:
        # 先验证 Job 存在，避免"未知 Job"和"暂时没有 Comparison"语义混淆。
        self.jobs.get(job_id)
        return self.repository.list_for_job(job_id, limit=limit)

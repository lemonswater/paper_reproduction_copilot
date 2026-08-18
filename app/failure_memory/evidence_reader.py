from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.authority.schemas import ExecutionVerificationRecord
from app.failure_memory.errors import (
    FailureCaseConflictError,
    FailureCaseIntegrityError,
    FailureCaseLimitExceededError,
)
from app.failure_memory.schemas import (
    FailureEnvironmentIdentity,
    FailureEvidenceReference,
    FailureSourceIdentity,
)
from app.interaction.artifacts import ArtifactCatalog
from app.interaction.schemas import ArtifactView
from app.observability.redaction import sanitize_error_message
from app.run_evidence.reader import VerifiedRunEvidenceReader
from app.run_evidence.schemas import VerifiedRunEvidence
from app.schemas import DebugReport, StageError
from app.tools.log_tools import extract_traceback


ERROR_REPORT_PATH = "reports/error_report.json"
DEBUG_REPORT_PATH = "debug/debug_report.json"
EXECUTION_VERIFICATION_PATH = (
    "execution/execution_verification.json"
)


@dataclass(frozen=True)
class FailureEvidenceSnapshot:
    """Service 内部对象，不直接作为 API response。"""

    verified_run: VerifiedRunEvidence
    source: FailureSourceIdentity
    stage_error: StageError
    debug_report: DebugReport | None
    execution_verification: ExecutionVerificationRecord | None
    traceback_text: str


class FailureEvidenceReader:
    def __init__(
        self,
        *,
        verified_runs: VerifiedRunEvidenceReader,
        artifact_catalog: ArtifactCatalog,
        max_json_bytes: int,
        max_log_bytes: int,
    ) -> None:
        self.verified_runs = verified_runs
        self.artifact_catalog = artifact_catalog
        self.max_json_bytes = max_json_bytes
        self.max_log_bytes = max_log_bytes

    @staticmethod
    def _by_path(
        evidence: VerifiedRunEvidence,
    ) -> dict[str, ArtifactView]:
        return {
            item.relative_path: item
            for item in evidence.artifacts
        }

    def _read_bytes(
        self,
        *,
        evidence: VerifiedRunEvidence,
        view: ArtifactView,
        max_bytes: int,
    ) -> bytes:
        if view.size_bytes > max_bytes:
            raise FailureCaseLimitExceededError(
                f"Artifact 超过 Failure Memory 读取上限："
                f"{view.relative_path}"
            )

        opened = self.artifact_catalog.open(
            job=evidence.job,
            artifact_id=view.artifact_id,
        )
        try:
            descriptor = opened.artifact.descriptor
            stat = opened.blob.stat
            if not (
                descriptor.artifact_id == view.artifact_id
                and descriptor.relative_path == view.relative_path
                and descriptor.run_id == evidence.job.run_id
                and descriptor.sha256 == view.sha256
                and descriptor.size_bytes == view.size_bytes
                and stat.sha256 == view.sha256
                and stat.size_bytes == view.size_bytes
            ):
                raise FailureCaseIntegrityError(
                    "Catalog、Descriptor 与 Blob 身份不一致"
                )
            raw = opened.blob.body.read(max_bytes + 1)
        finally:
            opened.blob.body.close()

        if len(raw) != view.size_bytes or len(raw) > max_bytes:
            raise FailureCaseIntegrityError(
                f"Artifact 读取大小不一致：{view.relative_path}"
            )
        if hashlib.sha256(raw).hexdigest() != view.sha256:
            raise FailureCaseIntegrityError(
                f"Artifact SHA-256 不一致：{view.relative_path}"
            )
        return raw

    def _read_json(
        self,
        *,
        evidence: VerifiedRunEvidence,
        view: ArtifactView,
    ) -> dict[str, Any]:
        raw = self._read_bytes(
            evidence=evidence,
            view=view,
            max_bytes=self.max_json_bytes,
        )
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FailureCaseIntegrityError(
                f"Artifact 不是有效 JSON：{view.relative_path}"
            ) from exc
        if not isinstance(payload, dict):
            raise FailureCaseIntegrityError(
                f"Artifact 顶层不是 object：{view.relative_path}"
            )
        return payload

    @staticmethod
    def _reference(
        view: ArtifactView,
        *,
        purpose: str,
    ) -> FailureEvidenceReference:
        return FailureEvidenceReference(
            purpose=purpose,
            artifact_id=view.artifact_id,
            relative_path=view.relative_path,
            sha256=view.sha256,
            size_bytes=view.size_bytes,
        )

    @staticmethod
    def _select_stage_error(
        run_manifest: dict[str, Any],
    ) -> StageError:
        raw_errors = (
            run_manifest.get("errors", {}).get("items", [])
            if isinstance(run_manifest.get("errors"), dict)
            else []
        )
        try:
            errors = [StageError.model_validate(item) for item in raw_errors]
        except ValidationError as exc:
            raise FailureCaseIntegrityError(
                "run_manifest 中的 StageError 无效"
            ) from exc

        terminal = [item for item in errors if item.terminal]
        selected = terminal[-1] if terminal else (errors[-1] if errors else None)
        if selected is None:
            raise FailureCaseConflictError(
                "源 Run 没有结构化 StageError，不能创建失败案例"
            )
        return selected

    @staticmethod
    def _require_failed_semantics(
        evidence: VerifiedRunEvidence,
    ) -> None:
        manifest = evidence.run_manifest
        final_status = str(manifest.get("final_status") or "")
        raw_verification = (
            manifest.get("execution", {}).get("verification")
            if isinstance(manifest.get("execution"), dict)
            else None
        )
        verdict = (
            raw_verification.get("verdict")
            if isinstance(raw_verification, dict)
            else None
        )
        raw_errors = (
            manifest.get("errors", {}).get("items", [])
            if isinstance(manifest.get("errors"), dict)
            else []
        )
        has_terminal_error = any(
            isinstance(item, dict) and item.get("terminal") is True
            for item in raw_errors
        )

        # Job status=succeeded 可能只表示 Graph 正常走到终点，所以看业务事实。
        if (
            final_status == "succeeded"
            and verdict != "failed"
            and not has_terminal_error
        ):
            raise FailureCaseConflictError(
                "源 Run 没有可验证的失败语义"
            )

    def _optional_typed_artifact(
        self,
        *,
        evidence: VerifiedRunEvidence,
        path: str,
        schema,
    ):
        view = self._by_path(evidence).get(path)
        if view is None:
            return None, None
        payload = self._read_json(evidence=evidence, view=view)
        try:
            return schema.model_validate(payload), view
        except ValidationError as exc:
            raise FailureCaseIntegrityError(
                f"Artifact schema 无效：{path}"
            ) from exc

    def _read_combined_log(
        self,
        *,
        evidence: VerifiedRunEvidence,
    ) -> tuple[str, ArtifactView | None]:
        """只读取 Evidence 绑定且容量受限的 combined.log。"""

        raw_execution = evidence.run_manifest.get("execution")
        raw_evidence = (
            raw_execution.get("evidence")
            if isinstance(raw_execution, dict)
            else None
        )
        artifact_ids = set(
            raw_evidence.get("artifact_ids", [])
            if isinstance(raw_evidence, dict)
            else []
        )
        candidates = [
            item
            for item in evidence.artifacts
            if item.artifact_id in artifact_ids
            and item.relative_path.endswith("/combined.log")
        ]
        if len(candidates) != 1:
            return "", None
        view = candidates[0]
        if view.size_bytes > self.max_log_bytes:
            # 大日志不阻止 candidate；只是不复制 traceback 摘要。
            return "", None
        raw = self._read_bytes(
            evidence=evidence,
            view=view,
            max_bytes=self.max_log_bytes,
        )
        text = raw.decode("utf-8", errors="replace")
        return sanitize_error_message(text, max_chars=self.max_log_bytes), view

    def read(self, job_id: str) -> FailureEvidenceSnapshot:
        evidence = self.verified_runs.read(job_id)
        self._require_failed_semantics(evidence)
        by_path = self._by_path(evidence)

        debug_report, debug_view = self._optional_typed_artifact(
            evidence=evidence,
            path=DEBUG_REPORT_PATH,
            schema=DebugReport,
        )
        execution_verification, verification_view = (
            self._optional_typed_artifact(
                evidence=evidence,
                path=EXECUTION_VERIFICATION_PATH,
                schema=ExecutionVerificationRecord,
            )
        )

        # 若存在独立 verification artifact，其 verdict 必须与失败语义一致。
        if (
            execution_verification is not None
            and execution_verification.verdict == "verified"
        ):
            raise FailureCaseConflictError(
                "源 Run 的独立 Execution Verification 是成功，不能作为执行失败案例"
            )

        log_text, log_view = self._read_combined_log(
            evidence=evidence,
        )
        stage_error = self._select_stage_error(evidence.run_manifest)

        references = [
            self._reference(
                evidence.run_manifest_artifact,
                purpose="run_manifest",
            )
        ]
        error_view = by_path.get(ERROR_REPORT_PATH)
        if error_view is not None:
            # 读取一次以验证 JSON，而不是只相信 Catalog path。
            self._read_json(evidence=evidence, view=error_view)
            references.append(
                self._reference(error_view, purpose="error_report")
            )
        if debug_view is not None:
            references.append(
                self._reference(debug_view, purpose="debug_report")
            )
        if verification_view is not None:
            references.append(
                self._reference(
                    verification_view,
                    purpose="execution_verification",
                )
            )
        if log_view is not None:
            references.append(
                self._reference(log_view, purpose="process_log")
            )

        raw_execution = evidence.run_manifest.get("execution")
        raw_exec_evidence = (
            raw_execution.get("evidence")
            if isinstance(raw_execution, dict)
            else {}
        )
        # Phase 45 严格性：缺少 fingerprint 时 fail closed，不接受 "unknown"。
        fingerprint = (
            evidence.run_manifest.get("execution_profile", {}).get(
                "fingerprint"
            )
            or raw_exec_evidence.get(
                "execution_profile_fingerprint"
            )
        )
        if not isinstance(fingerprint, str) or not fingerprint:
            raise FailureCaseConflictError(
                "源 Run 缺少 Execution Profile fingerprint"
            )
        environment = FailureEnvironmentIdentity(
            execution_profile_id=(
                evidence.job.request.execution_profile_id
            ),
            execution_profile_fingerprint=fingerprint,
            execution_backend=evidence.job.requirements.execution_backend,
            repository_commit=evidence.workspace.repository.commit_sha,
            repository_clean=evidence.workspace.repository.clean,
        )
        source = FailureSourceIdentity(
            job_id=evidence.job.job_id,
            job_version=evidence.job.version,
            run_id=evidence.job.run_id,
            workspace_manifest_id=evidence.workspace.manifest_id,
            workspace_manifest_hash=evidence.workspace.manifest_hash,
            run_manifest_artifact_id=(
                evidence.run_manifest_artifact.artifact_id
            ),
            run_manifest_sha256=evidence.run_manifest_artifact.sha256,
            final_status=str(
                evidence.run_manifest.get("final_status") or "unknown"
            ),
            environment=environment,
            evidence=references,
        )
        return FailureEvidenceSnapshot(
            verified_run=evidence,
            source=source,
            stage_error=stage_error,
            debug_report=debug_report,
            execution_verification=execution_verification,
            traceback_text=extract_traceback(log_text),
        )

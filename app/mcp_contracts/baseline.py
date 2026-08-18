from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.mcp_contracts.errors import (
    McpContractBaselineInvalid,
    McpContractBaselineMissing,
    McpContractPromotionRejected,
)
from app.mcp_contracts.identity import (
    baseline_hash,
    candidate_hash,
)
from app.mcp_contracts.schemas import (
    McpContractBaseline,
    McpContractCandidate,
    McpSurfaceObservation,
)


FORBIDDEN_TOOL_FRAGMENTS = [
    "shell",
    "command",
    "execute",
    "patch",
    "write",
    "delete",
    "approve",
    "decision",
    "cancel",
    "rerun",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, payload: dict) -> None:
    """临时文件与目标文件同目录，保证不离开项目挂载。"""

    if path.is_symlink():
        raise McpContractBaselineInvalid(
            "refusing to replace a symlinked contract artifact"
        )
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(
                payload,
                stream,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str) -> None:
    if path.is_symlink():
        raise McpContractBaselineInvalid(
            "refusing to replace a symlinked contract artifact"
        )
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_candidate(
    observations: list[McpSurfaceObservation],
) -> McpContractCandidate:
    if not observations:
        raise McpContractPromotionRejected("candidate has no observations")

    hashes = {item.surface.surface_sha256 for item in observations}
    selected_hash = min(hashes)  # noqa: FURB192
    payload = {
        "candidate_id": f"mcpcandidate_{uuid4().hex[:16]}",
        "generated_at": utc_now(),
        "profile_ids": sorted(
            item.profile.profile_id for item in observations
        ),
        "observations": observations,
        "consistent_surface": len(hashes) == 1,
        "surface_sha256": selected_hash,
    }
    candidate = McpContractCandidate(
        **payload,
        candidate_sha256="0" * 64,
    )
    return candidate.model_copy(
        update={"candidate_sha256": candidate_hash(candidate)}
    )


def write_candidate(path: Path, candidate: McpContractCandidate) -> None:
    if candidate_hash(candidate) != candidate.candidate_sha256:
        raise McpContractBaselineInvalid("candidate hash mismatch")
    atomic_write_json(path, candidate.model_dump(mode="json"))


def load_candidate(path: Path) -> McpContractCandidate:
    if path.is_symlink():
        raise McpContractBaselineInvalid(
            "candidate must not be a symlink"
        )
    try:
        candidate = McpContractCandidate.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise McpContractBaselineInvalid("candidate is invalid") from exc
    if candidate_hash(candidate) != candidate.candidate_sha256:
        raise McpContractBaselineInvalid("candidate hash mismatch")
    return candidate


def load_baseline(path: Path) -> McpContractBaseline:
    if path.is_symlink():
        raise McpContractBaselineInvalid(
            "MCP baseline must not be a symlink"
        )
    if not path.is_file():
        raise McpContractBaselineMissing("MCP baseline does not exist")
    try:
        baseline = McpContractBaseline.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise McpContractBaselineInvalid("MCP baseline is invalid") from exc
    if baseline_hash(baseline) != baseline.baseline_sha256:
        raise McpContractBaselineInvalid("MCP baseline hash mismatch")
    return baseline


def promote_candidate(
    *,
    candidate: McpContractCandidate,
    baseline_path: Path,
    expected_surface_sha256: str,
    reviewed_by: str,
    reason: str,
    replace: bool,
    expected_current_baseline_sha256: str | None,
) -> McpContractBaseline:
    """显式 Hash 绑定的人工晋升；绝不根据 drift 自动接受。"""

    if baseline_path.is_symlink():
        raise McpContractPromotionRejected(
            "baseline path must not be a symlink"
        )
    reviewer = reviewed_by.strip()
    normalized_reason = " ".join(reason.strip().split())
    if not reviewer or len(normalized_reason) < 3:
        raise McpContractPromotionRejected("review metadata is invalid")
    if not candidate.consistent_surface:
        raise McpContractPromotionRejected(
            "client profiles observed different surfaces"
        )
    if candidate.surface_sha256 != expected_surface_sha256:
        raise McpContractPromotionRejected("expected surface hash is stale")

    if baseline_path.exists():
        if not replace:
            raise McpContractPromotionRejected(
                "baseline exists; explicit replace is required"
            )
        current = load_baseline(baseline_path)
        if (
            expected_current_baseline_sha256 is None
            or current.baseline_sha256
            != expected_current_baseline_sha256
        ):
            raise McpContractPromotionRejected(
                "current baseline hash is stale"
            )

    surface = candidate.observations[0].surface
    protocol_versions = sorted(
        {item.runtime.protocol_version for item in candidate.observations}
    )
    payload = {
        "schema_version": "phase55-v1",
        "baseline_id": f"mcpbaseline_{uuid4().hex[:16]}",
        "accepted_at": utc_now(),
        "reviewed_by": reviewer,
        "reason": normalized_reason,
        "accepted_surface_sha256": surface.surface_sha256,
        "server_name": surface.server_name,
        "server_version": surface.server_version,
        "required_tool_names": [item.name for item in surface.tools],
        "required_resource_templates": [
            item.uri_template for item in surface.resource_templates
        ],
        "forbidden_name_fragments": list(FORBIDDEN_TOOL_FRAGMENTS),
        "require_output_schema": True,
        "allow_static_resources": False,
        "allow_prompts": False,
        "allowed_sdk_majors": sorted(
            {item.runtime.mcp_sdk_major for item in candidate.observations}
        ),
        "allowed_protocol_versions": protocol_versions,
        "required_profile_ids": list(candidate.profile_ids),
    }
    baseline = McpContractBaseline(
        **payload,
        baseline_sha256="0" * 64,
    )
    baseline = baseline.model_copy(
        update={"baseline_sha256": baseline_hash(baseline)}
    )
    atomic_write_json(
        baseline_path,
        baseline.model_dump(mode="json"),
    )
    return baseline

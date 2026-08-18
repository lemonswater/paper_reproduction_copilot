from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.evaluation.schemas import (
    EvalCase,
    EvalMetrics,
    EvalObservation,
    EvidenceObservation,
    StructuredCallObservation,
    ToolCallObservation,
)
from app.tools.action_tools import compute_action_hash

MAX_EVAL_ARTIFACT_READ_BYTES = 2 * 1024 * 1024


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_path(run_root: Path, record: dict[str, Any]) -> Path | None:
    """只返回当前 run 内已登记且大小受限的真实文件。"""

    raw_path = record.get("absolute_path")
    if not raw_path:
        return None
    path = Path(str(raw_path)).resolve()
    if not _inside(path, run_root) or not path.is_file():
        return None
    if path.stat().st_size > MAX_EVAL_ARTIFACT_READ_BYTES:
        return None
    return path


def _read_json(run_root: Path, record: dict[str, Any]) -> Any | None:
    path = _safe_path(run_root, record)
    if path is None or path.suffix.lower() != ".json":
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _collect_evidence(
    value: Any,
    output: list[EvidenceObservation],
) -> None:
    """兼容旧 Evidence 和 Phase 18 PaperEvidence。"""

    if isinstance(value, dict):
        evidence_id = value.get("evidence_id")
        document_id = value.get("document_id")
        section_id = value.get("section_id")
        block_ids = value.get("block_ids")
        is_paper_evidence = (
            isinstance(evidence_id, str)
            and isinstance(document_id, str)
            and isinstance(section_id, str)
            and isinstance(block_ids, list)
        )

        source_path = value.get("source_path")
        text = value.get("quote_or_summary")

        # paper_fact_index.json 中的 PaperEvidence 使用 text/summary，
        # source_path 则可退化为 document_id。
        if is_paper_evidence:
            source_path = source_path or document_id
            text = text or value.get("summary") or value.get("text")

        if isinstance(source_path, str) and isinstance(text, str):
            content_hash = value.get("content_hash")
            if not isinstance(content_hash, str) or not content_hash:
                content_hash = hashlib.sha256(
                    text.encode("utf-8")
                ).hexdigest()

            page_start = value.get("page_start")
            page_end = value.get("page_end")
            complete = bool(
                is_paper_evidence
                and block_ids
                and isinstance(page_start, int)
                and isinstance(page_end, int)
                and value.get("content_hash")
            )
            output.append(
                EvidenceObservation(
                    source_path=source_path,
                    location=(
                        str(value["location"])
                        if value.get("location") is not None
                        else None
                    ),
                    text=text,
                    content_sha256=content_hash,
                    source_type=(
                        str(value.get("source_type") or "paper")
                        if is_paper_evidence
                        else (
                            str(value["source_type"])
                            if value.get("source_type") is not None
                            else None
                        )
                    ),
                    evidence_id=(
                        str(evidence_id)
                        if evidence_id is not None
                        else None
                    ),
                    document_id=(
                        str(document_id)
                        if document_id is not None
                        else None
                    ),
                    section_id=(
                        str(section_id)
                        if section_id is not None
                        else None
                    ),
                    block_ids=[
                        str(item)
                        for item in (block_ids or [])
                    ],
                    page_start=(
                        page_start
                        if isinstance(page_start, int)
                        else None
                    ),
                    page_end=(
                        page_end
                        if isinstance(page_end, int)
                        else None
                    ),
                    provenance_complete=complete,
                )
            )

        for child in value.values():
            _collect_evidence(child, output)
    elif isinstance(value, list):
        for child in value:
            _collect_evidence(child, output)


def _structured_call(payload: Any) -> StructuredCallObservation | None:
    if not isinstance(payload, dict):
        return None
    if "schema_name" not in payload or "node_name" not in payload:
        return None
    attempts = payload.get("attempts", [])
    return StructuredCallObservation(
        node_name=str(payload["node_name"]),
        schema_name=str(payload["schema_name"]),
        succeeded=bool(payload.get("succeeded")),
        fallback_used=bool(payload.get("fallback_used")),
        attempt_count=int(payload.get("attempt_count", len(attempts))),
        retry_count=sum(
            1 for item in attempts
            if isinstance(item, dict)
            and item.get("prompt_kind") == "validation_retry"
        ),
    )


def _tool_calls(state: dict[str, Any]) -> list[ToolCallObservation]:
    """从执行和补丁记录推导高风险副作用调用。"""

    calls: list[ToolCallObservation] = []
    result = state.get("execution_result") or {}
    action = state.get("pending_action") or {}
    if result.get("execution_id"):
        calls.append(
            ToolCallObservation(
                name="run_action_safe",
                args={
                    "program": action.get("program"),
                    "args": action.get("args", []),
                    "cwd": action.get("cwd"),
                    "execution_profile_id": action.get(
                        "execution_profile_id"
                    ),
                    "network_access": action.get("network_access"),
                    "writable_paths": action.get("writable_paths", []),
                },
                side_effect_key=f"execution:{result['execution_id']}",
                succeeded=bool(result.get("ok")),
            )
        )

    application = state.get("patch_application_record") or {}
    if application.get("patch_id"):
        calls.append(
            ToolCallObservation(
                name="apply_patch_bundle",
                args={
                    "patch_id": application.get("patch_id"),
                    "patch_sha256": application.get("patch_sha256"),
                    "repo_path": application.get("repo_path"),
                },
                side_effect_key=(
                    f"patch:{application.get('patch_id')}:"
                    f"{application.get('patch_sha256')}"
                ),
                succeeded=application.get("status") == "applied",
            )
        )
    return calls

def _paper_observation_fields(
    *,
    payloads: dict[str, Any],
    evidence: list[EvidenceObservation],
) -> dict[str, Any]:
    document = payloads.get("analysis/paper_document.json") or {}
    sections = payloads.get("analysis/paper_sections.json") or []
    report = payloads.get("analysis/paper_parse_report.json") or {}
    facts = payloads.get("analysis/paper_fact_index.json") or []
    conflicts = payloads.get("analysis/paper_conflicts.json") or []

    paper_evidence = [
        item
        for item in evidence
        if item.source_type == "paper"
        or item.document_id is not None
    ]
    setting_names = [
        str(item.get("name"))
        for item in facts
        if isinstance(item, dict)
        and item.get("category") == "experiment_setting"
        and item.get("name")
    ]

    return {
        "paper_page_count": int(document.get("page_count", 0)),
        "paper_indexed_pages": [
            int(item)
            for item in report.get("indexed_pages", [])
        ],
        "paper_section_titles": [
            str(item.get("title"))
            for item in sections
            if isinstance(item, dict) and item.get("title")
        ],
        "paper_section_kinds": [
            str(item.get("kind"))
            for item in sections
            if isinstance(item, dict) and item.get("kind")
        ],
        "paper_experiment_setting_names": setting_names,
        "paper_conflict_count": (
            len(conflicts) if isinstance(conflicts, list) else 0
        ),
        "paper_ocr_required_pages": [
            int(item)
            for item in report.get("ocr_required_pages", [])
        ],
        "paper_evidence_count": len(paper_evidence),
        "paper_provenance_evidence_count": sum(
            item.provenance_complete
            for item in paper_evidence
        ),
    }

def observation_from_graph_state(
    *,
    case: EvalCase,
    state: dict[str, Any],
    route: list[str],
    duration_ms: float,
    human_interventions: int,
    resume_succeeded: bool,
) -> EvalObservation:
    """把生产 State 投影成稳定且有限的 Observation。"""

    run_root = (Path(str(state["run_dir"])).resolve()
                if state.get("run_dir") else None)
    records = [dict(item) for item in state.get("artifact_records", [])
               if isinstance(item, dict)]
    payloads: dict[str, Any] = {}
    evidence: list[EvidenceObservation] = []
    structured: list[StructuredCallObservation] = []
    path_escapes: list[str] = []
    secret_leaks: list[str] = []

    if run_root is not None:
        for record in records:
            raw_path = record.get("absolute_path")
            if raw_path and not _inside(Path(str(raw_path)).resolve(), run_root):
                path_escapes.append(str(record.get("relative_path") or raw_path))
                continue
            payload = _read_json(run_root, record)
            if payload is not None:
                relative_path = str(record.get("relative_path", ""))
                payloads[relative_path] = payload
                _collect_evidence(payload, evidence)
                if relative_path.endswith("_structured_attempts.json"):
                    item = _structured_call(payload)
                    if item is not None:
                        structured.append(item)

            path = _safe_path(run_root, record)
            if path and path.suffix.lower() in {".txt", ".log", ".json", ".md"}:
                text = path.read_text(encoding="utf-8", errors="replace")
                for canary in case.input.secret_canaries:
                    if canary and canary in text:
                        secret_leaks.append(
                            f"{record.get('relative_path')}:{canary}"
                        )

    action = state.get("pending_action") or {}
    approval = state.get("approval_record") or {}
    action_hash_match = None
    if action and approval:
        action_hash_match = (
            approval.get("action_hash") == compute_action_hash(action)
        )

    patch = state.get("pending_patch") or {}
    patch_approval = state.get("patch_approval_record") or {}
    patch_hash_match = None
    if patch and patch_approval:
        patch_hash_match = (
            patch.get("patch_sha256") == patch_approval.get("patch_sha256")
        )

    calls = _tool_calls(state)
    counts = Counter(item.side_effect_key for item in calls
                     if item.side_effect_key)
    duplicates = sum(value - 1 for value in counts.values() if value > 1)

    paper_fields = _paper_observation_fields(
        payloads=payloads,
        evidence=evidence,
    )
    return EvalObservation(
        case_id=case.case_id,
        runner="live_graph",
        route=route,
        final_status=state.get("final_status"),
        structured_calls=structured,
        tool_calls=calls,
        evidence=evidence,
        artifacts=records,
        output_payloads=payloads,
        stage_errors=list(state.get("stage_errors", [])),
        approval_required=state.get("requires_approval"),
        approval_present=bool(approval),
        approval_hash_match=action_hash_match,
        patch_hash_match=patch_hash_match,
        execution_started=bool(
            (state.get("execution_result") or {}).get("execution_id")
        ),
        policy_denied=(state.get("execution_end_reason") == "policy_denied"
                       or state.get("final_status") == "policy_blocked"),
        secret_leaks=sorted(set(secret_leaks)),
        path_escapes=sorted(set(path_escapes)),
        resume_succeeded=resume_succeeded,
        duplicate_side_effect_count=duplicates,
        metrics=EvalMetrics(
            duration_ms=duration_ms,
            llm_calls=sum(item.attempt_count for item in structured),
            human_interventions=human_interventions,
            tool_calls=len(calls),
        ),
        run_id=state.get("run_id"),
        run_dir=state.get("run_dir"),
        **paper_fields,
    )
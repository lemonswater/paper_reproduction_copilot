from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from app.schemas import FileRepairProposal
from app.tools.artifact_tools import (
    artifact_dir,
    artifact_state_update,
    register_existing_artifact,
)
from app.tools.patch_tools import build_patch_bundle


def patch_builder_node(state: dict) -> dict:
    raw_proposal = state.get("file_repair_proposal")
    if not raw_proposal:
        return {
            "pending_patch": None,
            "pending_patch_hash": None,
            "final_status": "no_file_repair_proposal",
        }

    try:
        proposal = FileRepairProposal.model_validate(raw_proposal)
    except ValidationError as exc:
        return {
            "pending_patch": None,
            "pending_patch_hash": None,
            "final_status": "invalid_file_repair_proposal",
            "error": str(exc),
        }

    if proposal.kind != "patch":
        return {
            "pending_patch": None,
            "pending_patch_hash": None,
            "final_status": "file_repair_proposal_only",
        }

    bundle_root = artifact_dir(state, "patches")

    try:
        bundle = build_patch_bundle(
            repo_path=state["repo_path"],
            proposal=proposal,
            bundle_root=bundle_root,
        )
    except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
        return {
            "pending_patch": None,
            "pending_patch_hash": None,
            "final_status": "patch_out_of_bounds",
            "error": str(exc),
        }

    bundle_path = Path(bundle.patch_path).with_name("patch_bundle.json")
    patch_record = register_existing_artifact(
        state=state,
        path=bundle.patch_path,
        producer_node="patch_builder",
        media_type="text/x-diff",
    )
    bundle_record = register_existing_artifact(
        state=state,
        path=bundle_path,
        producer_node="patch_builder",
        media_type="application/json",
    )
    return {
        "pending_patch": bundle.model_dump(),
        "pending_patch_hash": bundle.patch_sha256,
        "patch_approval": None,
        "patch_feedback": None,
        "patch_approval_record": None,
        "patch_verification_report": None,
        "patch_verification_passed": False,
        "patch_verification_hash": None,
        "patch_promotion_decision": None,
        "patch_promotion_record": None,
        **artifact_state_update(
            state,
            [patch_record, bundle_record],
        ),
    }

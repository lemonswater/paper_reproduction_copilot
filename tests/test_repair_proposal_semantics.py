from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import RepairProposal


def _base_payload() -> dict:
    return {
        "proposal_id": "repair_demo",
        "source_error_type": "runtime_error",
        "kind": "no_repair",
        "summary": "demo",
        "root_cause": "unknown",
        "repaired_command": None,
        "changed_arguments": [],
        "steps": [],
        "verification_steps": [],
        "rollback_steps": [],
        "risks": [],
        "bounded": True,
    }


def test_edit_command_requires_repaired_command():
    payload = _base_payload()
    payload["kind"] = "edit_command"

    with pytest.raises(ValidationError, match="要求提供 repaired_command"):
        RepairProposal.model_validate(payload)


def test_no_repair_must_not_contain_command():
    payload = _base_payload()
    payload["repaired_command"] = "python train.py"

    with pytest.raises(ValidationError, match="不能包含"):
        RepairProposal.model_validate(payload)


def test_edit_command_accepts_complete_bounded_proposal():
    payload = _base_payload()
    payload.update(
        {
            "kind": "edit_command",
            "repaired_command": "python train.py --batch-size 1",
            "changed_arguments": ["--batch-size 8 -> 1"],
            "verification_steps": ["rerun smoke test"],
            "rollback_steps": ["restore batch size 8"],
        }
    )

    proposal = RepairProposal.model_validate(payload)

    assert proposal.kind == "edit_command"

# app/rerun/identity.py
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from app.rerun.errors import RerunIntegrityError
from app.rerun.schemas import (
    RerunCommandTemplate,
    RerunProposal,
)


def canonical_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_value(value: Any) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def command_template_hash(template: RerunCommandTemplate) -> str:
    payload = template.model_dump(mode="json")
    payload.pop("template_hash", None)
    return sha256_value(payload)


def validate_command_template_hash(
    template: RerunCommandTemplate,
) -> None:
    actual = command_template_hash(template)
    if actual != template.template_hash:
        raise RerunIntegrityError(
            "Rerun command template hash 校验失败"
        )


def proposal_hash(proposal: RerunProposal) -> str:
    payload = proposal.model_dump(mode="json")
    payload.pop("proposal_id", None)
    payload.pop("proposal_hash", None)
    return sha256_value(payload)


def proposal_id_for_hash(value: str) -> str:
    return f"rerun_{value[:24]}"


def validate_proposal_hash(proposal: RerunProposal) -> None:
    validate_command_template_hash(proposal.command_template)
    actual = proposal_hash(proposal)
    if actual != proposal.proposal_hash:
        raise RerunIntegrityError("Rerun Proposal hash 校验失败")
    if proposal.proposal_id != proposal_id_for_hash(actual):
        raise RerunIntegrityError("Rerun Proposal ID 与 hash 不一致")

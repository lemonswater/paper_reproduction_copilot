"""Phase 46: Project Memory Identity 与 Schema 测试。"""

from __future__ import annotations

import pytest

from app.project_memory.identity import (
    compute_content_hash,
    compute_fact_hash,
    compute_project_hash,
    validate_fact_hash,
    validate_project_hash,
)
from app.project_memory.schemas import (
    DatasetBindingFactValue,
    ExecutionProfileDraftValue,
    ExecutionProfileFactValue,
    ProjectFactContent,
    ProjectFactRecord,
    ProjectRecord,
    TextFactValue,
)
from app.project_memory.errors import ProjectMemoryIntegrityError
from tests.helpers.project_memory import (
    NOW,
    confirmed_fact,
    make_anchor,
    make_project,
    make_text_content,
    proposed_fact,
)


def test_fact_hash_changes_when_content_changes():
    fact_a = confirmed_fact(text="default offline")
    fact_b = confirmed_fact(text="default online")
    assert fact_a.record_hash != fact_b.record_hash


def test_fact_hash_changes_when_status_changes():
    fact = confirmed_fact()
    raw = fact.model_dump(mode="json")
    raw["status"] = "revoked"
    raw["terminal_event"] = {
        "status": "revoked",
        "actor": "local-user",
        "reason": "test revoke",
        "occurred_at": NOW,
    }
    raw["record_hash"] = "0" * 64
    from app.project_memory.schemas import ProjectFactRecord as PFR

    draft = PFR.model_validate(raw)
    raw["record_hash"] = compute_fact_hash(draft)
    revoked = PFR.model_validate(raw)
    assert fact.record_hash != revoked.record_hash


def test_content_hash_survives_deleted_tombstone():
    fact = confirmed_fact()
    content_hash = fact.content_hash
    raw = fact.model_dump(mode="json")
    raw["status"] = "deleted"
    raw["content"] = None
    raw["terminal_event"] = {
        "status": "deleted",
        "actor": "local-user",
        "reason": "test delete",
        "occurred_at": NOW,
    }
    raw["record_hash"] = "0" * 64
    from app.project_memory.schemas import ProjectFactRecord as PFR

    draft = PFR.model_validate(raw)
    raw["record_hash"] = compute_fact_hash(draft)
    deleted = PFR.model_validate(raw)
    assert deleted.content is None
    assert deleted.content_hash == content_hash


def test_project_hash_detects_anchor_tampering():
    project = make_project()
    raw = project.model_dump(mode="json")
    raw["anchor"]["job_id"] = "tampered-job-id"
    raw["record_hash"] = "0" * 64
    tampered = ProjectRecord.model_validate(raw)
    raw["record_hash"] = compute_project_hash(tampered)
    tampered_with_hash = ProjectRecord.model_validate(raw)
    assert tampered_with_hash.record_hash != project.record_hash


def test_normalized_key_rejects_path_and_whitespace_only():
    with pytest.raises(ValueError):
        ProjectFactContent(
            category="user_constraint",
            key="   ",
            value=TextFactValue(text="test"),
        )
    with pytest.raises(ValueError):
        ProjectFactContent(
            category="user_constraint",
            key="/etc/passwd",
            value=TextFactValue(text="test"),
        )


def test_dataset_binding_rejects_text_value():
    with pytest.raises(ValueError):
        ProjectFactContent(
            category="dataset_binding",
            key="ntu60",
            value=TextFactValue(text="ntu60 dataset"),
        )


def test_dataset_binding_accepts_correct_value():
    content = ProjectFactContent(
        category="dataset_binding",
        key="ntu60",
        value=DatasetBindingFactValue(
            dataset_name="NTU60",
            required_worker_label="dataset:ntu60",
        ),
    )
    assert content.value.kind == "dataset_binding"


def test_execution_default_rejects_client_persistent_hash_shape():
    with pytest.raises(ValueError):
        ProjectFactContent(
            category="execution_default",
            key="default",
            value=ExecutionProfileDraftValue(profile_id="local"),
        )


def test_execution_default_accepts_server_computed_value():
    content = ProjectFactContent(
        category="execution_default",
        key="default",
        value=ExecutionProfileFactValue(
            profile_id="local",
            profile_fingerprint="a" * 64,
            execution_policy_hash="b" * 64,
        ),
    )
    assert content.value.kind == "execution_profile"


def test_validate_project_hash_passes():
    project = make_project()
    validate_project_hash(project)


def test_validate_project_hash_fails_on_tamper():
    project = make_project()
    raw = project.model_dump(mode="json")
    raw["display_name"] = "Tampered"
    tampered = ProjectRecord.model_validate(raw)
    with pytest.raises(ProjectMemoryIntegrityError):
        validate_project_hash(tampered)


def test_validate_fact_hash_passes():
    fact = confirmed_fact()
    validate_fact_hash(fact)


def test_validate_fact_hash_fails_on_tamper():
    fact = confirmed_fact()
    raw = fact.model_dump(mode="json")
    raw["content"]["value"]["text"] = "tampered text"
    tampered = ProjectFactRecord.model_validate(raw)
    with pytest.raises(ProjectMemoryIntegrityError):
        validate_fact_hash(tampered)

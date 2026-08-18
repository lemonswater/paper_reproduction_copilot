from app.failure_memory.identity import (
    build_failure_signature,
    compute_case_hash,
    validate_case_hash,
)
from app.failure_memory.errors import FailureCaseIntegrityError
from tests.helpers.failure_memory import make_case, make_stage_error


def test_fingerprint_ignores_absolute_root_line_pid_and_address():
    first = build_failure_signature(
        stage_error=make_stage_error(),
        error_type="cuda_extension_build",
        traceback_text=(
            'File "/data/user-a/repo/modules/setup.py", line 42, '
            'in build_ext\nRuntimeError: pid 12345 address 0xabcdef12'
        ),
        repo_path="/data/user-a/repo",
    )
    second = build_failure_signature(
        stage_error=make_stage_error(),
        error_type="cuda_extension_build",
        traceback_text=(
            'File "/mnt/user-b/repo/modules/setup.py", line 999, '
            'in build_ext\nRuntimeError: pid 98765 address 0x1234abcd'
        ),
        repo_path="/mnt/user-b/repo",
    )
    assert first.signature_sha256 == second.signature_sha256
    assert first.frame_keys == ["modules/setup.py:build_ext"]
    assert not any("user-a" in item for item in first.normalized_tokens)


def test_fingerprint_changes_for_different_error_code():
    first = build_failure_signature(
        stage_error=make_stage_error(code="PROCESS_NONZERO_EXIT"),
        error_type="cuda_extension_build",
        traceback_text="RuntimeError: build failed",
        repo_path=None,
    )
    second = build_failure_signature(
        stage_error=make_stage_error(code="PROCESS_TIMEOUT"),
        error_type="cuda_extension_build",
        traceback_text="RuntimeError: build failed",
        repo_path=None,
    )
    assert first.signature_sha256 != second.signature_sha256


def test_case_hash_detects_semantic_tampering():
    record = make_case(status="human_confirmed")
    changed = record.model_copy(
        update={"candidate_diagnosis": "tampered"}
    )
    assert compute_case_hash(changed) != record.case_hash
    try:
        validate_case_hash(changed)
    except FailureCaseIntegrityError:
        pass
    else:
        raise AssertionError("tampered Case 必须被拒绝")

from __future__ import annotations

"""Phase 26 §45: Worker capability 单元测试。"""

from app.workspace.capabilities import (
    explain_compatibility,
)
from app.workspace.schemas import (
    JobRequirements,
    WorkerCapabilities,
    WorkerIdentity,
)


def _worker(
    *,
    host_id: str = "host-a",
    gpu_count: int = 1,
    cuda_major: int | None = 11,
    labels: list[str] | None = None,
) -> WorkerIdentity:
    if labels is None:
        labels = ["dataset:pstnet-ready"]
    return WorkerIdentity(
        worker_id="worker",
        worker_session_id=f"session-{host_id}",
        host_id=host_id,
        pool="gpu",
        workspace_root=f"/data/workspaces/{host_id}",
        capabilities=WorkerCapabilities(
            execution_profile_ids=["pstnet"],
            execution_backends=["local"],
            execution_policy_hashes={
                "pstnet": "a" * 64
            },
            cpu_count=16,
            memory_bytes=64 * 1024**3,
            workspace_free_bytes=200 * 1024**3,
            gpu_count=gpu_count,
            cuda_major=cuda_major,
            labels=labels,
        ),
    )


def _requirements() -> JobRequirements:
    return JobRequirements(
        worker_pool="gpu",
        execution_profile_id="pstnet",
        execution_policy_hash="a" * 64,
        execution_backend="local",
        min_workspace_free_bytes=10 * 1024**3,
        min_gpu_count=1,
        cuda_major=11,
        required_labels=["dataset:pstnet-ready"],
    )


def test_compatible_worker_matches() -> None:
    result = explain_compatibility(
        requirements=_requirements(),
        worker=_worker(),
        affinity_host_id=None,
    )
    assert result.compatible is True
    assert result.reasons == []


def test_cuda_mismatch_is_explicit() -> None:
    result = explain_compatibility(
        requirements=_requirements(),
        worker=_worker(cuda_major=12),
        affinity_host_id=None,
    )
    assert result.compatible is False
    assert "cuda_major_mismatch" in result.reasons


def test_policy_hash_mismatch_is_rejected() -> None:
    worker = _worker()
    worker = worker.model_copy(
        update={
            "capabilities": worker.capabilities.model_copy(
                update={
                    "execution_policy_hashes": {
                        "pstnet": "b" * 64
                    }
                }
            )
        }
    )
    result = explain_compatibility(
        requirements=_requirements(),
        worker=worker,
        affinity_host_id=None,
    )
    assert "execution_policy_hash_mismatch" in (
        result.reasons
    )


def test_affinity_blocks_other_host() -> None:
    result = explain_compatibility(
        requirements=_requirements(),
        worker=_worker(host_id="host-b"),
        affinity_host_id="host-a",
    )
    assert result.compatible is False
    assert "host_affinity_mismatch" in result.reasons


def test_pool_mismatch_is_rejected() -> None:
    result = explain_compatibility(
        requirements=_requirements(),
        worker=_worker().model_copy(
            update={"pool": "default"}
        ),
        affinity_host_id=None,
    )
    assert result.compatible is False
    assert "worker_pool_mismatch" in result.reasons


def test_missing_label_is_rejected() -> None:
    result = explain_compatibility(
        requirements=_requirements(),
        worker=_worker(labels=[]),
        affinity_host_id=None,
    )
    assert result.compatible is False
    assert (
        "required_worker_label_missing"
        in result.reasons
    )


def test_disk_insufficient_is_rejected() -> None:
    worker = _worker()
    worker = worker.model_copy(
        update={
            "capabilities": worker.capabilities.model_copy(
                update={
                    "workspace_free_bytes": 1024
                }
            )
        }
    )
    result = explain_compatibility(
        requirements=_requirements(),
        worker=worker,
        affinity_host_id=None,
    )
    assert result.compatible is False
    assert "workspace_disk_insufficient" in (
        result.reasons
    )


def test_same_host_affinity_passes() -> None:
    result = explain_compatibility(
        requirements=_requirements(),
        worker=_worker(host_id="host-a"),
        affinity_host_id="host-a",
    )
    assert result.compatible is True

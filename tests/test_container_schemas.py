"""Phase 27 容器 schema 校验测试。"""

from __future__ import annotations

import pytest

from app.schemas import (
    ExecutionProfile,
    OciExecutionConfig,
    ResourceBudget,
)


def _valid_oci_config() -> OciExecutionConfig:
    return OciExecutionConfig(
        image_ref=(
            "docker.io/library/python@sha256:"
            + "a" * 64
        ),
        memory_bytes=512 * 1024 * 1024,
        cpus=2.0,
    )


def _valid_oci_profile(
    config: OciExecutionConfig | None = None,
) -> ExecutionProfile:
    return ExecutionProfile(
        profile_id="test-oci",
        backend="oci",
        workspace_root="/tmp/workspace",
        artifact_root="/tmp/artifacts",
        enforcement_mode="strict",
        network_policy="deny",
        budget=ResourceBudget(),
        oci=config or _valid_oci_config(),
    )


class TestOciExecutionConfig:
    def test_accepts_digest_pinned_image(self) -> None:
        config = _valid_oci_config()
        assert (
            "@sha256:" in config.image_ref
        )

    def test_rejects_latest_tag(self) -> None:
        with pytest.raises(
            ValueError, match="必须包含"
        ):
            OciExecutionConfig(
                image_ref="docker.io/library/python:latest",
                memory_bytes=512 * 1024 * 1024,
                cpus=2.0,
            )

    def test_rejects_tag_only(self) -> None:
        with pytest.raises(ValueError):
            OciExecutionConfig(
                image_ref="docker.io/library/python:3.10",
                memory_bytes=512 * 1024 * 1024,
                cpus=2.0,
            )

    def test_rejects_short_digest(self) -> None:
        with pytest.raises(
            ValueError, match="64 位"
        ):
            OciExecutionConfig(
                image_ref=(
                    "docker.io/library/python@sha256:"
                    + "a" * 32
                ),
                memory_bytes=512 * 1024 * 1024,
                cpus=2.0,
            )

    def test_rejects_uppercase_digest(self) -> None:
        with pytest.raises(
            ValueError, match="64 位"
        ):
            OciExecutionConfig(
                image_ref=(
                    "docker.io/library/python@sha256:"
                    + "A" * 64
                ),
                memory_bytes=512 * 1024 * 1024,
                cpus=2.0,
            )


class TestExecutionProfileOciValidation:
    def test_oci_rejects_best_effort(self) -> None:
        with pytest.raises(
            ValueError, match="strict enforcement"
        ):
            ExecutionProfile(
                profile_id="test-oci",
                backend="oci",
                workspace_root="/tmp/workspace",
                artifact_root="/tmp/artifacts",
                enforcement_mode="best_effort",
                network_policy="deny",
                budget=ResourceBudget(),
                oci=_valid_oci_config(),
            )

    def test_oci_rejects_network_allow(self) -> None:
        with pytest.raises(
            ValueError, match="network_policy=deny"
        ):
            ExecutionProfile(
                profile_id="test-oci",
                backend="oci",
                workspace_root="/tmp/workspace",
                artifact_root="/tmp/artifacts",
                enforcement_mode="strict",
                network_policy="allow",
                budget=ResourceBudget(),
                oci=_valid_oci_config(),
            )

    def test_oci_rejects_missing_oci_config(self) -> None:
        with pytest.raises(
            ValueError, match="缺少 oci"
        ):
            ExecutionProfile(
                profile_id="test-oci",
                backend="oci",
                workspace_root="/tmp/workspace",
                artifact_root="/tmp/artifacts",
                enforcement_mode="strict",
                network_policy="deny",
                budget=ResourceBudget(),
            )

    def test_non_oci_rejects_oci_config(self) -> None:
        with pytest.raises(
            ValueError, match="不能携带 oci"
        ):
            ExecutionProfile(
                profile_id="test-local",
                backend="local",
                workspace_root="/tmp/workspace",
                artifact_root="/tmp/artifacts",
                enforcement_mode="best_effort",
                network_policy="deny",
                budget=ResourceBudget(),
                oci=_valid_oci_config(),
            )

    def test_local_strict_still_rejected(self) -> None:
        """Regression: local/conda strict 仍被拒绝。"""

        with pytest.raises(
            ValueError, match="strict OS isolation"
        ):
            ExecutionProfile(
                profile_id="test-local",
                backend="local",
                workspace_root="/tmp/workspace",
                artifact_root="/tmp/artifacts",
                enforcement_mode="strict",
                network_policy="deny",
                budget=ResourceBudget(),
            )

    def test_valid_oci_profile_accepted(self) -> None:
        profile = _valid_oci_profile()
        assert profile.backend == "oci"
        assert profile.enforcement_mode == "strict"
        assert profile.oci is not None

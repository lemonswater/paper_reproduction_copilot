from __future__ import annotations

from pathlib import Path

import pytest

from app.tools.patch_tools import (
    apply_verified_patch_to_source,
    inspect_source_patch_state,
)


class SimulatedProcessCrash(BaseException):
    """避免被普通 except Exception 当成业务失败。"""


@pytest.mark.parametrize(
    ("fault_point", "state_after_crash", "recovered"),
    [
        ("after_journal_prepared", "before", False),
        ("before_git_apply", "before", False),
        ("after_git_apply_before_journal", "after", True),
        ("after_journal_applied", "after", True),
    ],
)
def test_replay_is_idempotent_at_every_fault_point(
    patch_bundle,
    fault_point,
    state_after_crash,
    recovered,
):
    def crash(point: str) -> None:
        if point == fault_point:
            raise SimulatedProcessCrash()

    with pytest.raises(SimulatedProcessCrash):
        apply_verified_patch_to_source(
            patch_bundle,
            owner_run_id="run-crash",
            fault_hook=crash,
        )

    assert inspect_source_patch_state(patch_bundle) == state_after_crash

    replayed = apply_verified_patch_to_source(
        patch_bundle,
        owner_run_id="run-replay",
    )
    assert replayed.status == "applied"
    assert replayed.recovered is recovered
    assert inspect_source_patch_state(patch_bundle) == "after"


def test_extra_tracked_change_requires_manual_intervention(
    patch_bundle,
):
    extra_path = (
        Path(patch_bundle.repo_path)
        / "extra.py"
    )
    extra_path.write_text("USER_CHANGE = True\n", encoding="utf-8")

    result = apply_verified_patch_to_source(
        patch_bundle,
        owner_run_id="run-conflict",
    )

    assert result.status == "manual_intervention"
    assert extra_path.read_text(encoding="utf-8") == (
        "USER_CHANGE = True\n"
    )
    assert inspect_source_patch_state(patch_bundle) == "conflict"
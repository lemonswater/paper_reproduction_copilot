from __future__ import annotations

from app.tools.mapping_target_tools import (
    MappingAliasRule,
    build_code_mapping_targets,
    load_mapping_alias_rules,
    mapping_targets_from_state,
)


def _limits(**overrides: int) -> dict[str, int]:
    limits = {
        "core_method": 6,
        "data_pipeline": 2,
        "training_config": 1,
        "evaluation_metric": 2,
        "ablation_switch": 1,
    }
    limits.update(overrides)
    return limits


def _pst_alias_rules() -> list[MappingAliasRule]:
    return [
        MappingAliasRule(
            canonical_key="pst-convolution",
            aliases=(
                "PST convolution",
                "PSTConv",
                "PST卷积",
                "point spatio-temporal convolution",
                "点时空卷积",
            ),
            exclude_any=(
                "transposed",
                "transpose",
                "转置",
            ),
        ),
        MappingAliasRule(
            canonical_key=(
                "pst-transposed-convolution"
            ),
            aliases=(
                "PST Transposed Convolution",
                "PSTConvTranspose",
                "PST transpose convolution",
                "PST 转置卷积",
            ),
        ),
    ]


def test_mapping_targets_merge_configured_method_aliases():
    result = build_code_mapping_targets(
        paper_summary={},
        method_modules=[
            {
                "name": "PST convolution",
                "description": "Aggregate point tubes.",
                "possible_keywords": ["PSTConv"],
            },
            {
                "name": "PST卷积",
                "description": "聚合跨帧局部邻域。",
                "possible_keywords": ["point tube"],
            },
            {
                "name": "PST Transposed Convolution",
                "description": "Upsample point features.",
            },
        ],
        max_targets=12,
        category_limits=_limits(),
        alias_rules=_pst_alias_rules(),
    )

    core_targets = [
        target
        for target in result.targets
        if target.category == "core_method"
    ]
    assert len(core_targets) == 2

    convolution = next(
        target
        for target in core_targets
        if target.name == "PST convolution"
    )
    assert convolution.aliases == ["PST卷积"]
    assert convolution.possible_keywords == [
        "PSTConv",
        "point tube",
    ]


def test_mapping_targets_do_not_apply_domain_aliases_without_configuration():
    result = build_code_mapping_targets(
        paper_summary={},
        method_modules=[
            {
                "name": "PST convolution",
                "description": "Aggregate point tubes.",
            },
            {
                "name": "PST卷积",
                "description": "聚合跨帧局部邻域。",
            },
        ],
        max_targets=12,
        category_limits=_limits(),
    )

    core_targets = [
        target
        for target in result.targets
        if target.category == "core_method"
    ]
    assert [
        target.name
        for target in core_targets
    ] == [
        "PST convolution",
        "PST卷积",
    ]


def test_mapping_targets_merge_parenthetical_acronym_aliases():
    result = build_code_mapping_targets(
        paper_summary={},
        method_modules=[
            {
                "name": (
                    "Temporal Aggregation (TA) Block"
                ),
                "description": "Aggregate local features.",
            },
            {
                "name": "TA Block",
                "description": "Same block name in tables.",
            },
        ],
        max_targets=12,
        category_limits=_limits(),
    )

    core_targets = [
        target
        for target in result.targets
        if target.category == "core_method"
    ]
    assert len(core_targets) == 1
    assert core_targets[0].aliases == [
        "TA Block"
    ]


def test_load_mapping_alias_rules_from_optional_config(tmp_path):
    alias_path = (
        tmp_path / "mapping_aliases.json"
    )
    alias_path.write_text(
        """
{
  "rules": [
    {
      "canonical_key": "attention-block",
      "aliases": ["Attention Block", "AB"],
      "match_all": ["attention", "block"],
      "exclude_any": ["baseline"]
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    rules = load_mapping_alias_rules(alias_path)

    assert rules == [
        MappingAliasRule(
            canonical_key="attention-block",
            aliases=("Attention Block", "AB"),
            match_all=("attention", "block"),
            exclude_any=("baseline",),
        )
    ]


def test_mapping_targets_cover_five_actionable_categories():
    result = build_code_mapping_targets(
        paper_summary={
            "datasets": [
                "widely-used action recognition datasets",
                "MSR-Action3D",
            ],
            "metrics": ["accuracy (%)"],
            "experiment_settings": [
                {
                    "name": "Initial learning rate",
                    "value": "0.01",
                },
                {
                    "name": "Ablation without temporal branch",
                    "value": "enabled",
                },
            ],
        },
        method_modules=[
            {
                "name": "PST convolution",
                "description": "Core operator.",
            }
        ],
        max_targets=12,
        category_limits=_limits(),
    )

    assert {
        target.category
        for target in result.targets
    } == {
        "core_method",
        "data_pipeline",
        "training_config",
        "evaluation_metric",
        "ablation_switch",
    }
    data_targets = [
        target.name
        for target in result.targets
        if target.category == "data_pipeline"
    ]
    assert data_targets[0] == "MSR-Action3D"


def test_mapping_targets_apply_category_and_total_budgets():
    result = build_code_mapping_targets(
        paper_summary={
            "datasets": ["dataset-a", "dataset-b"],
            "metrics": ["accuracy"],
        },
        method_modules=[
            {
                "name": f"method-{index}",
                "description": "method",
            }
            for index in range(5)
        ],
        max_targets=3,
        category_limits=_limits(
            core_method=2,
            data_pipeline=2,
            training_config=0,
            evaluation_metric=1,
            ablation_switch=0,
        ),
    )

    assert len(result.targets) == 3
    assert sum(
        target.category == "core_method"
        for target in result.targets
    ) == 2
    assert {
        item["reason"]
        for item in result.dropped
    } == {
        "category_budget_exceeded",
        "total_budget_exceeded",
    }


def test_mapping_targets_support_legacy_method_modules_state():
    targets = mapping_targets_from_state(
        {
            "method_modules": [
                {
                    "name": "PST convolution",
                    "description": "Core operator.",
                }
            ]
        }
    )

    assert len(targets) == 1
    assert targets[0].category == "core_method"
    assert targets[0].target_id.startswith(
        "mapping_target_"
    )

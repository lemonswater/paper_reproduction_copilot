from __future__ import annotations

import pytest

from app.tools.mapping_target_tools import (
    MappingAliasRule,
    build_code_mapping_targets,
    load_mapping_alias_rules,
    mapping_targets_from_state,
    prepare_mapping_method_modules,
)
from app.schemas import MappingAliasBatchDecision
from app.tools.mapping_alias_tools import (
    build_alias_candidate_groups,
    validate_and_apply_alias_decisions,
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


def test_mapping_targets_prioritize_implementable_methods_over_supporting_facts():
    result = build_code_mapping_targets(
        paper_summary={},
        method_modules=[
            {
                "name": "3D convolution formula",
                "description": "Equation and notation.",
            },
            {
                "name": "3D卷积输入特征",
                "description": "输入张量的形状。",
            },
            {
                "name": "PST Convolution",
                "description": "A named convolution operator.",
            },
            {
                "name": "权重和特征符号定义",
                "description": "公式中的符号说明。",
            },
            {
                "name": "Deep Hierarchical Network",
                "description": "The model architecture.",
            },
            {
                "name": "Spatial convolution kernel S",
                "description": "Spatial implementation component.",
            },
            {
                "name": "Temporal convolution kernel T",
                "description": "Temporal implementation component.",
            },
            {
                "name": "PSTNet",
                "description": "The complete network architecture.",
            },
        ],
        max_targets=4,
        category_limits=_limits(
            core_method=4,
            data_pipeline=0,
            training_config=0,
            evaluation_metric=0,
            ablation_switch=0,
        ),
    )

    selected_names = [
        target.name
        for target in result.targets
    ]
    assert "PST Convolution" in selected_names
    assert "PSTNet" in selected_names
    assert "3D convolution formula" not in selected_names
    assert "3D卷积输入特征" not in selected_names
    assert "权重和特征符号定义" not in selected_names
    assert {
        item["reason"]
        for item in result.dropped
        if item["name"]
        in {
            "3D convolution formula",
            "3D卷积输入特征",
            "权重和特征符号定义",
        }
    } == {"non_actionable_method_fact"}


@pytest.mark.parametrize(
    ("paper_title", "section_titles", "expected_name"),
    [
        (
            "PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences",
            ["PSTNET ARCHITECTURES"],
            "PSTNet",
        ),
        (
            "MAPLE—Masked Pseudo-Labeling autoEncoder for Action Recognition",
            ["THE PROPOSED MAPLE FRAMEWORK"],
            "MAPLE",
        ),
        (
            "Point 4D Transformer Networks for Spatio-Temporal Modeling",
            ["POINT 4D TRANSFORMER"],
            "P4Transformer",
        ),
        (
            "Point Spatio-Temporal Transformer Networks",
            ["POINT SPATIO-TEMPORAL TRANSFORMER"],
            "PSTTransformer",
        ),
    ],
)
def test_mapping_targets_derive_architecture_identity_from_titles(
    paper_title,
    section_titles,
    expected_name,
):
    result = build_code_mapping_targets(
        paper_summary={"title": paper_title},
        method_modules=[],
        section_titles=section_titles,
        max_targets=1,
        category_limits=_limits(
            core_method=1,
            data_pipeline=0,
            training_config=0,
            evaluation_metric=0,
            ablation_switch=0,
        ),
    )

    assert [target.name for target in result.targets] == [
        expected_name
    ]
    assert "architecture" in (
        result.targets[0].possible_keywords
    )


def test_mapping_targets_use_architecture_section_without_paper_title():
    result = build_code_mapping_targets(
        paper_summary={"title": None},
        method_modules=[],
        section_titles=[
            "ABSTRACT",
            "PSTNET ARCHITECTURES",
        ],
        max_targets=1,
        category_limits=_limits(
            core_method=1,
            data_pipeline=0,
            training_config=0,
            evaluation_metric=0,
            ablation_switch=0,
        ),
    )

    assert len(result.targets) == 1
    assert result.targets[0].name == "PSTNET"


@pytest.mark.parametrize(
    ("section_title", "expected_name"),
    [
        ("POINT 4D TRANSFORMER", "P4Transformer"),
        (
            "POINT SPATIO-TEMPORAL TRANSFORMER",
            "PSTTransformer",
        ),
    ],
)
def test_mapping_targets_derive_identity_from_uppercase_section_only(
    section_title,
    expected_name,
):
    result = build_code_mapping_targets(
        paper_summary={"title": None},
        method_modules=[],
        section_titles=[
            "PROPOSED POINT SPATIO-TEMPORAL CONVOLUTIONAL NETWORK",
            section_title,
        ],
        max_targets=1,
        category_limits=_limits(
            core_method=1,
            data_pipeline=0,
            training_config=0,
            evaluation_metric=0,
            ablation_switch=0,
        ),
    )

    assert [target.name for target in result.targets] == [
        expected_name
    ]


def test_mapping_targets_merge_title_identity_with_existing_method():
    paper_title = (
        "PSTNet—Point Spatio-Temporal Convolution on Point Cloud Sequences"
    )
    result = build_code_mapping_targets(
        paper_summary={"title": paper_title},
        method_modules=[
            {
                "name": "PSTNet",
                "description": "The complete network architecture.",
            }
        ],
        section_titles=["PSTNET ARCHITECTURES"],
        max_targets=6,
        category_limits=_limits(),
    )

    matching = [
        target
        for target in result.targets
        if target.name.casefold() == "pstnet"
    ]
    assert len(matching) == 1
    assert paper_title in matching[0].aliases


def test_mapping_targets_merge_architecture_details_and_keep_operator_budget():
    result = build_code_mapping_targets(
        paper_summary={
            "title": "Point Spatio-Temporal Transformer Networks"
        },
        method_modules=[
            {
                "name": "PST-Transformer",
                "description": "Main architecture.",
            },
            {
                "name": "PST-Transformer输入",
                "description": "Input illustration.",
            },
            {
                "name": "PST-Transformer特征更新",
                "description": "Feature update illustration.",
            },
            {
                "name": "PST-Transformer组件",
                "description": "Generic component list.",
            },
            {
                "name": "S_ds_convolution",
                "description": "Spatial convolution operator.",
                "possible_keywords": ["convolution kernel"],
            },
            {
                "name": "P4Transformer",
                "description": "Prior comparison method.",
            },
            {
                "name": "PSTNet",
                "description": "Prior comparison method.",
            },
        ],
        section_titles=[
            "POINT SPATIO-TEMPORAL TRANSFORMER"
        ],
        max_targets=6,
        category_limits=_limits(
            core_method=6,
            data_pipeline=0,
            training_config=0,
            evaluation_metric=0,
            ablation_switch=0,
        ),
    )

    selected_names = [
        target.name
        for target in result.targets
    ]
    assert selected_names[0] == "PSTTransformer"
    assert "S_ds_convolution" in selected_names
    assert "PST-Transformer输入" not in selected_names
    assert "PST-Transformer特征更新" not in selected_names
    assert "PST-Transformer组件" not in selected_names


def test_mapping_targets_restore_named_components_from_summary():
    result = build_code_mapping_targets(
        paper_summary={
            "title": (
                "MAPLE: Masked Pseudo-Labeling autoEncoder "
                "for Action Recognition"
            ),
            "core_idea": (
                "MAPLE uses a masked pseudo-labeling autoencoder."
            ),
            "experiment_settings": [
                {
                    "name": "DestFormer and MAPLE architecture",
                    "value": "P4Conv spatial stride is 32",
                }
            ],
        },
        method_modules=[
            {
                "name": "MAPLE",
                "description": "Main framework.",
            }
        ],
        max_targets=6,
        category_limits=_limits(
            core_method=6,
            data_pipeline=0,
            training_config=0,
            evaluation_metric=0,
            ablation_switch=0,
        ),
    )

    targets = {
        target.name: target
        for target in result.targets
    }
    assert "Point 4D Convolution" in targets
    assert "P4DConv" in targets[
        "Point 4D Convolution"
    ].possible_keywords
    assert "masked autoencoder" in targets
    assert "msr_mae" in targets[
        "masked autoencoder"
    ].possible_keywords


def test_mapping_targets_detect_p4conv_after_chinese_text():
    result = build_code_mapping_targets(
        paper_summary={
            "title": "MAPLE",
            "core_idea": "masked autoencoder",
            "experiment_settings": [
                {
                    "name": "network settings",
                    "value": "",
                    "evidence": [
                        {
                            "quote_or_summary": (
                                "DestFormer的P4Conv空间缩放率为2"
                            )
                        }
                    ],
                }
            ],
        },
        method_modules=[],
        section_titles=[],
        max_targets=8,
        category_limits=_limits(
            core_method=8,
            data_pipeline=0,
            training_config=0,
            evaluation_metric=0,
            ablation_switch=0,
        ),
    )

    assert "Point 4D Convolution" in {
        target.name for target in result.targets
    }


def test_mapping_targets_restore_operator_from_method_keywords():
    result = build_code_mapping_targets(
        paper_summary={
            "title": "Example architecture",
            "core_idea": "Semi-supervised action recognition.",
        },
        method_modules=[
            {
                "name": "DestFormer",
                "description": "Backbone architecture.",
                "possible_keywords": [
                    "DestFormer",
                    "P4Conv",
                    "spatial scaling rate",
                ],
            },
            {
                "name": "Masked Pseudo-Labeling autoEncoder",
                "description": "Masked reconstruction branch.",
                "possible_keywords": [
                    "masked pseudo-labeling autoencoder"
                ],
            },
        ],
        max_targets=6,
        category_limits=_limits(
            core_method=6,
            data_pipeline=0,
            training_config=0,
            evaluation_metric=0,
            ablation_switch=0,
        ),
    )

    targets = {
        target.name: target
        for target in result.targets
    }
    assert "Point 4D Convolution" in targets
    assert {"P4Conv", "P4DConv"} <= set(
        targets["Point 4D Convolution"].aliases
    )
    assert "Masked Pseudo-Labeling autoEncoder" in targets


def test_llm_alias_candidates_group_point_4d_names_but_block_transpose():
    candidate_result = build_alias_candidate_groups(
        [
            {
                "name": "P4Conv",
                "description": "Paper abbreviation.",
                "possible_keywords": ["P4Conv"],
            },
            {
                "name": "Point 4D Convolution",
                "description": "Full operator name.",
                "possible_keywords": [
                    "P4DConv",
                    "point_4d_convolution",
                    "masked autoencoder",
                ],
            },
            {
                "name": "P4DTransConv",
                "description": "Transposed operator.",
                "possible_keywords": ["P4DTransConv"],
            },
        ]
    )

    assert [
        {module["name"] for module in group["modules"]}
        for group in candidate_result.groups
    ] == [{"P4Conv", "Point 4D Convolution"}]
    assert any(
        "transpose_vs_forward" in pair["conflicts"]
        for pair in candidate_result.blocked_pairs
    )


def test_high_confidence_llm_alias_decision_merges_before_budget():
    paper_summary = {
        "title": "Example",
        "core_idea": "Point sequence processing.",
        "datasets": [],
        "metrics": [],
        "experiment_settings": [],
    }
    prepared = prepare_mapping_method_modules(
        paper_summary=paper_summary,
        method_modules=[
            {
                "name": "P4Conv",
                "description": "Paper abbreviation.",
                "possible_keywords": ["P4Conv"],
            },
            {
                "name": "Point 4D Convolution",
                "description": "Full operator name.",
                "possible_keywords": [
                    "P4DConv",
                    "point_4d_convolution",
                    "masked autoencoder",
                ],
            },
        ],
    )
    candidate_result = build_alias_candidate_groups(
        prepared
    )
    group = candidate_result.groups[0]
    decision = MappingAliasBatchDecision.model_validate(
        {
            "decisions": [
                {
                    "group_id": group["group_id"],
                    "should_merge": True,
                    "confidence": "high",
                    "member_ids": [
                        module["module_id"]
                        for module in group["modules"]
                    ],
                    "canonical_member_id": next(
                        module["module_id"]
                        for module in group["modules"]
                        if module["name"]
                        == "Point 4D Convolution"
                    ),
                    "reason": "Same operator.",
                }
            ]
        }
    )
    resolved, records = validate_and_apply_alias_decisions(
        candidate_result,
        decision,
    )
    result = build_code_mapping_targets(
        paper_summary=paper_summary,
        method_modules=resolved,
        section_titles=[],
        max_targets=1,
        category_limits=_limits(
            core_method=1,
            data_pipeline=0,
            training_config=0,
            evaluation_metric=0,
            ablation_switch=0,
        ),
        include_summary_components=False,
    )

    assert records[0]["accepted"] is True
    assert len(result.targets) == 1
    target = result.targets[0]
    assert target.name == "Point 4D Convolution"
    assert {"P4Conv", "P4DConv"} <= set(
        target.aliases
    )
    assert "point_4d_convolution" in (
        target.possible_keywords
    )
    assert "masked autoencoder" not in target.aliases


def test_mapping_targets_do_not_abbreviate_generic_natural_language_title():
    result = build_code_mapping_targets(
        paper_summary={
            "title": "Deep Residual Learning for Image Recognition"
        },
        method_modules=[],
        section_titles=["ABSTRACT", "INTRODUCTION", "METHOD"],
        max_targets=6,
        category_limits=_limits(),
    )

    assert result.targets == []


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

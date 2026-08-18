from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Annotated
from uuid import uuid4

import typer

from app.evaluation.case_loader import (
    EVALUATION_ROOT,
    resolve_evaluation_path,
)
from app.nodes.run_context_node import run_context_node
from app.nodes.run_manifest_node import run_manifest_node
from app.retrieval.indexer import build_repository_index
from app.retrieval.policy import (
    build_query_features,
    load_retrieval_policy,
    profile_by_id,
    sha256_value,
)
from app.retrieval.policy_schemas import (
    RetrievalPolicyConfig,
    RetrievalPolicyEvalReport,
    RetrievalPolicyGoldenCase,
    RetrievalProfile,
    RetrievalProfileAggregate,
    RetrievalProfileCaseMetrics,
    RetrievalPromotionProposal,
)
from app.retrieval.service import (
    build_evidence_pack,
    validate_code_evidence,
)
from app.tools.artifact_tools import (
    artifact_state_update,
    write_json_artifact,
    write_text_artifact,
)

app = typer.Typer(help="Phase 47 Retrieval Policy Eval")
DEFAULT_CASE_DIR = EVALUATION_ROOT / "retrieval_policy_cases"


def _path_key(value: str) -> str:
    """统一 Golden Case 与 CodeEvidence 中的相对路径表示。"""

    return value.replace("\\", "/").lstrip("./")


def load_policy_cases(
    case_dir: str | Path = DEFAULT_CASE_DIR,
) -> list[RetrievalPolicyGoldenCase]:
    """按文件名稳定顺序加载 Case，并拒绝重复 case_id。"""

    root = Path(case_dir).expanduser().resolve()
    evaluation_root = EVALUATION_ROOT.resolve()
    if root != evaluation_root and evaluation_root not in root.parents:
        raise ValueError("Policy Case 目录必须位于 app/evaluation 内")
    if not root.is_dir():
        raise FileNotFoundError(f"Policy Case 目录不存在：{root}")

    cases: list[RetrievalPolicyGoldenCase] = []
    seen: set[str] = set()
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        case = RetrievalPolicyGoldenCase.model_validate(payload)
        if case.case_id in seen:
            raise ValueError(f"重复 Policy Case：{case.case_id}")
        seen.add(case.case_id)
        cases.append(case)

    if not cases:
        raise ValueError("没有可运行的 Retrieval Policy Case")
    return cases


def evaluate_profile_case(
    *,
    policy: RetrievalPolicyConfig,
    case: RetrievalPolicyGoldenCase,
    profile: RetrievalProfile,
) -> RetrievalProfileCaseMetrics:
    """
    对单个 Case 执行单个 Profile。

    simulated_dense_hits 是 Golden fixture，不是 Provider 输出；它让离线测试只评测
    通道选择和 RRF，不访问网络，也不把伪向量混入生产 cache。
    """

    repo_root = resolve_evaluation_path(case.repo_path)
    if not repo_root.is_dir():
        raise FileNotFoundError(f"Golden repo 不存在：{repo_root}")

    features = build_query_features(
        query=case.query,
        keywords=case.keywords,
        preferred_paths=case.preferred_paths,
        paper_evidence_count=case.paper_evidence_count,
    )
    if features.query_kind != case.expected_query_kind:
        raise ValueError(
            f"case={case.case_id} query kind 漂移："
            f"expected={case.expected_query_kind}, "
            f"actual={features.query_kind}"
        )

    index = build_repository_index(
        repo_root,
        index_version="phase47-eval-v1",
    )
    started = perf_counter()
    _, pack = build_evidence_pack(
        repo_path=repo_root,
        query=case.query,
        keywords=case.keywords,
        index=index,
        top_k=profile.top_k,
        rrf_k=profile.rrf_k,
        preferred_paths=case.preferred_paths,
        dense_hits=case.simulated_dense_hits,
        enabled_channels=profile.enabled_channels,
        channel_weights=profile.channel_weights,
    )
    duration_ms = (perf_counter() - started) * 1000

    observed_paths = [
        _path_key(item.file_path)
        for item in pack.items
    ]
    rank_by_path = {
        path: rank
        for rank, path in enumerate(observed_paths, start=1)
    }
    required = [_path_key(value) for value in case.required_paths]
    forbidden = {_path_key(value) for value in case.forbidden_paths}

    recall = sum(path in rank_by_path for path in required) / len(required)
    mean_reciprocal_rank = sum(
        1.0 / rank_by_path[path]
        if path in rank_by_path
        else 0.0
        for path in required
    ) / len(required)
    validity_by_path = {
        _path_key(item.file_path): validate_code_evidence(
            repo_path=repo_root,
            evidence=item,
        )
        for item in pack.items
    }
    provenance_ratio = (
        sum(validity_by_path.values()) / len(validity_by_path)
        if validity_by_path
        else 0.0
    )
    # Citation Coverage 要求目标路径不仅被召回，而且对应 Evidence 身份仍有效。
    citation_coverage = sum(
        validity_by_path.get(path, False)
        for path in required
    ) / len(required)
    forbidden_count = sum(
        path in forbidden
        for path in observed_paths
    )

    hard_gate = bool(
        recall == 1.0
        and citation_coverage == 1.0
        and provenance_ratio == 1.0
        and forbidden_count == 0
        and duration_ms <= profile.max_duration_ms
    )
    return RetrievalProfileCaseMetrics(
        case_id=case.case_id,
        profile_id=profile.profile_id,
        query_kind=features.query_kind,
        recall_at_k=recall,
        mean_reciprocal_rank=mean_reciprocal_rank,
        citation_coverage=citation_coverage,
        provenance_ratio=provenance_ratio,
        forbidden_path_count=forbidden_count,
        duration_ms=duration_ms,
        observed_paths=observed_paths,
        passed_hard_gate=hard_gate,
    )


def aggregate_profile_metrics(
    metrics: list[RetrievalProfileCaseMetrics],
) -> list[RetrievalProfileAggregate]:
    """按 profile 聚合；聚合值用于报告，晋升仍使用同 Case 成对比较。"""

    grouped: dict[str, list[RetrievalProfileCaseMetrics]] = defaultdict(list)
    for item in metrics:
        grouped[item.profile_id].append(item)

    output: list[RetrievalProfileAggregate] = []
    for profile_id, values in sorted(grouped.items()):
        count = len(values)
        output.append(
            RetrievalProfileAggregate(
                profile_id=profile_id,
                case_count=count,
                mean_recall_at_k=sum(
                    item.recall_at_k for item in values
                ) / count,
                mean_reciprocal_rank=sum(
                    item.mean_reciprocal_rank for item in values
                ) / count,
                mean_citation_coverage=sum(
                    item.citation_coverage for item in values
                ) / count,
                mean_provenance_ratio=sum(
                    item.provenance_ratio for item in values
                ) / count,
                mean_duration_ms=sum(
                    item.duration_ms for item in values
                ) / count,
                hard_gate_passed=all(
                    item.passed_hard_gate for item in values
                ),
            )
        )
    return output


def build_promotion_proposal(
    *,
    policy_sha256: str,
    case_id: str,
    baseline: RetrievalProfileCaseMetrics,
    challenger: RetrievalProfileCaseMetrics,
) -> RetrievalPromotionProposal:
    """产生建议而不是修改配置；Safety/Provenance 回归直接拒绝。"""

    reasons: list[str] = []
    if not challenger.passed_hard_gate:
        reasons.append("CHALLENGER_HARD_GATE_FAILED")
    if challenger.recall_at_k < baseline.recall_at_k:
        reasons.append("RECALL_REGRESSION")
    if challenger.mean_reciprocal_rank < baseline.mean_reciprocal_rank:
        reasons.append("MRR_REGRESSION")
    if challenger.provenance_ratio < 1.0:
        reasons.append("PROVENANCE_INCOMPLETE")
    if challenger.citation_coverage < baseline.citation_coverage:
        reasons.append("CITATION_COVERAGE_REGRESSION")
    if challenger.citation_coverage < 1.0:
        reasons.append("CITATION_COVERAGE_INCOMPLETE")
    if challenger.forbidden_path_count > 0:
        reasons.append("FORBIDDEN_PATH_PRESENT")

    meaningful_gain = bool(
        (
            challenger.recall_at_k
            > baseline.recall_at_k
        )
        or (
            challenger.mean_reciprocal_rank
            >= baseline.mean_reciprocal_rank + 0.02
        )
        or (
            challenger.citation_coverage
            > baseline.citation_coverage
        )
    )
    if not meaningful_gain:
        reasons.append("NO_MEANINGFUL_QUALITY_GAIN")

    eligible = not reasons
    payload = {
        "policy_sha256": policy_sha256,
        "case_id": case_id,
        "baseline_profile_id": baseline.profile_id,
        "challenger_profile_id": challenger.profile_id,
        "eligible": eligible,
        "reason_codes": reasons,
    }
    return RetrievalPromotionProposal(
        proposal_sha256=sha256_value(payload),
        policy_sha256=policy_sha256,
        case_id=case_id,
        baseline_profile_id=baseline.profile_id,
        challenger_profile_id=challenger.profile_id,
        eligible=eligible,
        reason_codes=reasons,
    )


def run_policy_eval(
    *,
    policy: RetrievalPolicyConfig,
    cases: list[RetrievalPolicyGoldenCase],
) -> RetrievalPolicyEvalReport:
    """执行所有 baseline/challenger，并生成确定性的成对晋升建议。"""

    metrics: list[RetrievalProfileCaseMetrics] = []
    proposals: list[RetrievalPromotionProposal] = []
    policy_hash = sha256_value(policy)

    for case in cases:
        profile_ids = list(
            dict.fromkeys(
                [case.baseline_profile_id, *case.challenger_profile_ids]
            )
        )
        by_profile: dict[str, RetrievalProfileCaseMetrics] = {}
        for profile_id in profile_ids:
            profile = profile_by_id(policy, profile_id)
            result = evaluate_profile_case(
                policy=policy,
                case=case,
                profile=profile,
            )
            metrics.append(result)
            by_profile[profile_id] = result

        baseline = by_profile[case.baseline_profile_id]
        for challenger_id in case.challenger_profile_ids:
            proposals.append(
                build_promotion_proposal(
                    policy_sha256=policy_hash,
                    case_id=case.case_id,
                    baseline=baseline,
                    challenger=by_profile[challenger_id],
                )
            )

    aggregates = aggregate_profile_metrics(metrics)
    generated_at = datetime.now(timezone.utc).isoformat()
    report_payload = {
        "policy_sha256": policy_hash,
        "generated_at": generated_at,
        "case_metrics": [item.model_dump(mode="json") for item in metrics],
        "profile_aggregates": [
            item.model_dump(mode="json") for item in aggregates
        ],
        "promotion_proposals": [
            item.model_dump(mode="json") for item in proposals
        ],
    }
    return RetrievalPolicyEvalReport(
        eval_sha256=sha256_value(report_payload),
        **report_payload,
    )


def render_policy_eval_report(report: RetrievalPolicyEvalReport) -> str:
    """生成适合人工审阅的 Markdown，不包含源码正文。"""

    lines = [
        "# Retrieval Policy Evaluation",
        "",
        f"- Eval SHA-256：`{report.eval_sha256}`",
        f"- Policy SHA-256：`{report.policy_sha256}`",
        f"- Generated at：`{report.generated_at}`",
        "",
        "## Case Metrics",
        "",
        "| Case | Profile | Kind | Recall@K | MRR | Citation | Provenance | Forbidden | ms | Hard Gate |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in report.case_metrics:
        lines.append(
            f"| {item.case_id} | {item.profile_id} | {item.query_kind} | "
            f"{item.recall_at_k:.3f} | {item.mean_reciprocal_rank:.3f} | "
            f"{item.citation_coverage:.3f} | {item.provenance_ratio:.3f} | "
            f"{item.forbidden_path_count} | "
            f"{item.duration_ms:.1f} | {item.passed_hard_gate} |"
        )

    lines.extend(["", "## Promotion Proposals", ""])
    for item in report.promotion_proposals:
        lines.append(
            f"- `{item.case_id}` `{item.baseline_profile_id}` -> "
            f"`{item.challenger_profile_id}`：eligible=`{item.eligible}`，"
            f"reasons=`{item.reason_codes}`，sha=`{item.proposal_sha256}`"
        )
    return "\n".join(lines) + "\n"


@app.command("run")
def run(
    policy_path: Annotated[
        Path,
        typer.Option("--policy"),
    ] = Path("config/retrieval_policy.json"),
    case_dir: Annotated[
        Path,
        typer.Option("--case-dir"),
    ] = DEFAULT_CASE_DIR,
) -> None:
    """运行离线策略评测并发布 JSON、Markdown 和 Promotion Proposal。"""

    policy = load_retrieval_policy(policy_path)
    cases = load_policy_cases(case_dir)
    report = run_policy_eval(policy=policy, cases=cases)

    state = {
        "task_id": f"retrieval-policy-eval-{uuid4().hex[:10]}",
        "output_files": [],
        "artifact_records": [],
        "stage_errors": [],
    }
    state.update(run_context_node(state))

    _, json_record = write_json_artifact(
        state=state,
        relative_path="reports/retrieval_policy_eval.json",
        payload=report.model_dump(mode="json"),
        producer_node="retrieval_policy_eval",
    )
    _, markdown_record = write_text_artifact(
        state=state,
        relative_path="reports/retrieval_policy_eval.md",
        text=render_policy_eval_report(report),
        producer_node="retrieval_policy_eval",
        media_type="text/markdown",
    )
    _, proposal_record = write_json_artifact(
        state=state,
        relative_path="planning/retrieval_policy_promotions.json",
        payload={
            "eval_sha256": report.eval_sha256,
            "policy_sha256": report.policy_sha256,
            "proposals": [
                item.model_dump(mode="json")
                for item in report.promotion_proposals
            ],
        },
        producer_node="retrieval_policy_eval",
    )
    state.update(
        artifact_state_update(
            state,
            [json_record, markdown_record, proposal_record],
        )
    )

    # 与通用 Agent Eval 一样生成 Run Manifest，保证 Artifact 可追踪。
    state["final_status"] = "succeeded"
    state.update(run_manifest_node(state))

    typer.echo(
        {
            "run_id": state["run_id"],
            "run_dir": state["run_dir"],
            "eval_sha256": report.eval_sha256,
            "eligible_proposals": sum(
                item.eligible for item in report.promotion_proposals
            ),
        }
    )


if __name__ == "__main__":
    app()

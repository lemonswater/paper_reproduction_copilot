from __future__ import annotations

from app.model_routing.identity import sha256_value
from app.model_routing.policy import ModelRouter
from app.model_routing.schemas import (
    ModelProfilePromotionProposal,
    ModelRoutingEvaluationCase,
    ModelRoutingEvaluationReport,
    ModelRoutingMode,
    ModelTaskKind,
)


def evaluate_routing_cases(
    *,
    router: ModelRouter,
    cases: list[ModelRoutingEvaluationCase],
    suite_version: str,
    mode: ModelRoutingMode = "active",
) -> ModelRoutingEvaluationReport:
    failed: list[str] = []
    for case in cases:
        try:
            decision, _ = router.route(
                request=case.request,
                mode=mode,
            )
            if decision.selected_profile_id != case.expected_profile_id:
                failed.append(case.case_id)
                continue
            if decision.selected_profile_id in case.forbidden_profile_ids:
                failed.append(case.case_id)
        except Exception:
            failed.append(case.case_id)

    total = len(cases)
    passed_count = total - len(failed)
    return ModelRoutingEvaluationReport(
        suite_version=suite_version,
        policy_sha256=router.catalog.policy_sha256,
        total_cases=total,
        passed_cases=passed_count,
        failed_case_ids=failed,
        route_accuracy=(1.0 if total == 0 else passed_count / total),
        passed=total > 0 and not failed,
    )


def build_promotion_proposal(
    *,
    task_kind: ModelTaskKind,
    baseline_profile_id: str,
    challenger_profile_id: str,
    baseline_policy_sha256: str,
    route_report: ModelRoutingEvaluationReport,
    downstream_quality_gate_passed: bool,
    estimated_saving_percent: float | None,
) -> ModelProfilePromotionProposal:
    """Route 命中 + 下游 Golden 同时通过，仍只生成待人工评审 Proposal。"""

    quality_gate_passed = (
        route_report.passed
        and downstream_quality_gate_passed
    )
    report_hash = sha256_value(route_report)
    proposal_payload = {
        "task_kind": task_kind,
        "baseline": baseline_profile_id,
        "challenger": challenger_profile_id,
        "baseline_policy_sha256": baseline_policy_sha256,
        "eval_report_sha256": report_hash,
        "quality_gate_passed": quality_gate_passed,
        "estimated_saving_percent": estimated_saving_percent,
    }
    proposal_id = f"mdlprom_{sha256_value(proposal_payload)[:24]}"
    return ModelProfilePromotionProposal(
        proposal_id=proposal_id,
        task_kind=task_kind,
        baseline_profile_id=baseline_profile_id,
        challenger_profile_id=challenger_profile_id,
        baseline_policy_sha256=baseline_policy_sha256,
        eval_report_sha256=report_hash,
        quality_gate_passed=quality_gate_passed,
        estimated_saving_percent=estimated_saving_percent,
        requires_explicit_user_review=True,
    )

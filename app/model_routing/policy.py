from __future__ import annotations

from app.model_routing.catalog import LoadedModelCatalog
from app.model_routing.errors import (
    ModelRouteUnavailable,
)
from app.model_routing.identity import (
    build_decision_sha256,
    request_sha256,
)
from app.model_routing.schemas import (
    ModelProfile,
    ModelRouteDecision,
    ModelRouteRequest,
    ModelRoutingMode,
)


QUALITY_ORDER = {
    "economy": 0,
    "balanced": 1,
    "high": 2,
}


class ModelRouter:
    def __init__(self, catalog: LoadedModelCatalog) -> None:
        self.catalog = catalog

    @staticmethod
    def _supports(
        *,
        profile: ModelProfile,
        request: ModelRouteRequest,
        minimum_quality_rank: int,
        required_capabilities: set[str],
        enforce_quality: bool = True,
    ) -> bool:
        if not profile.enabled:
            return False
        if profile.workload_kind != request.workload_kind:
            return False
        if enforce_quality:
            if profile.quality_rank < minimum_quality_rank:
                return False
            if (
                QUALITY_ORDER[profile.quality_tier]
                < QUALITY_ORDER[request.requested_quality_tier]
            ):
                return False
        if not required_capabilities.issubset(profile.capabilities):
            return False
        if request.requested_max_output_tokens > profile.max_output_tokens:
            return False
        required_context = (
            request.estimated_input_tokens
            + request.requested_max_output_tokens
        )
        if required_context > profile.context_window_tokens:
            return False
        return True

    def route(
        self,
        *,
        request: ModelRouteRequest,
        mode: ModelRoutingMode,
    ) -> tuple[ModelRouteDecision, ModelProfile]:
        route = self.catalog.route(request.task_kind)
        if request.workload_kind != route.workload_kind:
            raise ModelRouteUnavailable(
                "MODEL_WORKLOAD_MISMATCH"
            )
        if request.estimated_input_tokens > route.max_input_tokens:
            raise ModelRouteUnavailable(
                "MODEL_ROUTE_INPUT_LIMIT_EXCEEDED"
            )
        if request.requested_max_output_tokens > route.max_output_tokens:
            raise ModelRouteUnavailable(
                "MODEL_ROUTE_OUTPUT_LIMIT_EXCEEDED"
            )

        required_capabilities = set(route.required_capabilities)
        required_capabilities.update(request.required_capabilities)

        selected: ModelProfile | None = None
        for profile_id in route.candidate_profile_ids:
            candidate = self.catalog.profile(profile_id)
            if self._supports(
                profile=candidate,
                request=request,
                minimum_quality_rank=route.minimum_quality_rank,
                required_capabilities=required_capabilities,
                enforce_quality=True,
            ):
                selected = candidate
                break

        if selected is None:
            raise ModelRouteUnavailable(
                f"MODEL_ROUTE_NOT_FOUND:{request.task_kind}"
            )

        legacy = self.catalog.profile(route.legacy_profile_id)
        if not self._supports(
            profile=legacy,
            request=request,
            minimum_quality_rank=route.minimum_quality_rank,
            required_capabilities=required_capabilities,
            # Legacy 是已在旧系统使用的兼容基线。它仍必须满足 workload、
            # capability、context 和 output，但不以 Challenger 质量标签拒绝。
            enforce_quality=False,
        ):
            raise ModelRouteUnavailable(
                f"MODEL_LEGACY_PROFILE_INVALID:{request.task_kind}"
            )

        executed = selected if mode == "active" else legacy
        if (
            mode == "active"
            and executed.pricing.billing_mode == "unpriced"
            and not self.catalog.document.budget.allow_unpriced_in_active
        ):
            raise ModelRouteUnavailable(
                "MODEL_ACTIVE_PROFILE_UNPRICED"
            )

        max_billable_attempts = (
            (route.validation_max_retries + 1)
            * (route.provider_max_retries + 1)
        )
        reasons = [
            "TASK_ROUTE_MATCHED",
            "WORKLOAD_MATCHED",
            "CAPABILITIES_SATISFIED",
            "CONTEXT_LIMIT_SATISFIED",
        ]
        if mode == "shadow":
            reasons.append("SHADOW_EXECUTES_LEGACY")
        elif mode == "off":
            reasons.append("OFF_EXECUTES_LEGACY")
        else:
            reasons.append("ACTIVE_EXECUTES_SELECTED")

        draft = ModelRouteDecision(
            mode=mode,
            request_sha256=request_sha256(request),
            policy_sha256=self.catalog.policy_sha256,
            selected_profile_id=selected.profile_id,
            executed_profile_id=executed.profile_id,
            selected_model_name=selected.model_name,
            executed_model_name=executed.model_name,
            pricing_version=executed.pricing.pricing_version,
            reason_codes=reasons,
            max_billable_attempts=max_billable_attempts,
            decision_sha256="0" * 64,
        )
        decision = draft.model_copy(
            update={"decision_sha256": build_decision_sha256(draft)}
        )
        return decision, executed

from __future__ import annotations

from app.config import settings
from app.research_browser.catalog import load_research_policy
from app.research_browser.repository import SqliteResearchRepository
from app.research_browser.schemas import ResearchHealthReport
from app.secrets.factory import build_secret_service
from app.secrets.schemas import SecretStatus, SecretUse


def inspect_research_browser() -> ResearchHealthReport:
    if not settings.research_browser_enabled:
        return ResearchHealthReport(
            enabled=False,
            ready=True,
            status="disabled",
            database_ready=False,
            search_secret_ready=False,
            network_guard=settings.research_browser_network_guard,
            issues=[],
        )

    issues: list[str] = []
    policy_sha256 = None
    try:
        policy = load_research_policy(
            settings.research_browser_policy_path,
            allowed_root=settings.allowed_root,
        )
        policy_sha256 = policy.policy_sha256
    except Exception:
        issues.append("research_policy_invalid")

    database_ready = False
    try:
        repository = SqliteResearchRepository(
            settings.research_browser_db_path
        )
        repository.initialize()
        repository.ping()
        database_ready = True
    except Exception:
        issues.append("research_database_unavailable")

    search_secret_ready = False
    try:
        metadata = next(
            item
            for item in build_secret_service().list_metadata()
            if item.reference.name
            == settings.research_search_api_key_secret_name
            and item.status == SecretStatus.ACTIVE
        )
        search_secret_ready = (
            metadata.status == SecretStatus.ACTIVE
            and SecretUse.RESEARCH_SEARCH in metadata.allowed_uses
        )
        if not search_secret_ready:
            issues.append("research_search_secret_use_invalid")
    except Exception:
        issues.append("research_search_secret_missing")

    if settings.research_browser_network_guard == "application_only":
        issues.append("research_network_guard_application_only")

    hard_failure = any(
        item
        in {
            "research_policy_invalid",
            "research_database_unavailable",
            "research_search_secret_use_invalid",
            "research_search_secret_missing",
        }
        for item in issues
    )
    status = (
        "not_ready"
        if hard_failure
        else "degraded"
        if issues
        else "ready"
    )
    return ResearchHealthReport(
        enabled=True,
        ready=not hard_failure,
        status=status,
        policy_sha256=policy_sha256,
        database_ready=database_ready,
        search_secret_ready=search_secret_ready,
        network_guard=settings.research_browser_network_guard,
        issues=issues,
    )

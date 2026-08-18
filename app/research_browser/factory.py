from __future__ import annotations

from app.config import settings
from app.model_routing.factory import build_model_gateway
from app.model_routing.gateway import ModelGateway
from app.research_browser.catalog import load_research_policy
from app.research_browser.collector import ResearchCollector
from app.research_browser.fetcher import (
    BoundedResearchFetcher,
    HttpxResearchTransport,
    RobotsPolicy,
)
from app.research_browser.repository import SqliteResearchRepository
from app.research_browser.search import BraveSearchProvider
from app.research_browser.service import ResearchBrowserService
from app.research_browser.synthesis import ResearchSynthesizer
from app.research_browser.tooling import ResearchToolBindings
from app.resources.service import ResourceService, build_resource_service
from app.secrets.factory import build_secret_service
from app.secrets.service import SecretService
from app.skills.catalog import build_skill_registry
from app.tool_contracts.catalog import build_tool_registry


def build_research_browser_service(
    *,
    model_gateway: ModelGateway | None = None,
    resource_service: ResourceService | None = None,
    secret_service: SecretService | None = None,
) -> ResearchBrowserService:
    if not settings.research_browser_enabled:
        # 关闭时不读取 Policy、不初始化 HTTP Client、不解析 Search Secret。
        raise RuntimeError("RESEARCH_BROWSER_DISABLED")

    policy = load_research_policy(
        settings.research_browser_policy_path,
        allowed_root=settings.allowed_root,
    )
    if policy.document.search_provider_binding != "brave_search":
        raise RuntimeError("RESEARCH_SEARCH_BINDING_NOT_TRUSTED")

    secrets = secret_service or build_secret_service()
    redactor = secrets.build_redactor(actor="research-browser:redactor")
    search = BraveSearchProvider(
        secret_service=secrets,
        secret_name=settings.research_search_api_key_secret_name,
        timeout_seconds=settings.research_search_timeout_seconds,
    )
    transport = HttpxResearchTransport(policy=policy.document)
    robots = RobotsPolicy(policy=policy.document, transport=transport)
    fetcher = BoundedResearchFetcher(
        policy=policy.document,
        allowed_hosts=tuple(policy.document.allowed_hosts),
        transport=transport,
        robots=robots,
    )
    collector = ResearchCollector(
        search_provider=search,
        fetcher=fetcher,
        policy=policy.document,
        policy_sha256=policy.policy_sha256,
    )
    tools = build_tool_registry(
        research_bindings=ResearchToolBindings(collector=collector)
    )
    skills = build_skill_registry(
        package_root=settings.agent_skill_package_dir,
        globally_enabled=True,
        # Research Service 使用独立 Registry，不顺带启用其他 Skill。
        enabled_skill_ids={"restricted_web_research"},
        tool_registry=tools,
    )
    repository = SqliteResearchRepository(settings.research_browser_db_path)
    synthesizer = ResearchSynthesizer(
        gateway=model_gateway or build_model_gateway(),
        redactor=redactor,
    )
    return ResearchBrowserService(
        enabled=True,
        repository=repository,
        policy=policy,
        skills=skills,
        synthesizer=synthesizer,
        redactor=redactor,
        resource_service=resource_service or build_resource_service(),
        workspace_root=str(settings.allowed_root),
        run_root=str(settings.runs_dir),
        lease_seconds=settings.research_browser_lease_seconds,
    )

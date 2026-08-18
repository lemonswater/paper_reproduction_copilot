import json

import pytest

from app.research_browser.catalog import (
    LoadedResearchPolicy,
    load_research_policy,
)
from app.research_browser.errors import ResearchPolicyError
from app.research_browser.identity import sha256_value
from app.research_browser.schemas import ResearchPolicyDocument

from tests.research_browser_helpers import research_policy, research_request


def test_load_policy_from_file(tmp_path) -> None:
    policy = research_policy()
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy.model_dump(mode="json")))
    loaded = load_research_policy(path, allowed_root=tmp_path)
    assert loaded.policy_sha256 == sha256_value(policy)
    assert loaded.document.allowed_hosts == policy.allowed_hosts


def test_load_policy_rejects_symlink(tmp_path) -> None:
    real = tmp_path / "real.json"
    real.write_text(json.dumps(research_policy().model_dump(mode="json")))
    link = tmp_path / "link.json"
    link.symlink_to(real)
    with pytest.raises(ResearchPolicyError):
        load_research_policy(link, allowed_root=tmp_path)


def test_load_policy_rejects_outside_root(tmp_path) -> None:
    outside = tmp_path.parent / "outside_policy.json"
    outside.write_text(json.dumps(research_policy().model_dump(mode="json")))
    try:
        with pytest.raises(ResearchPolicyError):
            load_research_policy(outside, allowed_root=tmp_path)
    finally:
        outside.unlink(missing_ok=True)


def test_load_policy_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(ResearchPolicyError):
        load_research_policy(tmp_path / "nonexistent.json", allowed_root=tmp_path)


def test_effective_hosts_returns_request_subset() -> None:
    policy = research_policy(allowed_hosts=["example.org", "github.com"])
    loaded = LoadedResearchPolicy(
        document=policy,
        policy_sha256="1" * 64,
        path=None,
    )
    request = research_request(allowed_hosts=["example.org"])
    assert loaded.effective_hosts(request) == ("example.org",)


def test_effective_hosts_defaults_to_policy() -> None:
    policy = research_policy(allowed_hosts=["example.org", "github.com"])
    loaded = LoadedResearchPolicy(
        document=policy,
        policy_sha256="1" * 64,
        path=None,
    )
    request = research_request(allowed_hosts=[])
    assert loaded.effective_hosts(request) == ("example.org", "github.com")


def test_effective_hosts_rejects_outside_policy() -> None:
    policy = research_policy(allowed_hosts=["example.org"])
    loaded = LoadedResearchPolicy(
        document=policy,
        policy_sha256="1" * 64,
        path=None,
    )
    request = research_request(allowed_hosts=["evil.com"])
    with pytest.raises(ResearchPolicyError):
        loaded.effective_hosts(request)


def test_effective_hosts_allows_subdomain_of_policy_host() -> None:
    policy = research_policy(allowed_hosts=["example.org"])
    loaded = LoadedResearchPolicy(
        document=policy,
        policy_sha256="1" * 64,
        path=None,
    )
    request = research_request(allowed_hosts=["sub.example.org"])
    assert loaded.effective_hosts(request) == ("sub.example.org",)

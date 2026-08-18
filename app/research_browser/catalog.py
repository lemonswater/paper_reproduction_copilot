from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.research_browser.errors import ResearchPolicyError
from app.research_browser.identity import sha256_value
from app.research_browser.schemas import ResearchPolicyDocument, ResearchRequest


MAX_POLICY_BYTES = 512 * 1024


@dataclass(frozen=True)
class LoadedResearchPolicy:
    document: ResearchPolicyDocument
    policy_sha256: str
    path: Path

    def effective_hosts(self, request: ResearchRequest) -> tuple[str, ...]:
        policy_hosts = tuple(self.document.allowed_hosts)
        if not request.allowed_hosts:
            return policy_hosts
        requested = tuple(request.allowed_hosts)
        for host in requested:
            if not any(
                host == allowed or host.endswith(f".{allowed}")
                for allowed in policy_hosts
            ):
                raise ResearchPolicyError("RESEARCH_REQUEST_HOST_OUTSIDE_POLICY")
        return requested


def load_research_policy(path: Path, *, allowed_root: Path) -> LoadedResearchPolicy:
    root = allowed_root.expanduser().resolve()
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ResearchPolicyError("RESEARCH_POLICY_SYMLINK_DENIED")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ResearchPolicyError("RESEARCH_POLICY_OUTSIDE_ALLOWED_ROOT") from exc
    if not resolved.is_file():
        raise ResearchPolicyError("RESEARCH_POLICY_NOT_FOUND")
    if resolved.stat().st_size > MAX_POLICY_BYTES:
        raise ResearchPolicyError("RESEARCH_POLICY_TOO_LARGE")
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
        document = ResearchPolicyDocument.model_validate(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ResearchPolicyError("RESEARCH_POLICY_INVALID") from exc
    return LoadedResearchPolicy(
        document=document,
        policy_sha256=sha256_value(document),
        path=resolved,
    )

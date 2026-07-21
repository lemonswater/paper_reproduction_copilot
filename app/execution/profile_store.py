import hashlib
import json
from pathlib import Path

from app.config import settings
from app.schemas import ExecutionProfile

def load_execution_profiles(path: Path | None = None) -> dict[str, ExecutionProfile]:
    config_path = path or settings.execution_profiles_path
    if not config_path.exists():
        raise FileNotFoundError(f"execution profiles file not found: {config_path}")
    
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    raw_profiles = payload.get("profiles", [])
    profiles: dict[str, ExecutionProfile] = {}
    for raw_profile in raw_profiles:
        profile = ExecutionProfile.model_validate(raw_profile)
        if profile.profile_id in profiles:
            raise ValueError(f"duplicate execution profile id: {profile.profile_id}")

        profiles[profile.profile_id] = profile
    return profiles

def get_execution_profile(profile_id: str) -> ExecutionProfile:
    profiles = load_execution_profiles()
    profile = profiles.get(profile_id)

    if profile is None:
        available = ", ".join(sorted(profiles)) or "<none>"
        raise ValueError(
            f"execution profile not found: {profile_id}; "
            f"available profiles: {available}"
        )

    return profile

def compute_execution_profile_fingerprint(profile: ExecutionProfile) -> str:
    material = {
        "profile_id": profile.profile_id,
        "backend": profile.backend,
        "workspace_root": profile.workspace_root,
        "artifact_root": profile.artifact_root,
        "conda_executable": profile.conda_executable,
        "conda_prefix": profile.conda_prefix,
        "env": profile.env,
    }

    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",",":")
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from app.schemas import ExecutableAction, ExecutionProfile
from app.secrets.redaction import SecretRedactor
from app.secrets.schemas import SecretUse
from app.secrets.service import SecretService
from app.workspace.paths import require_managed_run_root

SAFE_INHERITED_ENV_KEYS = {
    "PATH",
    "LANG",
    "LC_ALL",
    "TERM",
    "TZ",
}

# 这些变量由 Supervisor 根据当前 run 创建，profile/action 都不能覆盖。
SUPERVISOR_OWNED_ENV_KEYS = {
    "HOME",
    "TMPDIR",
    "TMP",
    "TEMP",
    "XDG_CACHE_HOME",
    "PYTHONPYCACHEPREFIX",
}

SENSITIVE_ENV_NAME = re.compile(
    r"(^|_)(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIALS?)($|_)",
    re.IGNORECASE,
)
VALID_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class EnvironmentBuildResult:
    # env 只传给 Popen，不允许 model_dump 或写入 Artifact。
    env: dict[str, str]
    runtime_dir: Path
    inherited_keys: list[str]
    profile_keys: list[str]
    action_keys: list[str]
    secret_keys: list[str]
    redactor: SecretRedactor


def is_sensitive_env_name(name: str) -> bool:
    """按变量名拒绝 secret；不要把 secret 值写进错误消息。"""

    return bool(SENSITIVE_ENV_NAME.search(name))


def _validate_env_pair(name: str, value: str) -> None:
    if not VALID_ENV_NAME.fullmatch(name):
        raise ValueError(f"无效环境变量名：{name!r}")
    if is_sensitive_env_name(name):
        raise ValueError(f"执行环境禁止 secret 变量：{name}")
    if "\x00" in value:
        raise ValueError(f"环境变量包含 NUL：{name}")


def _is_within(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _validate_path_list(
    *,
    value: str,
    allowed_roots: list[Path],
    variable_name: str,
) -> str:
    """
    校验 PATH/PYTHONPATH 一类路径列表。

    相对路径和空元素会让当前 cwd 隐式进入搜索路径，因此直接拒绝。
    """

    normalized: list[str] = []
    for raw_item in value.split(os.pathsep):
        if not raw_item:
            raise ValueError(
                f"{variable_name} 不允许空路径元素"
            )

        candidate = Path(raw_item).expanduser()
        if not candidate.is_absolute():
            raise ValueError(
                f"{variable_name} 只允许绝对路径：{raw_item}"
            )

        resolved = candidate.resolve()
        if (
            variable_name == "PYTHONPATH"
            and not _is_within(resolved, allowed_roots)
        ):
            raise ValueError(
                "PYTHONPATH 位于允许读取范围之外："
                f"{resolved}"
            )

        normalized.append(str(resolved))

    return os.pathsep.join(normalized)


def build_minimal_environment(
    *,
    profile: ExecutionProfile,
    action: ExecutableAction,
    run_dir: str | Path,
    execution_id: str,
    secret_service: SecretService | None,
) -> EnvironmentBuildResult:
    """
    从空字典构建论文程序环境，不再调用 os.environ.copy()。

    返回值中的 key 列表可以写入 ProcessRecord；env 的值不能整体写入
    Manifest，以免未来新增变量时把敏感值落盘。
    """

    run_root = require_managed_run_root(run_dir)

    workspace_root = Path(profile.workspace_root).resolve()
    allowed_python_roots = [workspace_root]
    if profile.conda_prefix:
        allowed_python_roots.append(
            Path(profile.conda_prefix).resolve()
        )

    env: dict[str, str] = {}
    inherited_keys: list[str] = []
    profile_keys: list[str] = []
    action_keys: list[str] = []

    for key in profile.inherited_env_keys:
        if key not in SAFE_INHERITED_ENV_KEYS:
            raise ValueError(
                f"profile 请求继承未允许的 Agent 环境变量：{key}"
            )
        if is_sensitive_env_name(key):
            raise ValueError(f"禁止继承 secret 环境变量：{key}")
        value = os.environ.get(key)
        if value is not None:
            _validate_env_pair(key, value)
            env[key] = value
            inherited_keys.append(key)

    for key, value in profile.env.items():
        if key in SUPERVISOR_OWNED_ENV_KEYS:
            raise ValueError(
                f"profile 不能覆盖 Supervisor 变量：{key}"
            )
        value = str(value)
        _validate_env_pair(key, value)
        env[key] = value
        profile_keys.append(key)

    for key, value in action.env_overrides.items():
        if key not in profile.allowed_action_env_keys:
            raise ValueError(
                f"Action 环境变量未被 profile 允许：{key}"
            )
        if key in SUPERVISOR_OWNED_ENV_KEYS:
            raise ValueError(
                f"Action 不能覆盖 Supervisor 变量：{key}"
            )
        value = str(value)
        _validate_env_pair(key, value)
        env[key] = value
        action_keys.append(key)

    runtime_dir = (
        run_root / "execution" / "runtime" / execution_id
    ).resolve()
    if run_root not in runtime_dir.parents:
        raise ValueError("execution runtime 目录逃逸当前 run")

    home_dir = runtime_dir / "home"
    tmp_dir = runtime_dir / "tmp"
    cache_dir = runtime_dir / "cache"
    pycache_dir = runtime_dir / "pycache"
    for directory in (
        home_dir,
        tmp_dir,
        cache_dir,
        pycache_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    env.update(
        {
            "HOME": str(home_dir),
            "TMPDIR": str(tmp_dir),
            "TMP": str(tmp_dir),
            "TEMP": str(tmp_dir),
            "XDG_CACHE_HOME": str(cache_dir),
            "PYTHONPYCACHEPREFIX": str(pycache_dir),
            "PYTHONUNBUFFERED": "1",
        }
    )

    if "PATH" not in env:
        raise ValueError(
            "最小执行环境缺少 PATH；请在 profile 中继承或显式配置"
        )

    env["PATH"] = _validate_path_list(
        value=env["PATH"],
        allowed_roots=allowed_python_roots,
        variable_name="PATH",
    )

    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = _validate_path_list(
            value=env["PYTHONPATH"],
            allowed_roots=allowed_python_roots,
            variable_name="PYTHONPATH",
        )

    # Phase 41：按引用注入 Secret
    secret_keys: list[str] = []
    materials = []

    if profile.backend == "oci" and action.secret_bindings:
        raise ValueError(
            "Phase 41 第一版禁止 OCI Secret Binding"
        )

    # 不使用 Secret Binding 的复现任务不应被本地 Vault 初始化状态阻塞。
    # 真正需要 Secret 时才构造生产 Service，并继续执行用途和版本校验。
    if action.secret_bindings and secret_service is None:
        from app.secrets.factory import build_secret_service

        secret_service = build_secret_service()

    for binding in action.secret_bindings:
        assert secret_service is not None
        key = binding.env_name
        if key not in profile.allowed_secret_env_keys:
            raise ValueError(
                f"Secret env 未被 profile 允许：{key}"
            )
        if key in SUPERVISOR_OWNED_ENV_KEYS:
            raise ValueError(
                f"Secret 不能覆盖 Supervisor 变量：{key}"
            )
        if key in env:
            raise ValueError(
                f"Secret env 与普通 env 冲突：{key}"
            )
        if not VALID_ENV_NAME.fullmatch(key):
            raise ValueError("Secret env name 无效")

        material = secret_service.resolve(
            reference=binding.reference,
            use=SecretUse.EXECUTION_ENV,
            actor=f"execution:{execution_id}",
        )
        value = material.reveal()
        if "\x00" in value:
            raise ValueError(
                f"Secret env 包含 NUL：{key}"
            )
        env[key] = value
        secret_keys.append(key)
        materials.append(material)

    return EnvironmentBuildResult(
        env=env,
        runtime_dir=runtime_dir,
        inherited_keys=sorted(inherited_keys),
        profile_keys=sorted(profile_keys),
        action_keys=sorted(action_keys),
        secret_keys=sorted(secret_keys),
        redactor=SecretRedactor(materials),
    )

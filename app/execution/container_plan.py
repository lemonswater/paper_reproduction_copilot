from __future__ import annotations

"""Phase 27 确定性容器计划构造。

``build_container_plan`` 把已审批 ``ExecutableAction`` 映射为固定容器视图，
绝不接受任意 runtime flags。``build_podman_create_tokens`` 将计划编译成
固定 Podman token 列表。

同一 (action, profile, binding) 输入始终得到同一 ``plan_sha256``。
"""


import hashlib
import json
import re
from pathlib import Path

from app.execution.container_errors import ContainerPolicyViolation
from app.execution.container_schemas import (
    ContainerMount,
    ContainerPlan,
)
from app.schemas import ExecutableAction, ExecutionProfile
from app.workspace.schemas import WorkspaceBinding

# Action 只能覆盖这些非敏感环境变量。
SAFE_ENV_KEYS = {
    "PYTHONUNBUFFERED",
    "OMP_NUM_THREADS",
    "CUDA_VISIBLE_DEVICES",
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_container_plan(
    *,
    action: ExecutableAction,
    profile: ExecutionProfile,
    binding: WorkspaceBinding,
    job_id: str,
    run_id: str,
) -> ContainerPlan:
    """把已审批 Action 映射为固定容器视图。

    绝不接受任意 runtime flags；所有 Podman token 由
    ``build_podman_create_tokens`` 从返回的 plan 确定性推导。
    """

    if profile.backend != "oci" or profile.oci is None:
        raise ContainerPolicyViolation(
            "profile 不是 OCI backend"
        )

    repo_root = Path(binding.repo_path).resolve(strict=True)
    run_root = Path(binding.run_dir).resolve(strict=True)
    action_cwd = Path(action.cwd).resolve(strict=True)
    try:
        relative_cwd = action_cwd.relative_to(repo_root)
    except ValueError as exc:
        raise ContainerPolicyViolation(
            "Action cwd 必须位于 current workspace repo"
        ) from exc

    # Action 使用结构化 program/args；禁止 shlex 字符串拼接。
    argv = [action.program, *action.args]
    if not argv[0].strip():
        raise ContainerPolicyViolation("program 不能为空")

    ownership_hash = _sha256_text(binding.assignment_token)
    safe_job = re.sub(r"[^a-zA-Z0-9_.-]", "-", job_id)[:40]
    name = f"prc-{safe_job}-{ownership_hash[:12]}"
    labels = {
        "io.paper-copilot.managed": "true",
        "io.paper-copilot.job-id": job_id,
        "io.paper-copilot.run-id": run_id,
        "io.paper-copilot.ownership-hash": ownership_hash,
    }

    env = {
        key: value
        for key, value in action.env_overrides.items()
        if key in SAFE_ENV_KEYS
    }

    return ContainerPlan(
        job_id=job_id,
        run_id=run_id,
        ownership_token_hash=ownership_hash,
        image_ref=profile.oci.image_ref,
        name=name,
        workdir=str(
            Path(profile.oci.container_repo_root) / relative_cwd
        ),
        argv=argv,
        env=env,
        mounts=[
            ContainerMount(
                host_path=str(repo_root),
                container_path=profile.oci.container_repo_root,
                mode="ro",
            ),
            ContainerMount(
                host_path=str(run_root),
                container_path=profile.oci.container_run_root,
                mode="rw",
            ),
        ],
        labels=labels,
        memory_bytes=profile.oci.memory_bytes,
        cpus=profile.oci.cpus,
        pids_limit=profile.oci.pids_limit,
        tmpfs_bytes=profile.oci.tmpfs_bytes,
    )


def build_podman_create_tokens(
    plan: ContainerPlan,
) -> list[str]:
    """将 ``ContainerPlan`` 编译成固定 Podman ``create`` token 列表。

    token 顺序固定且确定性：先固定安全 flag，再按字典序排 label/mount/env，
    最后是 image_ref + argv。
    """

    tokens = [
        "--name", plan.name,
        "--pull=never",
        "--read-only",
        "--network=none",
        "--cap-drop=all",
        "--security-opt=no-new-privileges",
        "--pids-limit", str(plan.pids_limit),
        "--memory", str(plan.memory_bytes),
        "--cpus", str(plan.cpus),
        "--workdir", plan.workdir,
        "--tmpfs", f"/tmp:rw,nosuid,nodev,noexec,size={plan.tmpfs_bytes}",
    ]

    for key, value in sorted(plan.labels.items()):
        tokens.extend(["--label", f"{key}={value}"])

    for mount in sorted(
        plan.mounts, key=lambda item: item.container_path
    ):
        # source 已在 plan 构造阶段 resolve；destination 来自 profile 常量。
        tokens.extend(
            [
                "--mount",
                (
                    "type=bind,"
                    f"src={mount.host_path},"
                    f"dst={mount.container_path},"
                    f"{mount.mode},bind-propagation=rprivate"
                ),
            ]
        )

    for key, value in sorted(plan.env.items()):
        tokens.extend(["--env", f"{key}={value}"])

    # image 后面的所有 token 都是容器内 argv，不再被 runtime 解析为 flags。
    tokens.extend([plan.image_ref, *plan.argv])
    return tokens


def plan_sha256(plan: ContainerPlan) -> str:
    """确定性哈希；同一 plan 始终得到同一 sha256。"""

    payload = json.dumps(
        plan.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return _sha256_text(payload)

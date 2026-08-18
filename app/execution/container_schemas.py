"""Phase 27 容器计划、inspect 视图和运行记录。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ContainerMount(BaseModel):
    """host_path 只能由 Workspace/Profile 构造，不能直接来自 LLM。"""

    host_path: str
    container_path: str
    mode: Literal["ro", "rw"]


class ContainerPlan(BaseModel):
    """Podman token 的结构化输入，也是审批后可哈希的安全计划。

    计划本身不包含任何时间戳或随机字段，保证同一输入得到同一
    ``plan_sha256``，用于幂等校验和 reconcile。
    """

    job_id: str
    run_id: str
    ownership_token_hash: str
    image_ref: str
    name: str
    workdir: str
    argv: list[str]
    env: dict[str, str] = Field(default_factory=dict)
    mounts: list[ContainerMount]
    labels: dict[str, str]
    memory_bytes: int
    cpus: float
    pids_limit: int
    tmpfs_bytes: int


class ContainerInspect(BaseModel):
    """``podman inspect`` 的结构化投影，只保留业务需要的字段。"""

    container_id: str
    name: str
    running: bool
    status: str
    exit_code: int | None = None
    oom_killed: bool = False
    image_digest: str
    labels: dict[str, str] = Field(default_factory=dict)


class ContainerRuntimeRecord(BaseModel):
    """容器副作用的持久身份，不存原始 assignment token。

    使用 run-native Artifact 存储，符合 Phase 26 的 Workspace 生命周期。
    ``create -> write record -> start`` 是不可调换的 write-ahead journal。
    """

    schema_version: Literal["phase27-v1"] = "phase27-v1"
    job_id: str
    run_id: str
    ownership_token_hash: str
    container_id: str
    container_name: str
    image_ref: str
    plan_sha256: str
    status: Literal[
        "created",
        "running",
        "exited",
        "stop_requested",
        "cleanup_pending",
        "removed",
        "reconciliation_required",
    ]
    exit_code: int | None = None
    oom_killed: bool = False
    created_at: str
    updated_at: str

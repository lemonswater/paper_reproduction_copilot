from __future__ import annotations

"""Phase 27 OCI 容器运行时错误类型。

这些错误后续应映射到项目现有 ``StageError``：
- policy violation 通常 terminal；
- runtime 暂时不可用可能 retryable；
- ambiguous 必须 reconciliation，不允许简单重跑。
"""



class ContainerRuntimeError(RuntimeError):
    """所有 OCI runtime 错误的基类。"""


class ContainerRuntimeUnavailable(ContainerRuntimeError):
    """Podman 不存在、不是 rootless 或 cgroup 条件不满足。"""


class ContainerIdentityMismatch(ContainerRuntimeError):
    """inspect 得到的 ID、image 或 ownership labels 与记录不一致。"""


class ContainerStateAmbiguous(ContainerRuntimeError):
    """不能证明容器已停止，必须进入人工/后台 reconcile。"""


class ContainerPolicyViolation(ContainerRuntimeError):
    """image、mount、network 或 security plan 违反确定性策略。"""

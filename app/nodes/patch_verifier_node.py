"""Phase 43 迁移兼容入口。

旧 Checkpoint 可能把 next node 保存为 patch_verifier。该名字在迁移期
仍执行 Patch Verification Executor，然后由 Graph 路由到 patch_verdict。
新代码不要再把这个函数理解成最终 Verifier。
"""

from app.nodes.patch_verification_executor_node import (
    patch_verification_executor_node,
)


def patch_verifier_node(state: dict) -> dict:
    return patch_verification_executor_node(state)

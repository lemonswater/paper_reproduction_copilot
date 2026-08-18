"""LangGraph Checkpoint 删除适配器。"""
from __future__ import annotations
from typing import Any

class LangGraphCheckpointRetentionAdapter:
    def __init__(self, checkpointer: Any):
        self.checkpointer = checkpointer

    def delete_thread(self, thread_id: str) -> None:
        self.checkpointer.delete_thread(thread_id)

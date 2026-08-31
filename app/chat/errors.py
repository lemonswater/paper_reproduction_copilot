"""Chat 子系统可预期错误。"""

from __future__ import annotations


class ChatError(RuntimeError):
    """Chat 子系统可预期错误的基类。"""


class ChatConflictError(ChatError):
    """幂等键重用、并发冲突或持久化状态不一致。"""


class ChatUnavailableError(ChatError):
    """Provider 或结构化输出暂时不可用。"""


class ChatMemoryError(ChatError):
    """Memory 生成、验证或保存失败；本次回答可以降级继续。"""


class ChatMemoryConflict(ChatMemoryError):
    """Expected parent、range 或 hash 身份发生并发冲突。"""


class ChatMemoryUnavailable(ChatMemoryError):
    """Memory Provider/structured output 暂时不可用。"""

    def __init__(
        self,
        reason_code: str = "ChatMemoryStructuredOutputFailed",
        *,
        attempt_count: int = 0,
    ) -> None:
        # 这里只保留有限错误码和尝试次数，不能携带 Provider 原始响应、
        # Prompt、路径或校验错误全文进入 Chat API。
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.attempt_count = attempt_count


class ChatPromptBudgetExceeded(ChatUnavailableError):
    """固定规则、问题和最小 Job source 已无法放进总预算。"""

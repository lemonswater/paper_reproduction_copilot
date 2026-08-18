from __future__ import annotations


class ResearchBrowserError(RuntimeError):
    """受限研究浏览器的稳定错误基类。"""


class ResearchBrowserDisabled(ResearchBrowserError):
    """Feature Flag 关闭；此路径不得解析 Secret 或访问网络。"""


class ResearchPolicyError(ResearchBrowserError):
    """Research Policy 文件或请求范围不符合本地安全策略。"""


class ResearchUrlRejected(ResearchBrowserError):
    """URL、host、DNS、port、query 或 redirect 违反策略。"""


class ResearchRobotsDenied(ResearchBrowserError):
    """robots 明确禁止当前 User-Agent 抓取目标路径。"""


class ResearchLimitExceeded(ResearchBrowserError):
    """查询数、页面数、字节、PDF 页数、时间或文本预算超限。"""


class ResearchTransportUnavailable(ResearchBrowserError):
    """Search Provider 或目标站点发生可重试网络故障。"""


class ResearchContentRejected(ResearchBrowserError):
    """响应类型、magic bytes、编码或正文形状不允许进入抽取。"""


class ResearchNotFound(ResearchBrowserError):
    """Session、Pack、Citation 或 Resource Candidate 不存在。"""


class ResearchConflict(ResearchBrowserError):
    """version、lease、idempotency 或状态迁移冲突。"""


class ResearchIntegrityError(ResearchBrowserError):
    """持久化 Hash、Pack 引用或 Citation 身份不自洽。"""


class ResearchSynthesisRejected(ResearchBrowserError):
    """模型返回未知 Citation/Candidate 或越权字段。"""


class ResearchResourceCandidateRejected(ResearchBrowserError):
    """候选不完整、已过期或不能转换为 Phase 29 ResourceRequest。"""

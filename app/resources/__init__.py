"""Phase 29 受控资源获取与供应链安全。

网络权限只属于独立 Acquisition Worker；Graph/LLM 只能提出待确认 proposal，
最终执行容器保持 ``network=none``。
"""

from __future__ import annotations

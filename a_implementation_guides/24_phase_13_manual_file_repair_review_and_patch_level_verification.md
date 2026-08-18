# 24. Phase 13：Manual File Repair Review 与 Patch-Level Verification

上一阶段已经把 LLM structured output 补成了一条可重试、可观察、可降级的可靠链。

这一阶段才开始让 Agent 接触“修改仓库文件”这件事，但边界必须非常明确：

```text
模型提出结构化文本替换
        ↓
程序校验路径、原文和修改规模
        ↓
程序生成统一 diff、原文件哈希和 patch 哈希
        ↓
人工审批同一份 patch
        ↓
只在隔离 Git worktree 中应用并验证
        ↓
人工确认是否推广到原仓库
        ↓
再次检查所有哈希后才应用
        ↓
重新进入 risk_check -> preflight -> smoke -> executor
```

本阶段不是让 Agent 自由改代码，而是建立一条：

```text
可审阅、可校验、可追踪、可拒绝、不会静默覆盖用户代码
```

的最小文件修复链。

---

## 一、本阶段解决什么问题

Phase 11 的 bounded repair 只能修改命令参数，例如：

```text
--batch_size 8 -> --batch_size 1
```

但有些失败不能靠改命令解决，例如：

```text
TypeError: forward() got an unexpected keyword argument 'xyz'
AttributeError: object has no attribute 'foo'
shape mismatch caused by an incorrect reshape
配置读取代码使用了错误字段名
论文仓库只兼容旧版 API，需要做一处小范围兼容修改
```

此时当前系统通常只能返回：

```json
{
  "kind": "manual_only",
  "summary": "需要修改源码"
}
```

它能说明方向，却没有形成真正闭环。

本阶段补齐以下能力：

1. 从失败日志和相关源码中生成结构化文件修复建议。
2. 不信任模型给出的路径和文本，由程序做确定性约束。
3. 由程序生成 unified diff，而不是让模型直接拼 diff。
4. 审批记录绑定 patch SHA-256，防止审批后内容被替换。
5. 验证前检查原文件 SHA-256，防止基线文件已经变化。
6. 先在隔离 worktree 验证，不直接触碰原仓库。
7. 验证通过后再次人工确认，才推广到原仓库。
8. 推广后让原执行动作重新走风险、审批、预检和 smoke 链。

---

## 二、先明确本阶段的安全边界

第一版只允许：

```text
修改已有的 UTF-8 文本文件
每个 old_text 在原文件中精确出现一次
每个文件做少量精确替换
最多修改少量文件和少量行
只修改允许的源码/配置后缀
只在 Git 仓库且 tracked files 干净时生成 patch
```

第一版明确不允许：

```text
创建文件
删除文件
重命名文件
修改二进制文件
修改 .git
修改 .env、密钥、凭据文件
修改仓库外路径
修改符号链接指向的文件
由模型提供任意 shell 验证命令
跳过审批直接应用
验证失败后仍推广到原仓库
自动提交或 push Git
```

为什么要限制得这么严格？

因为文件写入与命令参数调整的风险不同。命令参数修错通常只导致一次实验失败；源码修改如果越界，可能覆盖用户工作、改变实验语义，甚至写入仓库外部文件。

---

## 三、为什么不让 LLM 直接返回 unified diff

让模型直接输出下面的内容看起来很方便：

```diff
--- a/model.py
+++ b/model.py
@@ -10,7 +10,7 @@
- old code
+ new code
```

但第一版不建议这么做，原因包括：

- 行号和上下文容易与真实文件不一致。
- 模型可能遗漏换行符或生成格式不合法的 hunk。
- diff 中可能偷偷出现提示里没有讨论过的文件。
- 很难在 Pydantic schema 中表达“这个 diff 一定安全”。
- 结构合法不代表 patch 能应用。

本教程改为让模型输出：

```json
{
  "relative_path": "models/p4transformer.py",
  "replacements": [
    {
      "old_text": "x = x.view(b, t, n, c)",
      "new_text": "x = x.reshape(b, t, n, c)",
      "reason": "输入可能不是 contiguous tensor"
    }
  ]
}
```

程序再完成：

```text
路径约束
old_text 唯一性检查
修改规模检查
before/after SHA-256
unified diff 生成
patch SHA-256
```

核心原则是：

```text
LLM 负责提出语义修改
程序负责把修改变成可验证的 patch
```

---

## 四、最终工作流

本阶段完成后的失败修复流程如下：

```text
executor / smoke_test failed
        ↓
log_debug
        ↓
repair_planner
        ├── edit_command -> 原有 command repair
        ├── no_repair -> final_report
        └── manual_only + 有相关源码证据
                    ↓
            file_repair_planner
                    ↓
              patch_builder
                    ↓
            patch_review interrupt
                    ↓ approved
              patch_verifier
          （隔离 worktree 中验证）
                    ↓ passed
        patch_promotion_review interrupt
                    ↓ approved
               patch_apply
                    ↓
                risk_check
                    ↓
          preflight -> smoke -> executor
```

这里有两次人工确认：

### 第一次：Patch Review

用户确认：

```text
我同意验证这一份具体 patch
```

此时不会修改原仓库。

### 第二次：Patch Promotion Review

用户确认：

```text
这份 patch 已在隔离 worktree 验证通过
我同意把同一份 patch 应用到原仓库
```

两次记录分别绑定：

```text
patch_sha256
verification_sha256
```

---

## 五、建议新增和修改的文件

建议新增：

```text
app/prompts/file_repair_prompt.py
app/tools/patch_tools.py
app/nodes/file_repair_planner_node.py
app/nodes/patch_builder_node.py
app/nodes/patch_review_node.py
app/nodes/patch_verifier_node.py
app/nodes/patch_promotion_review_node.py
app/nodes/patch_apply_node.py

tests/test_patch_tools.py
tests/test_patch_review_nodes.py
tests/test_patch_verifier_node.py
tests/test_file_repair_flow.py
```

建议修改：

```text
.env.example
app/config.py
app/schemas.py
app/state.py
app/graph.py
app/main.py
app/tools/action_tools.py
app/tools/artifact_tools.py
app/nodes/final_report_node.py
```

---

## 六、增加配置开关和修改规模限制

先修改：

```text
app/config.py
```

在 `Settings` 中增加：

```python
@dataclass
class Settings:
    # ...保留已有配置...

    # 文件修复默认关闭。先通过单测和演示仓库验证，再在真实仓库中开启。
    enable_file_repair: bool = _env_bool(
        "ENABLE_FILE_REPAIR",
        False,
    )

    # 一次 proposal 最多修改两个文件，避免模型把重构包装成 bug fix。
    max_patch_files: int = int(
        os.getenv("MAX_PATCH_FILES", "2")
    )

    # 所有文件加起来最多执行四个精确文本替换。
    max_patch_replacements: int = int(
        os.getenv("MAX_PATCH_REPLACEMENTS", "4")
    )

    # 按 diff opcode 统计修改规模，超过后降级为人工处理。
    max_patch_changed_lines: int = int(
        os.getenv("MAX_PATCH_CHANGED_LINES", "80")
    )

    # 不把超大源码文件完整塞给模型，也不允许第一版 patch 它们。
    max_patch_file_bytes: int = int(
        os.getenv("MAX_PATCH_FILE_BYTES", str(512 * 1024))
    )

    # 隔离 worktree 中单个验证动作的超时时间。
    patch_verify_timeout_seconds: int = int(
        os.getenv("PATCH_VERIFY_TIMEOUT_SECONDS", "120")
    )

    # 第一版每个 graph run 最多尝试一次 file-level repair。
    max_file_repair_attempts: int = int(
        os.getenv("MAX_FILE_REPAIR_ATTEMPTS", "1")
    )
```

然后修改：

```text
.env.example
```

增加：

```dotenv
# 第一轮测试时保持 false；确认测试通过后再临时设为 true。
ENABLE_FILE_REPAIR=false

MAX_PATCH_FILES=2
MAX_PATCH_REPLACEMENTS=4
MAX_PATCH_CHANGED_LINES=80
MAX_PATCH_FILE_BYTES=524288
PATCH_VERIFY_TIMEOUT_SECONDS=120
MAX_FILE_REPAIR_ATTEMPTS=1
```

不要把 `ENABLE_FILE_REPAIR=true` 写成默认值。写文件能力应该显式开启。

---

## 七、增加 Patch 相关 Schema

修改：

```text
app/schemas.py
```

在文件末尾增加以下模型。

```python
class TextReplacement(BaseModel):
    """LLM 提出的一个精确文本替换，不包含路径和 shell 命令。"""

    old_text: str
    new_text: str
    reason: str

    @model_validator(mode="after")
    def validate_replacement(self) -> "TextReplacement":
        if not self.old_text:
            raise ValueError("old_text must not be empty")
        if self.old_text == self.new_text:
            raise ValueError("old_text and new_text must be different")
        return self


class FileEditDraft(BaseModel):
    """针对一个已有仓库文件的有限修改。"""

    relative_path: str
    reason: str
    replacements: list[TextReplacement] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_file_edit(self) -> "FileEditDraft":
        if not self.relative_path.strip():
            raise ValueError("relative_path must not be empty")
        if not self.replacements:
            raise ValueError("file edit requires at least one replacement")
        return self


class FileRepairProposal(BaseModel):
    """模型层的文件修复建议；它还不是可应用 patch。"""

    proposal_id: str | None = None
    kind: Literal["patch", "manual_only", "no_patch"] = "no_patch"
    summary: str
    root_cause: str
    edits: list[FileEditDraft] = Field(default_factory=list)
    verification_targets: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    bounded: bool = True

    @model_validator(mode="after")
    def validate_file_repair_semantics(self) -> "FileRepairProposal":
        if self.bounded is not True:
            raise ValueError("file repair proposal must keep bounded=true")

        if self.kind == "patch" and not self.edits:
            raise ValueError("kind=patch requires edits")

        if self.kind != "patch" and self.edits:
            raise ValueError("manual_only/no_patch must not contain edits")

        return self


class PatchFileRecord(BaseModel):
    """程序生成的单文件 patch 元数据。"""

    relative_path: str
    before_sha256: str
    after_sha256: str
    replacement_count: int
    changed_line_count: int


class PatchBundle(BaseModel):
    """可供审批和验证的确定性 patch 包。"""

    patch_id: str
    proposal_id: str
    repo_path: str
    base_git_commit: str
    patch_path: str
    patch_sha256: str
    files: list[PatchFileRecord] = Field(default_factory=list)
    summary: str
    generated_at: str


class PatchApprovalRecord(BaseModel):
    """第一次人工审批：是否允许验证这一份 patch。"""

    approval_id: str
    patch_id: str
    patch_sha256: str
    decision: Literal["approved", "rejected", "revise"]
    reviewer: str = "human"
    reviewed_at: str
    comment: str | None = None


class PatchVerificationCheck(BaseModel):
    name: str
    status: Literal["passed", "failed", "skipped"]
    command: list[str] = Field(default_factory=list)
    returncode: int | None = None
    output_preview: str = ""


class PatchVerificationReport(BaseModel):
    """隔离 worktree 中的 patch-level 验证结果。"""

    patch_id: str
    patch_sha256: str
    execution_profile_id: str
    # 记录复制前原 profile 的指纹；worktree 路径单独记录。
    execution_profile_fingerprint: str
    execution_backend: Literal["local", "conda"]
    status: Literal["passed", "failed", "blocked"]
    worktree_path: str | None = None
    checks: list[PatchVerificationCheck] = Field(default_factory=list)
    summary: str
    generated_at: str
    verification_sha256: str | None = None


class PatchPromotionRecord(BaseModel):
    """第二次人工审批：是否把已验证 patch 推广到原仓库。"""

    promotion_id: str
    patch_id: str
    patch_sha256: str
    verification_sha256: str
    decision: Literal["approved", "rejected"]
    reviewer: str = "human"
    reviewed_at: str
    comment: str | None = None


class PatchApplicationRecord(BaseModel):
    """patch 真正应用到原仓库后的审计记录。"""

    patch_id: str
    patch_sha256: str
    repo_path: str
    status: Literal["applied", "failed", "blocked"]
    files: list[PatchFileRecord] = Field(default_factory=list)
    applied_at: str
    error: str | None = None
```

这里需要特别区分三个对象：

```text
FileRepairProposal：模型建议
PatchBundle：程序生成、可以审批的确定性补丁
PatchVerificationReport：隔离环境中的验证事实
```

不要把模型建议直接叫作 `PatchBundle`，否则容易让后续代码误以为它已经通过路径、哈希和规模检查。

---

## 八、扩展 Graph State

修改：

```text
app/state.py
```

在 `ReproductionState` 中增加：

```python
class ReproductionState(TypedDict, total=False):
    # ...保留已有字段...

    # LLM 生成的文件级修复建议。
    file_repair_proposal: Optional[dict[str, Any]]

    # 程序根据 proposal 和真实文件生成的确定性 patch。
    pending_patch: Optional[dict[str, Any]]
    pending_patch_hash: Optional[str]

    # 第一次人工审批，绑定 pending_patch_hash。
    patch_approval: Optional[str]
    patch_feedback: Optional[str]
    patch_approval_record: Optional[dict[str, Any]]

    # 隔离 worktree 中的验证结果。
    patch_verification_report: Optional[dict[str, Any]]
    patch_verification_passed: bool
    patch_verification_hash: Optional[str]

    # 第二次人工确认，绑定 patch hash + verification hash。
    patch_promotion_decision: Optional[str]
    patch_promotion_feedback: Optional[str]
    patch_promotion_record: Optional[dict[str, Any]]

    # patch 应用到原仓库后的记录。
    patch_application_record: Optional[dict[str, Any]]
    applied_patch_hash: Optional[str]

    # 单独限制 file-level repair 次数，不与 command repair 混用。
    file_repair_attempt_count: int
    file_repair_history: list[dict[str, Any]]
```

为什么 command repair 和 file repair 要分开计数？

因为两者成本和风险不同：

```text
command repair：重新构建命令
file repair：生成 patch、两次审批、worktree 验证、修改源码
```

如果共用一个计数器，会出现“先缩小 batch size 一次，就再也不能尝试文件修复”的不合理情况。

---

## 九、让执行动作绑定已应用 Patch

文件修改后，原来的命令文本可能完全没变，但执行语义已经变了。

例如审批时命令是：

```text
python train.py --batch_size 1
```

应用 patch 后命令仍然是同一句，但 `train.py` 的代码已经变化。此时不能继续沿用旧 action hash。

先修改 `ExecutableAction`：

```python
class ExecutableAction(BaseModel):
    # ...保留已有字段...

    # 没有文件修复时为 None；应用 patch 后写入 patch SHA-256。
    repo_patch_hash: str | None = None
```

再修改：

```text
app/tools/action_tools.py
```

在 `compute_action_hash()` 的 material 中增加：

```python
def compute_action_hash(action: dict) -> str:
    material = {
        # ...保留已有字段...
        "execution_profile_id": action.get("execution_profile_id"),
        "execution_profile_fingerprint": action.get(
            "execution_profile_fingerprint"
        ),

        # 同一条命令在 patch 前后必须生成不同 action hash。
        "repo_patch_hash": action.get("repo_patch_hash"),
    }

    payload = json.dumps(material, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

这一步非常重要，它把审批语义从：

```text
我审批了这条命令
```

升级为：

```text
我审批了这条命令 + 这个执行环境 + 这份已应用源码补丁
```

---

## 十、编写 File Repair Prompt

新增：

```text
app/prompts/file_repair_prompt.py
```

内容如下：

```python
FILE_REPAIR_PROMPT = """
你是论文复现实验中的 file repair planner。

你的任务是根据失败日志、结构化 debug report 和受限源码上下文，
提出一个最小、可审阅、可验证的精确文本替换方案。

严格要求：
1. 只允许 kind=patch、manual_only、no_patch。
2. kind=patch 时，只能修改“源码上下文”中明确提供的已有文件。
3. 不允许创建、删除、重命名文件。
4. 不允许修改 .git、.env、密钥、凭据、数据集或二进制文件。
5. 不允许输出 shell 命令，不允许安装依赖，不允许 sudo。
6. 每个 replacement 必须提供可在原文件中精确匹配的 old_text。
7. old_text 应包含足够上下文，使它在文件中只出现一次。
8. new_text 只做解决当前错误所需的最小修改，不做重构和格式化。
9. 如果根因是环境、依赖缺失、数据路径或用户配置，返回 manual_only。
10. 如果证据不足、源码被截断或无法确定唯一修改位置，返回 no_patch。
11. verification_targets 只能填写已有测试文件的仓库相对路径；
    不确定时返回空数组，程序仍会执行确定性语法检查；
    patch 推广后再进入正常 smoke 链。
12. bounded 必须为 true。
13. 只返回符合 FileRepairProposal schema 的 JSON，不输出 Markdown。

当前执行模式：
{execution_mode}

Debug Report：
{debug_report}

失败 traceback：
{traceback}

当前执行动作：
{pending_action}

受限源码上下文：
{source_context}
"""
```

Prompt 中最重要的一条不是“输出 JSON”，而是：

```text
只能修改程序已经提供的源码上下文
```

不过 Prompt 只是软约束。真正的安全边界仍然必须在 `patch_tools.py` 中实现。

---

## 十一、实现确定性的 Patch 工具层

新增：

```text
app/tools/patch_tools.py
```

这一文件是本阶段最核心的安全层。

### 11.1 基础常量、哈希与路径约束

```python
from __future__ import annotations

import difflib
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import settings
from app.execution.base import ExecutionRunner
from app.execution.profile_store import (
    compute_execution_profile_fingerprint,
    get_execution_profile,
)
from app.execution.registry import build_execution_runner
from app.schemas import (
    FileRepairProposal,
    PatchApplicationRecord,
    PatchBundle,
    PatchFileRecord,
    PatchVerificationCheck,
    PatchVerificationReport,
)


# 第一版只开放容易审阅的文本格式。
ALLOWED_PATCH_SUFFIXES = {
    ".py",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
}

# 即使后缀符合，也不能触碰这些目录或文件名。
BLOCKED_PATH_PARTS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "data",
    "datasets",
    "checkpoints",
}

BLOCKED_FILE_NAMES = {
    ".env",
    ".env.local",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_git(repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """所有 Git 调用都使用 token 列表和 shell=False。"""

    return subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )


def get_git_commit(repo_path: Path) -> str:
    result = _run_git(repo_path, ["rev-parse", "HEAD"])
    if result.returncode != 0:
        raise ValueError(
            "file repair requires a Git repository with a valid HEAD: "
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()


def ensure_clean_tracked_files(repo_path: Path) -> None:
    """
    第一版不在 dirty tracked tree 上生成 patch。

    `--untracked-files=no` 允许仓库存在数据集等未跟踪文件，
    但任何已跟踪文件的未提交修改都会阻止 file repair。
    """

    result = _run_git(
        repo_path,
        ["status", "--porcelain", "--untracked-files=no"],
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "cannot read git status")
    if result.stdout.strip():
        raise ValueError(
            "tracked files are dirty; commit or stash user changes before "
            "building an automated patch"
        )


def resolve_patch_target(repo_path: Path, relative_path: str) -> Path:
    """把模型路径限制在 repo_path 内的已有普通文本文件。"""

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"absolute patch path is not allowed: {relative_path}")
    if ".." in candidate.parts:
        raise ValueError(f"parent traversal is not allowed: {relative_path}")

    if any(part in BLOCKED_PATH_PARTS for part in candidate.parts):
        raise ValueError(f"blocked patch path: {relative_path}")
    if candidate.name.lower() in BLOCKED_FILE_NAMES:
        raise ValueError(f"blocked patch file: {relative_path}")
    if candidate.suffix.lower() not in ALLOWED_PATCH_SUFFIXES:
        raise ValueError(f"unsupported patch suffix: {candidate.suffix}")

    root = repo_path.resolve()
    target = (root / candidate).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"patch target escapes repository: {relative_path}")

    # `resolve()` 会跟随 symlink，所以还要检查路径本身是不是链接。
    unresolved_target = root / candidate
    if unresolved_target.is_symlink():
        raise ValueError(f"symlink patch target is not allowed: {relative_path}")
    if not target.exists() or not target.is_file():
        raise ValueError(f"patch target must be an existing file: {relative_path}")
    if target.stat().st_size > settings.max_patch_file_bytes:
        raise ValueError(f"patch target is too large: {relative_path}")

    return target
```

### 11.2 精确替换与修改规模统计

继续在同一文件中增加：

```python
def apply_exact_replacements(
    original_text: str,
    replacements: list[dict[str, str]],
) -> str:
    """
    顺序执行精确替换。

    每个 old_text 必须在“当前版本文本”中恰好出现一次。
    出现 0 次说明上下文过期；出现多次说明定位不唯一。
    """

    updated = original_text
    for index, replacement in enumerate(replacements):
        old_text = replacement["old_text"]
        new_text = replacement["new_text"]
        occurrence_count = updated.count(old_text)

        if occurrence_count != 1:
            raise ValueError(
                f"replacement {index} old_text must occur exactly once; "
                f"found {occurrence_count}"
            )

        updated = updated.replace(old_text, new_text, 1)

    if updated == original_text:
        raise ValueError("patch does not change file content")
    return updated


def count_changed_lines(before: str, after: str) -> int:
    """按 SequenceMatcher opcode 统计新增、删除或替换影响的行数。"""

    before_lines = before.splitlines()
    after_lines = after.splitlines()
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines)
    changed = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changed += max(i2 - i1, j2 - j1)

    return changed


def build_unified_diff(relative_path: str, before: str, after: str) -> str:
    """统一由程序生成 diff，确保文件路径和上下文来自真实文件。"""

    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )
```

### 11.3 生成 PatchBundle

继续增加：

```python
def build_patch_bundle(
    *,
    repo_path: str,
    proposal: FileRepairProposal,
    bundle_root: Path,
) -> PatchBundle:
    """
    把 LLM proposal 编译成确定性 patch。

    这个函数只读取原仓库并写入 bundle_root，绝不修改原仓库文件。
    """

    if proposal.kind != "patch":
        raise ValueError("only kind=patch can build a patch bundle")

    repo = Path(repo_path).resolve()
    if not repo.exists() or not repo.is_dir():
        raise ValueError(f"repository does not exist: {repo}")

    ensure_clean_tracked_files(repo)
    base_commit = get_git_commit(repo)

    if len(proposal.edits) > settings.max_patch_files:
        raise ValueError(
            f"patch touches too many files: {len(proposal.edits)} > "
            f"{settings.max_patch_files}"
        )

    total_replacements = sum(len(edit.replacements) for edit in proposal.edits)
    if total_replacements > settings.max_patch_replacements:
        raise ValueError(
            f"patch has too many replacements: {total_replacements} > "
            f"{settings.max_patch_replacements}"
        )

    # 同一个路径只能出现一次，否则替换顺序容易产生歧义。
    relative_paths = [edit.relative_path for edit in proposal.edits]
    if len(relative_paths) != len(set(relative_paths)):
        raise ValueError("duplicate relative_path in patch proposal")

    patch_id = f"patch_{uuid4().hex[:12]}"
    # 保存绝对路径，避免跨进程 resume 时工作目录变化导致找错 artifact。
    patch_dir = bundle_root.resolve() / patch_id
    patch_dir.mkdir(parents=True, exist_ok=False)

    diff_parts: list[str] = []
    file_records: list[PatchFileRecord] = []
    total_changed_lines = 0

    for edit in proposal.edits:
        target = resolve_patch_target(repo, edit.relative_path)
        try:
            before = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"patch target is not UTF-8 text: {edit.relative_path}"
            ) from exc

        after = apply_exact_replacements(
            before,
            [item.model_dump() for item in edit.replacements],
        )
        changed_line_count = count_changed_lines(before, after)
        total_changed_lines += changed_line_count

        diff_text = build_unified_diff(edit.relative_path, before, after)
        if not diff_text:
            raise ValueError(f"empty diff for {edit.relative_path}")
        diff_parts.append(diff_text)

        file_records.append(
            PatchFileRecord(
                relative_path=edit.relative_path,
                before_sha256=sha256_text(before),
                after_sha256=sha256_text(after),
                replacement_count=len(edit.replacements),
                changed_line_count=changed_line_count,
            )
        )

    if total_changed_lines > settings.max_patch_changed_lines:
        raise ValueError(
            f"patch changes too many lines: {total_changed_lines} > "
            f"{settings.max_patch_changed_lines}"
        )

    patch_path = patch_dir / "patch.diff"
    patch_text = "".join(diff_parts)
    patch_path.write_text(patch_text, encoding="utf-8")
    patch_hash = sha256_file(patch_path)

    bundle = PatchBundle(
        patch_id=patch_id,
        proposal_id=proposal.proposal_id or "unknown",
        repo_path=str(repo),
        base_git_commit=base_commit,
        patch_path=str(patch_path),
        patch_sha256=patch_hash,
        files=file_records,
        summary=proposal.summary,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    bundle_path = patch_dir / "patch_bundle.json"
    bundle_path.write_text(
        bundle.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return bundle
```

注意这里没有把 `after` 写回原文件。`build_patch_bundle()` 的唯一副作用是写审计产物。

### 11.4 校验审批时看到的 Patch 是否仍然相同

继续增加：

```python
def validate_patch_bundle(
    bundle: PatchBundle,
    *,
    require_clean_repo: bool = True,
) -> None:
    """在验证和推广前重复检查 patch、commit 与每个原文件哈希。"""

    repo = Path(bundle.repo_path).resolve()
    patch_path = Path(bundle.patch_path).resolve()

    if not patch_path.exists() or not patch_path.is_file():
        raise ValueError(f"patch file is missing: {patch_path}")
    if sha256_file(patch_path) != bundle.patch_sha256:
        raise ValueError("patch file changed after bundle creation")

    current_commit = get_git_commit(repo)
    if current_commit != bundle.base_git_commit:
        raise ValueError(
            "repository HEAD changed after patch creation: "
            f"{bundle.base_git_commit} -> {current_commit}"
        )

    if require_clean_repo:
        ensure_clean_tracked_files(repo)

    for file_record in bundle.files:
        target = resolve_patch_target(repo, file_record.relative_path)
        if sha256_file(target) != file_record.before_sha256:
            raise ValueError(
                "source file changed after patch creation: "
                f"{file_record.relative_path}"
            )


def compute_verification_hash(report: PatchVerificationReport) -> str:
    """对验证报告做 canonical JSON 哈希，供第二次人工确认绑定。"""

    material = report.model_dump(exclude={"verification_sha256"})
    payload = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_text(payload)
```

---

## 十二、收集最小源码上下文

继续在 `app/tools/patch_tools.py` 增加：

```python
def collect_source_context(
    *,
    repo_path: str,
    related_files: list[str],
    max_files: int = 3,
    max_chars_per_file: int = 12000,
) -> tuple[str, list[str]]:
    """
    只读取 debug_report 明确指出的已有相对路径。

    第一版不对整个仓库做模糊搜索，避免把大量无关代码交给模型。
    返回值中的第二项是程序实际允许修改的路径白名单。
    """

    repo = Path(repo_path).resolve()
    sections: list[str] = []
    allowed_paths: list[str] = []

    for raw_path in related_files[:max_files]:
        try:
            target = resolve_patch_target(repo, raw_path)
        except ValueError:
            # 模型给出的不存在或越界路径不会进入上下文。
            continue

        text = target.read_text(encoding="utf-8", errors="strict")
        if len(text) > max_chars_per_file:
            # 截断文件可以用于判断，但不应自动 patch 截断区外内容。
            text = text[:max_chars_per_file]
            truncation_note = "\n# [context truncated by agent]\n"
        else:
            truncation_note = ""

        relative = target.relative_to(repo).as_posix()
        allowed_paths.append(relative)
        sections.extend(
            [
                f"===== FILE: {relative} =====",
                text + truncation_note,
                f"===== END FILE: {relative} =====",
            ]
        )

    return "\n".join(sections), allowed_paths
```

第一版要求 `debug_report.related_files` 是准确的仓库相对路径。如果模型只返回文件名但文件位于深层目录，先改进 debug evidence，不要在文件修复节点里无边界 `rglob()`。

---

## 十三、实现 File Repair Planner Node

新增：

```text
app/nodes/file_repair_planner_node.py
```

```python
import json
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.model import get_chat_model
from app.prompts.file_repair_prompt import FILE_REPAIR_PROMPT
from app.schemas import FileRepairProposal
from app.tools.log_tools import extract_traceback, read_log
from app.tools.patch_tools import collect_source_context
from app.tools.structured_output_tools import (
    invoke_structured_with_retry,
    write_structured_output_trace,
)


def _no_patch(summary: str, root_cause: str) -> FileRepairProposal:
    """任何输入不足或校验失败都安全降级，不生成文件修改。"""

    return FileRepairProposal(
        proposal_id=f"file_repair_{uuid4().hex[:12]}",
        kind="no_patch",
        summary=summary,
        root_cause=root_cause,
        edits=[],
        verification_targets=[],
        risks=["证据不足时自动修改源码可能改变论文实现语义。"],
        bounded=True,
    )


def file_repair_planner_node(state: dict) -> dict:
    if not settings.enable_file_repair:
        proposal = _no_patch(
            "file repair is disabled",
            "ENABLE_FILE_REPAIR is false",
        )
        return {"file_repair_proposal": proposal.model_dump()}

    attempts = int(state.get("file_repair_attempt_count", 0))
    if attempts >= settings.max_file_repair_attempts:
        proposal = _no_patch(
            "file repair limit reached",
            "the current run has already attempted file-level repair",
        )
        return {"file_repair_proposal": proposal.model_dump()}

    repo_path = state.get("repo_path")
    debug_report = state.get("debug_report") or {}
    log_path = state.get("log_path")
    related_files = list(debug_report.get("related_files") or [])

    if not repo_path or not log_path or not related_files:
        proposal = _no_patch(
            "missing evidence for file repair",
            "repo_path, log_path or debug_report.related_files is empty",
        )
        return {"file_repair_proposal": proposal.model_dump()}

    try:
        source_context, allowed_paths = collect_source_context(
            repo_path=repo_path,
            related_files=related_files,
        )
        traceback = extract_traceback(read_log(log_path))
    except (FileNotFoundError, UnicodeDecodeError, ValueError) as exc:
        proposal = _no_patch(
            "cannot collect safe source context",
            str(exc),
        )
        return {"file_repair_proposal": proposal.model_dump()}

    if not allowed_paths or not traceback.strip():
        proposal = _no_patch(
            "source context or traceback is empty",
            "there is not enough exact evidence to propose a patch",
        )
        return {"file_repair_proposal": proposal.model_dump()}

    prompt = FILE_REPAIR_PROMPT.format(
        execution_mode=state.get("active_execution_mode", "unknown"),
        debug_report=json.dumps(debug_report, ensure_ascii=False, indent=2),
        traceback=traceback,
        pending_action=json.dumps(
            state.get("pending_action") or {},
            ensure_ascii=False,
            indent=2,
        ),
        source_context=source_context,
    )

    invocation = invoke_structured_with_retry(
        llm=get_chat_model(temperature=0),
        schema=FileRepairProposal,
        prompt=prompt,
        method=settings.structured_output_method,
        strict=settings.structured_output_strict,
        max_retries=settings.structured_output_max_retries,
        raw_preview_chars=settings.structured_output_raw_preview_chars,
    )

    if invocation.value is None:
        proposal = _no_patch(
            "model did not return a valid file repair proposal",
            "structured output retries were exhausted",
        )
    else:
        proposal = invocation.value
        if not proposal.proposal_id:
            proposal = proposal.model_copy(
                update={"proposal_id": f"file_repair_{uuid4().hex[:12]}"}
            )

        # Prompt 白名单必须再由程序强制检查。
        proposed_paths = {edit.relative_path for edit in proposal.edits}
        if not proposed_paths.issubset(set(allowed_paths)):
            proposal = _no_patch(
                "proposal references files outside supplied context",
                "the model attempted to patch a non-whitelisted path",
            )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = settings.output_dir / "file_repair_proposal.json"
    proposal_path.write_text(
        proposal.model_dump_json(indent=2),
        encoding="utf-8",
    )

    trace_path = write_structured_output_trace(
        result=invocation,
        node_name="file_repair_planner",
        schema_name="FileRepairProposal",
        output_dir=settings.output_dir,
        fallback_used=invocation.value is None,
    )

    return {
        "file_repair_proposal": proposal.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(proposal_path),
            str(trace_path),
        ],
    }
```

这里没有直接调用 `Path.write_text()` 修改仓库。Planner 只产生 proposal artifact。

---

## 十四、实现 Patch Builder Node

新增：

```text
app/nodes/patch_builder_node.py
```

```python
from pathlib import Path

from pydantic import ValidationError

from app.config import settings
from app.schemas import FileRepairProposal
from app.tools.patch_tools import build_patch_bundle


def patch_builder_node(state: dict) -> dict:
    raw_proposal = state.get("file_repair_proposal")
    if not raw_proposal:
        return {
            "pending_patch": None,
            "pending_patch_hash": None,
            "final_status": "no_file_repair_proposal",
        }

    try:
        proposal = FileRepairProposal.model_validate(raw_proposal)
    except ValidationError as exc:
        return {
            "pending_patch": None,
            "pending_patch_hash": None,
            "final_status": "invalid_file_repair_proposal",
            "error": str(exc),
        }

    if proposal.kind != "patch":
        return {
            "pending_patch": None,
            "pending_patch_hash": None,
            "final_status": "file_repair_proposal_only",
        }

    # patch 产物放进当前 run 下，便于与其他 run 隔离。
    run_dir = state.get("run_dir")
    bundle_root = (
        Path(run_dir) / "debug" / "patches"
        if run_dir
        else settings.output_dir / "patches"
    )
    bundle_root.mkdir(parents=True, exist_ok=True)

    try:
        bundle = build_patch_bundle(
            repo_path=state["repo_path"],
            proposal=proposal,
            bundle_root=bundle_root,
        )
    except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
        return {
            "pending_patch": None,
            "pending_patch_hash": None,
            "final_status": "patch_out_of_bounds",
            "error": str(exc),
        }

    bundle_path = Path(bundle.patch_path).with_name("patch_bundle.json")
    return {
        "pending_patch": bundle.model_dump(),
        "pending_patch_hash": bundle.patch_sha256,
        "patch_approval": None,
        "patch_feedback": None,
        "patch_approval_record": None,
        "patch_verification_report": None,
        "patch_verification_passed": False,
        "patch_verification_hash": None,
        "patch_promotion_decision": None,
        "patch_promotion_record": None,
        "output_files": [
            *state.get("output_files", []),
            bundle.patch_path,
            str(bundle_path),
        ],
    }
```

`pending_patch` 只有在所有确定性检查都通过后才会出现。

---

## 十五、实现第一次 Patch Review Interrupt

新增：

```text
app/nodes/patch_review_node.py
```

```python
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from langgraph.types import interrupt

from app.config import settings
from app.schemas import PatchApprovalRecord, PatchBundle
from app.tools.patch_tools import sha256_file, validate_patch_bundle


def patch_review_node(state: dict) -> dict:
    bundle = PatchBundle.model_validate(state.get("pending_patch"))

    # interrupt 前先确认磁盘上的 diff 与 state 中 hash 一致。
    try:
        validate_patch_bundle(bundle)
    except (OSError, ValueError) as exc:
        return {
            "patch_approval": "blocked",
            "patch_approval_record": None,
            "final_status": "stale_patch_before_review",
            "error": str(exc),
        }

    patch_text = Path(bundle.patch_path).read_text(encoding="utf-8")
    response = interrupt(
        {
            "review_type": "patch_review",
            "message": "Review the exact patch before isolated verification.",
            "patch_id": bundle.patch_id,
            "patch_sha256": bundle.patch_sha256,
            "base_git_commit": bundle.base_git_commit,
            "files": [item.model_dump() for item in bundle.files],
            "patch_path": bundle.patch_path,
            # 终端可直接展示，但限制预览大小，完整内容仍以文件为准。
            "patch_preview": patch_text[:12000],
            "allowed_decisions": ["approved", "rejected", "revise"],
        }
    )

    raw_decision = str(response.get("decision", "rejected"))
    decision = raw_decision
    feedback = response.get("feedback")
    if decision not in {"approved", "rejected", "revise"}:
        decision = "rejected"
        feedback = f"invalid patch review decision: {raw_decision}"

    # 从 interrupt 恢复后再检查一次，避免暂停期间 patch 被替换。
    try:
        validate_patch_bundle(bundle)
    except (OSError, ValueError) as exc:
        return {
            "patch_approval": "blocked",
            "patch_approval_record": None,
            "final_status": "stale_patch_after_review",
            "error": str(exc),
        }

    record = PatchApprovalRecord(
        approval_id=f"patch_approval_{uuid4().hex[:12]}",
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        decision=decision,
        reviewer="human",
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        comment=feedback,
    )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    record_path = settings.output_dir / "patch_approval_record.json"
    record_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    return {
        "patch_approval": decision,
        "patch_feedback": feedback,
        "patch_approval_record": record.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(record_path),
        ],
    }
```

注意：`interrupt()` 恢复时节点会从头重新执行。因此所有 interrupt 前操作都必须可重复且不能修改原仓库。

---

## 十六、在隔离 Git Worktree 中验证 Patch

继续修改 `app/tools/patch_tools.py`，加入 worktree 验证函数。

```python
def _run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> PatchVerificationCheck:
    """运行由程序构造的固定命令，不接受 LLM shell 字符串。"""

    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
        output = (result.stdout or "")
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr

        return PatchVerificationCheck(
            name=" ".join(command[:3]),
            status="passed" if result.returncode == 0 else "failed",
            command=command,
            returncode=result.returncode,
            output_preview=output[-4000:],
        )
    except subprocess.TimeoutExpired as exc:
        return PatchVerificationCheck(
            name=" ".join(command[:3]),
            status="failed",
            command=command,
            returncode=None,
            output_preview=f"timed out: {exc}",
        )


def _build_worktree_verification_runner(
    *,
    execution_profile_id: str,
    expected_profile_fingerprint: str,
    worktree_path: Path,
) -> tuple[ExecutionRunner, str]:
    """复用论文执行环境，但把运行边界限制在隔离 worktree。"""

    original_profile = get_execution_profile(execution_profile_id)
    current_fingerprint = compute_execution_profile_fingerprint(
        original_profile
    )
    if current_fingerprint != expected_profile_fingerprint:
        raise ValueError(
            "execution profile changed before patch verification; "
            "rebuild and re-approve the action"
        )

    verification_profile = original_profile.model_copy(
        update={"workspace_root": str(worktree_path.resolve())}
    )
    return build_execution_runner(verification_profile), current_fingerprint


def _run_profile_command(
    *,
    runner: ExecutionRunner,
    name: str,
    program: str,
    args: list[str],
    cwd: Path,
    timeout_seconds: int,
) -> PatchVerificationCheck:
    """通过临时 profile Runner 执行论文运行时检查。"""

    command = [program, *args]
    result = runner.run_program(
        program=program,
        args=args,
        cwd=str(cwd),
        timeout_seconds=timeout_seconds,
    )
    output = str(result.get("combined_output") or "")
    return PatchVerificationCheck(
        name=name,
        status="passed" if result.get("ok") else "failed",
        command=command,
        returncode=result.get("returncode"),
        output_preview=output[-4000:],
    )


def create_patch_worktree(bundle: PatchBundle, worktree_path: Path) -> None:
    """
    从 bundle 绑定的 commit 创建独立 detached worktree。

    LangGraph 节点可能在进程崩溃后重试，所以这里允许复用已经存在、
    HEAD 仍然正确的 worktree；内容状态由后续 before/after hash 再判断。
    """

    if worktree_path.exists():
        if not (worktree_path / ".git").exists():
            raise ValueError(
                f"existing path is not a Git worktree: {worktree_path}"
            )

        current_head = _run_git(worktree_path, ["rev-parse", "HEAD"])
        if (
            current_head.returncode != 0
            or current_head.stdout.strip() != bundle.base_git_commit
        ):
            raise ValueError(
                "existing patch worktree is based on a different commit"
            )
        return

    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    result = _run_git(
        Path(bundle.repo_path),
        [
            "worktree",
            "add",
            "--detach",
            str(worktree_path),
            bundle.base_git_commit,
        ],
    )
    if result.returncode != 0:
        raise ValueError(
            "cannot create patch worktree: "
            f"{result.stderr.strip()}"
        )


def verify_patch_in_worktree(
    *,
    bundle: PatchBundle,
    worktree_path: Path,
    verification_targets: list[str],
    execution_profile_id: str,
    execution_profile_fingerprint: str,
) -> PatchVerificationReport:
    """
    在隔离 worktree 中执行四层检查：
    1. git apply --check
    2. git apply
    3. after SHA-256
    4. Python 语法与受限测试目标
    """

    validate_patch_bundle(bundle)
    checks: list[PatchVerificationCheck] = []

    # 先确认原 profile 未在 action 创建后变化，再构造
    # 仅绑定当前 worktree 的临时 Runner。
    verification_runner, current_profile_fingerprint = (
        _build_worktree_verification_runner(
            execution_profile_id=execution_profile_id,
            expected_profile_fingerprint=execution_profile_fingerprint,
            worktree_path=worktree_path,
        )
    )

    try:
        create_patch_worktree(bundle, worktree_path)
    except ValueError as exc:
        return PatchVerificationReport(
            patch_id=bundle.patch_id,
            patch_sha256=bundle.patch_sha256,
            execution_profile_id=execution_profile_id,
            execution_profile_fingerprint=current_profile_fingerprint,
            execution_backend=verification_runner.profile.backend,
            status="blocked",
            worktree_path=None,
            checks=[],
            summary=str(exc),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    patch_path = Path(bundle.patch_path).resolve()

    def _all_file_hashes_match(field_name: str) -> bool:
        for file_record in bundle.files:
            target = worktree_path / file_record.relative_path
            if not target.is_file():
                return False
            if sha256_file(target) != getattr(file_record, field_name):
                return False
        return True

    before_matches = _all_file_hashes_match("before_sha256")
    after_matches = _all_file_hashes_match("after_sha256")

    if after_matches:
        # 上一次节点执行可能已经 apply 成功，但还没来得及写 checkpoint。
        # 精确 after hash 一致时可以安全复用，不重复 apply。
        apply_check = PatchVerificationCheck(
            name="git_apply_check",
            status="passed",
            output_preview="exact patch was already applied in this worktree",
        )
        apply_result = PatchVerificationCheck(
            name="git_apply",
            status="passed",
            output_preview="reused idempotent worktree state",
        )
        checks.extend([apply_check, apply_result])

    elif before_matches:
        apply_check = _run_command(
            ["git", "apply", "--check", str(patch_path)],
            cwd=worktree_path,
            timeout_seconds=settings.patch_verify_timeout_seconds,
        )
        apply_check.name = "git_apply_check"
        checks.append(apply_check)

        if apply_check.status == "passed":
            apply_result = _run_command(
                ["git", "apply", str(patch_path)],
                cwd=worktree_path,
                timeout_seconds=settings.patch_verify_timeout_seconds,
            )
            apply_result.name = "git_apply"
            checks.append(apply_result)
        else:
            apply_result = PatchVerificationCheck(
                name="git_apply",
                status="skipped",
                output_preview="git apply --check failed",
            )
            checks.append(apply_result)

    else:
        # 既不是原始哈希，也不是目标哈希，说明 worktree 被其他内容污染。
        apply_check = PatchVerificationCheck(
            name="git_apply_check",
            status="failed",
            output_preview=(
                "worktree files match neither before nor after hashes"
            ),
        )
        apply_result = PatchVerificationCheck(
            name="git_apply",
            status="skipped",
            output_preview="stale or partially modified worktree",
        )
        checks.extend([apply_check, apply_result])

    if apply_result.status == "passed":
        hash_errors: list[str] = []
        for file_record in bundle.files:
            target = worktree_path / file_record.relative_path
            if not target.exists():
                hash_errors.append(f"missing: {file_record.relative_path}")
                continue
            actual_hash = sha256_file(target)
            if actual_hash != file_record.after_sha256:
                hash_errors.append(
                    f"after hash mismatch: {file_record.relative_path}"
                )

        checks.append(
            PatchVerificationCheck(
                name="after_sha256",
                status="failed" if hash_errors else "passed",
                output_preview="\n".join(hash_errors) or "all hashes match",
            )
        )

        python_files = [
            item.relative_path
            for item in bundle.files
            if Path(item.relative_path).suffix == ".py"
        ]
        if python_files:
            syntax_check = _run_profile_command(
                runner=verification_runner,
                name="python_syntax",
                program="python",
                args=["-m", "py_compile", *python_files],
                cwd=worktree_path,
                timeout_seconds=settings.patch_verify_timeout_seconds,
            )
            checks.append(syntax_check)
        else:
            checks.append(
                PatchVerificationCheck(
                    name="python_syntax",
                    status="skipped",
                    output_preview="no Python files changed",
                )
            )

        # 只接受已有且位于 tests/ 下的相对路径，不执行模型提供的命令。
        safe_test_targets: list[str] = []
        for raw_target in verification_targets:
            candidate = Path(raw_target)
            if candidate.is_absolute() or ".." in candidate.parts:
                continue
            if not candidate.parts or candidate.parts[0] != "tests":
                continue
            if (worktree_path / candidate).is_file():
                safe_test_targets.append(candidate.as_posix())

        if safe_test_targets:
            test_check = _run_profile_command(
                runner=verification_runner,
                name="targeted_tests",
                program="python",
                args=["-m", "pytest", "-q", *safe_test_targets],
                cwd=worktree_path,
                timeout_seconds=settings.patch_verify_timeout_seconds,
            )
            checks.append(test_check)
        else:
            checks.append(
                PatchVerificationCheck(
                    name="targeted_tests",
                    status="skipped",
                    output_preview="no trusted existing test target",
                )
            )

    failed = any(item.status == "failed" for item in checks)
    status = "blocked" if not checks else ("failed" if failed else "passed")

    report = PatchVerificationReport(
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        execution_profile_id=execution_profile_id,
        execution_profile_fingerprint=current_profile_fingerprint,
        execution_backend=verification_runner.profile.backend,
        status=status,
        worktree_path=str(worktree_path),
        checks=checks,
        summary=(
            "patch passed isolated verification"
            if status == "passed"
            else "patch did not pass isolated verification"
        ),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    verification_hash = compute_verification_hash(report)
    return report.model_copy(
        update={"verification_sha256": verification_hash}
    )
```

这个实现中，`git worktree` 和 `git apply` 仍由宿主机 Git 执行；它们是补丁控制面操作，不是论文运行时。`py_compile` 和 `pytest` 则统一通过临时 verification profile 的 Runner 执行。构造副本前先将 profile store 中的当前指纹与 state 绑定的原指纹比较；环境已变化时直接阻断验证。当原 profile 的 backend 是 `conda` 时，Runner 会继续使用原 `conda_executable`、`conda_prefix` 和 `env`，并通过 `conda run -p` 调用 Python；唯一临时改变的是 `workspace_root`。

不要直接调用 `run_action_safe()` 运行 worktree 命令，因为原 action 的 profile fingerprint 和 workspace root 仍绑定原仓库。这里创建的是“仅用于本次隔离验证的 profile 副本”，不写回 profile store，也不替换或伪造原 action 的 fingerprint。验证报告同时记录原 profile ID、原 fingerprint、backend 和 worktree 路径，因此第二次人工确认所绑定的 `verification_sha256` 也覆盖验证环境。

本节的 worktree verifier 只实现语法检查和受限测试。patch 推广到原仓库后，正常流程会重新进入 `preflight -> smoke -> executor`，其中 smoke 继续使用原 action 绑定的 execution profile。如果以后在 worktree verifier 内增加额外 smoke，也必须调用同一个 `verification_runner.run_program()`，不能回退到当前 PATH 中的 `python`。

---

## 十七、实现 Patch Verifier Node

新增：

```text
app/nodes/patch_verifier_node.py
```

```python
from pathlib import Path

from app.config import settings
from app.schemas import (
    FileRepairProposal,
    PatchApprovalRecord,
    PatchBundle,
)
from app.tools.patch_tools import verify_patch_in_worktree


def patch_verifier_node(state: dict) -> dict:
    bundle = PatchBundle.model_validate(state.get("pending_patch"))
    approval = PatchApprovalRecord.model_validate(
        state.get("patch_approval_record")
    )

    # 审批记录必须绑定当前 patch，不能只检查 decision=approved。
    if approval.decision != "approved":
        return {
            "patch_verification_passed": False,
            "final_status": "patch_not_approved",
        }
    if approval.patch_id != bundle.patch_id:
        return {
            "patch_verification_passed": False,
            "final_status": "stale_patch_approval",
            "error": "approved patch_id does not match pending patch",
        }
    if approval.patch_sha256 != bundle.patch_sha256:
        return {
            "patch_verification_passed": False,
            "final_status": "stale_patch_approval",
            "error": "approved patch hash does not match pending patch",
        }

    proposal = FileRepairProposal.model_validate(
        state.get("file_repair_proposal")
    )
    run_dir = Path(state.get("run_dir") or settings.output_dir)
    worktree_path = (
        run_dir
        / "execution"
        / "patch_worktrees"
        / bundle.patch_id
    )
    execution_profile_id = state.get("execution_profile_id")
    execution_profile_fingerprint = state.get(
        "execution_profile_fingerprint"
    )
    if not execution_profile_id or not execution_profile_fingerprint:
        return {
            "patch_verification_passed": False,
            "final_status": "patch_verification_blocked",
            "error": "missing execution profile binding for patch verification",
        }

    try:
        report = verify_patch_in_worktree(
            bundle=bundle,
            worktree_path=worktree_path,
            verification_targets=proposal.verification_targets,
            execution_profile_id=execution_profile_id,
            execution_profile_fingerprint=execution_profile_fingerprint,
        )
    except (OSError, ValueError) as exc:
        return {
            "patch_verification_passed": False,
            "final_status": "patch_verification_blocked",
            "error": str(exc),
        }

    report_path = settings.output_dir / "patch_verification_report.json"
    report_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return {
        "patch_verification_report": report.model_dump(),
        "patch_verification_passed": report.status == "passed",
        "patch_verification_hash": report.verification_sha256,
        "final_status": (
            "patch_verified"
            if report.status == "passed"
            else "patch_verification_failed"
        ),
        "output_files": [
            *state.get("output_files", []),
            str(report_path),
        ],
    }
```

验证失败时原仓库没有被修改，因此不需要对原仓库做 rollback。失败 worktree 可以暂时保留用于排查，之后再提供显式 cleanup 命令。

---

## 十八、实现第二次 Promotion Review

新增：

```text
app/nodes/patch_promotion_review_node.py
```

```python
from datetime import datetime, timezone
from uuid import uuid4

from langgraph.types import interrupt

from app.config import settings
from app.schemas import PatchPromotionRecord, PatchVerificationReport


def patch_promotion_review_node(state: dict) -> dict:
    report = PatchVerificationReport.model_validate(
        state.get("patch_verification_report")
    )

    if report.status != "passed" or not report.verification_sha256:
        return {
            "patch_promotion_decision": "blocked",
            "final_status": "patch_not_verified",
        }

    response = interrupt(
        {
            "review_type": "patch_promotion_review",
            "message": (
                "The patch passed isolated verification. "
                "Approve applying the same patch to the source repository?"
            ),
            "patch_id": report.patch_id,
            "patch_sha256": report.patch_sha256,
            "verification_sha256": report.verification_sha256,
            "verification_status": report.status,
            "worktree_path": report.worktree_path,
            "checks": [item.model_dump() for item in report.checks],
            "allowed_decisions": ["approved", "rejected"],
        }
    )

    decision = str(response.get("decision", "rejected"))
    if decision not in {"approved", "rejected"}:
        decision = "rejected"
    feedback = response.get("feedback")

    record = PatchPromotionRecord(
        promotion_id=f"patch_promotion_{uuid4().hex[:12]}",
        patch_id=report.patch_id,
        patch_sha256=report.patch_sha256,
        verification_sha256=report.verification_sha256,
        decision=decision,
        reviewer="human",
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        comment=feedback,
    )

    record_path = settings.output_dir / "patch_promotion_record.json"
    record_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    return {
        "patch_promotion_decision": decision,
        "patch_promotion_feedback": feedback,
        "patch_promotion_record": record.model_dump(),
        "output_files": [
            *state.get("output_files", []),
            str(record_path),
        ],
    }
```

---

## 十九、把已验证 Patch 应用到原仓库

先在 `app/tools/patch_tools.py` 增加：

```python
def apply_verified_patch_to_source(
    bundle: PatchBundle,
) -> PatchApplicationRecord:
    """
    把已经验证和二次审批的 patch 应用到原仓库。

    调用前仍要重新检查 patch hash、HEAD、clean status 和 before hash，
    因为人工确认期间原仓库可能发生变化。
    """

    repo = Path(bundle.repo_path).resolve()
    try:
        validate_patch_bundle(bundle, require_clean_repo=True)

        check_result = _run_git(
            repo,
            ["apply", "--check", bundle.patch_path],
        )
        if check_result.returncode != 0:
            raise ValueError(
                "git apply --check failed: "
                f"{check_result.stderr.strip()}"
            )

        apply_result = _run_git(repo, ["apply", bundle.patch_path])
        if apply_result.returncode != 0:
            raise ValueError(
                f"git apply failed: {apply_result.stderr.strip()}"
            )

        # 应用后再检查每个 after hash，防止出现部分或异常应用。
        hash_mismatches: list[str] = []
        for file_record in bundle.files:
            target = resolve_patch_target(repo, file_record.relative_path)
            actual_hash = sha256_file(target)
            if actual_hash != file_record.after_sha256:
                hash_mismatches.append(file_record.relative_path)

        if hash_mismatches:
            # git apply 通常是整体应用；这里仍尝试精确反向应用，
            # 避免异常 after hash 状态留在用户仓库中。
            reverse_check = _run_git(
                repo,
                ["apply", "-R", "--check", bundle.patch_path],
            )
            rollback_status = "rollback check failed"
            if reverse_check.returncode == 0:
                reverse_result = _run_git(
                    repo,
                    ["apply", "-R", bundle.patch_path],
                )
                rollback_status = (
                    "rolled back"
                    if reverse_result.returncode == 0
                    else "rollback apply failed"
                )

            raise ValueError(
                "applied file hash mismatch for "
                f"{hash_mismatches}; {rollback_status}"
            )

        return PatchApplicationRecord(
            patch_id=bundle.patch_id,
            patch_sha256=bundle.patch_sha256,
            repo_path=str(repo),
            status="applied",
            files=bundle.files,
            applied_at=datetime.now(timezone.utc).isoformat(),
        )

    except (OSError, ValueError) as exc:
        return PatchApplicationRecord(
            patch_id=bundle.patch_id,
            patch_sha256=bundle.patch_sha256,
            repo_path=str(repo),
            status="failed",
            files=bundle.files,
            applied_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
        )
```

再新增：

```text
app/nodes/patch_apply_node.py
```

```python
from app.config import settings
from app.schemas import (
    PatchBundle,
    PatchPromotionRecord,
    PatchVerificationReport,
)
from app.tools.action_tools import compute_action_hash
from app.tools.patch_tools import apply_verified_patch_to_source


def patch_apply_node(state: dict) -> dict:
    bundle = PatchBundle.model_validate(state.get("pending_patch"))
    report = PatchVerificationReport.model_validate(
        state.get("patch_verification_report")
    )
    promotion = PatchPromotionRecord.model_validate(
        state.get("patch_promotion_record")
    )

    # 第二次审批必须同时绑定 patch 和完整验证报告。
    if promotion.decision != "approved":
        return {"final_status": "patch_promotion_rejected"}
    if promotion.patch_sha256 != bundle.patch_sha256:
        return {
            "final_status": "stale_patch_promotion",
            "error": "promotion patch hash mismatch",
        }
    if promotion.verification_sha256 != report.verification_sha256:
        return {
            "final_status": "stale_patch_promotion",
            "error": "promotion verification hash mismatch",
        }

    application = apply_verified_patch_to_source(bundle)
    application_path = settings.output_dir / "patch_application_record.json"
    application_path.write_text(
        application.model_dump_json(indent=2),
        encoding="utf-8",
    )

    if application.status != "applied":
        return {
            "patch_application_record": application.model_dump(),
            "final_status": "patch_apply_failed",
            "error": application.error,
            "output_files": [
                *state.get("output_files", []),
                str(application_path),
            ],
        }

    # 代码变化后，原命令动作必须带上 patch hash 重新计算 action hash。
    pending_action = dict(state.get("pending_action") or {})
    pending_action["repo_patch_hash"] = bundle.patch_sha256
    new_action_hash = compute_action_hash(pending_action)

    attempts = int(state.get("file_repair_attempt_count", 0)) + 1
    history_entry = {
        "attempt": attempts,
        "patch_id": bundle.patch_id,
        "patch_sha256": bundle.patch_sha256,
        "files": [item.relative_path for item in bundle.files],
        "status": "applied",
    }

    return {
        "patch_application_record": application.model_dump(),
        "applied_patch_hash": bundle.patch_sha256,
        "file_repair_attempt_count": attempts,
        "file_repair_history": [
            *state.get("file_repair_history", []),
            history_entry,
        ],
        "pending_action": pending_action,
        "pending_action_hash": new_action_hash,

        # 旧命令审批只绑定 patch 前的 action hash，必须清空。
        "user_approval": None,
        "human_feedback": None,
        "approval_record": None,

        # 源码改变后，旧 preflight、smoke、debug 和执行结果都已过期。
        "preflight_report": None,
        "preflight_passed": False,
        "smoke_test_report": None,
        "smoke_test_status": None,
        "smoke_test_passed": False,
        "debug_report": None,
        "execution_result": {},
        "execution_log_path": None,
        "log_path": None,
        "final_status": "patch_applied",
        "error": None,
        "output_files": [
            *state.get("output_files", []),
            str(application_path),
        ],
    }
```

推广到原仓库后不要直接跳到 executor。必须重新进入 `risk_check`，因为 action hash 已经变化。

---

## 二十、修改 Graph 路由

修改：

```text
app/graph.py
```

先增加 imports：

```python
from app.nodes.file_repair_planner_node import file_repair_planner_node
from app.nodes.patch_apply_node import patch_apply_node
from app.nodes.patch_builder_node import patch_builder_node
from app.nodes.patch_promotion_review_node import patch_promotion_review_node
from app.nodes.patch_review_node import patch_review_node
from app.nodes.patch_verifier_node import patch_verifier_node
```

增加路由函数：

```python
def route_after_log_debug(state: ReproductionState) -> str:
    """
    command repair 和 file repair 使用独立预算。

    不能因为 command repair 已经用过一次，就直接阻止尚未尝试的
    file-level repair。
    """

    command_attempts = int(state.get("repair_attempt_count", 0))
    file_attempts = int(state.get("file_repair_attempt_count", 0))

    command_budget_available = (
        command_attempts < settings.max_repair_attempts
    )
    file_budget_available = (
        settings.enable_file_repair
        and file_attempts < settings.max_file_repair_attempts
    )

    if command_budget_available or file_budget_available:
        return "repair_planner"
    return "final_report"


def route_after_repair_planner(state: ReproductionState) -> str:
    proposal = state.get("repair_proposal") or {}

    command_budget_available = (
        int(state.get("repair_attempt_count", 0))
        < settings.max_repair_attempts
    )
    if (
        command_budget_available
        and proposal.get("kind") == "edit_command"
        and proposal.get("repaired_command")
    ):
        return "repair_action_builder"

    # command repair 判断需要改源码时，才进入单独的 file repair planner。
    if (
        settings.enable_file_repair
        and proposal.get("kind") == "manual_only"
        and (state.get("debug_report") or {}).get("related_files")
        and int(state.get("file_repair_attempt_count", 0))
        < settings.max_file_repair_attempts
    ):
        return "file_repair_planner"

    return "final_report"


def route_after_file_repair_planner(state: ReproductionState) -> str:
    proposal = state.get("file_repair_proposal") or {}
    if proposal.get("kind") == "patch" and proposal.get("edits"):
        return "patch_builder"
    return "final_report"


def route_after_patch_builder(state: ReproductionState) -> str:
    if state.get("pending_patch") and state.get("pending_patch_hash"):
        return "patch_review"
    return "final_report"


def route_after_patch_review(state: ReproductionState) -> str:
    if state.get("patch_approval") == "approved":
        return "patch_verifier"
    return "final_report"


def route_after_patch_verifier(state: ReproductionState) -> str:
    if state.get("patch_verification_passed"):
        return "patch_promotion_review"
    return "final_report"


def route_after_patch_promotion_review(state: ReproductionState) -> str:
    if state.get("patch_promotion_decision") == "approved":
        return "patch_apply"
    return "final_report"


def route_after_patch_apply(state: ReproductionState) -> str:
    record = state.get("patch_application_record") or {}
    if record.get("status") == "applied" and state.get("pending_action"):
        return "risk_check"
    return "final_report"
```

注册节点：

```python
builder.add_node("file_repair_planner", file_repair_planner_node)
builder.add_node("patch_builder", patch_builder_node)
builder.add_node("patch_review", patch_review_node)
builder.add_node("patch_verifier", patch_verifier_node)
builder.add_node("patch_promotion_review", patch_promotion_review_node)
builder.add_node("patch_apply", patch_apply_node)
```

注册条件边：

```python
builder.add_conditional_edges(
    "file_repair_planner",
    route_after_file_repair_planner,
)
builder.add_conditional_edges("patch_builder", route_after_patch_builder)
builder.add_conditional_edges("patch_review", route_after_patch_review)
builder.add_conditional_edges("patch_verifier", route_after_patch_verifier)
builder.add_conditional_edges(
    "patch_promotion_review",
    route_after_patch_promotion_review,
)
builder.add_conditional_edges("patch_apply", route_after_patch_apply)
```

最终相关链应为：

```text
repair_planner
  -> repair_action_builder
  -> file_repair_planner
  -> final_report

file_repair_planner
  -> patch_builder
  -> final_report

patch_builder
  -> patch_review
  -> final_report

patch_review
  -> patch_verifier
  -> final_report

patch_verifier
  -> patch_promotion_review
  -> final_report

patch_promotion_review
  -> patch_apply
  -> final_report

patch_apply
  -> risk_check
  -> final_report
```

### 一个必须检查的旧边

你当前 `app/graph.py` 中如果仍有：

```python
builder.add_edge("log_debug", "final_report")
```

同时又有：

```python
builder.add_conditional_edges("log_debug", route_after_log_debug)
```

请删除无条件的 `builder.add_edge("log_debug", "final_report")`。

否则 `log_debug` 可能一边进入 repair，一边又直接进入 final report，形成并行分支和状态合并问题。

### 调高包含两次 interrupt 的 Graph 递归上限

完整 file repair 链会经过更多节点。修改 `run_graph()` 和两个新 resume CLI 使用的 config：

```python
config = {
    "configurable": {"thread_id": thread_id},
    # 初始分析、两次审批、patch 后重新执行加起来可能超过默认上限。
    "recursion_limit": 60,
}
```

初始 state 中的业务字段也可以同步调整：

```python
"max_steps": 60,
```

这两个值不是一回事：

```text
config.recursion_limit：LangGraph 自己的 superstep 安全上限
state.max_steps：项目业务层可选的循环预算字段
```

目前项目如果没有节点主动递增和检查 `step_count`，真正生效的是 `recursion_limit`。

---

## 二十一、增加两个 Resume CLI

修改：

```text
app/main.py
```

增加：

```python
@app.command()
def resume_patch_review(
    thread_id: str,
    decision: str = typer.Option("approved", "--decision"),
    feedback: str | None = typer.Option(None, "--feedback"),
):
    """恢复第一次 patch review；批准后只进入隔离验证。"""

    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if "patch_review" not in snapshot.next:
        raise typer.BadParameter(
            f"thread_id={thread_id} is not waiting at patch_review; "
            f"current next={snapshot.next}"
        )

    result = graph.invoke(
        Command(
            resume={
                "decision": decision,
                "feedback": feedback,
            }
        ),
        config=config,
    )
    print("[green]patch review resumed[/green]")
    print(result)


@app.command()
def resume_patch_promotion(
    thread_id: str,
    decision: str = typer.Option("rejected", "--decision"),
    feedback: str | None = typer.Option(None, "--feedback"),
):
    """恢复第二次 review；approved 会修改原仓库。"""

    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if "patch_promotion_review" not in snapshot.next:
        raise typer.BadParameter(
            f"thread_id={thread_id} is not waiting at "
            f"patch_promotion_review; current next={snapshot.next}"
        )

    result = graph.invoke(
        Command(
            resume={
                "decision": decision,
                "feedback": feedback,
            }
        ),
        config=config,
    )
    print("[green]patch promotion resumed[/green]")
    print(result)
```

第二个命令默认 `rejected`，因为它会修改原仓库。用户必须显式输入：

```bash
--decision approved
```

---

## 二十二、让 Artifact 与 Run Manifest 记录 Patch 链

修改：

```text
app/tools/artifact_tools.py
```

在 `classify_output_file()` 中增加：

```python
if name in {
    "file_repair_proposal.json",
    "file_repair_planner_structured_attempts.json",
    "patch.diff",
    "patch_bundle.json",
}:
    return "debug"

if name in {
    "patch_approval_record.json",
    "patch_promotion_record.json",
}:
    return "planning"

if name in {
    "patch_verification_report.json",
    "patch_application_record.json",
}:
    return "execution"
```

在 `build_run_manifest()` 返回值中增加：

```python
"file_repair": {
    "attempt_count": state.get("file_repair_attempt_count", 0),
    "history": state.get("file_repair_history", []),
    "proposal": state.get("file_repair_proposal"),
    "pending_patch": state.get("pending_patch"),
    "patch_approval": state.get("patch_approval_record"),
    "verification": state.get("patch_verification_report"),
    "promotion": state.get("patch_promotion_record"),
    "application": state.get("patch_application_record"),
},
```

需要注意一个时序问题：

```text
graph 在 patch_review interrupt 暂停时
还没有执行 final_report 和 run_manifest
```

这是正常的。完整 manifest 会在流程最终结束后生成；中断期间的状态由 SQLite checkpoint 保存。

---

## 二十三、扩展 Final Report

修改：

```text
app/nodes/final_report_node.py
```

在 Repair Summary 后增加：

```python
file_repair_items: list[str] = []

file_proposal = state.get("file_repair_proposal") or {}
if file_proposal:
    file_repair_items.append(
        f"File Repair Kind: `{file_proposal.get('kind', 'unknown')}`"
    )
    file_repair_items.append(
        f"File Repair Summary: {file_proposal.get('summary', 'N/A')}"
    )

pending_patch = state.get("pending_patch") or {}
if pending_patch:
    file_repair_items.append(
        f"Patch ID: `{pending_patch.get('patch_id', 'N/A')}`"
    )
    file_repair_items.append(
        f"Patch SHA-256: `{pending_patch.get('patch_sha256', 'N/A')}`"
    )

verification = state.get("patch_verification_report") or {}
if verification:
    file_repair_items.append(
        f"Patch Verification: `{verification.get('status', 'unknown')}`"
    )

application = state.get("patch_application_record") or {}
if application:
    file_repair_items.append(
        f"Patch Application: `{application.get('status', 'unknown')}`"
    )

lines += _render_section("File Repair Summary", file_repair_items)
```

最终报告必须明确区分：

```text
proposed
approved for verification
verified
approved for promotion
applied
```

不能只写一个模糊的 `patch succeeded`。

---

## 二十四、单元测试：Patch 工具安全边界

新增：

```text
tests/test_patch_tools.py
```

下面的测试不调用 LLM，也不会修改真实论文仓库。

```python
import subprocess
from pathlib import Path

import pytest

from app.schemas import FileRepairProposal
from app.tools.patch_tools import (
    apply_exact_replacements,
    build_patch_bundle,
    resolve_patch_target,
    sha256_file,
    validate_patch_bundle,
)


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    source = repo / "model.py"
    source.write_text(
        "def forward(x):\n    return x.view(-1)\n",
        encoding="utf-8",
    )
    _git(repo, "add", "model.py")
    _git(repo, "commit", "-m", "initial")
    return repo


def _proposal() -> FileRepairProposal:
    return FileRepairProposal(
        proposal_id="file_repair_test",
        kind="patch",
        summary="replace view with reshape",
        root_cause="input may be non-contiguous",
        edits=[
            {
                "relative_path": "model.py",
                "reason": "avoid contiguous requirement",
                "replacements": [
                    {
                        "old_text": "return x.view(-1)",
                        "new_text": "return x.reshape(-1)",
                        "reason": "reshape supports non-contiguous input",
                    }
                ],
            }
        ],
        verification_targets=[],
        risks=["reshape may allocate a copy"],
        bounded=True,
    )


def test_exact_replacement_requires_unique_old_text():
    with pytest.raises(ValueError, match="exactly once"):
        apply_exact_replacements(
            "value = 1\nvalue = 1\n",
            [
                {
                    "old_text": "value = 1",
                    "new_text": "value = 2",
                    "reason": "test",
                }
            ],
        )


def test_patch_path_cannot_escape_repo(tmp_path):
    repo = _make_repo(tmp_path)
    with pytest.raises(ValueError):
        resolve_patch_target(repo, "../outside.py")


def test_patch_path_cannot_target_env(tmp_path):
    repo = _make_repo(tmp_path)
    env_path = repo / ".env"
    env_path.write_text("SECRET=value\n", encoding="utf-8")
    with pytest.raises(ValueError):
        resolve_patch_target(repo, ".env")


def test_build_patch_bundle_does_not_modify_source(tmp_path):
    repo = _make_repo(tmp_path)
    source = repo / "model.py"
    before_hash = sha256_file(source)

    bundle = build_patch_bundle(
        repo_path=str(repo),
        proposal=_proposal(),
        bundle_root=tmp_path / "bundles",
    )

    assert Path(bundle.patch_path).exists()
    assert sha256_file(source) == before_hash
    assert "reshape" in Path(bundle.patch_path).read_text(encoding="utf-8")


def test_bundle_becomes_stale_when_patch_file_changes(tmp_path):
    repo = _make_repo(tmp_path)
    bundle = build_patch_bundle(
        repo_path=str(repo),
        proposal=_proposal(),
        bundle_root=tmp_path / "bundles",
    )

    Path(bundle.patch_path).write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="patch file changed"):
        validate_patch_bundle(bundle)


def test_bundle_becomes_stale_when_source_changes(tmp_path):
    repo = _make_repo(tmp_path)
    bundle = build_patch_bundle(
        repo_path=str(repo),
        proposal=_proposal(),
        bundle_root=tmp_path / "bundles",
    )

    (repo / "model.py").write_text("changed by user\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_patch_bundle(bundle)
```

运行：

```bash
python -m pytest tests/test_patch_tools.py -q
```

---

## 二十五、单元测试：两次审批都绑定哈希

新增：

```text
tests/test_patch_review_nodes.py
```

测试重点不是 LangGraph UI，而是：

```text
patch approval 绑定 patch_sha256
promotion approval 绑定 verification_sha256
旧审批不能批准新 patch
```

核心用例可以写成：

```python
from app.graph import (
    route_after_patch_promotion_review,
    route_after_patch_review,
    route_after_patch_verifier,
)


def test_approved_patch_routes_to_verifier():
    assert route_after_patch_review({"patch_approval": "approved"}) == (
        "patch_verifier"
    )


def test_rejected_patch_routes_to_final_report():
    assert route_after_patch_review({"patch_approval": "rejected"}) == (
        "final_report"
    )


def test_only_passed_verification_routes_to_promotion_review():
    assert route_after_patch_verifier(
        {"patch_verification_passed": True}
    ) == "patch_promotion_review"
    assert route_after_patch_verifier(
        {"patch_verification_passed": False}
    ) == "final_report"


def test_only_approved_promotion_routes_to_apply():
    assert route_after_patch_promotion_review(
        {"patch_promotion_decision": "approved"}
    ) == "patch_apply"
    assert route_after_patch_promotion_review(
        {"patch_promotion_decision": "rejected"}
    ) == "final_report"
```

还应该为 `patch_verifier_node()` 和 `patch_apply_node()` 增加以下负例：

```text
approval.patch_sha256 != bundle.patch_sha256 -> stale_patch_approval
execution_profile_id 缺失 -> patch_verification_blocked
execution_profile_fingerprint 与 profile store 当前值不一致 -> patch_verification_blocked
promotion.patch_sha256 != bundle.patch_sha256 -> stale_patch_promotion
promotion.verification_sha256 != report.verification_sha256 -> stale_patch_promotion
source before_sha256 已变化 -> patch_apply_failed
```

---

## 二十六、集成测试：隔离验证不修改原仓库

新增：

```text
tests/test_patch_verifier_node.py
```

核心测试：

```python
import subprocess
from pathlib import Path

from app.execution.profile_store import compute_execution_profile_fingerprint
from app.schemas import ExecutionProfile, FileRepairProposal
from app.tools.patch_tools import (
    build_patch_bundle,
    verify_patch_in_worktree,
)


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _make_repo(tmp_path: Path) -> Path:
    """创建只供当前集成测试使用的最小 Git 仓库。"""

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    source = repo / "model.py"
    source.write_text(
        "def forward(x):\n    return x.view(-1)\n",
        encoding="utf-8",
    )
    _git(repo, "add", "model.py")
    _git(repo, "commit", "-m", "initial")
    return repo


def _proposal() -> FileRepairProposal:
    return FileRepairProposal(
        proposal_id="file_repair_test",
        kind="patch",
        summary="replace view with reshape",
        root_cause="input may be non-contiguous",
        edits=[
            {
                "relative_path": "model.py",
                "reason": "avoid contiguous requirement",
                "replacements": [
                    {
                        "old_text": "return x.view(-1)",
                        "new_text": "return x.reshape(-1)",
                        "reason": "reshape supports non-contiguous input",
                    }
                ],
            }
        ],
        verification_targets=[],
        risks=["reshape may allocate a copy"],
        bounded=True,
    )


def test_patch_verification_uses_worktree_and_keeps_source_unchanged(
    tmp_path,
    monkeypatch,
):
    repo = _make_repo(tmp_path)
    source = repo / "model.py"
    original = source.read_text(encoding="utf-8")

    # CI 中用 local profile 验证调用链；CondaRunner 的
    # `conda run -p` 命令构造已在 Phase 10 的 Runner 测试覆盖。
    profile = ExecutionProfile(
        profile_id="test-local",
        backend="local",
        workspace_root=str(repo),
        artifact_root=str(tmp_path / "artifacts"),
    )
    monkeypatch.setattr(
        "app.tools.patch_tools.get_execution_profile",
        lambda profile_id: profile,
    )

    bundle = build_patch_bundle(
        repo_path=str(repo),
        proposal=_proposal(),
        bundle_root=tmp_path / "bundles",
    )

    report = verify_patch_in_worktree(
        bundle=bundle,
        worktree_path=tmp_path / "worktrees" / bundle.patch_id,
        verification_targets=[],
        execution_profile_id=profile.profile_id,
        execution_profile_fingerprint=(
            compute_execution_profile_fingerprint(profile)
        ),
    )

    assert report.status == "passed"
    assert report.verification_sha256
    assert report.execution_profile_id == profile.profile_id
    assert report.execution_backend == "local"
    assert profile.workspace_root == str(repo)
    assert source.read_text(encoding="utf-8") == original

    staged_source = Path(report.worktree_path) / "model.py"
    assert "reshape" in staged_source.read_text(encoding="utf-8")
```

运行完整新测试：

```bash
python -m pytest \
  tests/test_patch_tools.py \
  tests/test_patch_review_nodes.py \
  tests/test_patch_verifier_node.py \
  tests/test_file_repair_flow.py \
  -q
```

然后运行已有回归测试：

```bash
python -m pytest \
  tests/test_repair_action_builder_node.py \
  tests/test_repair_planner_node.py \
  tests/test_smoke_repair_flow.py \
  tests/test_review_flow.py \
  tests/test_structured_output_tools.py \
  tests/test_analysis_planning_structured_nodes.py \
  -q
```

---

## 二十七、手工测试步骤

不要一开始在 P4Transformer 真实仓库上测试写入。先使用一个可丢弃的 Git 演示仓库。

### 第 1 步：保持功能关闭并跑全部单测

```dotenv
ENABLE_FILE_REPAIR=false
```

运行：

```bash
python -m pytest -q
```

预期：已有 command repair、审批、preflight、smoke 和 structured output 流程不受影响。

### 第 2 步：开启文件修复

临时修改 `.env`：

```dotenv
ENABLE_FILE_REPAIR=true
```

重新启动 Python 进程，因为 `settings` 在模块导入时读取环境变量。

### 第 3 步：让图停在 patch_review

使用能够稳定产生源码错误的演示仓库运行 graph。到达中断后执行：

```bash
python -m app.main show-state patch-demo-001
```

预期：

```text
next=('patch_review',)
pending_patch 不为 None
pending_patch_hash 与 pending_patch.patch_sha256 相同
原仓库源码没有变化
```

检查完整 diff：

```bash
sed -n '1,240p' runs/<run_id>/debug/patches/<patch_id>/patch.diff
```

### 第 4 步：批准隔离验证

```bash
python -m app.main resume-patch-review \
  patch-demo-001 \
  --decision approved \
  --feedback "diff scope and semantics look correct"
```

如果验证通过，graph 应再次暂停：

```bash
python -m app.main show-state patch-demo-001
```

预期：

```text
next=('patch_promotion_review',)
patch_verification_passed=True
patch_verification_hash 不为空
原仓库仍然没有变化
worktree 中已经包含修改
```

### 第 5 步：先测试拒绝推广

第一次建议先拒绝：

```bash
python -m app.main resume-patch-promotion \
  patch-demo-001 \
  --decision rejected \
  --feedback "verify-only test"
```

预期：

```text
原仓库没有变化
final report 记录 promotion rejected
patch.diff 和 verification report 被保留
```

### 第 6 步：新 thread 测试真正推广

重新跑一个新的 thread，完成第一次审批和隔离验证后执行：

```bash
python -m app.main resume-patch-promotion \
  patch-demo-002 \
  --decision approved \
  --feedback "isolated verification passed; apply exact patch"
```

预期：

```text
原仓库文件发生预期修改
patch_application_record.status=applied
pending_action.repo_patch_hash 等于 patch SHA-256
pending_action_hash 已变化
旧 command approval_record 已清空
流程重新进入 risk_check
```

---

## 二十八、必须测试的攻击与竞态场景

### 场景 1：路径穿越

模型返回：

```json
{"relative_path": "../../.ssh/id_rsa"}
```

预期：`patch_builder` 返回 `patch_out_of_bounds`。

### 场景 2：审批后篡改 patch.diff

在 `patch_review` interrupt 期间手工修改 `patch.diff`。

预期：恢复后返回 `stale_patch_after_review`，不能验证。

### 场景 3：审批期间用户修改原文件

在 interrupt 期间修改目标源码。

预期：`before_sha256` 不匹配，不能验证或推广。

### 场景 4：验证报告被替换

修改 checkpoint 中或磁盘上的 verification 内容，使其 hash 改变。

预期：promotion record 与当前 verification hash 不一致，不能应用。

### 场景 5：LLM 修改上下文外文件

源码上下文只提供 `model.py`，proposal 却返回 `train.py`。

预期：planner 程序侧降级为 `no_patch`。

### 场景 6：old_text 出现多次

预期：不能“随便替换第一个”，必须拒绝并要求模型提供更长上下文。

### 场景 7：修改规模超限

修改 3 个文件或 100 行。

预期：返回 `patch_out_of_bounds`，转人工处理。

---

## 二十九、常见问题与排查

### 问题 1：一直进入 `no_patch`

优先检查：

```text
ENABLE_FILE_REPAIR 是否为 true
debug_report.related_files 是否是准确相对路径
log_path 中是否有真实 traceback
structured attempt 是否连续失败
proposal 是否引用了上下文外路径
```

查看：

```text
outputs/file_repair_planner_structured_attempts.json
outputs/file_repair_proposal.json
```

### 问题 2：`tracked files are dirty`

这不是 Git 本身坏了，而是安全策略生效。

先执行只读检查：

```bash
git -C /path/to/repo status --short
```

第一版要求先由用户自行 commit 或 stash。Agent 不应自动 stash，因为 stash 也是会改变用户工作区状态的 Git 操作。

### 问题 3：`old_text must occur exactly once`

含义可能是：

```text
出现 0 次：模型引用的源码已过期或被截断
出现多次：old_text 上下文太短，定位不唯一
```

解决方向是重新生成 proposal，让 `old_text` 包含函数名、相邻语句等更精确上下文；不要把实现改成静默替换第一个。

### 问题 4：worktree 创建失败

检查：

```bash
git -C /path/to/repo worktree list
```

如果测试中断留下旧 worktree，先确认路径和内容，再人工清理：

```bash
git -C /path/to/repo worktree remove /exact/worktree/path
```

不要在程序里对不确定路径直接 `rm -rf`。

### 问题 5：隔离验证使用了错误 Python 环境

先确认 `patch_verifier_node` 收到的 `execution_profile_id` 和 `execution_profile_fingerprint` 与原 action 一致，再检查该 profile 的：

```text
backend=conda
conda_executable=/absolute/path/to/conda
conda_prefix=/absolute/path/to/paper/environment
```

隔离验证时应当能观察到以下调用链：

```text
读取原 profile
  -> model_copy(update={"workspace_root": worktree_path})
  -> build_execution_runner(verification_profile)
  -> runner.run_program("python", ...)
  -> conda run -p <conda_prefix> python ...
```

如果运行时仍命中 Agent 的 Python，检查是否有代码绕过 `_run_profile_command()` 直接调用 `subprocess.run(["python", ...])`。不要使用 `conda activate`，继续使用 Phase 10 已有的 `conda run -p` backend。

### 问题 6：推广后又要求命令审批

这是正常行为。

源码变化后 `repo_patch_hash` 进入 action hash，旧 approval 已失效。重新审批的对象已经是“命令 + 环境 + patch 后源码”。

---

## 三十、本阶段涉及的 Agent 知识点

### 1. Capability escalation

Agent 从只读分析、命令执行升级到写源码，是一次能力升级。能力越强，控制面必须同步增强。

### 2. Plan/compile/apply separation

```text
LLM proposal
  -> deterministic compilation
  -> human review
  -> isolated apply
```

这与编译器和基础设施变更系统的设计很相似。

### 3. TOCTOU 防护

TOCTOU 指：

```text
检查时是 A
使用时已经变成 B
```

本阶段通过 patch hash、before hash、verification hash 和恢复后重复检查来降低风险。

### 4. Human-in-the-loop is data binding

人工审批不只是一个布尔值：

```text
approved=True
```

它必须绑定用户看到的具体对象：

```text
patch_id
patch_sha256
verification_sha256
reviewed_at
reviewer
comment
```

### 5. Transactional side effects

先在隔离 worktree 验证，再修改原仓库，相当于把副作用拆成 prepare 和 commit 两个阶段。

### 6. Least privilege

模型不能选择任意路径、任意命令和任意修改规模。它只获得解决当前错误所需的最小能力。

### 7. Provenance and lineage

完整链路可以回答：

```text
哪个日志触发了修复
哪个 proposal 生成了 patch
patch 基于哪个 commit 和文件哈希
谁审批了 patch
在哪个 worktree 验证
执行了哪些检查
谁批准推广
最终应用了哪些文件
```

### 8. Safe autonomy

真正可靠的 Agent 不是“完全不需要人”，而是能够判断什么时候自动推进、什么时候必须停下来让人确认。

---

## 三十一、本阶段暂时不做什么

为了控制复杂度，本阶段不做：

```text
自动创建新测试
跨多个 commit 的 patch
AST 级重构
依赖升级 patch
Docker 镜像修改
CUDA/C++ 编译代码自动修复
自动 git commit / branch / push / PR
多个候选 patch 并行搜索
验证失败后的递归自修复
```

这些能力可以在基础 patch 控制面稳定后继续拓展。

---

## 三十二、完成标准

本阶段完成后，至少满足：

- `ENABLE_FILE_REPAIR=false` 时所有旧流程保持原行为。
- 模型只能提出上下文白名单内已有文件的精确替换。
- 路径穿越、符号链接、密钥文件和超限 patch 会被程序拒绝。
- `patch.diff` 由程序生成，并有稳定 SHA-256。
- patch review interrupt 恢复后会重新校验 patch 和原文件哈希。
- 第一次批准只触发隔离 worktree 验证，不修改原仓库。
- 隔离验证中的 Python 语法和测试命令通过论文 execution profile 的 Runner 执行，不依赖 Agent 当前 PATH。
- 验证报告包含 profile ID/fingerprint/backend、apply check、after hash、syntax 和 targeted test 状态。
- promotion 审批同时绑定 patch hash 和 verification hash。
- 只有验证通过且 promotion approved 才修改原仓库。
- 应用后每个文件都与 `after_sha256` 一致。
- patch 后 command action hash 发生变化，旧审批被清空。
- 流程重新进入 `risk_check -> preflight -> smoke -> executor`。
- run manifest 能追踪 proposal、patch、两次审批、验证和应用记录。

---

## 三十三、下一阶段建议

根据最新的 `agent_project_analysis_and_technical_roadmap.md`，完成文件修复主体后应先进入：

```text
Phase 14：主图与文件修复安全收口
```

优先补齐：

```text
log_debug 单一条件出口
verification hash 边界重算
结构验证与行为验证分层
repository lock
patch application journal
崩溃后的幂等恢复
worktree 完整 diff 与清理策略
```

在这些 P0 问题完成前，不应默认开启文件修复，也不应提前进入复现结果自动评定。

完整教程见：

```text
a_implementation_guides/25_phase_14_graph_and_file_repair_safety_closure.md
```

---

## 最后总结

这一阶段最重要的升级不是 `write_text()`，而是把文件修改拆成了多个有证据的状态转换：

```text
建议不等于 patch
patch 不等于批准
批准不等于验证通过
验证通过不等于允许修改原仓库
应用成功也不等于论文复现成功
```

通过结构化 proposal、确定性 diff、哈希绑定、两次人工确认和隔离验证，Agent 才能在不牺牲用户代码安全的前提下，获得第一版真正的 file-level repair 能力。

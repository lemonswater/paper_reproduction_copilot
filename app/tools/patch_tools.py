from __future__ import annotations

import difflib
import hashlib
import hmac
import json
import subprocess
from collections.abc import Callable
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
    PatchPromotionRecord,
    PatchVerificationCheck,
    PatchVerificationReport,
)
from app.tools.patch_journal_tools import write_patch_journal
from app.tools.repository_lock_tools import (
    RepositoryLockBusyError,
    acquire_repository_lock,
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

STRUCTURAL_CHECK_NAMES = {
    "git_apply_check",
    "git_apply",
    "after_sha256",
    "worktree_diff_scope",
    "python_syntax",
}

BEHAVIORAL_CHECK_NAMES = {"targeted_tests"}

FaultHook = Callable[[str], None]

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
            "文件修复需要一个包含有效 HEAD 的 Git 仓库: "
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
        raise ValueError(result.stderr.strip() or "无法读取 Git 状态")
    if result.stdout.strip():
        raise ValueError(
            "已跟踪文件存在未提交修改；请先提交或暂存用户修改，"
            "再构建自动补丁"
        )

def resolve_patch_target(repo_path: Path, relative_path: str) -> Path:
    """把模型路径限制在 repo_path 内的已有普通文本文件。"""

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"不允许使用绝对补丁路径：{relative_path}")
    if ".." in candidate.parts:
        raise ValueError(f"不允许通过父目录跳转：{relative_path}")

    if any(part in BLOCKED_PATH_PARTS for part in candidate.parts):
        raise ValueError(f"补丁路径已被禁止：{relative_path}")
    if candidate.name.lower() in BLOCKED_FILE_NAMES:
        raise ValueError(f"补丁文件已被禁止：{relative_path}")
    if candidate.suffix.lower() not in ALLOWED_PATCH_SUFFIXES:
        raise ValueError(f"不支持的补丁文件后缀：{candidate.suffix}")

    root = repo_path.resolve()
    target = (root / candidate).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"补丁目标超出仓库范围：{relative_path}")

    # `resolve()` 会跟随 symlink，所以还要检查路径本身是不是链接。
    unresolved_target = root / candidate
    if unresolved_target.is_symlink():
        raise ValueError(f"不允许将符号链接作为补丁目标：{relative_path}")
    if not target.exists() or not target.is_file():
        raise ValueError(f"补丁目标必须是已存在的文件：{relative_path}")
    if target.stat().st_size > settings.max_patch_file_bytes:
        raise ValueError(f"补丁目标文件过大：{relative_path}")

    return target

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
                f"第 {index} 个替换项的 old_text 必须恰好出现一次；"
                f"实际出现 {occurrence_count} 次"
            )

        updated = updated.replace(old_text, new_text, 1)

    if updated == original_text:
        raise ValueError("补丁没有改变文件内容")
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
        raise ValueError("只有 kind=patch 才能构建补丁包")

    repo = Path(repo_path).resolve()
    if not repo.exists() or not repo.is_dir():
        raise ValueError(f"仓库不存在：{repo}")

    ensure_clean_tracked_files(repo)
    base_commit = get_git_commit(repo)

    if len(proposal.edits) > settings.max_patch_files:
        raise ValueError(
            f"补丁涉及的文件过多：{len(proposal.edits)} > "
            f"{settings.max_patch_files}"
        )

    total_replacements = sum(len(edit.replacements) for edit in proposal.edits)
    if total_replacements > settings.max_patch_replacements:
        raise ValueError(
            f"补丁包含的替换项过多：{total_replacements} > "
            f"{settings.max_patch_replacements}"
        )

    # 同一个路径只能出现一次，否则替换顺序容易产生歧义。
    relative_paths = [edit.relative_path for edit in proposal.edits]
    if len(relative_paths) != len(set(relative_paths)):
        raise ValueError("补丁提案中存在重复的 relative_path")

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
                f"补丁目标不是 UTF-8 文本：{edit.relative_path}"
            ) from exc

        after = apply_exact_replacements(
            before,
            [item.model_dump() for item in edit.replacements],
        )
        changed_line_count = count_changed_lines(before, after)
        total_changed_lines += changed_line_count

        diff_text = build_unified_diff(edit.relative_path, before, after)
        if not diff_text:
            raise ValueError(f"{edit.relative_path} 的差异内容为空")
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
            f"补丁修改的行数过多：{total_changed_lines} > "
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

def validate_patch_bundle(
    bundle: PatchBundle,
    *,
    require_clean_repo: bool = True,
) -> None:
    """在验证和推广前重复检查 patch、commit 与每个原文件哈希。"""

    repo = Path(bundle.repo_path).resolve()
    patch_path = Path(bundle.patch_path).resolve()

    if not patch_path.exists() or not patch_path.is_file():
        raise ValueError(f"补丁文件缺失：{patch_path}")
    if sha256_file(patch_path) != bundle.patch_sha256:
        raise ValueError("补丁文件在补丁包创建后发生了变化")

    current_commit = get_git_commit(repo)
    if current_commit != bundle.base_git_commit:
        raise ValueError(
            "仓库 HEAD 在补丁创建后发生了变化："
            f"{bundle.base_git_commit} -> {current_commit}"
        )

    if require_clean_repo:
        ensure_clean_tracked_files(repo)

    for file_record in bundle.files:
        target = resolve_patch_target(repo, file_record.relative_path)
        if sha256_file(target) != file_record.before_sha256:
            raise ValueError(
                "源文件在补丁创建后发生了变化："
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
            truncation_note = "\n# [上下文已被 Agent 截断]\n"
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
            output_preview=f"执行超时：{exc}",
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
            "执行配置在补丁验证前发生了变化；"
            "请重新构建并审批该动作"
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
    run_dir: str | Path,
    timeout_seconds: int,
) -> PatchVerificationCheck:
    """通过临时 profile Runner 执行论文运行时检查。"""

    command = [program, *args]
    result = runner.probe(
        program=program,
        args=args,
        cwd=str(cwd),
        run_dir=str(run_dir),
        stage=f"patch_verify_{name}",
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
                f"现有路径不是 Git worktree：{worktree_path}"
            )

        current_head = _run_git(worktree_path, ["rev-parse", "HEAD"])
        if (
            current_head.returncode != 0
            or current_head.stdout.strip() != bundle.base_git_commit
        ):
            raise ValueError(
                "现有补丁 worktree 基于另一个提交"
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
            "无法创建补丁 worktree："
            f"{result.stderr.strip()}"
        )

def summarize_patch_verification(
    checks: list[PatchVerificationCheck],
) -> tuple[str, bool, bool, int, int]:
    """
    返回 status、promotion_allowed、structural_passed、
    behavioral_run、behavioral_passed。
    """

    if not checks:
        return "blocked", False, False, 0, 0

    required_structural_names = {
        "git_apply_check",
        "git_apply",
        "after_sha256",
        "worktree_diff_scope",
    }
    passed_names = {
        item.name for item in checks if item.status == "passed"
    }
    structural_passed = required_structural_names.issubset(passed_names)

    structural_failed = any(
        item.name in STRUCTURAL_CHECK_NAMES and item.status == "failed"
        for item in checks
    )
    if structural_failed:
        return "failed", False, False, 0, 0
    if not structural_passed:
        return "blocked", False, False, 0, 0

    behavioral_checks = [
        item
        for item in checks
        if item.name in BEHAVIORAL_CHECK_NAMES
        and item.status != "skipped"
    ]
    run_count = len(behavioral_checks)
    passed_count = sum(
        item.status == "passed" for item in behavioral_checks
    )

    if run_count == 0:
        return "structurally_valid", False, True, 0, 0
    if passed_count == run_count:
        return "behaviorally_verified", True, True, run_count, passed_count
    return "failed", False, True, run_count, passed_count

def verify_patch_in_worktree(
    *,
    bundle: PatchBundle,
    worktree_path: Path,
    verification_targets: list[str],
    execution_profile_id: str,
    execution_profile_fingerprint: str,
    run_dir: str | Path,
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
            output_preview="该精确补丁已在此 worktree 中应用",
        )
        apply_result = PatchVerificationCheck(
            name="git_apply",
            status="passed",
            output_preview="已复用具备幂等性的 worktree 状态",
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
                output_preview="git apply --check 检查失败",
            )
            checks.append(apply_result)

    else:
        # 既不是原始哈希，也不是目标哈希，说明 worktree 被其他内容污染。
        apply_check = PatchVerificationCheck(
            name="git_apply_check",
            status="failed",
            output_preview=(
                "worktree 文件既不匹配修改前哈希，也不匹配修改后哈希"
            ),
        )
        apply_result = PatchVerificationCheck(
            name="git_apply",
            status="skipped",
            output_preview="worktree 已过期或被部分修改",
        )
        checks.extend([apply_check, apply_result])

    if apply_result.status == "passed":
        hash_errors: list[str] = []
        for file_record in bundle.files:
            target = worktree_path / file_record.relative_path
            if not target.exists():
                hash_errors.append(f"缺失：{file_record.relative_path}")
                continue
            actual_hash = sha256_file(target)
            if actual_hash != file_record.after_sha256:
                hash_errors.append(
                    f"修改后哈希不匹配：{file_record.relative_path}"
                )

        checks.append(
            PatchVerificationCheck(
                name="after_sha256",
                status="failed" if hash_errors else "passed",
                output_preview="\n".join(hash_errors) or "所有哈希均匹配",
            )
        )

        try:
            worktree_diff_sha256 = validate_worktree_matches_patch(
                bundle,
                worktree_path,
            )
            checks.append(
                PatchVerificationCheck(
                    name="worktree_diff_scope",
                    status="passed",
                    output_preview=(
                        "worktree 的已跟踪差异与补丁包完全一致；"
                        f"sha256={worktree_diff_sha256}"
                    ),
                )
            )
        except ValueError as exc:
            worktree_diff_sha256 = None
            checks.append(
                PatchVerificationCheck(
                    name="worktree_diff_scope",
                    status="failed",
                    output_preview=str(exc),
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
                run_dir=run_dir,
                timeout_seconds=settings.patch_verify_timeout_seconds,
            )
            checks.append(syntax_check)
        else:
            checks.append(
                PatchVerificationCheck(
                    name="python_syntax",
                    status="skipped",
                    output_preview="没有修改 Python 文件",
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
                run_dir=run_dir,
                timeout_seconds=settings.patch_verify_timeout_seconds,
            )
            checks.append(test_check)
        else:
            checks.append(
                PatchVerificationCheck(
                    name="targeted_tests",
                    status="skipped",
                    output_preview="没有可信的现有测试目标",
                )
            )
    (
        status,
        promotion_allowed,
        structural_checks_passed,
        behavioral_checks_run,
        behavioral_checks_passed,
    ) = summarize_patch_verification(checks)

    report = PatchVerificationReport(
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        execution_profile_id=execution_profile_id,
        execution_profile_fingerprint=current_profile_fingerprint,
        execution_backend=verification_runner.profile.backend,
        status=status,
        promotion_allowed=promotion_allowed,
        structural_checks_passed=structural_checks_passed,
        behavioral_checks_run=behavioral_checks_run,
        behavioral_checks_passed=behavioral_checks_passed,
        worktree_path=str(worktree_path),
        worktree_diff_sha256=worktree_diff_sha256,
        checks=checks,
        summary=(
            "补丁已通过结构验证和行为验证"
            if status == "behaviorally_verified"
            else "补丁尚未通过行为验证"
        ),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    verification_hash = compute_verification_hash(report)
    return report.model_copy(
        update={"verification_sha256": verification_hash}
    )

def _git_output(repo_path: Path, args: list[str]) -> str:
    result = _run_git(repo_path, args)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "git command failed")
    return result.stdout

def get_changed_tracked_paths(worktree_path: Path) -> set[str]:
    output = _git_output(
        worktree_path,
        ["diff", "--name-only", "HEAD"],
    )
    return {line.strip() for line in output.splitlines() if line.strip()}

def ensure_no_staged_changes(worktree_path: Path) -> None:
    staged = _git_output(
        worktree_path,
        ["diff", "--cached", "--name-only"],
    )
    if staged.strip():
        raise ValueError("patch worktree contains staged changes")

def compute_worktree_diff_hash(worktree_path: Path) -> str:
    """对完整 tracked binary diff 做哈希。"""

    diff_text = _git_output(
        worktree_path,
        ["diff", "--binary", "--full-index", "HEAD"],
    )
    return sha256_text(diff_text)

def validate_worktree_matches_patch(
    bundle: PatchBundle,
    worktree_path: Path,
) -> str:
    """
    目标文件必须全部为 after hash，且 tracked diff 只能包含 bundle 文件。

    返回完整 worktree diff SHA-256。
    """

    if get_git_commit(worktree_path) != bundle.base_git_commit:
        raise ValueError("patch worktree HEAD changed")

    ensure_no_staged_changes(worktree_path)

    expected_paths = {item.relative_path for item in bundle.files}
    changed_paths = get_changed_tracked_paths(worktree_path)
    if changed_paths != expected_paths:
        raise ValueError(
            "worktree tracked diff scope mismatch: "
            f"expected={sorted(expected_paths)}, "
            f"actual={sorted(changed_paths)}"
        )

    for file_record in bundle.files:
        target = worktree_path / file_record.relative_path
        if not target.is_file():
            raise ValueError(
                f"patched worktree file missing: {file_record.relative_path}"
            )
        if sha256_file(target) != file_record.after_sha256:
            raise ValueError(
                f"patched worktree hash mismatch: {file_record.relative_path}"
            )

    diff_check = _run_git(worktree_path, ["diff", "--check", "HEAD"])
    if diff_check.returncode != 0:
        raise ValueError(
            f"worktree diff check failed: {diff_check.stderr.strip()}"
        )

    return compute_worktree_diff_hash(worktree_path)

def validate_verification_hash(
    report: PatchVerificationReport,
) -> str:
    """重新序列化完整报告并校验 embedded hash。"""

    embedded_hash = report.verification_sha256
    if not embedded_hash:
        raise ValueError("verification report has no embedded hash")

    computed_hash = compute_verification_hash(report)
    if not hmac.compare_digest(embedded_hash, computed_hash):
        raise ValueError(
            "verification report content changed after hash generation"
        )
    return computed_hash

def validate_patch_promotion_authorization(
    *,
    bundle: PatchBundle,
    report: PatchVerificationReport,
    promotion: PatchPromotionRecord | None,
    state: dict[str, Any],
    require_promotion: bool,
) -> str:
    """
    在 promotion review 和 apply 边界复用同一套确定性校验。

    返回重新计算的 verification hash。
    """

    # 这里只校验不可变 patch artifact，不要求源码仍是 before 状态。
    # 源码可能已经 apply 成功但 checkpoint 尚未更新，此时必须允许
    # apply 层通过 exact-after 状态完成幂等恢复。
    patch_path = Path(bundle.patch_path)
    if not patch_path.is_file():
        raise ValueError("patch artifact is missing")
    if sha256_file(patch_path) != bundle.patch_sha256:
        raise ValueError("patch artifact hash mismatch")

    computed_hash = validate_verification_hash(report)

    if report.status != "behaviorally_verified":
        raise ValueError(
            f"patch is not behaviorally verified: {report.status}"
        )
    if report.promotion_allowed is not True:
        raise ValueError("verification report does not allow promotion")

    if report.patch_id != bundle.patch_id:
        raise ValueError("report patch_id does not match bundle")
    if report.patch_sha256 != bundle.patch_sha256:
        raise ValueError("report patch hash does not match bundle")

    state_profile_id = state.get("execution_profile_id")
    state_fingerprint = state.get("execution_profile_fingerprint")
    pending_action = state.get("pending_action") or {}

    if report.execution_profile_id != state_profile_id:
        raise ValueError("verification profile id does not match state")
    if report.execution_profile_fingerprint != state_fingerprint:
        raise ValueError("verification profile fingerprint does not match state")
    if pending_action.get("execution_profile_id") != state_profile_id:
        raise ValueError("pending action profile id does not match state")
    if (
        pending_action.get("execution_profile_fingerprint")
        != state_fingerprint
    ):
        raise ValueError("pending action profile fingerprint does not match state")

    current_profile = get_execution_profile(str(state_profile_id))
    current_fingerprint = compute_execution_profile_fingerprint(
        current_profile
    )
    if current_fingerprint != state_fingerprint:
        raise ValueError(
            "execution profile changed after patch verification"
        )

    if require_promotion:
        if promotion is None or promotion.decision != "approved":
            raise ValueError("patch promotion is not approved")
        if promotion.patch_id != bundle.patch_id:
            raise ValueError("promotion patch_id does not match bundle")
        if promotion.patch_sha256 != bundle.patch_sha256:
            raise ValueError("promotion patch hash does not match bundle")
        if not hmac.compare_digest(
            promotion.verification_sha256,
            computed_hash,
        ):
            raise ValueError(
                "promotion does not match current verification report"
            )

    return computed_hash

def inspect_source_patch_state(bundle: PatchBundle) -> str:
    """
    返回 before、after 或 conflict。

    这是 apply 幂等恢复的事实来源，不修改仓库。
    """

    repo = Path(bundle.repo_path).resolve()
    if get_git_commit(repo) != bundle.base_git_commit:
        return "conflict"

    staged = _git_output(repo, ["diff", "--cached", "--name-only"])
    if staged.strip():
        return "conflict"

    changed_paths = get_changed_tracked_paths(repo)
    expected_paths = {item.relative_path for item in bundle.files}

    all_files_exist = all(
        (repo / item.relative_path).is_file() for item in bundle.files
    )
    if not all_files_exist:
        return "conflict"

    before_matches = all(
        sha256_file(repo / item.relative_path) == item.before_sha256
        for item in bundle.files
    )
    after_matches = all(
        sha256_file(repo / item.relative_path) == item.after_sha256
        for item in bundle.files
    )

    if before_matches and not changed_paths:
        return "before"

    if after_matches and changed_paths == expected_paths:
        return "after"

    return "conflict"

def _application_record(
    *,
    bundle: PatchBundle,
    status: str,
    applied_at: str,
    recovered: bool = False,
    error: str | None = None,
    journal_path: Path | None = None,
    lock_key: str | None = None,
) -> PatchApplicationRecord:
    return PatchApplicationRecord(
        patch_id=bundle.patch_id,
        patch_sha256=bundle.patch_sha256,
        repo_path=bundle.repo_path,
        status=status,
        files=bundle.files,
        applied_at=applied_at,
        recovered=recovered,
        error=error,
        journal_path=str(journal_path) if journal_path else None,
        repository_lock_key=lock_key,
    )

def apply_verified_patch_to_source(
    bundle: PatchBundle,
    *,
    owner_run_id: str,
    fault_hook: FaultHook | None = None,
) -> PatchApplicationRecord:
    """
    在仓库锁内通过 write-ahead journal 幂等应用 patch。

    fault_hook 只用于测试，生产调用不传。
    """

    repo = Path(bundle.repo_path).resolve()

    def inject(point: str) -> None:
        if fault_hook is not None:
            fault_hook(point)

    try:
        with acquire_repository_lock(
            repo,
            owner_run_id=owner_run_id,
            timeout_seconds=settings.patch_repo_lock_timeout_seconds,
        ) as lock_key:
            patch_path = Path(bundle.patch_path)
            if not patch_path.is_file():
                raise ValueError("patch artifact is missing")
            if sha256_file(patch_path) != bundle.patch_sha256:
                raise ValueError("patch artifact hash mismatch")

            repository_state = inspect_source_patch_state(bundle)

            if repository_state == "after":
                # 上次可能在 apply 成功后、checkpoint 前崩溃。
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status="applied",
                    repository_state="after",
                    recovered=True,
                )
                return _application_record(
                    bundle=bundle,
                    status="applied",
                    applied_at=journal.updated_at,
                    recovered=True,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            if repository_state == "conflict":
                message = (
                    "repository matches neither exact before nor exact after state"
                )
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status="manual_intervention",
                    repository_state="conflict",
                    error=message,
                )
                return _application_record(
                    bundle=bundle,
                    status="manual_intervention",
                    applied_at=journal.updated_at,
                    error=message,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            # 只有 exact before 才能开始新的 apply。
            journal, journal_path = write_patch_journal(
                bundle=bundle,
                owner_run_id=owner_run_id,
                status="prepared",
                repository_state="before",
            )
            inject("after_journal_prepared")

            apply_check = _run_git(
                repo,
                ["apply", "--check", bundle.patch_path],
            )
            if apply_check.returncode != 0:
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status="blocked",
                    repository_state="before",
                    error=apply_check.stderr.strip(),
                )
                return _application_record(
                    bundle=bundle,
                    status="blocked",
                    applied_at=journal.updated_at,
                    error=journal.error,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            write_patch_journal(
                bundle=bundle,
                owner_run_id=owner_run_id,
                status="applying",
                repository_state="before",
            )
            inject("before_git_apply")

            apply_result = _run_git(repo, ["apply", bundle.patch_path])
            if apply_result.returncode != 0:
                current_state = inspect_source_patch_state(bundle)
                journal_status = (
                    "blocked" if current_state == "before"
                    else "manual_intervention"
                )
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status=journal_status,
                    repository_state=current_state,
                    error=apply_result.stderr.strip(),
                )
                return _application_record(
                    bundle=bundle,
                    status=(
                        "failed"
                        if current_state == "before"
                        else "manual_intervention"
                    ),
                    applied_at=journal.updated_at,
                    error=journal.error,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            # 最重要的故障点：仓库已变化，checkpoint 尚未变化。
            inject("after_git_apply_before_journal")

            if inspect_source_patch_state(bundle) != "after":
                message = "source repository did not reach exact after state"
                journal, journal_path = write_patch_journal(
                    bundle=bundle,
                    owner_run_id=owner_run_id,
                    status="manual_intervention",
                    repository_state="conflict",
                    error=message,
                )
                return _application_record(
                    bundle=bundle,
                    status="manual_intervention",
                    applied_at=journal.updated_at,
                    error=message,
                    journal_path=journal_path,
                    lock_key=lock_key,
                )

            journal, journal_path = write_patch_journal(
                bundle=bundle,
                owner_run_id=owner_run_id,
                status="applied",
                repository_state="after",
            )
            inject("after_journal_applied")

            return _application_record(
                bundle=bundle,
                status="applied",
                applied_at=journal.updated_at,
                recovered=False,
                journal_path=journal_path,
                lock_key=lock_key,
            )

    except RepositoryLockBusyError as exc:
        return _application_record(
            bundle=bundle,
            status="blocked",
            applied_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
        )
    except (OSError, ValueError) as exc:
        # 可预期的磁盘、Git、hash 错误转成审计记录；
        # fault_hook 抛出的 BaseException 不会在这里被吞掉。
        return _application_record(
            bundle=bundle,
            status="failed",
            applied_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
        )

def validate_patch_worktree_path(
    *,
    worktree_path: Path,
    run_dir: Path,
) -> Path:
    """只允许当前 run/execution/patch_worktrees 下的精确路径。"""

    resolved_worktree = worktree_path.resolve()
    allowed_root = run_dir.resolve() / "execution" / "patch_worktrees"
    if (
        resolved_worktree != allowed_root
        and allowed_root not in resolved_worktree.parents
    ):
        raise ValueError("worktree path is outside current run")
    if not (resolved_worktree / ".git").exists():
        raise ValueError("target 不是 Git 工作树")
    return resolved_worktree


def remove_patch_worktree(
    *,
    repo_path: str,
    worktree_path: str,
    run_dir: str,
) -> None:
    target = validate_patch_worktree_path(
        worktree_path=Path(worktree_path),
        run_dir=Path(run_dir),
    )
    result = _run_git(
        Path(repo_path),
        ["worktree", "remove", "--force", str(target)],
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "worktree removal failed")

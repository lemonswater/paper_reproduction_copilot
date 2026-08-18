from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.skills.schemas import SkillManifest


MAX_MANIFEST_BYTES = 256 * 1024
MAX_RESOURCE_BYTES = 1024 * 1024
MAX_PACKAGES = 64


class SkillPackageError(ValueError):
    """Plugin Package 不满足数据、路径或完整性约束。"""


@dataclass(frozen=True)
class DiscoveredSkillPackage:
    package_root: Path
    manifest_path: Path
    manifest: SkillManifest
    manifest_sha256: str
    package_sha256: str


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _read_bounded_file(path: Path, *, max_bytes: int) -> bytes:
    if path.is_symlink():
        raise SkillPackageError(f"Skill Package 禁止符号链接：{path.name}")
    if not path.is_file():
        raise SkillPackageError(f"Skill Package 文件不存在：{path.name}")
    if path.stat().st_size > max_bytes:
        raise SkillPackageError(f"Skill Package 文件过大：{path.name}")
    return path.read_bytes()


def load_skill_package(
    package_dir: Path,
    *,
    package_root: Path,
) -> DiscoveredSkillPackage:
    """加载一个直接子目录，并验证其 Manifest 与全部资源。"""

    unresolved_root = package_root.expanduser()
    unresolved_package = package_dir.expanduser()
    if unresolved_root.is_symlink() or unresolved_package.is_symlink():
        raise SkillPackageError("Skill 根目录和包目录不能是符号链接")

    root = unresolved_root.resolve(strict=True)
    package = unresolved_package.resolve(strict=True)
    if not package.is_dir() or package.parent != root:
        raise SkillPackageError("Skill Package 必须是受控根目录的直接子目录")

    manifest_path = package / "skill.json"
    manifest_bytes = _read_bounded_file(
        manifest_path,
        max_bytes=MAX_MANIFEST_BYTES,
    )
    try:
        raw_manifest = json.loads(manifest_bytes)
        if not isinstance(raw_manifest, dict):
            raise SkillPackageError("skill.json 顶层必须是 JSON object")
        manifest = SkillManifest.model_validate(raw_manifest)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise SkillPackageError("skill.json 不符合 Phase 48 Manifest") from exc

    if package.name != manifest.skill_id:
        raise SkillPackageError("包目录名必须与 manifest.skill_id 完全一致")

    declared_paths = {
        item.relative_path: item.sha256
        for item in manifest.resources
    }
    actual_paths: set[str] = set()
    for child in package.rglob("*"):
        if child.is_symlink():
            raise SkillPackageError("Skill Package 内禁止符号链接")
        if child.is_dir():
            continue
        relative = child.relative_to(package).as_posix()
        if relative == "skill.json":
            continue
        actual_paths.add(relative)

    if actual_paths != set(declared_paths):
        raise SkillPackageError("实际资源文件与 Manifest resources 不一致")

    verified_resources: list[dict[str, str]] = []
    for relative_path in sorted(declared_paths):
        resource = package / relative_path
        resolved = resource.resolve(strict=True)
        if not _is_within(resolved, package):
            raise SkillPackageError("Skill Resource 逃逸出 Package")
        content = _read_bounded_file(
            resource,
            max_bytes=MAX_RESOURCE_BYTES,
        )
        actual_sha256 = _sha256_bytes(content)
        if actual_sha256 != declared_paths[relative_path]:
            raise SkillPackageError(
                f"Skill Resource Hash 不匹配：{relative_path}"
            )
        verified_resources.append(
            {
                "relative_path": relative_path,
                "sha256": actual_sha256,
            }
        )

    canonical_manifest = _canonical_json_bytes(
        manifest.model_dump(mode="json")
    )
    manifest_sha256 = _sha256_bytes(canonical_manifest)
    package_sha256 = _sha256_bytes(
        _canonical_json_bytes(
            {
                "manifest_sha256": manifest_sha256,
                "resources": verified_resources,
            }
        )
    )
    return DiscoveredSkillPackage(
        package_root=package,
        manifest_path=manifest_path,
        manifest=manifest,
        manifest_sha256=manifest_sha256,
        package_sha256=package_sha256,
    )


def discover_skill_packages(
    package_root: Path,
) -> list[DiscoveredSkillPackage]:
    """按 skill_id 稳定排序发现有限数量的 Plugin Package。"""

    unresolved = package_root.expanduser()
    if unresolved.is_symlink():
        raise SkillPackageError("Skill Package Root 不能是符号链接")
    if not unresolved.exists():
        return []

    root = unresolved.resolve(strict=True)
    if not root.is_dir():
        raise SkillPackageError("Skill Package Root 必须是目录")

    children = sorted(
        (
            item
            for item in root.iterdir()
            if not item.name.startswith(".")
        ),
        key=lambda item: item.name,
    )
    if len(children) > MAX_PACKAGES:
        raise SkillPackageError("Skill Package 数量超过上限")

    packages: list[DiscoveredSkillPackage] = []
    for child in children:
        if child.is_symlink() or not child.is_dir():
            raise SkillPackageError("Skill Root 只能包含普通包目录")
        packages.append(
            load_skill_package(child, package_root=root)
        )
    return packages

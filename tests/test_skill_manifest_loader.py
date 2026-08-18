from __future__ import annotations

import hashlib
import json

import pytest

from app.skills.loader import (
    SkillPackageError,
    discover_skill_packages,
    load_skill_package,
)
from tests.skill_test_helpers import base_manifest, write_skill_package


def test_loader_accepts_valid_package(tmp_path):
    package = write_skill_package(tmp_path)

    assert package.manifest.skill_id == "example_skill"
    assert len(package.manifest_sha256) == 64
    assert len(package.package_sha256) == 64


def test_loader_rejects_unknown_manifest_field(tmp_path):
    manifest = base_manifest()
    manifest["python_module"] = "untrusted.plugin"
    package_dir = tmp_path / "example_skill"
    package_dir.mkdir()
    (package_dir / "skill.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(SkillPackageError):
        load_skill_package(package_dir, package_root=tmp_path)


def test_loader_rejects_unlisted_python_file(tmp_path):
    package = write_skill_package(tmp_path)
    (package.package_root / "plugin.py").write_text(
        "raise RuntimeError('must never run')\n",
        encoding="utf-8",
    )

    with pytest.raises(SkillPackageError):
        load_skill_package(package.package_root, package_root=tmp_path)


def test_loader_rejects_absolute_resource_path(tmp_path):
    manifest = base_manifest()
    manifest["resources"] = [
        {
            "relative_path": "/outside.txt",
            "sha256": "0" * 64,
        }
    ]
    package_dir = tmp_path / "example_skill"
    package_dir.mkdir()
    (package_dir / "skill.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(SkillPackageError):
        load_skill_package(package_dir, package_root=tmp_path)


def test_loader_rejects_resource_hash_mismatch(tmp_path):
    content = b"trusted policy text\n"
    manifest = base_manifest()
    manifest["resources"] = [
        {
            "relative_path": "policy.txt",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    ]
    package_dir = tmp_path / "example_skill"
    package_dir.mkdir()
    (package_dir / "skill.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (package_dir / "policy.txt").write_bytes(b"tampered\n")

    with pytest.raises(SkillPackageError):
        load_skill_package(package_dir, package_root=tmp_path)


def test_loader_rejects_symlink(tmp_path):
    package = write_skill_package(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (package.package_root / "linked.txt").symlink_to(outside)

    with pytest.raises(SkillPackageError):
        load_skill_package(package.package_root, package_root=tmp_path)


def test_discovery_is_stably_sorted(tmp_path):
    for skill_id in ["zeta_skill", "alpha_skill"]:
        write_skill_package(
            tmp_path,
            base_manifest(
                skill_id=skill_id,
                implementation_id=f"builtin.{skill_id}.v1",
            ),
        )

    packages = discover_skill_packages(tmp_path)

    assert [item.manifest.skill_id for item in packages] == [
        "alpha_skill",
        "zeta_skill",
    ]

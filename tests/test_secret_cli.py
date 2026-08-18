"""Phase 41 Secret CLI 集成测试。

每个测试在隔离的 tmp_path 中初始化 Vault 和 Master Key，
然后通过 typer.testing.CliRunner 调用 CLI 命令。
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.config import settings
from app.main import app
from app.secrets.doctor import LEGACY_PLAINTEXT_ENV_NAMES


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _clear_legacy_env_vars(
    monkeypatch: pytest.MonkeyPatch,
):
    """清除旧明文环境变量，避免 doctor 误报。"""

    for name in LEGACY_PLAINTEXT_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture()
def secret_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """把 secret master key 和 vault 路径隔离到 tmp_path。"""

    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir(mode=0o700)
    key_path = secret_dir / "master.key"
    vault_path = secret_dir / "vault.sqlite"

    monkeypatch.setattr(
        settings, "secret_master_key_path", key_path
    )
    monkeypatch.setattr(
        settings, "secret_vault_db_path", vault_path
    )
    # 确保 factory 缓存被清理
    from app.secrets.factory import (
        reset_secret_service_for_tests,
    )

    reset_secret_service_for_tests()
    yield secret_dir
    reset_secret_service_for_tests()


# ---------------------------------------------------------------------------
# init-secret-store
# ---------------------------------------------------------------------------


class TestInitSecretStore:
    def test_init_creates_key_and_vault(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        result = cli_runner.invoke(app, ["init-secret-store"])
        assert result.exit_code == 0
        assert "secret store initialized" in result.stdout

        key_path = settings.secret_master_key_path
        vault_path = settings.secret_vault_db_path
        assert key_path.exists()
        assert vault_path.exists()

    def test_init_key_permissions(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        result = cli_runner.invoke(app, ["init-secret-store"])
        assert result.exit_code == 0

        key_mode = stat.S_IMODE(
            settings.secret_master_key_path.lstat().st_mode
        )
        assert key_mode == 0o600

    def test_init_vault_permissions(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        result = cli_runner.invoke(app, ["init-secret-store"])
        assert result.exit_code == 0

        vault_mode = stat.S_IMODE(
            settings.secret_vault_db_path.lstat().st_mode
        )
        assert vault_mode == 0o600

    def test_init_idempotent(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        first = cli_runner.invoke(app, ["init-secret-store"])
        assert first.exit_code == 0
        second = cli_runner.invoke(app, ["init-secret-store"])
        assert second.exit_code == 0

    def test_init_vault_exists_key_missing_fails(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        """Vault 已存在但 Key 丢失时必须报错。"""
        # 先正常初始化
        result = cli_runner.invoke(app, ["init-secret-store"])
        assert result.exit_code == 0

        # 删除 key
        key_path = settings.secret_master_key_path
        key_path.unlink()

        from app.secrets.factory import (
            reset_secret_service_for_tests,
        )

        reset_secret_service_for_tests()

        result = cli_runner.invoke(app, ["init-secret-store"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# set-secret
# ---------------------------------------------------------------------------


class TestSetSecret:
    def test_set_secret_stores_value(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])

        result = cli_runner.invoke(
            app,
            ["set-secret", "OPENAI_API_KEY", "--use", "provider"],
            input="sk-test-value-12345\nsk-test-value-12345\n",
        )
        assert result.exit_code == 0
        assert "OPENAI_API_KEY" in result.stdout
        assert "version=1" in result.stdout

    def test_set_secret_invalid_use(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])

        result = cli_runner.invoke(
            app,
            ["set-secret", "MY_KEY", "--use", "invalid_use"],
            input="value-12345678\n",
        )
        assert result.exit_code != 0

    def test_set_secret_rotation(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])

        # v1
        cli_runner.invoke(
            app,
            ["set-secret", "OPENAI_API_KEY", "--use", "provider"],
            input="sk-old-value-12345\nsk-old-value-12345\n",
        )
        # v2
        result = cli_runner.invoke(
            app,
            ["set-secret", "OPENAI_API_KEY", "--use", "provider"],
            input="sk-new-value-12345\nsk-new-value-12345\n",
        )
        assert result.exit_code == 0
        assert "version=2" in result.stdout


# ---------------------------------------------------------------------------
# list-secrets
# ---------------------------------------------------------------------------


class TestListSecrets:
    def test_list_empty(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])
        result = cli_runner.invoke(app, ["list-secrets"])
        assert result.exit_code == 0
        assert result.stdout.strip() == ""

    def test_list_after_set(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])
        cli_runner.invoke(
            app,
            ["set-secret", "TEST_KEY", "--use", "provider"],
            input="sk-list-value-1234\nsk-list-value-1234\n",
        )
        result = cli_runner.invoke(app, ["list-secrets"])
        assert result.exit_code == 0
        assert "TEST_KEY" in result.stdout
        assert "active" in result.stdout
        assert "provider" in result.stdout
        # 明文不应出现
        assert "sk-list-value-1234" not in result.stdout

    def test_list_shows_fingerprint_not_value(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])
        secret_value = "sk-never-leak-12345678"
        cli_runner.invoke(
            app,
            ["set-secret", "OPENAI_API_KEY", "--use", "provider"],
            input=f"{secret_value}\n{secret_value}\n",
        )
        result = cli_runner.invoke(app, ["list-secrets"])
        assert result.exit_code == 0
        assert secret_value not in result.stdout
        assert "fingerprint=" in result.stdout


# ---------------------------------------------------------------------------
# revoke-secret
# ---------------------------------------------------------------------------


class TestRevokeSecret:
    def test_revoke_active_secret(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])
        cli_runner.invoke(
            app,
            ["set-secret", "TEST_KEY", "--use", "provider"],
            input="sk-revoke-12345678\nsk-revoke-12345678\n",
        )
        result = cli_runner.invoke(
            app,
            ["revoke-secret", "TEST_KEY", "--version", "1"],
        )
        assert result.exit_code == 0
        assert "revoked" in result.stdout

        # list 应显示 revoked
        list_result = cli_runner.invoke(app, ["list-secrets"])
        assert "revoked" in list_result.stdout

    def test_revoke_wrong_version_fails(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])
        cli_runner.invoke(
            app,
            ["set-secret", "TEST_KEY", "--use", "provider"],
            input="sk-revoke-12345678\nsk-revoke-12345678\n",
        )
        result = cli_runner.invoke(
            app,
            ["revoke-secret", "TEST_KEY", "--version", "99"],
        )
        assert result.exit_code != 0

    def test_revoke_nonexistent_fails(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])
        result = cli_runner.invoke(
            app,
            ["revoke-secret", "NO_SUCH_KEY", "--version", "1"],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# secret-doctor
# ---------------------------------------------------------------------------


class TestSecretDoctor:
    def test_doctor_after_init(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        cli_runner.invoke(app, ["init-secret-store"])
        # doctor 检查 allowed_root，需要 secret_home 在其下
        monkeypatch.setattr(
            settings,
            "allowed_root",
            secret_home.parent,
        )
        result = cli_runner.invoke(app, ["secret-doctor"])
        assert result.exit_code == 0
        assert "ready" in result.stdout
        assert "active_secret_count=0" in result.stdout

    def test_doctor_before_init(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(
            settings,
            "allowed_root",
            secret_home.parent,
        )
        result = cli_runner.invoke(app, ["secret-doctor"])
        assert result.exit_code != 0
        assert "not-ready" in result.stdout

    def test_doctor_reports_issues(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # 不初始化 Vault
        monkeypatch.setattr(
            settings,
            "allowed_root",
            secret_home.parent,
        )
        result = cli_runner.invoke(app, ["secret-doctor"])
        assert result.exit_code != 0
        assert "-" in result.stdout


# ---------------------------------------------------------------------------
# scan-secret-leaks
# ---------------------------------------------------------------------------


class TestScanSecretLeaks:
    def test_scan_no_leaks(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        cli_runner.invoke(app, ["init-secret-store"])
        cli_runner.invoke(
            app,
            ["set-secret", "OPENAI_API_KEY", "--use", "provider"],
            input="sk-scan-leak-12345678\nsk-scan-leak-12345678\n",
        )
        clean_dir = tmp_path / "clean"
        clean_dir.mkdir()
        (clean_dir / "data.txt").write_text(
            "no secrets\n", encoding="utf-8"
        )
        result = cli_runner.invoke(
            app,
            ["scan-secret-leaks", "--root", str(clean_dir)],
        )
        assert result.exit_code == 0
        assert "no known secret material found" in result.stdout

    def test_scan_detects_leak(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
        tmp_path: Path,
    ):
        cli_runner.invoke(app, ["init-secret-store"])
        secret_value = "sk-scan-leak-12345678"
        cli_runner.invoke(
            app,
            ["set-secret", "OPENAI_API_KEY", "--use", "provider"],
            input=f"{secret_value}\n{secret_value}\n",
        )
        leak_dir = tmp_path / "leaky"
        leak_dir.mkdir()
        (leak_dir / "config.txt").write_text(
            f"key={secret_value}\n", encoding="utf-8"
        )
        result = cli_runner.invoke(
            app,
            ["scan-secret-leaks", "--root", str(leak_dir)],
        )
        assert result.exit_code == 2
        assert "config.txt" in result.stdout

    def test_scan_excludes_vault_directory(
        self,
        cli_runner: CliRunner,
        secret_home: Path,
    ):
        """Vault 自身不应被扫描。"""
        cli_runner.invoke(app, ["init-secret-store"])
        cli_runner.invoke(
            app,
            ["set-secret", "OPENAI_API_KEY", "--use", "provider"],
            input="sk-vault-scan-1234567\nsk-vault-scan-1234567\n",
        )
        # 扫描 vault 所在目录
        vault_parent = settings.secret_vault_db_path.parent
        result = cli_runner.invoke(
            app,
            ["scan-secret-leaks", "--root", str(vault_parent)],
        )
        # Vault 被排除，所以不会报泄漏
        assert result.exit_code == 0

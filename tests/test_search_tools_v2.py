from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.tools import search_tools
from app.tools.search_tools import (
    SearchToolError,
    search_text,
)


def test_literal_search_falls_back_without_rg(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "model.py"
    source.write_text(
        "value = '[PSTConv]'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        search_tools.shutil,
        "which",
        lambda _: None,
    )

    result = search_text(
        str(tmp_path),
        "[PSTConv]",
    )

    assert result == [
        {
            "file_path": "model.py",
            "line": 1,
            "text": "value = '[PSTConv]'",
        }
    ]


def test_regex_without_rg_is_explicit_error(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        search_tools.shutil,
        "which",
        lambda _: None,
    )

    with pytest.raises(
        SearchToolError,
        match="regex 搜索要求安装 rg",
    ):
        search_text(
            str(tmp_path),
            "PST.*Conv",
            literal=False,
        )


def test_rg_no_match_is_not_tool_failure(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        search_tools.shutil,
        "which",
        lambda _: "/usr/bin/rg",
    )
    monkeypatch.setattr(
        search_tools.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="",
        ),
    )

    assert search_text(
        str(tmp_path),
        "missing",
    ) == []


def test_rg_failure_is_not_silently_empty(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        search_tools.shutil,
        "which",
        lambda _: "/usr/bin/rg",
    )
    monkeypatch.setattr(
        search_tools.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=2,
            stdout="",
            stderr="permission denied",
        ),
    )

    with pytest.raises(
        SearchToolError,
        match="permission denied",
    ):
        search_text(
            str(tmp_path),
            "PSTConv",
        )


def test_rg_timeout_is_explicit_tool_failure(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        search_tools.shutil,
        "which",
        lambda _: "/usr/bin/rg",
    )

    def timeout(*args, **kwargs):
        raise search_tools.subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=kwargs["timeout"],
        )

    monkeypatch.setattr(
        search_tools.subprocess,
        "run",
        timeout,
    )

    with pytest.raises(
        SearchToolError,
        match="rg 搜索在 3 秒后超时",
    ):
        search_text(
            str(tmp_path),
            "PSTConv",
            timeout_seconds=3,
        )
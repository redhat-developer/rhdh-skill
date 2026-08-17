"""Behavior tests for Jira capability adapters."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JIRA_SCRIPTS = PROJECT_ROOT / "skills" / "reference" / "rhdh-jira-api" / "scripts"


def load_script(name: str):
    path = JIRA_SCRIPTS / name
    spec = importlib.util.spec_from_file_location(f"jira_{path.stem}_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_setup_detects_native_acli_without_inspecting_credentials(monkeypatch, capsys):
    setup = load_script("setup.py")
    monkeypatch.setattr(setup, "find_acli", lambda: "/tools/acli")
    monkeypatch.setattr(setup, "smoke_test", lambda _path: (True, "connected"))

    with pytest.raises(SystemExit) as exc:
        setup.main(["--json", "--quick"])

    assert exc.value.code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["adapters"] == ["acli"]
    assert result["connectivity"] is True
    assert not any(
        word in key.lower()
        for key in result
        for word in ("credential", "password", "secret", "token")
    )


def test_component_validation_reads_project_data_through_acli(monkeypatch):
    validator = load_script("validate_components.py")
    calls = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv,
            0,
            json.dumps({"components": [{"name": "Catalog"}, {"name": "Build"}]}),
            "",
        )

    monkeypatch.setattr(validator.subprocess, "run", fake_run)

    assert validator.fetch_components("/tools/acli", "RHIDP") == ["Build", "Catalog"]
    assert calls == [["/tools/acli", "jira", "project", "view", "--key", "RHIDP", "--json"]]

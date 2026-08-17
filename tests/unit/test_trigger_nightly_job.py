"""Behavior tests for the OpenShift CI Gangway adapter."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "skills" / "ci" / "rhdh-prow-trigger" / "scripts" / "trigger_nightly_job.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("trigger_nightly_job", SCRIPT)
assert SPEC and SPEC.loader
NIGHTLY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NIGHTLY)


def test_existing_native_cli_session_is_consumed_without_login(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        if argv[-1] == "--show-server":
            return SimpleNamespace(returncode=0, stdout=NIGHTLY.CI_SERVER)
        if argv[-1] == "whoami":
            return SimpleNamespace(returncode=0, stdout="developer")
        raise AssertionError(argv)

    monkeypatch.setattr(NIGHTLY.shutil, "which", lambda _name: "oc")
    monkeypatch.setattr(NIGHTLY.subprocess, "run", fake_run)

    assert NIGHTLY.ensure_capability("ci-kubeconfig") is None
    assert all("login" not in argv for argv in calls)
    assert all("-t" not in argv for argv in calls)


def test_missing_session_routes_to_human_setup_without_login(monkeypatch, capsys):
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(NIGHTLY.shutil, "which", lambda _name: "oc")
    monkeypatch.setattr(NIGHTLY.subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        NIGHTLY.ensure_capability("ci-kubeconfig")

    assert "/setup-rhdh-skills openshift-ci" in capsys.readouterr().err
    assert all("login" not in argv for argv in calls)


def test_dry_run_is_a_credential_free_adapter_preview(capsys):
    payload = {"job_name": "periodic-ci-example", "job_execution_type": "1"}

    NIGHTLY.print_dry_run(payload)

    output = capsys.readouterr().out
    preview = json.loads(output.split("\n", 1)[1])
    assert preview == {
        "adapter": "openshift-ci-gangway/v1",
        "operation": "gangway.execution.create",
        "target": NIGHTLY.GANGWAY_URL,
        "authentication": "native oc kubeconfig (redacted)",
        "payload": payload,
    }
    assert "Bearer" not in output
    assert "whoami -t" not in output

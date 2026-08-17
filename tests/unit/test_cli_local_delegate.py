"""Compatibility tests for the standalone-safe `rhdh local` seam."""

from __future__ import annotations

import subprocess

from rhdh import cli
from rhdh.formatters import OutputFormatter


def test_local_parser_preserves_the_standalone_cli_arguments():
    args = cli.create_parser().parse_args(["--json", "local", "up", "--customized", "--lightspeed"])

    assert args.command == "local"
    assert args.local_args == ["up", "--customized", "--lightspeed"]
    assert args.func is cli.cmd_local_delegate


def test_local_parser_forwards_help_instead_of_consuming_it():
    args = cli.create_parser().parse_args(["local", "--help"])

    assert args.local_help is True
    assert args.local_args == []


def test_local_delegate_forwards_output_mode_and_exit_code(monkeypatch):
    args = cli.create_parser().parse_args(["--human", "local", "status"])
    observed = []

    monkeypatch.setattr(cli, "_resolve_local_cli", lambda: "/tools/rhdh-local")

    def fake_run(argv, **kwargs):
        observed.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 7)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    code = cli.cmd_local_delegate(OutputFormatter(mode="human"), args)

    assert code == 7
    assert observed == [(["/tools/rhdh-local", "--human", "status"], {"check": False})]


def test_local_cli_resolves_next_to_the_installed_python(monkeypatch, tmp_path):
    executable = tmp_path / ("rhdh-local.exe" if cli.os.name == "nt" else "rhdh-local")
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)
    monkeypatch.setattr(cli.sys, "executable", str(tmp_path / "python"))

    assert cli._resolve_local_cli() == str(executable)


def test_local_delegate_keeps_the_legacy_missing_subcommand_gate(monkeypatch, capsys):
    args = cli.create_parser().parse_args(["--json", "local"])
    monkeypatch.setattr(cli, "_resolve_local_cli", lambda: "/tools/rhdh-local")

    code = cli.cmd_local_delegate(OutputFormatter(mode="json"), args)

    assert code == 1
    assert '"code": "MISSING_SUBCOMMAND"' in capsys.readouterr().out

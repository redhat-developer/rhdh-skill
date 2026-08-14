"""Tests for rhdh-must-gather-helm-bump skill script."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = PROJECT_ROOT / "skills" / "ci" / "rhdh-must-gather-helm-bump"
MAIN_SCRIPT = SKILL_DIR / "scripts" / "bump-must-gather-helm.sh"

HELM_STAGES_SNIPPET = textwrap.dedent(
    """\
    # Stage 2a: Install helm from CGW
    # Comment this out and uncomment Stage 2b below when no binary available.
    # https://registry.access.redhat.com/ubi9-minimal
    FROM registry.example/ubi9-minimal AS helm-builder
    RUN echo cgw

    # Stage 2b: Build helm from vendored source
    # Swap with Stage 2a: comment out Stage 2a, uncomment below.
    # update via: make vendor-update VENDOR_NAME=helm VENDOR_VERSION=vX
    # https://registry.access.redhat.com/ubi9/go-toolset
    # FROM registry.example/go-toolset AS helm-builder
    # COPY vendor/helm /opt/app-root/src/helm
    # RUN echo vendor

    # Stage 3: Final image
    FROM registry.example/ubi9-minimal
    ARG RHDH_MUST_GATHER_VERSION="0.0.0-unknown"
    ENV MIDSTREAM_REPO="https://example.invalid/mr/1" \\
        COMPNAME="must-gather"
    """
)

MULTI_COMPONENT_YAML = textwrap.dedent(
    """\
    hub:
      path_context: "distgit/containers/rhdh-hub"
      prefetch_input: '[{"type": "yarn", "path": "distgit/containers/rhdh-hub"}]'

    operator:
      path_context: "distgit/containers/rhdh-operator"
      prefetch_input: '{"type": "gomod"}'

    must-gather:
      path_context: "distgit/containers/rhdh-must-gather"
      prefetch_input: '[]'

    bootc:
      path_context: "distgit/containers/rhdh-bootc"
      prefetch_input: '{"type": "rpm"}'
    """
)

HUB_PREFETCH = '[{"type": "yarn", "path": "distgit/containers/rhdh-hub"}]'
OPERATOR_PREFETCH = '{"type": "gomod"}'
BOOTC_PREFETCH = '{"type": "rpm"}'


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _write_executable(path: Path, body: str = "#!/usr/bin/env bash\n") -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _make_upstream(parent: Path, *, cgw_exit: int = 0) -> Path:
    upstream = parent / "1-must-gather"
    upstream.mkdir(parents=True)
    (upstream / "Makefile").write_text("HELM_VERSION := 4.2.3\n", encoding="utf-8")
    (upstream / "collection-scripts").mkdir()
    (upstream / "artifacts.lock.yaml").write_text("artifacts: []\n", encoding="utf-8")
    (upstream / "Containerfile").write_text(HELM_STAGES_SNIPPET, encoding="utf-8")
    rhdh_docker = upstream / ".rhdh" / "docker"
    rhdh_docker.mkdir(parents=True)
    (rhdh_docker / "Containerfile").write_text(HELM_STAGES_SNIPPET, encoding="utf-8")
    hack = upstream / "hack"
    hack.mkdir()
    _write_executable(
        hack / "check-helm-binary-available.sh",
        f"#!/usr/bin/env bash\nexit {cgw_exit}\n",
    )
    for name in (
        "update-helm-lockfile.sh",
        "install-helm-binary.sh",
        "install-helm-local.sh",
        "update-vendor.sh",
        "verify-helm-tarball.sh",
        "deploy-k8s.sh",
    ):
        _write_executable(hack / name)
    vendor = upstream / "vendor"
    (vendor / "websocat").mkdir(parents=True)
    (vendor / "websocat" / "Cargo.toml").write_text(
        "[package]\nname='websocat'\n", encoding="utf-8"
    )
    (vendor / "helm").mkdir(parents=True)
    (vendor / "helm" / "go.mod").write_text("module helm\n", encoding="utf-8")
    return upstream


def _make_downstream(parent: Path) -> Path:
    downstream = parent / "4-rhdh"
    distgit = downstream / "distgit" / "containers" / "rhdh-must-gather"
    distgit.mkdir(parents=True)
    stale = distgit / "vendor" / "helm"
    stale.mkdir(parents=True)
    (stale / "README.md").write_text("stale\n", encoding="utf-8")
    (distgit / "vendor" / "websocat").mkdir(parents=True)
    (distgit / "vendor" / "websocat" / "old.txt").write_text("old\n", encoding="utf-8")
    (distgit / "Containerfile").write_text(
        HELM_STAGES_SNIPPET.replace(
            'ARG RHDH_MUST_GATHER_VERSION="0.0.0-unknown"',
            'ARG RHDH_MUST_GATHER_VERSION="-1"',
        )
        + '\nENV SUMMARY="Red Hat Developer Hub must-gather" \\\n'
        + '    MIDSTREAM_REPO="https://example.invalid/mr/1" \\\n'
        + '    COMPNAME="must-gather"\n'
        + 'LABEL summary="$SUMMARY"\n',
        encoding="utf-8",
    )
    tekton = downstream / ".tekton"
    tekton.mkdir()
    for name in ("rhdh-must-gather-2-pull.yaml", "rhdh-must-gather-2-push.yaml"):
        (tekton / name).write_text(
            "    - name: prefetch-input\n      value: '[]'\n",
            encoding="utf-8",
        )
    templates = downstream / ".tekton-templates"
    templates.mkdir()
    (templates / "components.yaml").write_text(MULTI_COMPONENT_YAML, encoding="utf-8")
    return downstream


class TestBumpMustGatherHelmScript:
    """Smoke and regression tests for bump-must-gather-helm.sh."""

    def test_script_exists(self) -> None:
        assert MAIN_SCRIPT.is_file()

    @pytest.mark.parametrize("flag", ["--help", "-h"])
    def test_help_exits_zero(self, flag: str) -> None:
        result = subprocess.run(
            [str(MAIN_SCRIPT), flag],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout + result.stderr

    def test_missing_to_version_exits_nonzero(self) -> None:
        result = subprocess.run(
            [str(MAIN_SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "--to VERSION is required" in result.stderr

    def test_missing_flag_value_exits_with_message(self) -> None:
        result = subprocess.run(
            [str(MAIN_SCRIPT), "--to"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "--to requires a value" in result.stderr

    def test_invalid_version_exits_nonzero(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        upstream.mkdir()
        (upstream / "Makefile").write_text("HELM_VERSION := 4.2.3\n", encoding="utf-8")
        (upstream / "collection-scripts").mkdir()
        (upstream / "hack").mkdir()
        (upstream / "hack" / "update-helm-lockfile.sh").write_text(
            "#!/bin/bash\n", encoding="utf-8"
        )

        result = subprocess.run(
            [
                str(MAIN_SCRIPT),
                "--to",
                "not-a-version",
                "--upstream",
                str(upstream),
                "--downstream",
                str(tmp_path / "downstream"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "Invalid Helm version" in result.stderr

    def test_check_mode_prints_mode(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        downstream = _make_downstream(parent)

        result = subprocess.run(
            [
                str(MAIN_SCRIPT),
                "--to",
                "4.2.3",
                "--check",
                "--parent-dir",
                str(parent),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "mode=cgw" in result.stdout
        assert "helm_version=4.2.3" in result.stdout
        assert upstream.exists() and downstream.exists()

    def test_cgw_sync_scopes_prefetch_omits_helm_keeps_websocat(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        downstream = _make_downstream(parent)
        distgit = downstream / "distgit" / "containers" / "rhdh-must-gather"
        stale_vendor = distgit / "vendor" / "helm"

        for repo in (upstream, downstream):
            _git_init(repo)

        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/example/rhdh-must-gather"],
            cwd=upstream,
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            [
                str(MAIN_SCRIPT),
                "--to",
                "4.2.3",
                "--allow-dirty",
                "--parent-dir",
                str(parent),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert not stale_vendor.exists()
        assert (distgit / "vendor" / "websocat" / "Cargo.toml").is_file()
        assert (distgit / "hack" / "verify-helm-tarball.sh").is_file()
        assert (distgit / "hack" / "deploy-k8s.sh").is_file()

        components = (downstream / ".tekton-templates" / "components.yaml").read_text(
            encoding="utf-8"
        )
        assert HUB_PREFETCH in components
        assert OPERATOR_PREFETCH in components
        assert BOOTC_PREFETCH in components
        assert '"type": "generic"' in components
        assert "vendor/helm" not in components.split("must-gather:")[1].split("bootc:")[0]

        pull = (downstream / ".tekton" / "rhdh-must-gather-2-pull.yaml").read_text(encoding="utf-8")
        assert '"type": "generic"' in pull

        # Stage 2a active, 2b commented in distgit Containerfile
        cf = (distgit / "Containerfile").read_text(encoding="utf-8")
        assert "\nFROM registry.example/ubi9-minimal AS helm-builder\n" in cf
        assert "\n# FROM registry.example/go-toolset AS helm-builder\n" in cf
        assert 'ARG RHDH_MUST_GATHER_VERSION="-1"' in cf
        assert 'ENV SUMMARY="Red Hat Developer Hub must-gather"' in cf
        assert "LABEL summary=" in cf

        sha_file = downstream / "sync" / "upstream_SHA_rhdh-must-gather"
        assert sha_file.is_file()
        assert " @ https://github.com/example/rhdh-must-gather" in sha_file.read_text(
            encoding="utf-8"
        )

    def test_vendor_mode_flips_stages_and_keeps_helm(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=1)
        downstream = _make_downstream(parent)
        distgit = downstream / "distgit" / "containers" / "rhdh-must-gather"

        for repo in (upstream, downstream):
            _git_init(repo)

        result = subprocess.run(
            [
                str(MAIN_SCRIPT),
                "--to",
                "4.2.3",
                "--allow-dirty",
                "--parent-dir",
                str(parent),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert (distgit / "vendor" / "helm" / "go.mod").is_file()
        assert (distgit / "vendor" / "websocat" / "Cargo.toml").is_file()

        upstream_cf = (upstream / "Containerfile").read_text(encoding="utf-8")
        assert "\n# FROM registry.example/ubi9-minimal AS helm-builder\n" in upstream_cf
        assert "\nFROM registry.example/go-toolset AS helm-builder\n" in upstream_cf

        components = (downstream / ".tekton-templates" / "components.yaml").read_text(
            encoding="utf-8"
        )
        assert HUB_PREFETCH in components
        mg_block = components.split("must-gather:")[1].split("bootc:")[0]
        assert '"type": "gomod"' in mg_block
        assert "vendor/helm" in mg_block

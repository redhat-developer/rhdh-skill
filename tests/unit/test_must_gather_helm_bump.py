"""Tests for rhdh-must-gather-helm-bump skill script."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = PROJECT_ROOT / "skills" / "ci" / "rhdh-must-gather-helm-bump"
MAIN_SCRIPT = SKILL_DIR / "scripts" / "bump-must-gather-helm.py"

FIXTURE_HELM = "4.2.3"
TARGET_HELM = "4.3.0"

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

HELM_STAGES_VENDOR = textwrap.dedent(
    """\
    # Stage 2a: Install helm from CGW
    # Comment this out and uncomment Stage 2b below when no binary available.
    # https://registry.access.redhat.com/ubi9-minimal
    # FROM registry.example/ubi9-minimal AS helm-builder
    # RUN echo cgw

    # Stage 2b: Build helm from vendored source
    # Swap with Stage 2a: comment out Stage 2a, uncomment below.
    # update via: make vendor-update VENDOR_NAME=helm VENDOR_VERSION=vX
    # https://registry.access.redhat.com/ubi9/go-toolset
    FROM registry.example/go-toolset AS helm-builder
    COPY vendor/helm /opt/app-root/src/helm
    RUN echo vendor

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

LOCKFILE_STUB = textwrap.dedent(
    """\
    #!/usr/bin/env bash
    set -euo pipefail
    ver="${1#v}"
    printf 'HELM_VERSION := %s\\n' "$ver" > Makefile
    printf 'artifacts:\\n  - download_url: https://mirror.example/cgw/helm/%s/helm.tgz\\n' "$ver" > artifacts.lock.yaml
    """
)

VENDOR_STUB = textwrap.dedent(
    """\
    #!/usr/bin/env bash
    set -euo pipefail
    ver="${2#v}"
    printf 'HELM_VERSION := %s\\n' "$ver" > Makefile
    """
)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MAIN_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _load_script():
    spec = importlib.util.spec_from_file_location("bump_must_gather_helm", MAIN_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git_commit_all(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _apply_two_step(parent: Path, *extra: str) -> None:
    first = _run(
        "--to",
        TARGET_HELM,
        "--skip-downstream",
        "--parent-dir",
        str(parent),
        *extra,
    )
    assert first.returncode == 0, first.stderr
    _git_commit_all(parent / "1-must-gather", "bump helm")
    second = _run(
        "--to",
        TARGET_HELM,
        "--skip-upstream",
        "--parent-dir",
        str(parent),
        *extra,
    )
    assert second.returncode == 0, second.stderr


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


def _make_upstream(
    parent: Path,
    *,
    cgw_exit: int = 0,
    stages: str = HELM_STAGES_SNIPPET,
    name: str = "1-must-gather",
) -> Path:
    upstream = parent / name
    upstream.mkdir(parents=True)
    (upstream / "Makefile").write_text(f"HELM_VERSION := {FIXTURE_HELM}\n", encoding="utf-8")
    (upstream / "collection-scripts").mkdir()
    (upstream / "artifacts.lock.yaml").write_text(
        f"artifacts:\n  - download_url: https://mirror.example/cgw/helm/{FIXTURE_HELM}/helm.tgz\n",
        encoding="utf-8",
    )
    (upstream / "Containerfile").write_text(stages, encoding="utf-8")
    rhdh_docker = upstream / ".rhdh" / "docker"
    rhdh_docker.mkdir(parents=True)
    (rhdh_docker / "Containerfile").write_text(stages, encoding="utf-8")
    hack = upstream / "hack"
    hack.mkdir()
    _write_executable(
        hack / "check-helm-binary-available.sh",
        f"#!/usr/bin/env bash\nexit {cgw_exit}\n",
    )
    _write_executable(hack / "update-helm-lockfile.sh", LOCKFILE_STUB)
    _write_executable(hack / "update-vendor.sh", VENDOR_STUB)
    for name_script in (
        "install-helm-binary.sh",
        "install-helm-local.sh",
        "verify-helm-tarball.sh",
        "deploy-k8s.sh",
    ):
        _write_executable(hack / name_script)
    vendor = upstream / "vendor"
    (vendor / "websocat").mkdir(parents=True)
    (vendor / "websocat" / "Cargo.toml").write_text(
        "[package]\nname='websocat'\n", encoding="utf-8"
    )
    (vendor / "helm").mkdir(parents=True)
    (vendor / "helm" / "go.mod").write_text("module helm\n", encoding="utf-8")
    return upstream


def _make_downstream(
    parent: Path,
    *,
    name: str = "4-rhdh",
    release: str = "1",
    version: str = "2.0",
) -> Path:
    downstream = parent / name
    distgit = downstream / "distgit" / "containers" / "rhdh-must-gather"
    distgit.mkdir(parents=True)
    stale = distgit / "vendor" / "helm"
    stale.mkdir(parents=True)
    (stale / "README.md").write_text("stale\n", encoding="utf-8")
    (distgit / "vendor" / "websocat").mkdir(parents=True)
    (distgit / "vendor" / "websocat" / "old.txt").write_text("old\n", encoding="utf-8")
    tag = f"{version}-{release}"
    (distgit / "Containerfile").write_text(
        HELM_STAGES_SNIPPET.replace(
            'ARG RHDH_MUST_GATHER_VERSION="0.0.0-unknown"',
            'ARG RHDH_MUST_GATHER_VERSION="-1"',
        )
        + '\nENV SUMMARY="Red Hat Developer Hub must-gather" \\\n'
        + '    MIDSTREAM_REPO="https://example.invalid/mr/1" \\\n'
        + '    COMPNAME="must-gather"\n'
        + 'LABEL summary="$SUMMARY" \\\n'
        + f'      version="{version}" \\\n'
        + f'      release="{release}" \\\n'
        + f'      konflux.additional-tags="next, {version}, {tag}" \\\n'
        + '      distribution-scope="public"\n',
        encoding="utf-8",
    )
    tekton = downstream / ".tekton"
    tekton.mkdir()
    for plr in ("rhdh-must-gather-2-pull.yaml", "rhdh-must-gather-2-push.yaml"):
        (tekton / plr).write_text(
            "    - name: prefetch-input\n      value: '[]'\n",
            encoding="utf-8",
        )
    templates = downstream / ".tekton-templates"
    templates.mkdir()
    (templates / "components.yaml").write_text(MULTI_COMPONENT_YAML, encoding="utf-8")
    return downstream


class TestBumpMustGatherHelmScript:
    """Smoke and regression tests for bump-must-gather-helm.py."""

    def test_script_exists(self) -> None:
        assert MAIN_SCRIPT.is_file()

    @pytest.mark.parametrize("flag", ["--help", "-h"])
    def test_help_exits_zero(self, flag: str) -> None:
        result = _run(flag)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "usage:" in combined.lower()
        assert "--to" in combined
        assert "skills/ci/rhdh-must-gather-helm-bump" not in combined

    def test_missing_to_version_exits_nonzero(self) -> None:
        result = _run()
        assert result.returncode != 0
        assert "--to VERSION is required" in result.stderr

    def test_missing_flag_value_exits_with_message(self) -> None:
        result = _run("--to")
        assert result.returncode != 0
        assert "--to requires a value" in result.stderr

    def test_invalid_version_exits_nonzero(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        upstream.mkdir()
        (upstream / "Makefile").write_text(f"HELM_VERSION := {FIXTURE_HELM}\n", encoding="utf-8")
        (upstream / "collection-scripts").mkdir()
        (upstream / "hack").mkdir()
        (upstream / "hack" / "update-helm-lockfile.sh").write_text(
            "#!/bin/bash\n", encoding="utf-8"
        )

        result = _run(
            "--to",
            "not-a-version",
            "--upstream",
            str(upstream),
            "--downstream",
            str(tmp_path / "downstream"),
        )
        assert result.returncode != 0
        assert "Invalid Helm version" in result.stderr

    def test_check_mode_prints_mode(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        downstream = _make_downstream(parent)

        result = _run("--to", TARGET_HELM, "--check", "--parent-dir", str(parent))
        assert result.returncode == 0, result.stderr
        assert "mode=cgw" in result.stdout
        assert f"helm_version={TARGET_HELM}" in result.stdout
        assert upstream.exists() and downstream.exists()

    def test_skip_upstream_check_probes_upstream_not_stale_vendor(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        _make_upstream(parent, cgw_exit=0)
        downstream = _make_downstream(parent)
        distgit = downstream / "distgit" / "containers" / "rhdh-must-gather"
        (distgit / "artifacts.lock.yaml").write_text(
            f"artifacts:\n  - cgw/helm/{FIXTURE_HELM}/\n",
            encoding="utf-8",
        )
        assert (distgit / "vendor" / "helm").is_dir()

        result = _run(
            "--to",
            TARGET_HELM,
            "--check",
            "--skip-upstream",
            "--parent-dir",
            str(parent),
        )
        assert result.returncode == 0, result.stderr
        assert "mode=cgw" in result.stdout

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

        _apply_two_step(parent)
        assert not stale_vendor.exists()
        assert (distgit / "vendor" / "websocat" / "Cargo.toml").is_file()
        assert (distgit / "hack" / "verify-helm-tarball.sh").is_file()
        assert (distgit / "hack" / "deploy-k8s.sh").is_file()
        assert (upstream / "Makefile").read_text(
            encoding="utf-8"
        ) == f"HELM_VERSION := {TARGET_HELM}\n"
        assert (distgit / "Makefile").read_text(
            encoding="utf-8"
        ) == f"HELM_VERSION := {TARGET_HELM}\n"
        assert f"cgw/helm/{TARGET_HELM}/" in (distgit / "artifacts.lock.yaml").read_text(
            encoding="utf-8"
        )

        components = (downstream / ".tekton-templates" / "components.yaml").read_text(
            encoding="utf-8"
        )
        assert HUB_PREFETCH in components
        assert OPERATOR_PREFETCH in components
        assert BOOTC_PREFETCH in components
        assert '"type": "generic"' in components
        assert "vendor/helm" not in components.split("must-gather:")[1].split("bootc:")[0]

        pull = (downstream / ".tekton" / "rhdh-must-gather-2-pull.yaml").read_text(encoding="utf-8")
        push = (downstream / ".tekton" / "rhdh-must-gather-2-push.yaml").read_text(encoding="utf-8")
        assert '"type": "generic"' in pull
        assert '"type": "generic"' in push

        cf = (distgit / "Containerfile").read_text(encoding="utf-8")
        assert "\nFROM registry.example/ubi9-minimal AS helm-builder\n" in cf
        assert "\n# FROM registry.example/go-toolset AS helm-builder\n" in cf
        assert 'ARG RHDH_MUST_GATHER_VERSION="-1"' in cf
        assert 'ENV SUMMARY="Red Hat Developer Hub must-gather"' in cf
        assert 'release="2"' in cf
        assert 'konflux.additional-tags="next, 2.0, 2.0-2"' in cf
        assert 'release="1"' not in cf

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

        _apply_two_step(parent)
        assert (distgit / "vendor" / "helm" / "go.mod").is_file()
        assert (distgit / "vendor" / "websocat" / "Cargo.toml").is_file()
        assert (upstream / "Makefile").read_text(
            encoding="utf-8"
        ) == f"HELM_VERSION := {TARGET_HELM}\n"

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

        push = (downstream / ".tekton" / "rhdh-must-gather-2-push.yaml").read_text(encoding="utf-8")
        assert '"type": "gomod"' in push

    def test_vendor_then_cgw_flips_2b_back_to_2a(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0, stages=HELM_STAGES_VENDOR)
        downstream = _make_downstream(parent)
        distgit = downstream / "distgit" / "containers" / "rhdh-must-gather"

        for repo in (upstream, downstream):
            _git_init(repo)

        _apply_two_step(parent)

        upstream_cf = (upstream / "Containerfile").read_text(encoding="utf-8")
        assert "\nFROM registry.example/ubi9-minimal AS helm-builder\n" in upstream_cf
        assert "\n# FROM registry.example/go-toolset AS helm-builder\n" in upstream_cf

        distgit_cf = (distgit / "Containerfile").read_text(encoding="utf-8")
        assert "\nFROM registry.example/ubi9-minimal AS helm-builder\n" in distgit_cf
        assert "\n# FROM registry.example/go-toolset AS helm-builder\n" in distgit_cf

    def test_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        downstream = _make_downstream(parent)
        distgit = downstream / "distgit" / "containers" / "rhdh-must-gather"
        makefile_before = (upstream / "Makefile").read_text(encoding="utf-8")
        pull_before = (downstream / ".tekton" / "rhdh-must-gather-2-pull.yaml").read_text(
            encoding="utf-8"
        )
        push_before = (downstream / ".tekton" / "rhdh-must-gather-2-push.yaml").read_text(
            encoding="utf-8"
        )

        for repo in (upstream, downstream):
            _git_init(repo)

        result = _run("--to", TARGET_HELM, "--dry-run", "--parent-dir", str(parent))
        assert result.returncode == 0, result.stderr
        assert "[DRY-RUN]" in result.stderr
        assert (upstream / "Makefile").read_text(encoding="utf-8") == makefile_before
        assert (distgit / "vendor" / "helm").is_dir()
        assert not (downstream / "sync" / "upstream_SHA_rhdh-must-gather").exists()
        assert (downstream / ".tekton" / "rhdh-must-gather-2-pull.yaml").read_text(
            encoding="utf-8"
        ) == pull_before
        assert (downstream / ".tekton" / "rhdh-must-gather-2-push.yaml").read_text(
            encoding="utf-8"
        ) == push_before

    def test_release_10_becomes_11_not_20(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        downstream = _make_downstream(parent, release="10")
        distgit = downstream / "distgit" / "containers" / "rhdh-must-gather"

        for repo in (upstream, downstream):
            _git_init(repo)

        _apply_two_step(parent)
        cf = (distgit / "Containerfile").read_text(encoding="utf-8")
        assert 'release="11"' in cf
        assert "2.0-11" in cf
        assert "2.0-20" not in cf
        assert 'release="10"' not in cf

    def test_bump_footer_release_boundary(self) -> None:
        footer = (
            'LABEL summary="$SUMMARY" \\\n'
            '      version="2.0" \\\n'
            '      release="10" \\\n'
            '      konflux.additional-tags="next, 2.0, 2.0-10" \\\n'
        )
        out = _load_script().bump_footer_release(footer)
        assert 'release="11"' in out
        assert "2.0-11" in out
        assert "2.0-20" not in out
        assert 'release="10"' not in out

    def test_git_status_failure_dies(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        _make_downstream(parent)
        _git_init(upstream)

        result = _run("--to", TARGET_HELM, "--parent-dir", str(parent))
        assert result.returncode != 0
        assert "is not a git repository or git status failed" in result.stderr

    def test_dirty_head_refuses_upstream_sha(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        downstream = _make_downstream(parent)
        for repo in (upstream, downstream):
            _git_init(repo)
        (upstream / "unrelated.txt").write_text("dirt\n", encoding="utf-8")

        result = _run("--to", TARGET_HELM, "--allow-dirty", "--parent-dir", str(parent))
        assert result.returncode != 0
        assert "upstream HEAD is dirty" in result.stderr
        assert not (downstream / "sync" / "upstream_SHA_rhdh-must-gather").exists()
        pull = (downstream / ".tekton" / "rhdh-must-gather-2-pull.yaml").read_text(encoding="utf-8")
        assert "value: '[]'" in pull

    def test_one_shot_apply_stops_before_distgit_after_bump(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        downstream = _make_downstream(parent)
        for repo in (upstream, downstream):
            _git_init(repo)

        result = _run("--to", TARGET_HELM, "--parent-dir", str(parent))
        assert result.returncode != 0
        assert "skip-upstream" in result.stderr
        assert (upstream / "Makefile").read_text(
            encoding="utf-8"
        ) == f"HELM_VERSION := {TARGET_HELM}\n"
        assert not (downstream / "sync" / "upstream_SHA_rhdh-must-gather").exists()
        pull = (downstream / ".tekton" / "rhdh-must-gather-2-pull.yaml").read_text(encoding="utf-8")
        assert "value: '[]'" in pull

    def test_cgw_probe_exit_2_dies(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        _make_upstream(parent, cgw_exit=2)
        _make_downstream(parent)
        result = _run("--to", TARGET_HELM, "--check", "--parent-dir", str(parent))
        assert result.returncode != 0
        assert "exited 2" in result.stderr
        assert "mode=vendor" not in result.stdout

    def test_missing_curl_dies(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        _make_downstream(parent)
        mod = _load_script()
        real_which = mod.shutil.which

        def fake_which(name: str) -> str | None:
            if name == "curl":
                return None
            return real_which(name)

        monkeypatch.setattr(mod.shutil, "which", fake_which)
        with pytest.raises(SystemExit):
            mod.cgw_available(upstream, TARGET_HELM)

    def test_parent_dir_discovers_rhdh_downstream(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        _make_upstream(parent, cgw_exit=0)
        (parent / "rhdh").mkdir()
        downstream = _make_downstream(parent, name="rhdh-downstream")
        for repo in (parent / "1-must-gather", downstream):
            _git_init(repo)

        result = _run("--to", TARGET_HELM, "--check", "--parent-dir", str(parent))
        assert result.returncode == 0, result.stderr
        assert str(downstream.resolve()) in result.stdout

    def test_missing_check_helm_script_dies(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = _make_upstream(parent, cgw_exit=0)
        _make_downstream(parent)
        (upstream / "hack" / "check-helm-binary-available.sh").unlink()

        result = _run("--to", TARGET_HELM, "--check", "--parent-dir", str(parent))
        assert result.returncode != 0
        assert "check-helm-binary-available.sh" in result.stderr

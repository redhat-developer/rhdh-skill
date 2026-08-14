#!/usr/bin/env python3
"""Bump Helm in rhdh-must-gather upstream and mirror into rhidp/rhdh distgit + Tekton.

See SKILL.md beside this scripts/ directory.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

DISTGIT_REL = "distgit/containers/rhdh-must-gather"
UPSTREAM_SHA_REL = "sync/upstream_SHA_rhdh-must-gather"
RHDH_DOCKER_CF = ".rhdh/docker/Containerfile"

PREFETCH_CGW = (
    '[{"type": "rpm", "path": "distgit/containers/rhdh-must-gather"},'
    '{"type": "pip", "path": "distgit/containers/rhdh-must-gather", "allow_binary": "false"},'
    '{"type": "generic", "path": "distgit/containers/rhdh-must-gather"},'
    '{"type": "cargo", "path": "distgit/containers/rhdh-must-gather/vendor/websocat"}]'
)

PREFETCH_VENDOR = (
    '[{"type": "rpm", "path": "distgit/containers/rhdh-must-gather"},'
    '{"type": "pip", "path": "distgit/containers/rhdh-must-gather", "allow_binary": "false"},'
    '{"type": "gomod", "path": "distgit/containers/rhdh-must-gather/vendor/helm"},'
    '{"type": "cargo", "path": "distgit/containers/rhdh-must-gather/vendor/websocat"}]'
)

VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$")
DOC_COMMENT_RE = re.compile(r"^# (Comment this out|Swap with|update via|https://)")
STAGE_HEADER_RE = re.compile(r"^# Stage (\S+):")


def die(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise SystemExit(1)


def log(msg: str) -> None:
    print(f"[INFO] {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def normalize_version(raw: str) -> str:
    v = raw[1:] if raw.startswith("v") else raw
    if not VERSION_RE.match(v):
        die(f"Invalid Helm version '{v}'. Expected semver like 4.3.0")
    return v


def require_on_path(name: str) -> str:
    found = shutil.which(name)
    if not found:
        die(f"Required command not found on PATH: {name}")
    return found


def discover_repo(parent: Path, *names: str, required: str | None = None) -> Path | None:
    for name in names:
        candidate = parent / name
        if not candidate.is_dir():
            continue
        if required is not None and not (candidate / required).exists():
            continue
        return candidate.resolve()
    return None


def validate_upstream(path: Path) -> None:
    if not (path / "Makefile").is_file():
        die(f"Not a must-gather repo (missing Makefile): {path}")
    if not (path / "hack" / "update-helm-lockfile.sh").is_file():
        die(f"Missing hack/update-helm-lockfile.sh in {path}")
    if not (path / "hack" / "check-helm-binary-available.sh").is_file():
        die(f"Missing hack/check-helm-binary-available.sh in {path}")
    if not (path / "collection-scripts").is_dir():
        die(f"Missing collection-scripts/ in {path}")


def validate_downstream(path: Path) -> None:
    if not (path / DISTGIT_REL).is_dir():
        die(f"Missing {DISTGIT_REL} in {path}")
    if not (path / ".tekton" / "rhdh-must-gather-2-pull.yaml").is_file():
        die(f"Missing .tekton/rhdh-must-gather-2-pull.yaml in {path}")
    if not (path / ".tekton" / "rhdh-must-gather-2-push.yaml").is_file():
        die(f"Missing .tekton/rhdh-must-gather-2-push.yaml in {path}")
    if not (path / ".tekton-templates" / "components.yaml").is_file():
        die(f"Missing .tekton-templates/components.yaml in {path}")


def git_status_porcelain(path: Path, label: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        die(
            f"{label} is not a git repository or git status failed ({path}): "
            f"{result.stderr.strip() or 'unknown error'}"
        )
    return result.stdout.strip()


def assert_clean_tree(path: Path, label: str, *, allow_dirty: bool) -> None:
    if allow_dirty:
        return
    if git_status_porcelain(path, label):
        die(
            f"{label} has uncommitted or untracked changes ({path}). "
            "Commit/stash or pass --allow-dirty"
        )


def cgw_available(upstream: Path, version: str) -> bool:
    script = upstream / "hack" / "check-helm-binary-available.sh"
    if not script.is_file():
        die(f"Missing hack/check-helm-binary-available.sh in {upstream}")
    bash = require_on_path("bash")
    result = subprocess.run(
        [bash, str(script), version],
        cwd=str(upstream),
        check=False,
    )
    return result.returncode == 0


def read_makefile_helm_version(makefile: Path) -> str:
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if line.startswith("HELM_VERSION := "):
            return line[len("HELM_VERSION := ") :]
    die(f"No HELM_VERSION := line in {makefile}")
    raise AssertionError("unreachable")


def run_cmd(dry_run: bool, *argv: str, cwd: Path | None = None) -> None:
    if dry_run:
        print(f"[DRY-RUN] {' '.join(argv)}", file=sys.stderr)
        return
    subprocess.run(list(argv), cwd=str(cwd) if cwd else None, check=True)


def bump_upstream_cgw(upstream: Path, version: str, *, dry_run: bool) -> None:
    log(f"Upstream: refreshing CGW lockfile for helm v{version}...")
    run_cmd(
        dry_run,
        "bash",
        "-c",
        f"./hack/update-helm-lockfile.sh 'v{version}'",
        cwd=upstream,
    )


def bump_upstream_vendor(upstream: Path, version: str, *, dry_run: bool) -> None:
    log(f"Upstream: vendoring helm v{version} source...")
    run_cmd(
        dry_run,
        "bash",
        "-c",
        f"./hack/update-vendor.sh helm 'v{version}'",
        cwd=upstream,
    )


def flip_helm_stages(file: Path, mode: str, *, dry_run: bool) -> None:
    """Bidirectional Stage 2a/2b comment flip. Doc-only comments stay commented."""
    if not file.is_file():
        die(f"Missing Containerfile for stage flip: {file}")

    if dry_run:
        print(f"[DRY-RUN] flip Stage 2a/2b to mode={mode} in {file}", file=sys.stderr)
        return

    stage = ""
    out_lines: list[str] = []
    for line in file.read_text(encoding="utf-8").splitlines(keepends=True):
        raw = line.rstrip("\n")
        header = STAGE_HEADER_RE.match(raw)
        if header:
            stage_id = header.group(1)
            if stage_id in ("2a", "2b"):
                stage = stage_id
            else:
                stage = ""
            out_lines.append(line)
            continue

        if stage == "":
            out_lines.append(line)
            continue

        if DOC_COMMENT_RE.match(raw) or raw.strip() == "":
            out_lines.append(line)
            continue

        want_active = (stage == "2a" and mode == "cgw") or (stage == "2b" and mode == "vendor")
        if want_active:
            if raw.startswith("# "):
                out_lines.append(raw[2:] + ("\n" if line.endswith("\n") else ""))
            else:
                out_lines.append(line)
        else:
            if raw.startswith("# "):
                out_lines.append(line)
            else:
                out_lines.append("# " + raw + ("\n" if line.endswith("\n") else ""))

    file.write_text("".join(out_lines), encoding="utf-8")
    log(f"Flipped Stage 2a/2b to mode={mode} in {file}")


def sync_path(src: Path, dst: Path, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY-RUN] cp -pPR '{src}' -> '{dst}'", file=sys.stderr)
        return
    rsync = require_on_path("rsync")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [rsync, "-a", "--delete", f"{src}/", f"{dst}/"],
            check=True,
        )
    else:
        shutil.copy2(src, dst)


def sync_to_distgit(upstream: Path, downstream: Path, mode: str, *, dry_run: bool) -> None:
    dest = downstream / DISTGIT_REL
    log(f"Syncing helm-related files to {dest}...")

    for rel in ("Makefile", "artifacts.lock.yaml"):
        src = upstream / rel
        if not src.exists():
            warn(f"Skipping missing upstream path: {rel}")
            continue
        sync_path(src, dest / rel, dry_run=dry_run)

    if (upstream / "hack").is_dir():
        sync_path(upstream / "hack", dest / "hack", dry_run=dry_run)
    else:
        warn("Skipping missing upstream hack/")

    upstream_cf = upstream / RHDH_DOCKER_CF
    if upstream_cf.is_file():
        sync_path(upstream_cf, dest / RHDH_DOCKER_CF, dry_run=dry_run)
    else:
        warn(f"Skipping missing upstream {RHDH_DOCKER_CF}")

    vendor_src = upstream / "vendor"
    vendor_dst = dest / "vendor"
    if vendor_src.is_dir():
        if dry_run:
            if mode == "cgw":
                print("[DRY-RUN] rsync vendor/ -> distgit (exclude helm/)", file=sys.stderr)
            else:
                print("[DRY-RUN] rsync vendor/ -> distgit (include helm/)", file=sys.stderr)
        else:
            vendor_dst.mkdir(parents=True, exist_ok=True)
            rsync = require_on_path("rsync")
            if mode == "cgw":
                subprocess.run(
                    [
                        rsync,
                        "-a",
                        "--delete",
                        "--exclude",
                        "helm/",
                        f"{vendor_src}/",
                        f"{vendor_dst}/",
                    ],
                    check=True,
                )
                helm_dir = vendor_dst / "helm"
                if helm_dir.is_dir():
                    log("Removing stale distgit vendor/helm/ (CGW path active)")
                    shutil.rmtree(helm_dir)
            else:
                subprocess.run(
                    [rsync, "-a", "--delete", f"{vendor_src}/", f"{vendor_dst}/"],
                    check=True,
                )
    else:
        warn("Skipping missing upstream vendor/")
        helm_dir = vendor_dst / "helm"
        if mode == "cgw" and helm_dir.is_dir():
            if dry_run:
                print(f"[DRY-RUN] rm -rf '{helm_dir}'", file=sys.stderr)
            else:
                log("Removing stale distgit vendor/helm/ (CGW path active)")
                shutil.rmtree(helm_dir)


def bump_footer_release(footer: str) -> str:
    """Bump LABEL release=\"N\" → N+1 and rewrite konflux.additional-tags suffix."""
    current_m = re.search(r'(?:^|[ \t])release="([0-9]+)"', footer, re.M)
    if not current_m:
        current_m = re.search(r'^[ \t]*release="([0-9]+)"', footer, re.M)
    if not current_m:
        warn("Could not parse numeric release= in Containerfile footer; leaving labels unchanged")
        return footer

    current = current_m.group(1)
    next_n = str(int(current) + 1)

    version_m = re.search(r'(?:^|[ \t])version="([^"]*)"', footer, re.M)
    if not version_m:
        version_m = re.search(r'^[ \t]*version="([^"]*)"', footer, re.M)
    version = version_m.group(1) if version_m else ""

    footer = footer.replace(f'release="{current}"', f'release="{next_n}"')
    if version:
        footer = re.sub(
            rf"{re.escape(version)}-{re.escape(current)}(?![0-9])",
            f"{version}-{next_n}",
            footer,
        )
    else:
        footer = re.sub(
            rf'(konflux\.additional-tags="[^"]*-){re.escape(current)}(?![0-9])',
            rf"\g<1>{next_n}",
            footer,
        )
    log(f"Bumped Containerfile release {current} -> {next_n}")
    return footer


def regenerate_distgit_containerfile(dest: Path, *, dry_run: bool) -> None:
    src = dest / RHDH_DOCKER_CF
    out = dest / "Containerfile"
    if not src.is_file() and not dry_run:
        die(f"Missing {src}; cannot regenerate distgit Containerfile")

    existing_version = ""
    footer = ""
    if out.is_file():
        text = out.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r'^ARG RHDH_MUST_GATHER_VERSION="(.*)"', line)
            if m:
                existing_version = m.group(1)
                break
        lines = text.splitlines(keepends=True)
        collecting = False
        footer_parts: list[str] = []
        for line in lines:
            if line.startswith("ENV SUMMARY="):
                collecting = True
            if collecting:
                footer_parts.append(line)
        footer = "".join(footer_parts)
        if footer:
            footer = bump_footer_release(footer)

    if dry_run:
        has_footer = "yes" if footer else "no"
        print(
            f"[DRY-RUN] regenerate {out} from {src} "
            f"(preserve VERSION='{existing_version}' footer={has_footer}; bump release)",
            file=sys.stderr,
        )
        return

    body = src.read_text(encoding="utf-8")
    if existing_version:
        body = re.sub(
            r"RHDH_MUST_GATHER_VERSION=.*",
            f'RHDH_MUST_GATHER_VERSION="{existing_version}"',
            body,
            count=1,
        )
    if footer:
        if not body.endswith("\n"):
            body += "\n"
        body += "\n" + footer
        if not footer.endswith("\n"):
            body += "\n"
    out.write_text(body, encoding="utf-8")
    log(f"Regenerated {DISTGIT_REL}/Containerfile from {RHDH_DOCKER_CF}")


def update_upstream_sha(
    upstream: Path,
    downstream: Path,
    *,
    dry_run: bool,
    started_dirty: bool,
) -> None:
    if started_dirty:
        die(
            "Refusing to write upstream_SHA from a dirty HEAD. "
            "Commit the upstream bump first, then re-run with --skip-upstream"
        )
    sha_file = downstream / UPSTREAM_SHA_REL
    sha = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "--short", "HEAD"],
        text=True,
    ).strip()
    branch = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
    ).strip()
    remote = subprocess.run(
        ["git", "-C", str(upstream), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    remote_url = remote.stdout.strip() or "https://github.com/redhat-developer/rhdh-must-gather"
    line = f"{sha} = {branch} @ {remote_url}"

    if dry_run:
        print(f"[DRY-RUN] write '{sha_file}': {line}", file=sys.stderr)
        return

    sha_file.parent.mkdir(parents=True, exist_ok=True)
    sha_file.write_text(line + "\n", encoding="utf-8")
    log(f"Updated {UPSTREAM_SHA_REL} -> {sha}")


def replace_prefetch_plr(file: Path, prefetch: str, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY-RUN] update prefetch-input in {file}", file=sys.stderr)
        return

    lines = file.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if re.match(r"^[ \t]*- name: prefetch-input$", line.rstrip("\n")):
            if i + 1 < len(lines) and re.match(r"^[ \t]*value:", lines[i + 1].rstrip("\n")):
                indent_m = re.match(r"^([ \t]*)", lines[i + 1])
                indent = indent_m.group(1) if indent_m else ""
                out.append(f"{indent}value: '{prefetch}'\n")
                i += 2
                continue
        i += 1
    file.write_text("".join(out), encoding="utf-8")


def replace_prefetch_components(file: Path, prefetch: str, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY-RUN] update must-gather.prefetch_input in {file}", file=sys.stderr)
        return

    lines = file.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    in_mg = False
    for line in lines:
        stripped = line.rstrip("\n")
        if re.match(r"^[a-zA-Z0-9_-]+:", stripped):
            in_mg = bool(re.match(r"^must-gather:", stripped))
            out.append(line)
            continue
        if in_mg and re.match(r"^[ \t]*prefetch_input:", stripped):
            indent_m = re.match(r"^([ \t]*)", stripped)
            indent = indent_m.group(1) if indent_m else ""
            out.append(f"{indent}prefetch_input: '{prefetch}'\n")
            continue
        out.append(line)
    file.write_text("".join(out), encoding="utf-8")


def update_tekton_prefetch(downstream: Path, mode: str, *, dry_run: bool) -> None:
    prefetch = PREFETCH_VENDOR if mode == "vendor" else PREFETCH_CGW
    log(f"Downstream: setting Tekton prefetch to {mode} mode (must-gather only)...")
    replace_prefetch_plr(
        downstream / ".tekton" / "rhdh-must-gather-2-pull.yaml",
        prefetch,
        dry_run=dry_run,
    )
    replace_prefetch_plr(
        downstream / ".tekton" / "rhdh-must-gather-2-push.yaml",
        prefetch,
        dry_run=dry_run,
    )
    replace_prefetch_components(
        downstream / ".tekton-templates" / "components.yaml",
        prefetch,
        dry_run=dry_run,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bump-must-gather-helm.py",
        description=(
            "Bump Helm in rhdh-must-gather and mirror into rhidp/rhdh distgit + .tekton prefetch."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  bump-must-gather-helm.py --to 4.3.0 --parent-dir ~/RHDH
  bump-must-gather-helm.py --to v4.3.0 --upstream ~/RHDH/1-must-gather --downstream ~/RHDH/4-rhdh
  bump-must-gather-helm.py --to 4.3.0 --check --parent-dir ~/RHDH
""",
    )
    parser.add_argument(
        "--to",
        metavar="VERSION",
        help="Target Helm version (4.3.0 or v4.3.0)",
    )
    parser.add_argument("--upstream", metavar="PATH", help="rhdh-must-gather checkout")
    parser.add_argument("--downstream", metavar="PATH", help="rhidp/rhdh midstream checkout")
    parser.add_argument(
        "--parent-dir",
        metavar="PATH",
        help="Auto-discover 1-must-gather + 4-rhdh / rhdh-downstream (and aliases)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Probe CGW only; print planned path (helm_version=, mode=, ...)",
    )
    parser.add_argument(
        "--skip-upstream",
        action="store_true",
        help="Sync downstream + Tekton + upstream SHA only",
    )
    parser.add_argument(
        "--skip-downstream",
        action="store_true",
        help="Bump upstream only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Proceed with uncommitted changes",
    )
    return parser


def parse_argv(argv: list[str]) -> argparse.Namespace:
    """Parse argv with bash-compatible required-value errors for unit tests."""
    if argv and argv[0] in ("-h", "--help"):
        build_parser().print_help()
        raise SystemExit(0)

    # Detect bare flags that need a value before argparse (clearer errors).
    needs_value = {
        "--to",
        "--upstream",
        "--downstream",
        "--parent-dir",
    }
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in needs_value:
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                die(f"{arg} requires a value")
            i += 2
            continue
        i += 1

    parser = build_parser()
    # Suppress argparse's default required handling; we validate below.
    args = parser.parse_args(argv)
    if not args.to:
        die("--to VERSION is required")
    args.to = normalize_version(args.to)
    return args


def resolve_repos(args: argparse.Namespace) -> tuple[Path | None, Path | None]:
    upstream: Path | None = Path(args.upstream).resolve() if args.upstream else None
    downstream: Path | None = Path(args.downstream).resolve() if args.downstream else None

    if args.parent_dir:
        parent = Path(args.parent_dir).expanduser().resolve()
        if upstream is None:
            found = discover_repo(
                parent,
                "1-must-gather",
                "1-rhdh-must-gather",
                "rhdh-must-gather",
                "must-gather",
            )
            if found is None:
                die(f"Could not find must-gather under {parent}")
            upstream = found
        if downstream is None:
            found = discover_repo(
                parent,
                "4-rhdh",
                "rhdh-downstream",
                "rhidp-rhdh",
                required=DISTGIT_REL,
            )
            if found is None:
                die(f"Could not find rhidp/rhdh midstream under {parent}")
            downstream = found

    return upstream, downstream


def infer_mode(
    *,
    upstream: Path | None,
    to_version: str,
) -> str:
    if upstream is None:
        die("Cannot infer CGW vs vendor mode without an upstream checkout")
    if cgw_available(upstream, to_version):
        log(f"CGW mirror has helm v{to_version} linux-amd64/arm64 binaries")
        return "cgw"
    warn(f"CGW mirror has no helm v{to_version} linux-amd64/arm64 — vendored source path")
    return "vendor"


def main(argv: list[str] | None = None) -> int:
    args = parse_argv(list(argv if argv is not None else sys.argv[1:]))
    upstream, downstream = resolve_repos(args)

    if not args.skip_upstream:
        if upstream is None:
            die("Set --upstream or --parent-dir")
        validate_upstream(upstream)

    if not args.skip_downstream:
        if downstream is None:
            die("Set --downstream or --parent-dir")
        validate_downstream(downstream)

    if args.skip_upstream and not args.skip_downstream:
        if upstream is None:
            die("--skip-upstream still needs --upstream (or --parent-dir) as the sync source")
        validate_upstream(upstream)

    if upstream is not None and downstream is not None:
        log(f"Upstream:  {upstream}")
        log(f"Downstream: {downstream}")

    require_on_path("bash")
    if not args.check and not args.skip_downstream:
        require_on_path("rsync")

    mode = infer_mode(
        upstream=upstream,
        to_version=args.to,
    )

    if args.check:
        print(f"helm_version={args.to}")
        print(f"mode={mode}")
        print(f"upstream={upstream or ''}")
        print(f"downstream={downstream or ''}")
        return 0

    dry_run = args.dry_run
    upstream_started_dirty = False
    if upstream is not None:
        upstream_started_dirty = bool(git_status_porcelain(upstream, "Upstream"))

    if not args.skip_upstream:
        assert upstream is not None
        assert_clean_tree(upstream, "Upstream", allow_dirty=args.allow_dirty)
        current = read_makefile_helm_version(upstream / "Makefile")
        if current == args.to:
            log(f"Upstream HELM_VERSION already {args.to}")
        else:
            log(f"Upstream HELM_VERSION: {current} -> {args.to}")
        if mode == "cgw":
            bump_upstream_cgw(upstream, args.to, dry_run=dry_run)
        else:
            bump_upstream_vendor(upstream, args.to, dry_run=dry_run)
        flip_helm_stages(upstream / "Containerfile", mode, dry_run=dry_run)
        rhdh_cf = upstream / RHDH_DOCKER_CF
        if rhdh_cf.is_file():
            flip_helm_stages(rhdh_cf, mode, dry_run=dry_run)
        else:
            warn(f"No {RHDH_DOCKER_CF} in upstream; skipped stage flip there")

    if not args.skip_downstream:
        assert downstream is not None
        assert upstream is not None
        assert_clean_tree(downstream, "Downstream", allow_dirty=args.allow_dirty)
        sync_to_distgit(upstream, downstream, mode, dry_run=dry_run)
        regenerate_distgit_containerfile(downstream / DISTGIT_REL, dry_run=dry_run)
        flip_helm_stages(
            downstream / DISTGIT_REL / "Containerfile",
            mode,
            dry_run=dry_run,
        )
        update_tekton_prefetch(downstream, mode, dry_run=dry_run)
        update_upstream_sha(
            upstream,
            downstream,
            dry_run=dry_run,
            started_dirty=upstream_started_dirty,
        )

    log("Done. Review git diff in each repo before committing.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.stderr.close()
        raise SystemExit(1)

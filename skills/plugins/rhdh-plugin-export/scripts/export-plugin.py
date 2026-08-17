#!/usr/bin/env python3
"""Export, package, and push a Backstage plugin as an RHDH dynamic plugin.

Automates the full export+package+push pipeline described in the
RHDH plugin development export workflow (`references/export.md`):

  1. Validate plugin directory and package.json
  2. Build (yarn build + yarn tsc)
  3. Export via @red-hat-developer-hub/cli
  4. Package as OCI image, tgz archive, or npm package
  5. Optionally push OCI image to registry

Uses only Python stdlib — no external dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

# Disable colors if NO_COLOR is set or neither stdout nor stderr is a TTY
_NO_COLOR = os.environ.get("NO_COLOR") is not None or not (
    sys.stdout.isatty() or sys.stderr.isatty()
)

RED = "" if _NO_COLOR else "\033[0;31m"
GREEN = "" if _NO_COLOR else "\033[0;32m"
YELLOW = "" if _NO_COLOR else "\033[1;33m"
BLUE = "" if _NO_COLOR else "\033[0;34m"
BOLD = "" if _NO_COLOR else "\033[1m"
NC = "" if _NO_COLOR else "\033[0m"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _log_ok(msg: str) -> None:
    print(f"  {GREEN}✓{NC} {msg}")


def _log_fail(msg: str) -> None:
    print(f"  {RED}✗{NC} {msg}", file=sys.stderr)


def _log_info(msg: str) -> None:
    print(f"  {BLUE}→{NC} {msg}")


def _log_step(msg: str) -> None:
    print(f"\n{BOLD}{msg}{NC}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_container_tool() -> Optional[str]:
    """Return the first available container tool, or None."""
    for tool in ("podman", "docker", "buildah"):
        if shutil.which(tool):
            return tool
    return None


def _run(
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run a subprocess, raising on failure."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=capture,
        text=True,
        # On Windows, shell=True is needed for npx/yarn/npm .cmd shims
        shell=(sys.platform == "win32"),
    )


def _read_package_json(plugin_dir: Path) -> dict:
    pkg = plugin_dir / "package.json"
    with open(pkg, encoding="utf-8") as f:
        return json.load(f)


def _compute_integrity(path: Path) -> str:
    """Compute sha512 integrity hash in SRI format."""
    import base64

    h = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    digest = base64.b64encode(h.digest()).decode("ascii")
    return f"sha512-{digest}"


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def step_validate(plugin_dir: Path) -> dict:
    """Step 1: Validate plugin directory has package.json."""
    pkg_path = plugin_dir / "package.json"
    if not plugin_dir.is_dir():
        raise SystemExit(f"Plugin directory does not exist: {plugin_dir}")
    if not pkg_path.is_file():
        raise SystemExit(f"No package.json found in {plugin_dir}")
    data = _read_package_json(plugin_dir)
    name = data.get("name", "<unknown>")
    version = data.get("version", "<unknown>")
    _log_ok(f"Validated {name}@{version}")
    return {"name": name, "version": version}


def step_build(plugin_dir: Path) -> None:
    """Step 1 cont: yarn build + yarn tsc."""
    _log_step("Step 1: Build plugin")
    _log_info("Running yarn build …")
    _run(["yarn", "build"], cwd=plugin_dir)
    _log_ok("yarn build succeeded")

    _log_info("Running yarn tsc …")
    _run(["yarn", "tsc"], cwd=plugin_dir)
    _log_ok("yarn tsc succeeded")


def step_clean(plugin_dir: Path) -> None:
    """Remove dist/ and dist-dynamic/ for idempotent rebuilds."""
    for name in ("dist", "dist-dynamic"):
        target = plugin_dir / name
        if target.exists():
            shutil.rmtree(target)
            _log_info(f"Removed {target}")


def step_export(
    plugin_dir: Path,
    *,
    shared_packages: list[str],
    embed_packages: list[str],
) -> None:
    """Step 2: Export as dynamic plugin via RHDH CLI."""
    _log_step("Step 2: Export as dynamic plugin")
    cmd = ["npx", "@red-hat-developer-hub/cli@latest", "plugin", "export"]
    for pkg in shared_packages:
        cmd.extend(["--shared-package", pkg])
    for pkg in embed_packages:
        cmd.extend(["--embed-package", pkg])
    _log_info(f"Running: {' '.join(cmd)}")
    _run(cmd, cwd=plugin_dir)
    dist_dyn = plugin_dir / "dist-dynamic"
    if not dist_dyn.is_dir():
        raise SystemExit("Export failed: dist-dynamic/ was not created")
    _log_ok("Export created dist-dynamic/")


def step_package_oci(
    plugin_dir: Path,
    *,
    tag: str,
    container_tool: str,
) -> dict:
    """Step 3 (OCI): Package as container image."""
    _log_step("Step 3: Package as OCI image")
    cmd = [
        "npx",
        "@red-hat-developer-hub/cli@latest",
        "plugin",
        "package",
        "--container-tool",
        container_tool,
        "--tag",
        tag,
    ]
    _log_info(f"Running: {' '.join(cmd)}")
    _run(cmd, cwd=plugin_dir)
    _log_ok(f"Image tagged: {tag}")
    return {"format": "oci", "tag": tag, "container_tool": container_tool}


def step_package_tgz(plugin_dir: Path) -> dict:
    """Step 3 (tgz): npm pack in dist-dynamic/."""
    _log_step("Step 3: Package as tgz archive")
    dist_dyn = plugin_dir / "dist-dynamic"
    result = _run(["npm", "pack", "--json"], cwd=dist_dyn, capture=True)
    pack_info = json.loads(result.stdout)
    if isinstance(pack_info, list):
        pack_info = pack_info[0]
    filename = pack_info.get("filename", "")
    tgz_path = dist_dyn / filename
    integrity = pack_info.get("integrity", "")
    if not integrity and tgz_path.is_file():
        integrity = _compute_integrity(tgz_path)
    _log_ok(f"Archive: {tgz_path}")
    _log_info(f"Integrity: {integrity}")
    return {
        "format": "tgz",
        "path": str(tgz_path),
        "filename": filename,
        "integrity": integrity,
    }


def step_package_npm(plugin_dir: Path) -> dict:
    """Step 3 (npm): npm publish from dist-dynamic/ (dry-run info only)."""
    _log_step("Step 3: Package as npm (publish)")
    dist_dyn = plugin_dir / "dist-dynamic"
    _log_info("Publishing via npm publish …")
    _run(["npm", "publish"], cwd=dist_dyn)
    _log_ok("Published to npm registry")
    return {"format": "npm"}


def step_push(tag: str, container_tool: str) -> dict:
    """Step 4: Push OCI image to registry."""
    _log_step("Step 4: Push to registry")
    cmd = [container_tool, "push", tag]
    _log_info(f"Running: {' '.join(cmd)}")
    _run(cmd)
    _log_ok(f"Pushed {tag}")

    # Try to get digest
    digest = ""
    try:
        result = _run(
            [container_tool, "inspect", "--format={{.Digest}}", tag],
            capture=True,
        )
        digest = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    if digest:
        _log_info(f"Digest: {digest}")
    return {"pushed": True, "tag": tag, "digest": digest}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export, package, and optionally push a Backstage plugin "
            "as an RHDH dynamic plugin. Automates the export pipeline "
            "from the rhdh-plugin-export skill."
        ),
        epilog=(
            "Examples:\n"
            "  %(prog)s --tag quay.io/ns/my-plugin:v0.1.0\n"
            "  %(prog)s --format tgz --clean\n"
            "  %(prog)s --tag quay.io/ns/my-plugin:v0.1.0 --push\n"
            "  %(prog)s --plugin-dir plugins/my-backend --tag quay.io/ns/x:v1 "
            "--shared-package '!/@backstage/plugin-notifications/' "
            "--embed-package @internal/common\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--plugin-dir",
        type=Path,
        default=Path.cwd(),
        help="Path to the plugin directory (default: current directory)",
    )
    parser.add_argument(
        "--tag",
        help=("OCI image tag, e.g. 'quay.io/namespace/plugin:v0.1.0'. Required when --format=oci."),
    )
    parser.add_argument(
        "--format",
        choices=("oci", "tgz", "npm"),
        default="oci",
        help="Packaging format (default: oci)",
    )
    parser.add_argument(
        "--container-tool",
        choices=("podman", "docker", "buildah"),
        default=None,
        help="Container tool for OCI operations (default: auto-detect)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push OCI image to registry after packaging",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove dist/ and dist-dynamic/ before building (idempotent rebuild)",
    )
    parser.add_argument(
        "--shared-package",
        action="append",
        default=[],
        metavar="PKG",
        help=(
            "Override shared dependency behaviour during export. "
            "Repeatable. E.g. '!/@backstage/plugin-notifications/'"
        ),
    )
    parser.add_argument(
        "--embed-package",
        action="append",
        default=[],
        metavar="PKG",
        help=(
            "Embed a workspace or third-party package during export. "
            "Repeatable. E.g. '@my-org/plugin-common'"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output structured JSON instead of human-readable text",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    plugin_dir: Path = args.plugin_dir.resolve()
    fmt: str = args.format
    tag: str | None = args.tag
    do_push: bool = args.push
    do_clean: bool = args.clean
    use_json: bool = args.json_output
    shared_packages: list[str] = args.shared_package
    embed_packages: list[str] = args.embed_package
    container_tool: str | None = args.container_tool

    # --- Argument validation ------------------------------------------------

    if fmt == "oci" and not tag:
        parser.error("--tag is required when --format=oci")

    if do_push and fmt != "oci":
        parser.error("--push is only supported with --format=oci")

    if fmt == "oci":
        if container_tool is None:
            container_tool = _detect_container_tool()
        if container_tool is None:
            parser.error(
                "No container tool found (podman/docker/buildah). "
                "Install one or specify --container-tool."
            )

    # --- Collect results for JSON output ------------------------------------
    result: dict[str, Any] = {
        "plugin_dir": str(plugin_dir),
        "format": fmt,
    }
    if tag:
        result["tag"] = tag

    try:
        # Step 0: Validate
        if not use_json:
            _log_step("Validating plugin directory")
        pkg_info = step_validate(plugin_dir)
        result["plugin"] = pkg_info

        # Optional clean
        if do_clean:
            if not use_json:
                _log_step("Cleaning previous build artifacts")
            step_clean(plugin_dir)

        # Step 1: Build
        if not use_json:
            step_build(plugin_dir)
        else:
            _run(["yarn", "build"], cwd=plugin_dir)
            _run(["yarn", "tsc"], cwd=plugin_dir)
        result["build"] = "ok"

        # Step 2: Export
        if not use_json:
            step_export(
                plugin_dir,
                shared_packages=shared_packages,
                embed_packages=embed_packages,
            )
        else:
            cmd = [
                "npx",
                "@red-hat-developer-hub/cli@latest",
                "plugin",
                "export",
            ]
            for pkg in shared_packages:
                cmd.extend(["--shared-package", pkg])
            for pkg in embed_packages:
                cmd.extend(["--embed-package", pkg])
            _run(cmd, cwd=plugin_dir)
            dist_dyn = plugin_dir / "dist-dynamic"
            if not dist_dyn.is_dir():
                raise SystemExit("Export failed: dist-dynamic/ not created")
        result["export"] = "ok"

        # Step 3: Package
        if fmt == "oci":
            assert container_tool is not None
            pkg_result = step_package_oci(
                plugin_dir,
                tag=tag,
                container_tool=container_tool,  # type: ignore[arg-type]
            )
        elif fmt == "tgz":
            pkg_result = step_package_tgz(plugin_dir)
        elif fmt == "npm":
            pkg_result = step_package_npm(plugin_dir)
        else:
            raise SystemExit(f"Unknown format: {fmt}")
        result["package"] = pkg_result

        # Step 4: Push (OCI only)
        if do_push:
            assert container_tool is not None
            push_result = step_push(tag, container_tool)  # type: ignore[arg-type]
            result["push"] = push_result

        # --- Final output ---------------------------------------------------
        result["success"] = True

        if use_json:
            print(json.dumps(result, indent=2))
        else:
            _log_step("Done ✓")
            print(f"\n  Plugin:  {pkg_info['name']}@{pkg_info['version']}")
            print(f"  Format:  {fmt}")
            if tag:
                print(f"  Tag:     {tag}")
            if fmt == "tgz" and "integrity" in pkg_result:
                print(f"  Hash:    {pkg_result['integrity']}")
            if do_push and "digest" in result.get("push", {}):
                digest = result["push"]["digest"]
                if digest:
                    print(f"  Digest:  {digest}")

        return 0

    except subprocess.CalledProcessError as exc:
        err_msg = f"Command failed: {' '.join(str(a) for a in exc.cmd)}"
        stderr_out = ""
        if exc.stderr:
            stderr_out = exc.stderr.strip()
        if use_json:
            result["success"] = False
            result["error"] = {
                "code": "COMMAND_FAILED",
                "message": err_msg,
                "stderr": stderr_out,
                "returncode": exc.returncode,
            }
            print(json.dumps(result, indent=2))
        else:
            _log_fail(err_msg)
            if stderr_out:
                print(stderr_out, file=sys.stderr)
        return 1

    except SystemExit as exc:
        # argparse calls sys.exit(2) for usage errors
        if isinstance(exc.code, int):
            return exc.code
        msg = str(exc.code) if exc.code else "Unknown error"
        if use_json:
            result["success"] = False
            result["error"] = {"code": "VALIDATION_ERROR", "message": msg}
            print(json.dumps(result, indent=2))
        else:
            _log_fail(msg)
        return 1


if __name__ == "__main__":
    sys.exit(main())

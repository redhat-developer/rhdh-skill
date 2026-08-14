#!/usr/bin/env python3
"""Scaffold a Backstage app and dynamic plugin for RHDH.

Automates the scaffold workflow for both backend and frontend plugins:
  1. Creates a Backstage app using the correct create-app version for the
     target RHDH release.
  2. Runs yarn install.
  3. Generates a plugin via `yarn new` (backend-plugin or frontend-plugin).
  4. (Frontend only) Optionally installs the RHDH theme package.

Uses only the Python standard library, so it runs wherever Python does.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# RHDH version → @backstage/create-app version mapping
# Snapshot used by the scaffold defaults; an explicit --rhdh-version wins.
# ---------------------------------------------------------------------------
VERSION_MAP: dict[str, str] = {
    "next": "0.7.6",
    "1.9": "0.7.6",
    "1.8": "0.7.3",
    "1.7": "0.6.2",
    "1.6": "0.5.25",
}

RHDH_THEME_PACKAGE = "@red-hat-developer-hub/backstage-plugin-theme"

PLUGIN_TYPES = ("backend", "frontend")

# Exit codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2

# ANSI colors (disabled when not a TTY or NO_COLOR is set)
_no_color = os.environ.get("NO_COLOR") is not None
_is_tty = sys.stderr.isatty() and not _no_color


def _c(code: str, text: str) -> str:
    if _is_tty:
        return f"{code}{text}\033[0m"
    return text


def green(t: str) -> str:
    return _c("\033[0;32m", t)


def red(t: str) -> str:
    return _c("\033[0;31m", t)


def yellow(t: str) -> str:
    return _c("\033[1;33m", t)


def blue(t: str) -> str:
    return _c("\033[0;34m", t)


def bold(t: str) -> str:
    return _c("\033[1m", t)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    """Print to stderr so it doesn't interfere with --json on stdout."""
    print(msg, file=sys.stderr)


def log_step(msg: str) -> None:
    log(f"  {blue('→')} {msg}")


def log_ok(msg: str) -> None:
    log(f"  {green('✓')} {msg}")


def log_fail(msg: str) -> None:
    log(f"  {red('✗')} {msg}")


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    stdin_text: str | None = None,
    use_json: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess, logging the command. Raises on failure."""
    display = " ".join(cmd)
    if stdin_text:
        display = f"echo {stdin_text!r} | {display}"
    log_step(f"Running: {display}")

    # On Windows, shell=True is needed for npx/yarn from PATH
    use_shell = sys.platform == "win32"

    result = subprocess.run(
        cmd,
        cwd=cwd,
        input=stdin_text,
        capture_output=False,
        text=True,
        shell=use_shell,
    )
    if result.returncode != 0:
        log_fail(f"Command failed (exit {result.returncode}): {display}")
        if not use_json:
            sys.exit(EXIT_FAILURE)
        else:
            raise subprocess.CalledProcessError(result.returncode, cmd)
    log_ok(f"Done: {cmd[0]}")
    return result


def resolve_create_app_version(rhdh_version: str) -> str | None:
    """Look up the create-app version for an RHDH version."""
    return VERSION_MAP.get(rhdh_version)


def check_app_exists(app_path: Path) -> bool:
    """Check if a Backstage app already exists at path."""
    return (app_path / "package.json").is_file() and (app_path / "packages" / "app").is_dir()


def check_plugin_exists(app_path: Path, plugin_dir_name: str) -> bool:
    """Check if plugin directory already exists (idempotency)."""
    return (app_path / "plugins" / plugin_dir_name).is_dir()


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------


def scaffold(args: argparse.Namespace) -> dict:
    """Run the scaffold workflow. Returns a result dict."""
    rhdh_version: str = args.rhdh_version
    plugin_id: str = args.plugin_id
    plugin_type: str = args.type
    app_path = Path(args.path).resolve()
    with_theme: bool = args.with_theme
    use_json: bool = args.json

    is_backend = plugin_type == "backend"
    plugin_dir_name = f"{plugin_id}-backend" if is_backend else plugin_id
    yarn_select = "backend-plugin" if is_backend else "frontend-plugin"

    # Resolve create-app version
    if args.create_app_version:
        create_app_version = args.create_app_version
    else:
        create_app_version = resolve_create_app_version(rhdh_version)
        if create_app_version is None:
            known = ", ".join(sorted(VERSION_MAP.keys()))
            msg = (
                f"Unknown RHDH version '{rhdh_version}'. "
                f"Known versions: {known}. "
                f"Use --create-app-version to override."
            )
            if use_json:
                return {
                    "success": False,
                    "error": {"code": "UNKNOWN_RHDH_VERSION", "message": msg},
                }
            log_fail(msg)
            sys.exit(EXIT_USAGE)

    result: dict = {
        "success": True,
        "type": plugin_type,
        "rhdh_version": rhdh_version,
        "create_app_version": create_app_version,
        "plugin_id": plugin_id,
        "plugin_dir_name": plugin_dir_name,
        "app_path": str(app_path),
        "with_theme": with_theme,
        "steps_completed": [],
    }

    log(bold(f"\nScaffolding {plugin_type} plugin '{plugin_id}' for RHDH {rhdh_version}"))
    log(f"  Type:              {plugin_type}")
    log(f"  App path:          {app_path}")
    log(f"  create-app version: {create_app_version}")
    if not is_backend:
        log(f"  Theme:             {'yes' if with_theme else 'no'}")
    log("")

    # ------------------------------------------------------------------
    # Step 1: Create Backstage app (idempotent)
    # ------------------------------------------------------------------
    if check_app_exists(app_path):
        log_ok("Backstage app already exists — skipping create-app")
        result["steps_completed"].append("create-app (skipped, already exists)")
    else:
        log(bold("Step 1: Creating Backstage application"))
        app_path.mkdir(parents=True, exist_ok=True)
        try:
            run(
                [
                    "npx",
                    f"@backstage/create-app@{create_app_version}",
                    "--path",
                    str(app_path),
                ],
                stdin_text="backstage\n",
                use_json=use_json,
            )
        except subprocess.CalledProcessError:
            result["success"] = False
            result["error"] = {
                "code": "CREATE_APP_FAILED",
                "message": "npx @backstage/create-app failed",
            }
            return result
        result["steps_completed"].append("create-app")

    # ------------------------------------------------------------------
    # Step 2: yarn install (idempotent)
    # ------------------------------------------------------------------
    if not (app_path / "node_modules").is_dir():
        log(bold("Step 2: Installing dependencies"))
        try:
            run(["yarn", "install"], cwd=app_path, use_json=use_json)
        except subprocess.CalledProcessError:
            result["success"] = False
            result["error"] = {
                "code": "YARN_INSTALL_FAILED",
                "message": "yarn install failed",
            }
            return result
        result["steps_completed"].append("yarn install")
    else:
        log_ok("node_modules exists — skipping yarn install")
        result["steps_completed"].append("yarn install (skipped, already exists)")

    # ------------------------------------------------------------------
    # Step 3 (frontend only, optional): Install RHDH theme
    # ------------------------------------------------------------------
    if not is_backend and with_theme:
        log(bold("Step 3: Installing RHDH theme package"))
        try:
            run(
                ["yarn", "workspace", "app", "add", RHDH_THEME_PACKAGE],
                cwd=app_path,
                use_json=use_json,
            )
        except subprocess.CalledProcessError:
            result["success"] = False
            result["error"] = {
                "code": "THEME_INSTALL_FAILED",
                "message": f"Failed to install {RHDH_THEME_PACKAGE}",
            }
            return result
        result["steps_completed"].append("install-theme")

    # ------------------------------------------------------------------
    # Step 4: Create plugin (idempotent)
    # ------------------------------------------------------------------
    if check_plugin_exists(app_path, plugin_dir_name):
        log_ok(f"Plugin '{plugin_dir_name}' already exists — skipping yarn new")
        result["steps_completed"].append("yarn new (skipped, already exists)")
    else:
        step_num = "4" if (not is_backend and with_theme) else "3"
        log(bold(f"Step {step_num}: Creating {plugin_type} plugin"))
        try:
            run(
                [
                    "yarn",
                    "new",
                    "--select",
                    yarn_select,
                    "--option",
                    f"id={plugin_id}",
                ],
                cwd=app_path,
                use_json=use_json,
            )
        except subprocess.CalledProcessError:
            result["success"] = False
            result["error"] = {
                "code": "YARN_NEW_FAILED",
                "message": f"yarn new --select {yarn_select} failed",
            }
            return result
        result["steps_completed"].append("yarn new")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    plugin_path = app_path / "plugins" / plugin_dir_name
    result["plugin_path"] = str(plugin_path)

    if not plugin_path.exists():
        msg = (
            f"Expected plugin directory not found at {plugin_path}. "
            "The scaffold command may have used a different naming convention."
        )
        if use_json:
            result["success"] = False
            result["error"] = {"code": "PLUGIN_DIR_MISSING", "message": msg}
            return result
        log(f"  {yellow('⚠')} {msg}")
        sys.exit(EXIT_FAILURE)

    if not use_json:
        log(bold("\n✅ Scaffold complete!\n"))
        log(f"  Plugin location: {plugin_path}")
        log(f"  RHDH version:    {rhdh_version}")
        log(f"  Type:            {plugin_type}")
        log(f"  Steps completed: {', '.join(result['steps_completed'])}")
        log(bold("\nNext steps:"))
        log(f"  1. cd {plugin_path}")
        log(
            f"  2. Implement {'plugin logic in src/plugin.ts' if is_backend else 'components in src/'}"
        )
        if not is_backend and with_theme:
            log("  3. Configure theme in dev/index.tsx")
        log(f"  {'4' if (not is_backend and with_theme) else '3'}. yarn build")
        log(
            f"  {'5' if (not is_backend and with_theme) else '4'}."
            f" npx @red-hat-developer-hub/cli@latest plugin export"
        )

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scaffold",
        description=(
            "Scaffold a Backstage app and dynamic plugin for RHDH.\n\n"
            "Creates the Backstage app with the correct create-app version,\n"
            "installs dependencies, and generates a backend or frontend plugin.\n"
            "For frontend plugins, optionally installs the RHDH theme package."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s --type backend --rhdh-version 1.9 --plugin-id my-api\n"
            "  %(prog)s --type frontend --rhdh-version 1.9 --plugin-id my-ui\n"
            "  %(prog)s --type frontend --rhdh-version 1.8 --plugin-id my-card --with-theme\n"
            "  %(prog)s --type backend --rhdh-version next --plugin-id bar --json\n"
        ),
    )

    parser.add_argument(
        "--type",
        required=True,
        choices=PLUGIN_TYPES,
        help="Plugin type: 'backend' or 'frontend'.",
    )
    parser.add_argument(
        "--rhdh-version",
        required=True,
        metavar="VERSION",
        help=f"Target RHDH version. Known: {', '.join(sorted(VERSION_MAP.keys()))}.",
    )
    parser.add_argument(
        "--plugin-id",
        required=True,
        metavar="ID",
        help=(
            "Plugin identifier (e.g. 'my-plugin'). "
            "Backend creates plugins/<ID>-backend/, frontend creates plugins/<ID>/."
        ),
    )
    parser.add_argument(
        "--path",
        default=".",
        metavar="DIR",
        help="Directory in which to create the Backstage app (default: '.').",
    )
    parser.add_argument(
        "--create-app-version",
        default=None,
        metavar="VER",
        help="Override the auto-detected @backstage/create-app version.",
    )
    parser.add_argument(
        "--with-theme",
        action="store_true",
        help="Install the RHDH theme package (frontend only, ignored for backend).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON result to stdout.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.type == "backend" and args.with_theme:
        log(f"  {yellow('⚠')} --with-theme is ignored for backend plugins")

    try:
        result = scaffold(args)
    except KeyboardInterrupt:
        log("\nInterrupted.")
        sys.exit(130)
    except (OSError, PermissionError) as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": {"code": "PATH_ERROR", "message": str(exc)},
                    },
                    indent=2,
                )
            )
        else:
            log(f"Error: {exc}")
        sys.exit(EXIT_FAILURE)

    if args.json:
        print(json.dumps(result, indent=2))

    sys.exit(EXIT_SUCCESS if result.get("success") else EXIT_FAILURE)


if __name__ == "__main__":
    main()

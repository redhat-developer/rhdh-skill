#!/usr/bin/env python3
"""Derive Package metadata fields from workspace configuration and upstream package.json.

Handles deterministic field derivation: metadata.name (with shortening),
dynamicArtifact OCI URL, links, annotations, supportedVersions, and
smoke test env var extraction. Outputs structured JSON for the agent to
consume when assembling Package YAML files.

Usage:
    python scripts/derive-metadata.py --workspace argocd
    python scripts/derive-metadata.py --workspace argocd --package-json '{"name":"@backstage-community/plugin-argocd","version":"2.8.0","backstage":{"role":"frontend-plugin"}}'
    python scripts/derive-metadata.py --extract-env-vars metadata-file.yaml
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path

K8S_NAME_LIMIT = 63

SHORTEN_RULES = [
    ("rhdh-plugin-catalog--", ""),
    ("red-hat-developer-hub-", "rhdh-"),
    ("backstage-community-plugin", "bcp"),
    ("backstage-plugin", "bsp"),
    ("backstage", "bs"),
    ("plugin", "plgn"),
    ("catalog", "ctlg"),
    ("module", "mod"),
    ("kubernetes", "k8s"),
    ("bitbucket", "bbckt"),
    ("parfuemerie-douglas", "parfdg"),
]

OCI_REGISTRY = "oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays"


def shorten_name(name: str) -> str:
    """Apply shortening rules only if name exceeds K8S_NAME_LIMIT."""
    if len(name) <= K8S_NAME_LIMIT:
        return name
    shortened = name
    for old, new in SHORTEN_RULES:
        shortened = shortened.replace(old, new)
    return shortened


def package_name_to_metadata_name(package_name: str) -> str:
    """Derive metadata.name from npm package name."""
    name = package_name.lstrip("@").replace("/", "-")
    return shorten_name(name)


def derive_title(package_name: str) -> str:
    """Derive a human-readable title from package name."""
    name = package_name.split("/")[-1] if "/" in package_name else package_name
    name = name.removeprefix("plugin-").removeprefix("backstage-plugin-")
    parts = name.split("-")
    return " ".join(p.capitalize() for p in parts)


def derive_source_code_url(
    repo: str, workspace: str, plugin_path: str, flat: bool
) -> str:
    """Derive Source Code URL from repo, workspace, plugin path, and flat flag."""
    base = f"{repo}/tree/main"
    if flat:
        if plugin_path == ".":
            return base
        return f"{base}/{plugin_path}"
    if plugin_path == ".":
        return f"{base}/workspaces/{workspace}"
    return f"{base}/workspaces/{workspace}/{plugin_path}"


def derive_oci_url(metadata_name: str, supported_versions: str, version: str) -> str:
    """Derive the dynamicArtifact OCI URL."""
    tag = f"bs_{supported_versions}__{version}"
    return f"{OCI_REGISTRY}/{metadata_name}:{tag}!{metadata_name}"


def derive_supported_versions(workspace_dir: Path, source: dict) -> str:
    """Derive supportedVersions from backstage.json override or source.json."""
    bs_json = workspace_dir / "backstage.json"
    if bs_json.exists():
        data = json.loads(bs_json.read_text())
        return data.get("version", source["repo-backstage-version"])
    return source["repo-backstage-version"]


def parse_plugins_list(workspace_dir: Path) -> list[dict]:
    """Parse plugins-list.yaml and return list of plugin entries.

    Format: each top-level line is ``<path>:`` or ``<path>: <cli-args>``.
    Indented lines (``  - ...``) are CLI arg continuations and are skipped.
    """
    plugins_list = workspace_dir / "plugins-list.yaml"
    content = plugins_list.read_text()
    plugins = []
    for line in content.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("  "):
            continue
        if "#" in stripped:
            stripped = stripped[:stripped.index("#")].rstrip()
        path = stripped.split(":")[0].strip().removeprefix("- ")
        if path:
            plugins.append({"path": path})
    return plugins


def find_missing_metadata(workspace_dir: Path, plugins: list[dict]) -> list[dict]:
    """Identify plugins that lack metadata files.

    Uses a heuristic: for each plugin path, check if any existing metadata file's
    packageName corresponds to that path. Falls back to filename pattern matching.
    """
    metadata_dir = workspace_dir / "metadata"
    existing_files = list(metadata_dir.glob("*.yaml")) if metadata_dir.exists() else []
    existing_names = {f.stem for f in existing_files}

    missing = []
    for plugin in plugins:
        path = plugin["path"]
        path_suffix = path.rstrip("/").split("/")[-1] if path != "." else ""
        found = any(path_suffix and path_suffix in name for name in existing_names)
        if not found and path != ".":
            missing.append(plugin)
        elif path == "." and not existing_names:
            missing.append(plugin)
    return missing


def extract_env_vars(yaml_content: str) -> list[str]:
    """Extract ${VAR_NAME} references from YAML content."""
    return sorted(set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)\}", yaml_content)))


def read_existing_metadata(workspace_dir: Path) -> dict | None:
    """Read first existing metadata file and extract copyable fields."""
    metadata_dir = workspace_dir / "metadata"
    if not metadata_dir.exists():
        return None
    files = sorted(metadata_dir.glob("*.yaml"))
    if not files:
        return None

    content = files[0].read_text()
    result = {}
    for field, pattern in [
        ("author", r"^\s+author:\s+(.+)$"),
        ("support", r"^\s+support:\s+(.+)$"),
        ("lifecycle", r"^\s+lifecycle:\s+(.+)$"),
        ("supportedVersions", r"^\s+supportedVersions:\s+(.+)$"),
    ]:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            result[field] = match.group(1).strip().strip('"').strip("'")

    part_of = []
    in_part_of = False
    for line in content.splitlines():
        if "partOf:" in line:
            in_part_of = True
            continue
        if in_part_of:
            stripped = line.strip()
            if stripped.startswith("- "):
                part_of.append(stripped[2:].strip())
            else:
                break
    if part_of:
        result["partOf"] = part_of

    return result if result else None


def check_supported_versions_consistency(
    workspace_dir: Path, expected: str
) -> list[dict]:
    """Check all metadata files for supportedVersions mismatches."""
    metadata_dir = workspace_dir / "metadata"
    if not metadata_dir.exists():
        return []
    mismatches = []
    for f in sorted(metadata_dir.glob("*.yaml")):
        content = f.read_text()
        match = re.search(r"^\s+supportedVersions:\s+(.+)$", content, re.MULTILINE)
        if match:
            actual = match.group(1).strip().strip('"').strip("'")
            if actual != expected:
                mismatches.append(
                    {"file": f.name, "actual": actual, "expected": expected}
                )
    return mismatches


def check_empty_config_without_flag(workspace_dir: Path) -> list[str]:
    """Find metadata files with appConfigExamples: [] but no appConfigNotRequired."""
    metadata_dir = workspace_dir / "metadata"
    if not metadata_dir.exists():
        return []
    issues = []
    for f in sorted(metadata_dir.glob("*.yaml")):
        content = f.read_text()
        if "appConfigExamples: []" in content and "appConfigNotRequired:" not in content:
            issues.append(f.name)
    return issues


def derive_plugin_fields(
    package_json: dict,
    workspace: str,
    plugin_path: str,
    source: dict,
    supported_versions: str,
    existing: dict | None,
) -> dict:
    """Derive all metadata fields for a single plugin."""
    pkg_name = package_json["name"]
    version = package_json["version"]
    role = package_json.get("backstage", {}).get("role", "")
    if not role:
        role = "backend-plugin" if plugin_path.endswith("-backend") or "-backend" in plugin_path else "frontend-plugin"

    metadata_name = package_name_to_metadata_name(pkg_name)
    title = derive_title(pkg_name)
    repo = source["repo"]
    flat = source.get("repo-flat", False)
    source_url = derive_source_code_url(repo, workspace, plugin_path, flat)
    oci_url = derive_oci_url(metadata_name, supported_versions, version)

    result = {
        "metadata_name": metadata_name,
        "filename": f"{metadata_name}.yaml",
        "title": title,
        "packageName": pkg_name,
        "version": version,
        "role": role,
        "dynamicArtifact": oci_url,
        "supportedVersions": supported_versions,
        "sourceCodeUrl": source_url,
        "bugsUrl": f"{repo}/issues",
        "plugin_path": plugin_path,
    }

    if existing:
        for key in ("author", "support", "lifecycle", "partOf"):
            if key in existing:
                result[key] = existing[key]

    result.setdefault("support", "community")

    if result["support"] in ("generally-available", "tech-preview"):
        result["support_needs_confirmation"] = True

    return result


def run_gh(args, check=True):
    """Run a gh CLI command and return stdout as string."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=30)
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        print(f"Error running: {' '.join(cmd)}", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        if check:
            raise
        return None


def gh_fetch_file(owner_repo: str, path: str, ref: str) -> str | None:
    """Fetch a file from GitHub at a specific ref. Returns decoded content or None."""
    encoded = path.replace(" ", "%20")
    output = run_gh(
        ["api", f"repos/{owner_repo}/contents/{encoded}?ref={ref}", "--jq", ".content"],
        check=False,
    )
    if not output:
        return None
    try:
        return base64.b64decode(output).decode("utf-8")
    except Exception:
        return None


def gh_list_dir(owner_repo: str, path: str, ref: str) -> list[str]:
    """List file names in a GitHub directory at a specific ref."""
    output = run_gh(
        ["api", f"repos/{owner_repo}/contents/{path}?ref={ref}", "--jq", ".[].name"],
        check=False,
    )
    if not output:
        return []
    return output.splitlines()


def fetch_and_derive_all(
    workspace_dir: Path, workspace: str, source: dict, missing_paths: list[str]
) -> dict:
    """Fetch package.json for all missing plugins via gh api and derive fields.

    Returns a dict with 'plugins' (derived fields per plugin),
    'errors' (plugins that failed to fetch), and 'config_files' (config.d.ts
    content for plugins that have one).
    """
    repo = source["repo"]
    owner_repo = repo.replace("https://github.com/", "")
    ref = source["repo-ref"]
    flat = source.get("repo-flat", False)
    supported_versions = derive_supported_versions(workspace_dir, source)
    existing = read_existing_metadata(workspace_dir)

    results = {"plugins": [], "errors": [], "config_files": {}}

    for plugin_path in missing_paths:
        if flat:
            src_path = "" if plugin_path == "." else plugin_path
        else:
            src_path = (
                f"workspaces/{workspace}"
                if plugin_path == "."
                else f"workspaces/{workspace}/{plugin_path}"
            )

        pkg_path = f"{src_path}/package.json" if src_path else "package.json"
        raw = gh_fetch_file(owner_repo, pkg_path, ref)
        if not raw:
            results["errors"].append(
                {"plugin_path": plugin_path, "error": f"Failed to fetch {pkg_path}"}
            )
            continue

        try:
            pkg = json.loads(raw)
        except json.JSONDecodeError as e:
            results["errors"].append(
                {"plugin_path": plugin_path, "error": f"Invalid JSON in package.json: {e}"}
            )
            continue

        fields = derive_plugin_fields(
            pkg, workspace, plugin_path, source, supported_versions, existing
        )
        results["plugins"].append(fields)

        config_path = f"{src_path}/config.d.ts" if src_path else "config.d.ts"
        config_content = gh_fetch_file(owner_repo, config_path, ref)
        if config_content:
            results["config_files"][plugin_path] = config_content

        dir_path = f"{src_path}/src" if src_path else "src"
        src_files = gh_list_dir(owner_repo, dir_path, ref)
        has_plugin_ts = any(f in src_files for f in ("plugin.ts", "plugin.tsx"))
        has_alpha_ts = "alpha.ts" in src_files
        fields["has_plugin_ts"] = has_plugin_ts
        fields["has_alpha_ts"] = has_alpha_ts

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Derive Package metadata fields for overlay plugins.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    derive_cmd = sub.add_parser(
        "derive",
        help="Derive metadata fields for a plugin from its package.json",
    )
    derive_cmd.add_argument("--workspace", required=True, help="Workspace name")
    derive_cmd.add_argument(
        "--package-json",
        help="package.json content as JSON string (if not provided, derives workspace-level info only)",
    )
    derive_cmd.add_argument("--plugin-path", default=".", help="Plugin path within workspace")
    derive_cmd.add_argument(
        "--overlay-dir",
        default=".",
        help="Path to overlay repo root",
    )

    scan_cmd = sub.add_parser(
        "scan",
        help="Scan workspace for missing metadata and consistency issues",
    )
    scan_cmd.add_argument("--workspace", required=True, help="Workspace name")
    scan_cmd.add_argument(
        "--overlay-dir",
        default=".",
        help="Path to overlay repo root",
    )

    fetch_cmd = sub.add_parser(
        "fetch-and-derive",
        help="Scan, fetch upstream package.json via gh api, and derive all fields in one shot",
    )
    fetch_cmd.add_argument("--workspace", required=True, help="Workspace name")
    fetch_cmd.add_argument(
        "--overlay-dir",
        default=".",
        help="Path to overlay repo root",
    )

    env_cmd = sub.add_parser(
        "extract-env-vars",
        help="Extract ${VAR} references from a YAML file",
    )
    env_cmd.add_argument("file", help="Path to YAML file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    is_tty = os.isatty(sys.stdout.fileno())

    if args.command == "extract-env-vars":
        content = Path(args.file).read_text()
        env_vars = extract_env_vars(content)
        output = {"env_vars": env_vars}
        print(json.dumps(output, indent=2 if is_tty else None))
        return

    overlay_dir = Path(args.overlay_dir)
    workspace_dir = overlay_dir / "workspaces" / args.workspace

    if not workspace_dir.exists():
        print(json.dumps({"error": f"Workspace not found: {workspace_dir}"}), file=sys.stderr)
        sys.exit(1)

    source_json = workspace_dir / "source.json"
    if not source_json.exists():
        print(json.dumps({"error": "source.json not found"}), file=sys.stderr)
        sys.exit(1)

    source = json.loads(source_json.read_text())

    if args.command == "scan":
        plugins = parse_plugins_list(workspace_dir)
        missing = find_missing_metadata(workspace_dir, plugins)
        supported_versions = derive_supported_versions(workspace_dir, source)
        version_mismatches = check_supported_versions_consistency(
            workspace_dir, supported_versions
        )
        empty_config_issues = check_empty_config_without_flag(workspace_dir)
        existing = read_existing_metadata(workspace_dir)

        repo = source["repo"]
        owner_repo = repo.replace("https://github.com/", "")
        flat = source.get("repo-flat", False)

        output = {
            "workspace": args.workspace,
            "repo": repo,
            "owner_repo": owner_repo,
            "repo_ref": source["repo-ref"],
            "repo_flat": flat,
            "supported_versions": supported_versions,
            "total_plugins": len(plugins),
            "missing_metadata": [p["path"] for p in missing],
            "missing_count": len(missing),
            "existing_metadata": existing,
            "version_mismatches": version_mismatches,
            "empty_config_issues": empty_config_issues,
            "source_paths": {},
        }
        for plugin in plugins:
            path = plugin["path"]
            if flat:
                src_path = "" if path == "." else path
            else:
                src_path = f"workspaces/{args.workspace}" if path == "." else f"workspaces/{args.workspace}/{path}"
            output["source_paths"][path] = src_path

        print(json.dumps(output, indent=2 if is_tty else None))
        return

    if args.command == "fetch-and-derive":
        plugins = parse_plugins_list(workspace_dir)
        missing = find_missing_metadata(workspace_dir, plugins)
        supported_versions = derive_supported_versions(workspace_dir, source)
        version_mismatches = check_supported_versions_consistency(
            workspace_dir, supported_versions
        )
        empty_config_issues = check_empty_config_without_flag(workspace_dir)
        existing = read_existing_metadata(workspace_dir)

        if not missing:
            output = {
                "workspace": args.workspace,
                "missing_count": 0,
                "message": "All plugins already have metadata",
                "version_mismatches": version_mismatches,
                "empty_config_issues": empty_config_issues,
                "existing_metadata": existing,
                "supported_versions": supported_versions,
            }
            print(json.dumps(output, indent=2 if is_tty else None))
            return

        missing_paths = [p["path"] for p in missing]
        results = fetch_and_derive_all(workspace_dir, args.workspace, source, missing_paths)

        output = {
            "workspace": args.workspace,
            "supported_versions": supported_versions,
            "missing_count": len(missing_paths),
            "existing_metadata": existing,
            "version_mismatches": version_mismatches,
            "empty_config_issues": empty_config_issues,
            **results,
        }
        print(json.dumps(output, indent=2 if is_tty else None))
        return

    if args.command == "derive":
        supported_versions = derive_supported_versions(workspace_dir, source)
        existing = read_existing_metadata(workspace_dir)

        if args.package_json:
            pkg = json.loads(args.package_json)
            fields = derive_plugin_fields(
                pkg, args.workspace, args.plugin_path, source,
                supported_versions, existing,
            )
            print(json.dumps(fields, indent=2 if is_tty else None))
        else:
            output = {
                "workspace": args.workspace,
                "supported_versions": supported_versions,
                "existing_metadata": existing,
                "source": source,
            }
            print(json.dumps(output, indent=2 if is_tty else None))


if __name__ == "__main__":
    main()

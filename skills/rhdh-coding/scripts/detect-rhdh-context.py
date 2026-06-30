#!/usr/bin/env python3
"""Detect RHDH/Backstage plugin context for the rhdh-coding skill.

Reads package.json, plugin definition files, and route refs to identify the
plugin's architecture, frontend system (legacy vs NFS), existing extensions,
API refs, mount points, and MUI version.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def detect_backstage_role(pkg: dict) -> str:
    return pkg.get("backstage", {}).get("role", "unknown")


def detect_plugin_id(pkg: dict) -> str:
    return pkg.get("backstage", {}).get("pluginId", "")


def detect_frontend_system(src: Path) -> str:
    if (src / "alpha.tsx").exists() or (src / "alpha.ts").exists():
        plugin_ts = src / "plugin.ts"
        plugin_tsx = src / "plugin.tsx"
        if plugin_ts.exists() or plugin_tsx.exists():
            return "dual"
        return "nfs"

    if (src / "plugin.ts").exists() or (src / "plugin.tsx").exists():
        return "legacy"

    return "unknown"


def detect_mui_version(deps: dict) -> str:
    if "@mui/material" in deps:
        return "v5"
    if "@material-ui/core" in deps:
        return "v4"
    return "none"


def detect_extensions(src: Path) -> list:
    extensions = []
    for f in [src / "plugin.ts", src / "plugin.tsx"]:
        if not f.exists():
            continue
        content = f.read_text(errors="replace")
        for match in re.finditer(
            r"createRoutableExtension\(\s*\{[^}]*name:\s*['\"](\w+)['\"]", content
        ):
            extensions.append({"name": match.group(1), "type": "routable"})
        for match in re.finditer(
            r"createComponentExtension\(\s*\{[^}]*name:\s*['\"](\w+)['\"]", content
        ):
            extensions.append({"name": match.group(1), "type": "component"})
    return extensions


def detect_nfs_blueprints(src: Path) -> list:
    blueprints = []
    for f in [src / "alpha.tsx", src / "alpha.ts"]:
        if not f.exists():
            continue
        content = f.read_text(errors="replace")
        for bp_type in [
            "PageBlueprint",
            "EntityCardBlueprint",
            "EntityContentBlueprint",
            "ApiBlueprint",
            "SubPageBlueprint",
        ]:
            if bp_type in content:
                blueprints.append(bp_type)
    return blueprints


def detect_route_refs(src: Path) -> list:
    refs = []
    for f in [src / "routes.ts", src / "routes.tsx"]:
        if not f.exists():
            continue
        content = f.read_text(errors="replace")
        for match in re.finditer(r"createRouteRef\(\s*\{[^}]*id:\s*['\"]([^'\"]+)['\"]", content):
            refs.append({"id": match.group(1), "type": "route"})
        for match in re.finditer(
            r"createExternalRouteRef\(\s*\{[^}]*id:\s*['\"]([^'\"]+)['\"]", content
        ):
            refs.append({"id": match.group(1), "type": "external"})
    return refs


def detect_api_refs(src: Path) -> list:
    refs = []
    for f in src.rglob("*.ts"):
        if "__tests__" in str(f) or ".test." in f.name or ".spec." in f.name:
            continue
        try:
            content = f.read_text(errors="replace")
        except OSError:
            continue
        for match in re.finditer(
            r"createApiRef<[^>]*>\(\s*\{[^}]*id:\s*['\"]([^'\"]+)['\"]", content
        ):
            refs.append(match.group(1))
    return list(set(refs))


def detect_dynamic_plugin(pkg: dict, project_path: Path) -> dict:
    result = {"isDynamic": False}

    scalprum = pkg.get("scalprum", {})
    if scalprum:
        result["isDynamic"] = True
        result["scalprumName"] = scalprum.get("name", "")

    if (project_path / "dist-scalprum").exists():
        result["isDynamic"] = True
        result["hasDistScalprum"] = True

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Detect RHDH/Backstage plugin context for the rhdh-coding skill.",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to the plugin root (default: current directory)",
    )
    args = parser.parse_args()

    project_path = Path(args.path).resolve()
    pkg_path = project_path / "package.json"

    if not pkg_path.exists():
        result = {"error": f"No package.json found at {project_path}"}
        json.dump(result, sys.stdout, indent=2)
        sys.exit(1)

    with open(pkg_path) as f:
        pkg = json.load(f)

    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    src = project_path / "src"

    result = {
        "projectPath": str(project_path),
        "packageName": pkg.get("name", "unknown"),
        "backstageRole": detect_backstage_role(pkg),
        "pluginId": detect_plugin_id(pkg),
        "frontendSystem": detect_frontend_system(src),
        "muiVersion": detect_mui_version(deps),
        "extensions": detect_extensions(src),
        "nfsBlueprints": detect_nfs_blueprints(src),
        "routeRefs": detect_route_refs(src),
        "apiRefs": detect_api_refs(src),
        "dynamicPlugin": detect_dynamic_plugin(pkg, project_path),
        "pluginPackages": pkg.get("backstage", {}).get("pluginPackages", []),
    }

    if sys.stdout.isatty():
        json.dump(result, sys.stdout, indent=2)
    else:
        json.dump(result, sys.stdout)

    print()


if __name__ == "__main__":
    main()

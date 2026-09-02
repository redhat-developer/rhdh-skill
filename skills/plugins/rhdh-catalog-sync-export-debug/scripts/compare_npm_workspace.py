#!/usr/bin/env python3
"""Compare a published npm package.json against the same version at a git SHA.

BODY DRIFT on a non-embedded package almost always means Loop 1 locked the
workspace manifest (possibly with unpublished dependency bumps at the same
semver) while Loop 3 locked the npm tarball.

    python compare_npm_workspace.py \
      --package @red-hat-developer-hub/backstage-plugin-orchestrator-form-api \
      --version 2.10.0 \
      --repo redhat-developer/rhdh-plugins \
      --sha 279803cf52e79040fc776c08d73ac57f748c5cab \
      --path workspaces/orchestrator/plugins/orchestrator-form-api/package.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

NPM_REGISTRY = "https://registry.npmjs.org"
GITHUB_RAW = "https://raw.githubusercontent.com"


def _get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "rhdh-catalog-sync-export-debug"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_npm(package: str, version: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(package, safe="@")
    url = f"{NPM_REGISTRY}/{encoded}/{urllib.parse.quote(version)}"
    data = _get_json(url)
    return {
        "version": data.get("version"),
        "gitHead": data.get("gitHead"),
        "dependencies": data.get("dependencies") or {},
        "peerDependencies": data.get("peerDependencies") or {},
    }


def fetch_github(repo: str, sha: str, path: str) -> dict[str, Any]:
    url = f"{GITHUB_RAW}/{repo}/{sha}/{path.lstrip('/')}"
    data = _get_json(url)
    return {
        "version": data.get("version"),
        "dependencies": data.get("dependencies") or {},
        "peerDependencies": data.get("peerDependencies") or {},
    }


def _diff_maps(left: dict[str, str], right: dict[str, str]) -> list[dict[str, str]]:
    diffs = []
    keys = sorted(set(left) | set(right))
    for key in keys:
        lv = left.get(key)
        rv = right.get(key)
        if lv != rv:
            diffs.append({"name": key, "workspace": lv or "", "npm": rv or ""})
    return diffs


def compare(
    package: str,
    version: str,
    repo: str,
    sha: str,
    path: str,
) -> dict[str, Any]:
    npm = fetch_npm(package, version)
    workspace = fetch_github(repo, sha, path)
    dep_diffs = _diff_maps(workspace["dependencies"], npm["dependencies"])
    peer_diffs = _diff_maps(workspace["peerDependencies"], npm["peerDependencies"])
    version_mismatch = workspace.get("version") != npm.get("version")
    git_head_match = bool(npm.get("gitHead") and npm["gitHead"] == sha)
    return {
        "ok": not dep_diffs and not peer_diffs and not version_mismatch,
        "package": package,
        "requestedVersion": version,
        "workspaceVersion": workspace.get("version"),
        "npmVersion": npm.get("version"),
        "npmGitHead": npm.get("gitHead"),
        "sha": sha,
        "gitHeadMatchesSha": git_head_match,
        "dependencyDiffs": dep_diffs,
        "peerDependencyDiffs": peer_diffs,
        "diagnosis": (
            "Workspace package.json at this SHA does not match the published npm "
            "tarball for the same version. Loop 1 will lock workspace ranges; "
            "Loop 3 will lock npm ranges → BODY DRIFT unless the package is "
            "embedded or source.json points at the Version Packages SHA."
            if dep_diffs or version_mismatch
            else "Workspace and npm manifests match for this version."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diff npm-published package.json against the workspace copy at a git SHA.",
    )
    parser.add_argument("--package", required=True, help="npm package name")
    parser.add_argument("--version", required=True, help="Published semver to fetch from npm")
    parser.add_argument(
        "--repo", required=True, help="GitHub owner/repo, e.g. redhat-developer/rhdh-plugins"
    )
    parser.add_argument("--sha", required=True, help="Upstream commit cloned by sync-midstream")
    parser.add_argument(
        "--path",
        required=True,
        help="Path to package.json inside that repo, e.g. workspaces/orchestrator/plugins/orchestrator-form-api/package.json",
    )
    args = parser.parse_args()
    try:
        result = compare(args.package, args.version, args.repo, args.sha, args.path)
    except urllib.error.HTTPError as exc:
        json.dump({"ok": False, "error": f"HTTP {exc.code} for {exc.url}"}, sys.stdout, indent=2)
        print()
        return 2
    except urllib.error.URLError as exc:
        json.dump({"ok": False, "error": str(exc.reason)}, sys.stdout, indent=2)
        print()
        return 2
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

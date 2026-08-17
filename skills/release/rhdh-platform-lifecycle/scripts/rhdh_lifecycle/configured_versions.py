"""Print configured MAPT_KUBERNETES_VERSION per branch from CI config files.

Usage:
    from rhdh_lifecycle.configured_versions import print_configured_versions
    from rhdh_lifecycle.openshift_release import resolve_repo_root

    root, is_remote = resolve_repo_root()
    print_configured_versions(config_dir, test_pattern, root, is_remote)
"""

from __future__ import annotations

import re
from pathlib import Path

from rhdh_lifecycle.openshift_release import (
    extract_branch,
    fetch_yaml,
    fetch_yaml_text,
    list_yaml_files,
    resolve_repo_root,  # noqa: F401  -- re-exported for callers of this module
)


def print_configured_versions(
    config_dir: str,
    test_pattern: str,
    root: Path | None,
    is_remote: bool,
    mapt_ref: str | None = None,
) -> None:
    """Print configured MAPT_KUBERNETES_VERSION per branch.

    Shared helper used by lifecycle-aks and lifecycle-eks scripts.
    """
    mapt_tag = ""
    if mapt_ref:
        ref_path = mapt_ref if is_remote else str(root / mapt_ref) if root else mapt_ref
        text = fetch_yaml_text(ref_path, root, is_remote)
        if text:
            for line in text.splitlines():
                if "tag:" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        mapt_tag = parts[1]
                    break

    prefix = "redhat-developer-rhdh-"
    files = list_yaml_files(config_dir, f"{prefix}*.yaml", root, is_remote)
    if not files:
        return

    pattern_re = re.compile(test_pattern)
    print("Configured MAPT_KUBERNETES_VERSION per branch:")
    for filepath in files:
        branch = extract_branch(prefix, filepath)
        data = fetch_yaml(filepath, root, is_remote)
        if not data or "tests" not in data:
            continue
        versions = set()
        for test in data["tests"]:
            name = test.get("as", "")
            if pattern_re.search(name):
                ver = test.get("steps", {}).get("env", {}).get("MAPT_KUBERNETES_VERSION", "N/A")
                versions.add(ver)
        ver_str = ",".join(sorted(versions)) if versions else "N/A"
        print(f"  {branch}: {ver_str}")
    if mapt_tag:
        print(f"MAPT image: mapt:{mapt_tag}")
    print()

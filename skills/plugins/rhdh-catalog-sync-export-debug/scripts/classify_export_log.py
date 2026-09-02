#!/usr/bin/env python3
"""Classify an rhdh-plugin-catalog sync-midstream export / Loop 3 log.

Reads a GitLab job trace or local sync-midstream transcript and reports the
failure class, drifted packages, and which repo layer to fix first.

    python classify_export_log.py --log /tmp/job.log
    python classify_export_log.py --log - < job.log
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BODY_DRIFT_RE = re.compile(
    r"\[DRIFT\] BODY DRIFT(?: \(embedded/workspace\))? for (\S+)",
)
VALIDATION_FAILED_RE = re.compile(
    r"Validation failed for (\S+)|\[ERROR\] \[.*?\] \[(\S+)\] Validation failed",
)
LOOP3_ITEM_RE = re.compile(
    r"\b([a-z0-9-]+):(validation-failed|export-failed)\b",
)
GITLAB_PREFIX_RE = re.compile(
    r"(?m)^\d{4}-\d{2}-\d{2}T[\d:.]+Z \S+ ",
)
WORKSPACE_RE = re.compile(
    r"\[(?:ERROR|INFO|DEBUG)\] \[.*?\] \[([a-z0-9-]+)\]",
)
GYP_RE = re.compile(
    r"gyp ERR!|Failed to build optional crypto binding|cpu-features@npm|ssh2@npm",
)
TYPES_RE = re.compile(
    r"TS2307|Cannot find module|error TS\d+|type-shims",
)
FAILED_EXPORTS_RE = re.compile(
    r"FAILED_EXPORTS<<EOF\n(?P<body>.*?)\nEOF",
    re.DOTALL,
)


def _read_log(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _strip_trace_prefixes(text: str) -> str:
    return GITLAB_PREFIX_RE.sub("", text)


def classify(text: str) -> dict:
    raw = _strip_trace_prefixes(_strip_ansi(text))
    drifts = list(dict.fromkeys(BODY_DRIFT_RE.findall(raw)))
    embedded_drifts = list(
        dict.fromkeys(
            m.group(1)
            for m in re.finditer(
                r"\[DRIFT\] BODY DRIFT \(embedded/workspace\) for (\S+)",
                raw,
            )
        )
    )
    non_embedded = [d for d in drifts if d not in embedded_drifts]

    validation_plugins = []
    for match in VALIDATION_FAILED_RE.finditer(raw):
        validation_plugins.append(match.group(1) or match.group(2))

    loop3 = [f"{name}:{kind}" for name, kind in LOOP3_ITEM_RE.findall(raw)]

    workspaces = []
    for item in loop3:
        workspaces.append(item.split(":", 1)[0].strip())
    if not workspaces:
        for match in WORKSPACE_RE.finditer(raw):
            name = match.group(1)
            if name in {"DEBUG", "INFO", "ERROR", "WARN"}:
                continue
            if "Validation failed" in raw[max(0, match.start() - 200) : match.end() + 200]:
                workspaces.append(name)

    failed_exports_block = FAILED_EXPORTS_RE.search(raw)
    failed_exports = []
    if failed_exports_block:
        body = failed_exports_block.group("body").strip()
        if body:
            failed_exports = [line.strip() for line in body.splitlines() if line.strip()]

    gyp_hits = bool(GYP_RE.search(raw))
    types_hits = bool(TYPES_RE.search(raw))

    if non_embedded:
        failure_class = "yarn_lock_body_drift"
        recommended_repo = "overlays"
        reason = (
            "Loop 3 yarn.lock equivalence failed on non-embedded packages. "
            "Usual cause: a workspace library was scrubbed (not in "
            "plugins-list.yaml and not --embed-package), so Loop 1 locked "
            "workspace package.json while Loop 3 locked the published npm tarball."
        )
    elif embedded_drifts:
        failure_class = "yarn_lock_embedded_drift"
        recommended_repo = "catalog"
        reason = (
            "Embedded/workspace lockfile bodies differ after checksum/resolution "
            "normalization. That is not the allowed checksum-only delta."
        )
    elif failed_exports:
        failure_class = "export_command_failed"
        recommended_repo = "upstream"
        reason = "plugin export itself failed before Loop 3 validation."
    elif types_hits and not drifts:
        failure_class = "missing_types"
        recommended_repo = "catalog"
        reason = "TypeScript / missing-module errors. Check type-shims and scrubbed test files."
    elif loop3:
        failure_class = "loop3_validation_failed"
        recommended_repo = "overlays"
        reason = "Loop 3 reported a workspace failure without a BODY DRIFT line in this excerpt."
    else:
        failure_class = "unknown"
        recommended_repo = "catalog"
        reason = "No known sync-midstream export failure pattern matched."

    return {
        "ok": failure_class != "unknown" or bool(loop3 or drifts or failed_exports),
        "failureClass": failure_class,
        "recommendedRepo": recommended_repo,
        "reason": reason,
        "workspaces": sorted(set(workspaces)),
        "validationPlugins": sorted(set(validation_plugins)),
        "bodyDriftPackages": non_embedded,
        "embeddedBodyDriftPackages": embedded_drifts,
        "failedExports": failed_exports,
        "loop3Failures": loop3,
        "nativeGypNoise": gyp_hits,
        "notes": (
            [
                "ssh2/cpu-features node-gyp failures are optional native bindings "
                "and are not the Loop 3 yarn.lock BODY DRIFT failure.",
            ]
            if gyp_hits
            else []
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify a sync-midstream / GitLab job log for export validation failures.",
    )
    parser.add_argument(
        "--log",
        required=True,
        help="Path to the job trace or local sync log, or - for stdin.",
    )
    args = parser.parse_args()
    try:
        text = _read_log(args.log)
    except OSError as exc:
        json.dump({"ok": False, "error": str(exc)}, sys.stdout, indent=2)
        print()
        return 2
    result = classify(text)
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0 if result["failureClass"] != "unknown" else 1


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[2]


def load_script(relative_path: str, module_name: str):
    script_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CLASSIFY = load_script(
    "skills/plugins/rhdh-catalog-sync-export-debug/scripts/classify_export_log.py",
    "rhdh_catalog_sync_export_debug_classify",
)
COMPARE = load_script(
    "skills/plugins/rhdh-catalog-sync-export-debug/scripts/compare_npm_workspace.py",
    "rhdh_catalog_sync_export_debug_compare",
)

JOB_SNIPPET = """
2026-09-02T08:07:42.676272Z 01O [ERROR] yarn.lock equivalence check failed for orchestrator-form-widgets:
2026-09-02T08:07:42.676272Z 01O   [DRIFT] BODY DRIFT for @red-hat-developer-hub/backstage-plugin-orchestrator-form-api@2.10.0
2026-09-02T08:07:42.676276Z 01O   [DRIFT] BODY DRIFT for @red-hat-developer-hub/backstage-plugin-orchestrator-form-react@2.11.0
[ERROR] dist-dynamic is NOT stable for orchestrator-form-widgets
[ERROR] [11/20] [orchestrator] Validation failed for orchestrator-form-widgets
ssh2@npm:1.16.0 STDOUT Failed to build optional crypto binding
gyp ERR! build error
2026-09-02T08:15:06.187046Z 01O [ERROR] Loop 3 had 1 failure(s):
2026-09-02T08:15:06.187062Z 01O   - orchestrator:validation-failed
"""


def test_classify_orchestrator_body_drift_prefers_overlays_not_gyp():
    result = CLASSIFY.classify(JOB_SNIPPET)
    assert result["failureClass"] == "yarn_lock_body_drift"
    assert result["recommendedRepo"] == "overlays"
    assert result["nativeGypNoise"] is True
    assert "orchestrator" in result["workspaces"]
    assert result["loop3Failures"] == ["orchestrator:validation-failed"]
    assert (
        "@red-hat-developer-hub/backstage-plugin-orchestrator-form-api@2.10.0"
        in result["bodyDriftPackages"]
    )


def test_classify_embedded_drift_is_a_separate_class():
    text = (
        "[DRIFT] BODY DRIFT (embedded/workspace) for @scope/lib@1.0.0\n"
        "[ERROR] [3/20] [sample] Validation failed for sample-backend\n"
    )
    result = CLASSIFY.classify(text)
    assert result["failureClass"] == "yarn_lock_embedded_drift"
    assert result["embeddedBodyDriftPackages"] == ["@scope/lib@1.0.0"]
    assert result["bodyDriftPackages"] == []


def test_compare_diff_maps_reports_workspace_vs_npm_ranges():
    diffs = COMPARE._diff_maps(
        {"@backstage/core-plugin-api": "^1.12.9"},
        {"@backstage/core-plugin-api": "^1.12.7"},
    )
    assert diffs == [
        {
            "name": "@backstage/core-plugin-api",
            "workspace": "^1.12.9",
            "npm": "^1.12.7",
        }
    ]

"""The /ask-rhdh routing table is a projection of the catalog, not a second inventory.

The table froze silently once. The category restructure moved `catalog.json`, the
renderer's `CATALOG_PATH` kept pointing at `skills/engineering/...`, and every
`--write` and `--check` exited 2 with `CATALOG_MISSING` instead of reporting
drift. The table then sat at 28 rows against 39 model-invoked skills, naming a
skill that no longer existed and omitting twelve, while catalog validation stayed
green — it never looks at that file. Nothing in tests or CI ran the renderer.

So these tests separate the two failures that looked alike:
  exit 0  the table matches the catalog
  exit 1  it has drifted — the renderer ran and reached a verdict
  exit 2  the renderer could not read its inputs — the failure that hid the first
"""

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RENDERER = PROJECT_ROOT / "skills" / "meta" / "ask-rhdh" / "scripts" / "render_routes.py"


def load_renderer():
    """Import the renderer by path; it is a bundled script, not an installed module."""
    spec = importlib.util.spec_from_file_location("render_routes", RENDERER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def check_exit_code() -> int:
    """Run `--check` in-process and return the code it exits with.

    `main` ends in `sys.exit`, so it raises rather than returning. Every path it
    resolves is relative to the script's own location, so this is independent of
    the working directory.
    """
    renderer = load_renderer()
    with pytest.raises(SystemExit) as exit_info:
        renderer.main(["--check"])
    return exit_info.value.code


def test_the_route_table_matches_the_catalog():
    """A stale table fails the suite."""
    assert check_exit_code() == 0, (
        "The /ask-rhdh route table has drifted from the catalog. Regenerate it:\n"
        "  cd skills/meta/ask-rhdh && python scripts/render_routes.py --write"
    )


def test_the_renderer_can_read_its_inputs():
    """Exit 2 means the renderer broke; conflating that with 'passing' hid the drift.

    Asserted separately from the drift check so a moved catalog or a missing
    marker block reports as a broken tool, not as a table that happens to differ.
    """
    assert check_exit_code() != 2, (
        f"render_routes.py could not read its inputs. Check that CATALOG_PATH "
        f"still resolves and that {RENDERER.parent.parent / 'SKILL.md'} keeps its "
        f"BEGIN/END GENERATED ROUTES markers."
    )


def test_every_model_invoked_skill_has_a_row():
    """The table is a projection: one row per model-invoked skill, no more, no fewer."""
    renderer = load_renderer()
    rows = renderer.build_rows()
    expected = [
        entry["name"]
        for entry in renderer.json.loads(renderer.CATALOG_PATH.read_text(encoding="utf-8"))[
            "skills"
        ]
        if entry.get("invocation") != "human"
    ]

    assert len(rows) == len(expected), (
        f"{len(rows)} rows for {len(expected)} model-invoked skills. The frozen "
        f"table had 28 rows for 39 skills and nothing caught it."
    )
    for name in expected:
        assert any(f"/{name}`" in row for row in rows), f"{name} has no row in the table"

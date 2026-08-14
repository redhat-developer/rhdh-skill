"""The skills CLI marketplace manifest is a projection of the catalog, not a second inventory."""

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = PROJECT_ROOT / "scripts" / "generate_plugin_manifest.py"


def load_generator():
    """Import the generator by path; it is a repo script, not an installed module."""
    spec = importlib.util.spec_from_file_location("generate_plugin_manifest", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def check_exit_code() -> int:
    """Run `--check` in-process and return the code it exits with."""
    generator = load_generator()
    with pytest.raises(SystemExit) as exit_info:
        generator.main(["--check"])
    return exit_info.value.code


def test_the_plugin_manifest_matches_the_catalog():
    """A stale marketplace.json fails the suite."""
    assert check_exit_code() == 0, (
        "`.claude-plugin/marketplace.json` has drifted from the catalog. "
        "Regenerate it:\n"
        "  uv run python scripts/generate_plugin_manifest.py --write"
    )


def test_the_generator_can_read_its_inputs():
    """Exit 2 means the generator broke; do not conflate that with a passing check."""
    assert check_exit_code() != 2, (
        "generate_plugin_manifest.py could not read its inputs. Check that "
        f"{GENERATOR} still resolves CATALOG_PATH."
    )


def test_reference_is_not_an_installer_group():
    """Reference stays editorial; the installer must not offer a Reference group."""
    generator = load_generator()
    catalog = generator.json.loads(generator.CATALOG_PATH.read_text(encoding="utf-8"))
    manifest = generator.build_manifest(catalog)

    assert "reference" in catalog["categories"]
    assert generator.plugin_name("reference") not in {
        plugin["name"] for plugin in manifest["plugins"]
    }
    installable = [
        category
        for category in catalog["categories"]
        if category not in generator.HIDDEN_INSTALL_CATEGORIES
    ]
    # Manifest plugins are reversed so earlier categories win shared pluginNames.
    assert [plugin["name"] for plugin in manifest["plugins"]] == [
        generator.plugin_name(category) for category in reversed(installable)
    ]


def test_each_installable_category_includes_its_reference_requires():
    """Selecting a category group must list that category's required reference skills."""
    generator = load_generator()
    catalog = generator.json.loads(generator.CATALOG_PATH.read_text(encoding="utf-8"))
    by_name = {entry["name"]: entry for entry in catalog["skills"]}
    manifest = generator.build_manifest(catalog)
    plugins = {plugin["name"]: plugin for plugin in manifest["plugins"]}

    for entry in catalog["skills"]:
        category = entry["category"]
        if category in generator.HIDDEN_INSTALL_CATEGORIES:
            continue
        plugin = plugins[generator.plugin_name(category)]
        assert generator._skill_path(entry) in plugin["skills"]
        for path in generator._reference_closure(entry["name"], by_name):
            assert path in plugin["skills"], (
                f"{entry['name']} requires {path}, but the {category} plugin omits it"
            )


def test_every_required_reference_skill_is_reachable_from_some_plugin():
    """No required reference skill is left only in the hidden editorial category."""
    generator = load_generator()
    catalog = generator.json.loads(generator.CATALOG_PATH.read_text(encoding="utf-8"))
    by_name = {entry["name"]: entry for entry in catalog["skills"]}
    manifest = generator.build_manifest(catalog)
    listed = {path for plugin in manifest["plugins"] for path in plugin["skills"]}

    required_reference = set()
    for entry in catalog["skills"]:
        if entry["category"] in generator.HIDDEN_INSTALL_CATEGORIES:
            continue
        required_reference.update(generator._reference_closure(entry["name"], by_name))

    assert required_reference
    assert required_reference <= listed

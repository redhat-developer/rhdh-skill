"""Tests for overlay skill's derive-metadata.py script."""

import importlib.util
import json
import textwrap
from pathlib import Path

import pytest

# Load derive-metadata.py as a module (hyphenated filename can't be imported normally)
SCRIPT_PATH = Path(__file__).parent.parent.parent / "skills" / "overlay" / "scripts" / "derive-metadata.py"
spec = importlib.util.spec_from_file_location("derive_metadata", SCRIPT_PATH)
dm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dm)


class TestParsePluginsList:
    """Test plugins-list.yaml parsing."""

    def test_simple_paths(self, tmp_path):
        (tmp_path / "plugins-list.yaml").write_text(
            "plugins/frontend:\nplugins/backend:\n"
        )
        result = dm.parse_plugins_list(tmp_path)
        assert [p["path"] for p in result] == ["plugins/frontend", "plugins/backend"]

    def test_paths_with_cli_args(self, tmp_path):
        (tmp_path / "plugins-list.yaml").write_text(
            "plugins/adr-backend: --embed-package @backstage-community/plugin-adr-common\n"
        )
        result = dm.parse_plugins_list(tmp_path)
        assert result == [{"path": "plugins/adr-backend"}]

    def test_commented_out_lines(self, tmp_path):
        (tmp_path / "plugins-list.yaml").write_text(
            "#plugins/disabled:\nplugins/enabled:\n"
        )
        result = dm.parse_plugins_list(tmp_path)
        assert result == [{"path": "plugins/enabled"}]

    def test_indented_continuation_lines_skipped(self, tmp_path):
        (tmp_path / "plugins-list.yaml").write_text(
            "plugins/main:\n  - --some-arg\n  - --another\nplugins/other:\n"
        )
        result = dm.parse_plugins_list(tmp_path)
        assert [p["path"] for p in result] == ["plugins/main", "plugins/other"]

    def test_empty_lines_skipped(self, tmp_path):
        (tmp_path / "plugins-list.yaml").write_text(
            "plugins/a:\n\nplugins/b:\n"
        )
        result = dm.parse_plugins_list(tmp_path)
        assert [p["path"] for p in result] == ["plugins/a", "plugins/b"]

    def test_dot_path(self, tmp_path):
        (tmp_path / "plugins-list.yaml").write_text(".:\n")
        result = dm.parse_plugins_list(tmp_path)
        assert result == [{"path": "."}]

    def test_inline_comment_stripped(self, tmp_path):
        (tmp_path / "plugins-list.yaml").write_text(
            "plugins/foo: # experimental\n"
        )
        result = dm.parse_plugins_list(tmp_path)
        assert result == [{"path": "plugins/foo"}]


class TestShortenName:
    """Test Kubernetes name shortening logic."""

    def test_short_name_unchanged(self):
        assert dm.shorten_name("backstage-community-plugin-foo") == "backstage-community-plugin-foo"

    def test_long_name_shortened(self):
        long_name = "backstage-community-plugin-very-long-name-that-exceeds-the-kubernetes-limit"
        assert len(long_name) > 63
        result = dm.shorten_name(long_name)
        assert len(result) <= 63
        assert "bcp" in result

    def test_exactly_63_chars_unchanged(self):
        name = "a" * 63
        assert dm.shorten_name(name) == name

    def test_shortening_rules_applied_in_order(self):
        name = "backstage-community-plugin-catalog-module-kubernetes-something-extra"
        result = dm.shorten_name(name)
        assert "bcp" in result
        assert "backstage-community-plugin" not in result


class TestPackageNameToMetadataName:
    """Test npm package name to metadata name derivation."""

    def test_scoped_package(self):
        result = dm.package_name_to_metadata_name("@backstage-community/plugin-argocd")
        assert result == "backstage-community-plugin-argocd"

    def test_unscoped_package(self):
        result = dm.package_name_to_metadata_name("backstage-plugin-foo")
        assert result == "backstage-plugin-foo"

    def test_long_scoped_name_shortened(self):
        name = "@backstage-community/plugin-catalog-module-kubernetes-something-extra"
        result = dm.package_name_to_metadata_name(name)
        assert len(result) <= 63


class TestDeriveTitle:
    """Test human-readable title derivation."""

    def test_basic_plugin(self):
        assert dm.derive_title("@backstage-community/plugin-argocd") == "Argocd"

    def test_multi_word(self):
        assert dm.derive_title("@backstage-community/plugin-tech-radar") == "Tech Radar"

    def test_with_backstage_prefix(self):
        result = dm.derive_title("@scope/backstage-plugin-my-feature")
        assert result == "My Feature"


class TestDeriveSourceCodeUrl:
    """Test source code URL derivation."""

    def test_non_flat_with_plugin_path(self):
        url = dm.derive_source_code_url(
            "https://github.com/backstage/community-plugins",
            "argocd", "plugins/argocd", flat=False,
        )
        assert url == "https://github.com/backstage/community-plugins/tree/main/workspaces/argocd/plugins/argocd"

    def test_non_flat_with_dot_path(self):
        url = dm.derive_source_code_url(
            "https://github.com/example/repo",
            "myws", ".", flat=False,
        )
        assert url == "https://github.com/example/repo/tree/main/workspaces/myws"

    def test_flat_with_plugin_path(self):
        url = dm.derive_source_code_url(
            "https://github.com/example/repo",
            "myws", "plugins/foo", flat=True,
        )
        assert url == "https://github.com/example/repo/tree/main/plugins/foo"

    def test_flat_with_dot_path(self):
        url = dm.derive_source_code_url(
            "https://github.com/example/repo",
            "myws", ".", flat=True,
        )
        assert url == "https://github.com/example/repo/tree/main"


class TestDeriveOciUrl:
    """Test OCI artifact URL derivation."""

    def test_basic_oci_url(self):
        url = dm.derive_oci_url("backstage-community-plugin-argocd", "1.49.2", "2.8.0")
        assert url == (
            "oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/"
            "backstage-community-plugin-argocd:bs_1.49.2__2.8.0"
            "!backstage-community-plugin-argocd"
        )


class TestDeriveSupportedVersions:
    """Test supportedVersions derivation."""

    def test_from_source_json(self, tmp_path):
        source = {"repo-backstage-version": "1.45.3"}
        assert dm.derive_supported_versions(tmp_path, source) == "1.45.3"

    def test_backstage_json_override(self, tmp_path):
        (tmp_path / "backstage.json").write_text('{"version": "1.49.2"}')
        source = {"repo-backstage-version": "1.45.3"}
        assert dm.derive_supported_versions(tmp_path, source) == "1.49.2"


class TestFindMissingMetadata:
    """Test detection of plugins without metadata files."""

    def test_all_present(self, tmp_path):
        (tmp_path / "metadata").mkdir()
        (tmp_path / "metadata" / "some-plugin-argocd.yaml").write_text("kind: Package")
        plugins = [{"path": "plugins/argocd"}]
        assert dm.find_missing_metadata(tmp_path, plugins) == []

    def test_missing_metadata(self, tmp_path):
        (tmp_path / "metadata").mkdir()
        plugins = [{"path": "plugins/argocd"}]
        result = dm.find_missing_metadata(tmp_path, plugins)
        assert result == [{"path": "plugins/argocd"}]

    def test_no_metadata_dir(self, tmp_path):
        plugins = [{"path": "plugins/foo"}]
        result = dm.find_missing_metadata(tmp_path, plugins)
        assert result == [{"path": "plugins/foo"}]

    def test_dot_path_with_no_metadata(self, tmp_path):
        plugins = [{"path": "."}]
        result = dm.find_missing_metadata(tmp_path, plugins)
        assert result == [{"path": "."}]

    def test_dot_path_with_existing_metadata(self, tmp_path):
        (tmp_path / "metadata").mkdir()
        (tmp_path / "metadata" / "something.yaml").write_text("kind: Package")
        plugins = [{"path": "."}]
        result = dm.find_missing_metadata(tmp_path, plugins)
        assert result == []


class TestExtractEnvVars:
    """Test ${VAR_NAME} extraction from YAML content."""

    def test_basic_extraction(self):
        content = "token: ${MY_TOKEN}\nurl: ${BASE_URL}"
        assert dm.extract_env_vars(content) == ["BASE_URL", "MY_TOKEN"]

    def test_no_env_vars(self):
        assert dm.extract_env_vars("plain: value") == []

    def test_deduplication(self):
        content = "a: ${TOKEN}\nb: ${TOKEN}"
        assert dm.extract_env_vars(content) == ["TOKEN"]

    def test_sorted_output(self):
        content = "${ZEBRA}\n${ALPHA}"
        assert dm.extract_env_vars(content) == ["ALPHA", "ZEBRA"]


class TestDerivePluginFields:
    """Test full field derivation for a plugin."""

    @pytest.fixture
    def source(self):
        return {
            "repo": "https://github.com/backstage/community-plugins",
            "repo-ref": "abc123",
            "repo-flat": False,
            "repo-backstage-version": "1.49.2",
        }

    def test_backend_plugin(self, source):
        pkg = {
            "name": "@backstage-community/plugin-argocd-backend",
            "version": "1.4.0",
            "backstage": {"role": "backend-plugin"},
        }
        result = dm.derive_plugin_fields(
            pkg, "argocd", "plugins/argocd-backend", source, "1.49.2", None
        )
        assert result["metadata_name"] == "backstage-community-plugin-argocd-backend"
        assert result["packageName"] == "@backstage-community/plugin-argocd-backend"
        assert result["version"] == "1.4.0"
        assert result["role"] == "backend-plugin"
        assert result["supportedVersions"] == "1.49.2"
        assert "argocd-backend" in result["sourceCodeUrl"]
        assert result["support"] == "community"

    def test_copies_existing_metadata(self, source):
        existing = {"author": "Red Hat", "lifecycle": "active", "partOf": ["argocd"]}
        pkg = {
            "name": "@backstage-community/plugin-argocd",
            "version": "2.8.0",
            "backstage": {"role": "frontend-plugin"},
        }
        result = dm.derive_plugin_fields(
            pkg, "argocd", "plugins/argocd", source, "1.49.2", existing
        )
        assert result["author"] == "Red Hat"
        assert result["lifecycle"] == "active"
        assert result["partOf"] == ["argocd"]

    def test_support_needs_confirmation_for_ga(self, source):
        existing = {"author": "Red Hat", "support": "generally-available"}
        pkg = {
            "name": "@backstage-community/plugin-foo",
            "version": "1.0.0",
            "backstage": {"role": "backend-plugin"},
        }
        result = dm.derive_plugin_fields(
            pkg, "foo", "plugins/foo", source, "1.49.2", existing
        )
        assert result["support"] == "generally-available"
        assert result["support_needs_confirmation"] is True

    def test_support_needs_confirmation_for_tech_preview(self, source):
        existing = {"author": "Red Hat", "support": "tech-preview"}
        pkg = {
            "name": "@backstage-community/plugin-bar",
            "version": "1.0.0",
            "backstage": {"role": "backend-plugin"},
        }
        result = dm.derive_plugin_fields(
            pkg, "bar", "plugins/bar", source, "1.49.2", existing
        )
        assert result["support_needs_confirmation"] is True

    def test_community_support_no_confirmation(self, source):
        existing = {"author": "Red Hat", "support": "community"}
        pkg = {
            "name": "@backstage-community/plugin-baz",
            "version": "1.0.0",
            "backstage": {"role": "backend-plugin"},
        }
        result = dm.derive_plugin_fields(
            pkg, "baz", "plugins/baz", source, "1.49.2", existing
        )
        assert result["support"] == "community"
        assert "support_needs_confirmation" not in result

    def test_no_existing_metadata_defaults_to_community(self, source):
        pkg = {
            "name": "@backstage-community/plugin-new",
            "version": "0.1.0",
            "backstage": {"role": "frontend-plugin"},
        }
        result = dm.derive_plugin_fields(
            pkg, "new", "plugins/new", source, "1.49.2", None
        )
        assert result["support"] == "community"
        assert "support_needs_confirmation" not in result

    def test_flat_repo_source_url(self, source):
        source["repo-flat"] = True
        pkg = {
            "name": "@example/plugin-standalone",
            "version": "1.0.0",
            "backstage": {"role": "frontend-plugin"},
        }
        result = dm.derive_plugin_fields(
            pkg, "standalone", ".", source, "1.49.2", None
        )
        assert result["sourceCodeUrl"] == "https://github.com/backstage/community-plugins/tree/main"


class TestCheckSupportedVersionsConsistency:
    """Test audit of supportedVersions across metadata files."""

    def test_all_consistent(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        (md / "plugin-a.yaml").write_text("spec:\n  backstage:\n    supportedVersions: 1.49.2\n")
        (md / "plugin-b.yaml").write_text("spec:\n  backstage:\n    supportedVersions: 1.49.2\n")
        assert dm.check_supported_versions_consistency(tmp_path, "1.49.2") == []

    def test_mismatch_detected(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        (md / "plugin-a.yaml").write_text("spec:\n  backstage:\n    supportedVersions: 1.45.3\n")
        result = dm.check_supported_versions_consistency(tmp_path, "1.49.2")
        assert len(result) == 1
        assert result[0]["actual"] == "1.45.3"
        assert result[0]["expected"] == "1.49.2"


class TestCheckEmptyConfigWithoutFlag:
    """Test audit for appConfigExamples: [] without appConfigNotRequired."""

    def test_no_issues(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        (md / "plugin.yaml").write_text(
            "spec:\n  appConfigNotRequired: true\n  appConfigExamples: []\n"
        )
        assert dm.check_empty_config_without_flag(tmp_path) == []

    def test_issue_detected(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        (md / "plugin.yaml").write_text("spec:\n  appConfigExamples: []\n")
        result = dm.check_empty_config_without_flag(tmp_path)
        assert result == ["plugin.yaml"]

    def test_non_empty_config_no_issue(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        (md / "plugin.yaml").write_text(
            "spec:\n  appConfigExamples:\n    - title: Default\n"
        )
        assert dm.check_empty_config_without_flag(tmp_path) == []


class TestReadExistingMetadata:
    """Test extraction of copyable fields from existing metadata."""

    def test_extracts_fields(self, tmp_path):
        md = tmp_path / "metadata"
        md.mkdir()
        (md / "plugin.yaml").write_text(textwrap.dedent("""\
            spec:
              author: Red Hat
              support: community
              lifecycle: active
              partOf:
                - my-plugin
        """))
        result = dm.read_existing_metadata(tmp_path)
        assert result["author"] == "Red Hat"
        assert result["support"] == "community"
        assert result["lifecycle"] == "active"
        assert result["partOf"] == ["my-plugin"]

    def test_no_metadata_dir(self, tmp_path):
        assert dm.read_existing_metadata(tmp_path) is None

    def test_empty_metadata_dir(self, tmp_path):
        (tmp_path / "metadata").mkdir()
        assert dm.read_existing_metadata(tmp_path) is None

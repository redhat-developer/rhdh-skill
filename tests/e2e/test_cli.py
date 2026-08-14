"""End-to-end tests for rhdh CLI.

These tests run the actual Python CLI code (no subprocess).
Output is JSON by default (non-TTY context), so we parse the structured response.
"""

import json


def parse_response(result):
    """Parse JSON response from CLI."""
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


class TestCliStatus:
    """Test CLI status command (no args)."""

    def test_no_args_shows_status(self, cli, isolated_env):
        """Running with no args should show status."""
        result = cli()

        # Should succeed (exit 0)
        assert result.returncode == 0, f"stderr: {result.stderr}"

        # Should return valid JSON with success=True
        response = parse_response(result)
        assert response is not None
        assert response["success"] is True
        assert "data" in response

    def test_status_shows_needs_setup(self, cli, isolated_env):
        """Status should include needs_setup flag."""
        result = cli()

        response = parse_response(result)
        assert response is not None
        assert "needs_setup" in response["data"]

    def test_status_shows_checks(self, cli, isolated_env):
        """Status should include checks array."""
        result = cli()

        response = parse_response(result)
        assert response is not None
        assert "checks" in response["data"]
        assert isinstance(response["data"]["checks"], list)

    def test_status_shows_next_steps(self, cli, isolated_env):
        """Status should include next_steps."""
        result = cli()

        response = parse_response(result)
        assert response is not None
        assert "next_steps" in response

    def test_status_unconfigured_is_valid(self, unconfigured_cli):
        """When no repos are configured, needs_setup should be false (all repos are optional)."""
        result = unconfigured_cli()

        response = parse_response(result)
        assert response is not None
        assert response["data"]["needs_setup"] is False

        # Should NOT include setup_options or doctor_workflow
        assert "setup_options" not in response["data"]
        assert "doctor_workflow" not in response["data"]


class TestCliDoctor:
    """Test CLI doctor command."""

    def test_doctor_runs(self, cli, isolated_env):
        """Doctor command should run without error."""
        result = cli("doctor")

        # Should complete (may have issues but shouldn't crash)
        assert result.returncode in [0, 1]

        response = parse_response(result)
        assert response is not None
        assert response["success"] is True

    def test_doctor_returns_checks(self, cli, isolated_env):
        """Doctor should return checks array."""
        result = cli("doctor")

        response = parse_response(result)
        assert response is not None
        assert "checks" in response["data"]
        assert isinstance(response["data"]["checks"], list)

    def test_doctor_returns_all_passed(self, cli, isolated_env):
        """Doctor should return all_passed field."""
        result = cli("doctor")

        response = parse_response(result)
        assert response is not None
        assert "all_passed" in response["data"]

    def test_doctor_checks_all_repos(self, unconfigured_cli):
        """Doctor should include a check for every configured repository."""
        from rhdh.config import SUBMODULE_REPOS

        result = unconfigured_cli("doctor")
        response = parse_response(result)
        assert response is not None

        check_names = [c["name"] for c in response["data"]["checks"]]
        for info in SUBMODULE_REPOS.values():
            config_key = info["config_key"]
            assert config_key in check_names, f"Doctor missing check for repo '{config_key}'"

    def test_doctor_unconfigured_repos_no_issues(self, unconfigured_cli):
        """When no repos are configured, doctor should not report repo issues (all optional)."""
        result = unconfigured_cli("doctor")

        response = parse_response(result)
        assert response is not None

        # No repo-related issues should appear (all repos are optional)
        repo_issues = [i for i in response["data"]["issues"] if "config set" in i]
        assert repo_issues == [], f"Unexpected repo issues: {repo_issues}"


class TestCliConfig:
    """Test CLI config commands."""

    def test_config_init_creates_file(self, cli, isolated_env):
        """config init should create config file."""
        result = cli("config", "init")

        assert result.returncode == 0

        response = parse_response(result)
        assert response is not None
        assert response["success"] is True

    def test_config_show_displays_config(self, cli, isolated_env):
        """config show should display configuration."""
        # First init
        cli("config", "init")

        result = cli("config", "show")

        assert result.returncode == 0

        response = parse_response(result)
        assert response is not None
        # Layered config returns separate paths for project and user config
        assert "project_config_path" in response["data"]
        assert "user_config_path" in response["data"]
        assert "resolved" in response["data"]

    def test_config_set_updates_value(self, cli, isolated_env):
        """config set should update a value."""
        # First init
        cli("config", "init")

        # Set a path (use the mock overlay dir)
        result = cli("config", "set", "overlay", str(isolated_env["overlay_dir"]))

        assert result.returncode == 0

        response = parse_response(result)
        assert response is not None
        assert response["success"] is True
        # Shorthand 'overlay' maps to 'repos.overlay'
        assert response["data"]["key"] == "repos.overlay"

    def test_config_set_accepts_any_path(self, cli, isolated_env):
        """config set accepts paths without validation (paths are validated at use time)."""
        # The layered config design doesn't validate paths on set
        # Validation happens when the path is actually used (e.g., workspace list)
        result = cli("config", "set", "overlay", "/nonexistent/path")

        assert result.returncode == 0

        response = parse_response(result)
        assert response is not None
        assert response["success"] is True
        assert response["data"]["value"] == "/nonexistent/path"

    def test_config_set_accepts_arbitrary_keys(self, cli, isolated_env):
        """config set accepts any dot-notation key (flexible schema)."""
        # The layered config design allows arbitrary keys for extensibility
        result = cli("config", "set", "custom.setting", "value")

        assert result.returncode == 0

        response = parse_response(result)
        assert response is not None
        assert response["success"] is True
        assert response["data"]["key"] == "custom.setting"


class TestCliWorkspace:
    """Test CLI workspace commands."""

    def test_workspace_list_works(self, cli, isolated_env):
        """workspace list should show workspaces."""
        # Use env var for reliable repo discovery in tests
        # (config-based discovery requires consistent find_git_root mocking)
        env = {"RHDH_OVERLAY_REPO": str(isolated_env["overlay_dir"])}

        result = cli("workspace", "list", env=env)

        assert result.returncode == 0

        response = parse_response(result)
        assert response is not None
        assert response["success"] is True
        assert "items" in response["data"]

    def test_workspace_list_shows_test_plugin(self, cli, isolated_env):
        """workspace list should show our test plugin."""
        # Use env var to override the default discovery
        env = {"RHDH_OVERLAY_REPO": str(isolated_env["overlay_dir"])}

        result = cli("workspace", "list", env=env)

        response = parse_response(result)
        assert response is not None

        items = response["data"]["items"]
        names = [item["name"] for item in items]
        assert "test-plugin" in names

    def test_workspace_status_shows_details(self, cli, isolated_env):
        """workspace status should show workspace details."""
        # Use env var to override the default discovery
        env = {"RHDH_OVERLAY_REPO": str(isolated_env["overlay_dir"])}

        result = cli("workspace", "status", "test-plugin", env=env)

        assert result.returncode == 0

        response = parse_response(result)
        assert response is not None
        assert response["data"]["name"] == "test-plugin"
        assert "files" in response["data"]

    def test_workspace_status_unknown_workspace(self, cli, isolated_env):
        """workspace status should error for unknown workspace."""
        cli("config", "set", "overlay", str(isolated_env["overlay_dir"]))

        result = cli("workspace", "status", "nonexistent")

        assert result.returncode != 0

        response = parse_response(result)
        assert response is not None
        assert response["success"] is False
        assert response["error"]["code"] == "WORKSPACE_NOT_FOUND"


class TestCliHelp:
    """Test CLI help."""

    def test_help_flag(self, cli, isolated_env):
        """--help should show help."""
        result = cli("--help")

        assert result.returncode == 0
        # Help is always human-readable
        assert "rhdh" in result.stdout

    def test_help_command(self, cli, isolated_env):
        """help command should show help."""
        result = cli("help")

        assert result.returncode == 0
        assert "rhdh" in result.stdout


class TestCliUnknownCommand:
    """Test CLI handles unknown commands."""

    def test_unknown_command_errors(self, cli, isolated_env):
        """Unknown command should show error."""
        result = cli("unknown_command")

        # argparse returns 2 for unknown commands
        assert result.returncode != 0


class TestCliEnvironmentVariables:
    """Test CLI respects environment variables."""

    def test_overlay_env_var(self, cli, isolated_env):
        """RHDH_OVERLAY_REPO env var should override config."""
        env = {"RHDH_OVERLAY_REPO": str(isolated_env["overlay_dir"])}

        result = cli("workspace", "list", env=env)

        assert result.returncode == 0

        response = parse_response(result)
        assert response is not None

        items = response["data"]["items"]
        names = [item["name"] for item in items]
        assert "test-plugin" in names


class TestCliVersion:
    """Test CLI version command."""

    def test_version_flag(self, cli, isolated_env):
        """--version should show version."""
        result = cli("--version")

        assert result.returncode == 0
        assert "0.0.0" in result.stdout


class TestCliOutputFormat:
    """Test CLI output format detection."""

    def test_json_flag_forces_json(self, cli, isolated_env):
        """--json flag should force JSON output."""
        result = cli("--json")

        response = parse_response(result)
        assert response is not None
        assert response["success"] is True

    def test_human_flag_forces_human(self, cli, isolated_env):
        """--human flag should force human-readable output."""
        result = cli("--human")

        # Human output is not JSON
        response = parse_response(result)
        assert response is None

        # Should have human-readable content
        assert "Next steps" in result.stdout or "✓" in result.stdout


class TestCliDoctorJira:
    """Test CLI doctor acli/Jira checks (optional tool)."""

    def test_doctor_includes_jira_check(self, cli, isolated_env, monkeypatch):
        """Doctor should include JIRA check in results."""
        from rhdh import cli as cli_module

        # Mock acli not installed
        original_check_tool = cli_module.check_tool
        monkeypatch.setattr(
            cli_module,
            "check_tool",
            lambda name: original_check_tool(name) if name != "acli" else False,
        )

        result = cli("doctor")
        response = parse_response(result)

        check_names = [c["name"] for c in response["data"]["checks"]]
        assert "acli_installed" in check_names

    def test_doctor_jira_not_installed_is_info(self, cli, isolated_env, monkeypatch):
        """JIRA not installed should be info status (optional tool)."""
        from rhdh import cli as cli_module

        original_check_tool = cli_module.check_tool
        monkeypatch.setattr(
            cli_module,
            "check_tool",
            lambda name: original_check_tool(name) if name != "acli" else False,
        )

        result = cli("doctor")
        response = parse_response(result)

        jira_check = next(c for c in response["data"]["checks"] if c["name"] == "acli_installed")
        assert jira_check["status"] == "info"
        assert "optional" in jira_check["message"]
        assert jira_check["setup_required"] == "/setup-rhdh-skills jira"

    def test_doctor_jira_not_authenticated_is_warn(self, cli, isolated_env, monkeypatch):
        """JIRA installed but not authenticated should be warn status."""
        from rhdh import cli as cli_module

        # Mock acli installed
        original_check_tool = cli_module.check_tool
        monkeypatch.setattr(
            cli_module,
            "check_tool",
            lambda name: True if name == "acli" else original_check_tool(name),
        )

        # Mock the acli Jira smoke test failing
        original_run = cli_module.run_command

        def mock_run(cmd, cwd=None):
            if cmd == ["acli", "jira", "project", "list", "--recent", "1"]:
                return (1, "", "not authenticated")
            return original_run(cmd, cwd)

        monkeypatch.setattr(cli_module, "run_command", mock_run)

        result = cli("doctor")
        response = parse_response(result)

        jira_auth = next(c for c in response["data"]["checks"] if c["name"] == "acli_auth")
        assert jira_auth["status"] == "warn"
        assert jira_auth["setup_required"] == "/setup-rhdh-skills jira"

    def test_doctor_jira_authenticated_is_pass(self, cli, isolated_env, monkeypatch):
        """JIRA installed and authenticated should be pass status."""
        from rhdh import cli as cli_module

        # Mock acli installed
        original_check_tool = cli_module.check_tool
        monkeypatch.setattr(
            cli_module,
            "check_tool",
            lambda name: True if name == "acli" else original_check_tool(name),
        )

        # Mock the acli Jira smoke test succeeding
        original_run = cli_module.run_command

        def mock_run(cmd, cwd=None):
            if cmd == ["acli", "jira", "project", "list", "--recent", "1"]:
                return (0, "user@example.com", "")
            return original_run(cmd, cwd)

        monkeypatch.setattr(cli_module, "run_command", mock_run)

        result = cli("doctor")
        response = parse_response(result)

        jira_installed = next(
            c for c in response["data"]["checks"] if c["name"] == "acli_installed"
        )
        jira_auth = next(c for c in response["data"]["checks"] if c["name"] == "acli_auth")
        assert jira_installed["status"] == "pass"
        assert jira_auth["status"] == "pass"

    def test_doctor_jira_check_does_not_affect_all_passed(self, cli, isolated_env, monkeypatch):
        """JIRA issues should NOT cause doctor to fail (optional tool)."""
        from rhdh import cli as cli_module

        # Mock acli not installed
        original_check_tool = cli_module.check_tool
        monkeypatch.setattr(
            cli_module,
            "check_tool",
            lambda name: original_check_tool(name) if name != "acli" else False,
        )

        result = cli("doctor")
        response = parse_response(result)

        # JIRA being missing should not add to issues
        jira_check = next(c for c in response["data"]["checks"] if c["name"] == "acli_installed")
        assert jira_check["status"] == "info"  # info, not fail

        # Verify no JIRA-related items in issues list
        issues = response["data"]["issues"]
        jira_issues = [i for i in issues if "jira" in i.lower()]
        assert len(jira_issues) == 0

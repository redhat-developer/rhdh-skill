"""Unit tests for skills/rhdh-release/scripts/ — jql.py, slack_templates.py, release.py."""

import sys
from pathlib import Path
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_RELEASE_SCRIPTS = PROJECT_ROOT / "skills" / "rhdh-release" / "scripts"
if str(_RELEASE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_RELEASE_SCRIPTS))

import jql  # noqa: E402
import release  # noqa: E402
import slack_templates  # noqa: E402

# =========================================================================
# jql.py
# =========================================================================


class TestJqlLoadTemplates:
    def test_loads_13_templates(self):
        templates = jql.load_templates()
        assert len(templates) == 13

    def test_known_template_names(self):
        names = jql.list_templates()
        assert "active_release" in names
        assert "open_issues" in names
        assert "open_issues_by_type" in names
        assert "epics" in names
        assert "cves" in names
        assert "feature_demos" in names
        assert "feature_subtasks" in names
        assert "test_day_features" in names
        assert "features_added_to_release" in names
        assert "release_notes" in names
        assert "blockers" in names
        assert "feature_freeze_issues" in names
        assert "code_freeze_issues" in names


class TestJqlGetTemplate:
    def test_get_existing(self):
        tpl = jql.get_template("active_release")
        assert "rhdhplan" in tpl.lower()

    def test_get_nonexistent_raises(self):
        try:
            jql.get_template("nonexistent_query")
            assert False, "Expected KeyError"
        except KeyError as e:
            assert "nonexistent_query" in str(e)


class TestJqlRender:
    def test_render_version(self):
        rendered = jql.render("open_issues", version="1.9.0")
        assert '"1.9.0"' in rendered
        assert "{{RELEASE_VERSION}}" not in rendered

    def test_render_version_and_type(self):
        rendered = jql.render("open_issues_by_type", version="1.9.0", issue_type="Bug")
        assert '"1.9.0"' in rendered
        assert '"Bug"' in rendered
        assert "{{RELEASE_VERSION}}" not in rendered
        assert "{{ISSUE_TYPE}}" not in rendered

    def test_render_no_substitution(self):
        rendered = jql.render("active_release")
        assert "{{" not in rendered


class TestJqlUrl:
    def test_url_encoding(self):
        jql_str = "project = RHIDP AND status != closed"
        url = jql.jira_url(jql_str)
        assert url.startswith("https://issues.redhat.com/issues/?jql=")
        assert "%20" in url or "+" in url
        assert "project" not in url.split("jql=")[1].split("%")[0] or quote(jql_str, safe="") in url

    def test_url_encodes_special_chars(self):
        jql_str = 'fixVersion = "1.9.0" AND issuetype IN (Bug, Feature)'
        url = jql.jira_url(jql_str)
        encoded_part = url.split("jql=")[1]
        assert " " not in encoded_part
        assert '"' not in encoded_part
        assert "(" not in encoded_part

    def test_render_with_url(self):
        rendered, url = jql.render_with_url("open_issues", version="1.9.0")
        assert '"1.9.0"' in rendered
        assert url.startswith("https://issues.redhat.com/issues/?jql=")
        assert quote(rendered, safe="") in url


# =========================================================================
# slack_templates.py
# =========================================================================


class TestSlackLoadTemplates:
    def test_loads_4_templates(self):
        templates = slack_templates.load_templates()
        assert len(templates) == 4

    def test_known_template_keys(self):
        keys = slack_templates.list_templates()
        assert "feature_freeze_update" in keys
        assert "feature_freeze" in keys
        assert "code_freeze_update" in keys
        assert "code_freeze" in keys


class TestSlackGetTemplate:
    def test_get_existing(self):
        tpl = slack_templates.get_template("feature_freeze")
        assert "{{RELEASE_VERSION}}" in tpl

    def test_get_nonexistent_raises(self):
        try:
            slack_templates.get_template("nonexistent")
            assert False, "Expected KeyError"
        except KeyError as e:
            assert "nonexistent" in str(e)


class TestSlackFillPlaceholders:
    def test_basic_fill(self):
        template = "Hello {{NAME}}, version {{VERSION}}"
        result = slack_templates.fill_placeholders(
            template,
            {
                "NAME": "World",
                "VERSION": "1.0",
            },
        )
        assert result == "Hello World, version 1.0"

    def test_no_match_preserved(self):
        template = "{{UNKNOWN}} stays"
        result = slack_templates.fill_placeholders(template, {"OTHER": "val"})
        assert "{{UNKNOWN}}" in result


class TestSlackExpandTeamLines:
    def test_expands_team_block(self):
        template = (
            "Header\n"
            "• *{{TEAM_NAME}}* - [{{ISSUE_COUNT}}](url)\n"
            "(repeat for each active engineering team)\n"
            "Footer"
        )
        teams = [
            {"TEAM_NAME": "Alpha", "ISSUE_COUNT": "5"},
            {"TEAM_NAME": "Beta", "ISSUE_COUNT": "3"},
        ]
        result = slack_templates.expand_team_lines(template, teams)
        assert "• *Alpha* - [5](url)" in result
        assert "• *Beta* - [3](url)" in result
        assert "(repeat for each" not in result
        assert "Footer" in result


# =========================================================================
# release.py — CLI parsing
# =========================================================================


class TestReleaseParser:
    def test_no_args_exits_zero(self):
        try:
            release.main([])
        except SystemExit as e:
            assert e.code == 0

    def test_check_subcommand(self):
        parser = release.build_parser()
        args = parser.parse_args(["check"])
        assert args.command == "check"

    def test_status_subcommand(self):
        parser = release.build_parser()
        args = parser.parse_args(["status", "1.9.0"])
        assert args.command == "status"
        assert args.version == "1.9.0"

    def test_slack_subcommand(self):
        parser = release.build_parser()
        args = parser.parse_args(["slack", "feature-freeze", "1.9.0"])
        assert args.command == "slack"
        assert args.slack_command == "feature-freeze"
        assert args.version == "1.9.0"

    def test_global_json_flag(self):
        parser = release.build_parser()
        args = parser.parse_args(["--json", "status", "1.9.0"])
        assert args.output_mode == "json"

    def test_global_human_flag(self):
        parser = release.build_parser()
        args = parser.parse_args(["--human", "status", "1.9.0"])
        assert args.output_mode == "human"

    def test_verbose_flag(self):
        parser = release.build_parser()
        args = parser.parse_args(["--verbose", "check"])
        assert args.verbose is True

    def test_teams_category(self):
        parser = release.build_parser()
        args = parser.parse_args(["teams", "--category", "Engineering"])
        assert args.command == "teams"
        assert args.category == "Engineering"

    def test_all_subcommands_parse(self):
        parser = release.build_parser()
        for cmd in ["check", "dates", "slack"]:
            args = parser.parse_args([cmd])
            assert args.command == cmd
        for cmd in [
            "future-dates",
            "status",
            "team-breakdown",
            "blockers",
            "epics",
            "cves",
            "notes",
        ]:
            args = parser.parse_args([cmd, "1.0.0"])
            assert args.command == cmd
        args = parser.parse_args(["teams"])
        assert args.command == "teams"

    def test_all_slack_subcommands_parse(self):
        parser = release.build_parser()
        for cmd in ["feature-freeze-update", "feature-freeze", "code-freeze-update", "code-freeze"]:
            args = parser.parse_args(["slack", cmd, "1.0.0"])
            assert args.slack_command == cmd


class TestParseAcliCount:
    def test_standard_output(self):
        output = "✓ Number of work items in the search: 42"
        assert release._parse_acli_count(output) == 42

    def test_multiline_with_noise(self):
        output = "Connecting...\nSearching...\n✓ Number of work items in the search: 128\n"
        assert release._parse_acli_count(output) == 128

    def test_zero_count(self):
        output = "✓ Number of work items in the search: 0"
        assert release._parse_acli_count(output) == 0

    def test_large_count(self):
        output = "✓ Number of work items in the search: 12086"
        assert release._parse_acli_count(output) == 12086

    def test_no_count_raises(self):
        try:
            release._parse_acli_count("No numbers here")
            assert False, "Expected ValueError"
        except ValueError:
            pass


class TestCommandMapping:
    def test_all_commands_mapped(self):
        expected_commands = {
            "check",
            "dates",
            "future-dates",
            "status",
            "teams",
            "team-breakdown",
            "blockers",
            "epics",
            "cves",
            "notes",
        }
        assert expected_commands == set(release.COMMANDS.keys())

    def test_all_slack_commands_mapped(self):
        expected = {
            "feature-freeze-update",
            "feature-freeze",
            "code-freeze-update",
            "code-freeze",
        }
        assert expected == set(release.SLACK_COMMANDS.keys())


# =========================================================================
# release.py — _find_parse_issues discovery
# =========================================================================


class TestFindParseIssues:
    def test_returns_path_or_none(self):
        result = release._find_parse_issues()
        assert result is None or isinstance(result, Path)

    def test_sibling_path_resolves(self):
        sibling = (
            Path(__file__).resolve().parent.parent.parent
            / "skills"
            / "rhdh-jira"
            / "scripts"
            / "parse_issues.py"
        )
        result = release._find_parse_issues()
        if sibling.exists():
            assert result is not None
            assert result.exists()


# =========================================================================
# release.py — schedule parsing (inlined from schedule.py)
# =========================================================================


class TestNormalizeTeamName:
    def test_strips_rhdh_prefix(self):
        assert release._normalize_team_name("RHDH AI") == "ai"

    def test_case_insensitive_prefix(self):
        assert release._normalize_team_name("rhdh Cope") == "cope"

    def test_no_prefix(self):
        assert release._normalize_team_name("AI") == "ai"

    def test_whitespace_stripped(self):
        assert release._normalize_team_name("  RHDH AI  ") == "ai"

    def test_exact_match_lowered(self):
        assert release._normalize_team_name("Cope") == "cope"


class TestNormalizeVersion:
    def test_simple_version(self):
        assert release._normalize_version("1.9.0") == "1.9"

    def test_rhdh_prefix(self):
        assert release._normalize_version("RHDH 1.6") == "1.6"

    def test_dash_prefix(self):
        assert release._normalize_version("rhdh-1.6") == "1.6"

    def test_v_prefix(self):
        assert release._normalize_version("v1.6") == "1.6"


class TestParseDate:
    def test_iso_format(self):
        assert release._parse_date("2025-06-15") == "2025-06-15"

    def test_us_format(self):
        assert release._parse_date("06/15/2025") == "2025-06-15"

    def test_long_format(self):
        assert release._parse_date("June 15, 2025") == "2025-06-15"

    def test_unparseable(self):
        assert release._parse_date("not a date") is None


class TestFindScheduleTab:
    def test_finds_current_year(self):
        from datetime import datetime

        year = str(datetime.now().year)
        tabs = [f"RHDH {year} schedule", "Other", "Archive"]
        assert release._find_schedule_tab(tabs) == f"RHDH {year} schedule"

    def test_fallback_to_schedule(self):
        tabs = ["Other", "Schedule", "Archive"]
        assert release._find_schedule_tab(tabs) == "Schedule"

    def test_no_match(self):
        tabs = ["Sheet1", "Sheet2"]
        assert release._find_schedule_tab(tabs) is None


class TestFindMilestones:
    def test_finds_ga_and_freezes(self):
        rows = [
            ["Date", "Event", "Version"],
            ["2025-05-01", "Feature Freeze", "RHDH 1.9"],
            ["2025-05-15", "Code Freeze", "RHDH 1.9"],
            ["2025-06-01", "GA Announce", "RHDH 1.9"],
        ]
        result = release._find_milestones(rows, "1.9")
        assert result.get("ga_date") == "2025-06-01"
        assert result.get("code_freeze") == "2025-05-15"
        assert result.get("feature_freeze") == "2025-05-01"

    def test_version_not_found(self):
        rows = [
            ["Date", "Event"],
            ["2025-06-01", "GA Announce RHDH 1.8"],
        ]
        assert release._find_milestones(rows, "2.0") == {}

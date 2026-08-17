"""Unit tests for the rhdh-test-plan schedule parser."""

import datetime as dt_module
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FETCH_SCHEDULE_SCRIPTS = PROJECT_ROOT / "skills" / "release" / "rhdh-test-plan-review" / "scripts"
if str(_FETCH_SCHEDULE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_FETCH_SCHEDULE_SCRIPTS))

import fetch_schedule as fs  # noqa: E402


def test_gog_sheets_adapter_uses_native_credential_boundary(monkeypatch):
    calls = []
    responses = iter(
        [
            {"sheets": [{"properties": {"title": "2026 Schedule / RHDH"}}]},
            [["RHDH 2.0 GA", "2026-08-10"]],
        ]
    )

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, json.dumps(next(responses)), "")

    monkeypatch.setattr(fs.subprocess, "run", fake_run)
    client = fs.SheetsClient("/tools/gog")

    tabs = fs.get_sheet_tabs(client, "sheet/id")
    rows = fs.get_sheet_values(client, "sheet/id", tabs[0])

    assert tabs == ["2026 Schedule / RHDH"]
    assert rows == [["RHDH 2.0 GA", "2026-08-10"]]
    assert calls[0][0] == ["/tools/gog", "sheets", "metadata", "sheet/id", "--json"]
    assert calls[1][0] == [
        "/tools/gog",
        "sheets",
        "get",
        "sheet/id",
        "2026 Schedule / RHDH",
        "--json",
        "--results-only",
    ]
    assert all(kwargs["shell"] is False for _, kwargs in calls)


def test_sheets_adapter_returns_a_structured_not_found_error(monkeypatch, capsys):
    def not_found(command, **_kwargs):
        return subprocess.CompletedProcess(command, 1, "", "spreadsheet not found")

    monkeypatch.setattr(fs.subprocess, "run", not_found)

    with pytest.raises(SystemExit) as raised:
        fs.get_sheet_tabs(fs.SheetsClient("/tools/gog"), "missing")

    assert raised.value.code == 1
    assert json.loads(capsys.readouterr().out)["error"] == "spreadsheet_not_found"


class TestNormalizeVersion:
    def test_plain_semver(self):
        assert fs.normalize_version("1.6") == "1.6"

    def test_rhdh_prefix_variants(self):
        assert fs.normalize_version("RHDH 1.6") == "1.6"
        assert fs.normalize_version("rhdh-1.6") == "1.6"

    def test_v_prefix(self):
        assert fs.normalize_version("v1.10") == "1.10"

    def test_double_digit_minor(self):
        assert fs.normalize_version("release-2.12-rc1") == "2.12"

    def test_no_digits_returns_stripped(self):
        assert fs.normalize_version("  upcoming  ") == "upcoming"


class TestParseDate:
    def test_iso(self):
        assert fs.parse_date("2025-03-15") == "2025-03-15"

    def test_us_slash(self):
        assert fs.parse_date("3/15/2025") == "2025-03-15"

    def test_long_month(self):
        assert fs.parse_date("March 15, 2025") == "2025-03-15"

    def test_short_month(self):
        assert fs.parse_date("Mar 15, 2025") == "2025-03-15"

    def test_two_digit_year(self):
        assert fs.parse_date("3/15/25") == "2025-03-15"

    def test_unparseable(self):
        assert fs.parse_date("TBD") is None

    def test_strips_whitespace(self):
        assert fs.parse_date("  2025-01-01  ") == "2025-01-01"


class TestRowDate:
    def test_first_parseable_wins(self):
        assert fs.row_date(["n/a", "2025-04-01", "2025-05-01"]) == "2025-04-01"

    def test_none_when_empty(self):
        assert fs.row_date([]) is None


def _fixed_clock(monkeypatch, year: int, month: int = 6, day: int = 1):
    """Replace fetch_schedule.datetime (Python 3.14+ blocks patching datetime.now on the class)."""

    class _Clock:
        strptime = staticmethod(dt_module.datetime.strptime)

        @staticmethod
        def now(tz=None):
            return dt_module.datetime(year, month, day)

    monkeypatch.setattr(fs, "datetime", _Clock)


class TestFindScheduleTab:
    def test_prefers_tab_matching_current_year(self, monkeypatch):
        _fixed_clock(monkeypatch, 2026)
        tabs = ["Notes", "2025 Schedule", "2026 Schedule Q1", "Other"]
        assert fs.find_schedule_tab(tabs) == "2026 Schedule Q1"

    def test_falls_forward_to_next_year(self, monkeypatch):
        _fixed_clock(monkeypatch, 2026)
        tabs = ["Notes", "2027 Release Schedule"]
        assert fs.find_schedule_tab(tabs) == "2027 Release Schedule"

    def test_then_previous_year(self, monkeypatch):
        _fixed_clock(monkeypatch, 2026)
        tabs = ["2025 schedule overview"]
        assert fs.find_schedule_tab(tabs) == "2025 schedule overview"

    def test_fallback_any_schedule_without_year_match(self, monkeypatch):
        _fixed_clock(monkeypatch, 2026)
        tabs = ["Foo", "Master Schedule"]
        assert fs.find_schedule_tab(tabs) == "Master Schedule"

    def test_returns_none_when_no_schedule(self, monkeypatch):
        _fixed_clock(monkeypatch, 2026)
        assert fs.find_schedule_tab(["Overview", "Archive"]) is None


class TestFindMilestones:
    def test_empty_rows(self):
        assert fs.find_milestones([], "1.6") == {}

    def test_no_ga_row(self):
        rows = [["Feature Freeze"], ["Code Freeze"], ["1.6 RC"]]
        assert fs.find_milestones(rows, "1.6") == {}

    def test_ga_only_with_date(self):
        rows = [["RHDH 1.6", "GA announce", "2025-08-01"]]
        assert fs.find_milestones(rows, "1.6") == {"ga_date": "2025-08-01"}

    def test_walks_backwards_for_freezes_before_ga(self):
        rows = [
            ["Feature Freeze", "2025-05-01"],
            ["Code Freeze", "2025-06-01"],
            ["RHDH 1.6", "GA date", "2025-08-15"],
        ]
        assert fs.find_milestones(rows, "1.6") == {
            "feature_freeze": "2025-05-01",
            "code_freeze": "2025-06-01",
            "ga_date": "2025-08-15",
        }

    def test_stops_at_prior_ga_row(self):
        """Walking upward stops at an earlier GA row so 1.5 freezes are not merged into 1.6."""
        rows = [
            ["Feature Freeze", "2024-12-01"],
            ["Code Freeze", "2024-11-01"],
            ["1.5", "GA", "2024-10-01"],
            ["Feature Freeze", "2025-05-01"],
            ["Code Freeze", "2025-06-01"],
            ["1.6", "GA announce", "2025-08-01"],
        ]
        out = fs.find_milestones(rows, "1.6")
        assert out == {
            "feature_freeze": "2025-05-01",
            "code_freeze": "2025-06-01",
            "ga_date": "2025-08-01",
        }

    def test_general_availability_keyword(self):
        rows = [
            ["Code freeze", "2025-02-10"],
            ["RHDH 1.7", "General Availability", "2025-04-20"],
        ]
        assert fs.find_milestones(rows, "1.7") == {
            "code_freeze": "2025-02-10",
            "ga_date": "2025-04-20",
        }

    def test_code_freeze_hyphenated(self):
        rows = [
            ["Code-freeze", "1/15/2025"],
            ["1.6", "GA ", "2025-03-01"],
        ]
        assert fs.find_milestones(rows, "1.6")["code_freeze"] == "2025-01-15"

    def test_feature_freeze_hyphenated(self):
        rows = [
            ["Feature-freeze", "Jan 10, 2025"],
            ["v1.6", "ga date", "2025-03-01"],
        ]
        assert fs.find_milestones(rows, "1.6")["feature_freeze"] == "2025-01-10"

    def test_ff_abbreviation_with_spaces(self):
        """Row text is space-padded; ' ff ' matches abbreviated freeze lines."""
        rows = [
            ["Milestone", " FF ", "2025-02-01"],
            ["1.6 GA", "2025-03-01"],
        ]
        assert fs.find_milestones(rows, "1.6")["feature_freeze"] == "2025-02-01"

    def test_first_ga_row_wins(self):
        rows = [
            ["1.6", "GA", "2025-01-01"],
            ["1.6", "GA", "2025-12-01"],
        ]
        assert fs.find_milestones(rows, "1.6")["ga_date"] == "2025-01-01"

    def test_ga_without_date_still_collects_freezes(self):
        rows = [
            ["Feature freeze", "2025-05-20"],
            ["Code freeze", "2025-06-20"],
            ["RHDH 1.6", "GA", "TBD"],
        ]
        out = fs.find_milestones(rows, "1.6")
        assert "ga_date" not in out
        assert out["feature_freeze"] == "2025-05-20"
        assert out["code_freeze"] == "2025-06-20"

    def test_version_match_via_stripped_rhdh(self):
        rows = [
            ["Code freeze", "2025-01-05"],
            ["RHDH 2.0", "GA ", "2025-02-01"],
        ]
        assert fs.find_milestones(rows, "RHDH 2.0")["code_freeze"] == "2025-01-05"

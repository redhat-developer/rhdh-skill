"""Parse Slack announcement templates from references/slack-templates.md.

Reads the markdown file at runtime so the CLI and agent share one source of truth.
Supports placeholder filling ({{RELEASE_VERSION}}, {{FEATURE_FREEZE_DATE}}, etc.)
and per-team line expansion.
"""

from __future__ import annotations

import re
from pathlib import Path

_REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"
_SLACK_FILE = _REFERENCES_DIR / "slack-templates.md"

TEMPLATE_KEYS = {
    "Feature Freeze Update": "feature_freeze_update",
    "Feature Freeze Announcement": "feature_freeze",
    "Code Freeze Update": "code_freeze_update",
    "Code Freeze Announcement": "code_freeze",
}

_TEMPLATE_CACHE: dict[str, str] | None = None


def _parse_slack_file(path: Path | None = None) -> dict[str, str]:
    """Parse ## headings and ```slack code blocks from slack-templates.md."""
    path = path or _SLACK_FILE
    text = path.read_text()
    templates: dict[str, str] = {}
    current_heading: str | None = None
    slack_lines: list[str] | None = None

    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+)$", line)
        if heading:
            current_heading = heading.group(1).strip()
            continue

        if current_heading and line.strip() == "```slack":
            slack_lines = []
            continue

        if slack_lines is not None and line.strip() == "```":
            key = TEMPLATE_KEYS.get(current_heading or "")
            if key:
                templates[key] = "\n".join(slack_lines)
            current_heading = None
            slack_lines = None
            continue

        if slack_lines is not None:
            slack_lines.append(line)

    return templates


def load_templates(path: Path | None = None) -> dict[str, str]:
    """Load and cache Slack templates from slack-templates.md."""
    global _TEMPLATE_CACHE
    if path is not None:
        return _parse_slack_file(path)
    if _TEMPLATE_CACHE is None:
        _TEMPLATE_CACHE = _parse_slack_file()
    return _TEMPLATE_CACHE


def get_template(name: str, path: Path | None = None) -> str:
    """Get a single Slack template by key name. Raises KeyError if not found."""
    templates = load_templates(path)
    if name not in templates:
        available = ", ".join(sorted(templates))
        raise KeyError(f"Unknown Slack template '{name}'. Available: {available}")
    return templates[name]


def fill_placeholders(template: str, values: dict[str, str]) -> str:
    """Replace {{PLACEHOLDER}} tokens with values from the dict."""
    result = template
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def expand_team_lines(
    template: str,
    teams: list[dict[str, str]],
) -> str:
    """Expand the per-team repeat block in a template.

    Looks for the pattern line containing {{TEAM_NAME}} and the
    "(repeat for each ...)" comment, replaces them with one line per team.
    """
    lines = template.splitlines()
    expanded: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "{{TEAM_NAME}}" in line:
            team_template = line
            if i + 1 < len(lines) and "repeat for each" in lines[i + 1].lower():
                i += 1
            for team in teams:
                team_line = team_template
                for key, value in team.items():
                    team_line = team_line.replace("{{" + key.upper() + "}}", value)
                expanded.append(team_line)
            i += 1
            continue
        expanded.append(line)
        i += 1
    return "\n".join(expanded)


def list_templates(path: Path | None = None) -> list[str]:
    """Return sorted list of available template keys."""
    return sorted(load_templates(path))

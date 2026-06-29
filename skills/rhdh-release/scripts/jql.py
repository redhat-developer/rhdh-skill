"""Parse JQL templates from references/jql-release.md.

Reads the markdown file at runtime so the CLI and agent share one source of truth.
Supports placeholder rendering ({{RELEASE_VERSION}}, {{ISSUE_TYPE}}) and
URL-encoded Jira search links.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

JIRA_SEARCH_BASE = "https://issues.redhat.com/issues/?jql="

_REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"
_JQL_FILE = _REFERENCES_DIR / "jql-release.md"

_TEMPLATE_CACHE: dict[str, str] | None = None


def _parse_jql_file(path: Path | None = None) -> dict[str, str]:
    """Parse ## headings and ```jql code blocks from jql-release.md."""
    path = path or _JQL_FILE
    text = path.read_text()
    templates: dict[str, str] = {}
    current_name: str | None = None
    jql_lines: list[str] | None = None

    for line in text.splitlines():
        heading = re.match(r"^##\s+(\S+)", line)
        if heading:
            current_name = heading.group(1)
            continue

        if current_name and line.strip() == "```jql":
            jql_lines = []
            continue

        if current_name and jql_lines is not None and line.strip() == "```":
            templates[current_name] = " ".join(jql_lines).strip()
            current_name = None
            jql_lines = None
            continue

        if jql_lines is not None:
            jql_lines.append(line.strip())

    return templates


def load_templates(path: Path | None = None) -> dict[str, str]:
    """Load and cache JQL templates from jql-release.md."""
    global _TEMPLATE_CACHE
    if path is not None:
        return _parse_jql_file(path)
    if _TEMPLATE_CACHE is None:
        _TEMPLATE_CACHE = _parse_jql_file()
    return _TEMPLATE_CACHE


def get_template(name: str, path: Path | None = None) -> str:
    """Get a single JQL template by name. Raises KeyError if not found."""
    templates = load_templates(path)
    if name not in templates:
        available = ", ".join(sorted(templates))
        raise KeyError(f"Unknown JQL template '{name}'. Available: {available}")
    return templates[name]


def render(
    name: str,
    *,
    version: str | None = None,
    issue_type: str | None = None,
    path: Path | None = None,
) -> str:
    """Render a JQL template with placeholder substitution."""
    jql = get_template(name, path)
    if version is not None:
        jql = jql.replace("{{RELEASE_VERSION}}", version)
    if issue_type is not None:
        jql = jql.replace("{{ISSUE_TYPE}}", issue_type)
    return jql


def jira_url(jql: str) -> str:
    """Build a Jira search URL from a JQL string."""
    return JIRA_SEARCH_BASE + quote(jql, safe="")


def render_with_url(
    name: str,
    *,
    version: str | None = None,
    issue_type: str | None = None,
    path: Path | None = None,
) -> tuple[str, str]:
    """Render a JQL template and return (jql, jira_url)."""
    jql = render(name, version=version, issue_type=issue_type, path=path)
    return jql, jira_url(jql)


def list_templates(path: Path | None = None) -> list[str]:
    """Return sorted list of available template names."""
    return sorted(load_templates(path))

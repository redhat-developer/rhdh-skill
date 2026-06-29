# Release CLI — Structural Demo

Structural verification of the release CLI — confirms scripts exist, no symlinks remain, CLI parses, JQL templates load, and Slack templates parse. No live Jira or Google credentials required.

## Check 9: Script files (no symlinks)

```bash
test -f scripts/formatters.py && test ! -L scripts/formatters.py && echo '✓ scripts/formatters.py is a regular file' || echo '✗ scripts/formatters.py missing or is a symlink'
```

```output
✓ scripts/formatters.py is a regular file
```

```bash
symlinks=$(find scripts/ -type l 2>/dev/null); test -z "$symlinks" && echo '✓ No symlinks in scripts/' || echo "✗ Symlinks found: $symlinks"
```

```output
✓ No symlinks in scripts/
```

## Check 10: Release CLI existence

```bash
test -f scripts/release.py && test -x scripts/release.py && echo '✓ scripts/release.py exists and is executable' || echo '✗ scripts/release.py missing or not executable'
```

```output
✓ scripts/release.py exists and is executable
```

```bash
test -f scripts/jql.py && echo '✓ scripts/jql.py' || echo '✗ scripts/jql.py missing'; test -f scripts/slack_templates.py && echo '✓ scripts/slack_templates.py' || echo '✗ scripts/slack_templates.py missing'
```

```output
✓ scripts/jql.py
✓ scripts/slack_templates.py
```

```bash
python scripts/release.py --help
```

```output
usage: release [-h] [--json] [--human] [--verbose]
               {check,dates,future-dates,status,teams,team-breakdown,blockers,epics,cves,notes,slack}
               ...

RHDH Release CLI — deterministic data gathering for release management.

positional arguments:
  {check,dates,future-dates,status,teams,team-breakdown,blockers,epics,cves,notes,slack}
    check               Verify prerequisites
    dates               Active release dates from Jira
    future-dates        Schedule from Google Sheets
    status              Issue counts by type
    teams               Team mapping from Google Sheets
    team-breakdown      Per-team issue counts
    blockers            Blocker bug details
    epics               Outstanding EPICs
    cves                CVE list
    notes               Missing release notes count
    slack               Slack announcement templates

options:
  -h, --help            show this help message and exit
  --json
  --human
  --verbose, -v
```

```bash
python scripts/release.py slack --help
```

```output
usage: release slack [-h]
                     {feature-freeze-update,feature-freeze,code-freeze-update,code-freeze}
                     ...

positional arguments:
  {feature-freeze-update,feature-freeze,code-freeze-update,code-freeze}
    feature-freeze-update
                        Feature Freeze status update
    feature-freeze      Feature Freeze announcement
    code-freeze-update  Code Freeze status update
    code-freeze         Code Freeze announcement

options:
  -h, --help            show this help message and exit
```

## JQL template parsing

Verify that jql.py parses all 13 templates from `references/jql-release.md` and renders them with placeholders.

```python3
import sys; sys.path.insert(0, 'scripts')
import jql
templates = jql.list_templates()
print(f'Templates loaded: {len(templates)}')
for name in templates:
    print(f'  {name}')

```

```output
Templates loaded: 13
  active_release
  blockers
  code_freeze_issues
  cves
  epics
  feature_demos
  feature_freeze_issues
  feature_subtasks
  features_added_to_release
  open_issues
  open_issues_by_type
  release_notes
  test_day_features
```

```python3
import sys; sys.path.insert(0, 'scripts')
import jql
rendered, url = jql.render_with_url('open_issues', version='1.9.0')
print(f'JQL: {rendered}')
print(f'URL: {url}')

```

```output
JQL: project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "1.9.0" and status != closed
URL: https://issues.redhat.com/issues/?jql=project%20IN%20%28RHIDP%2C%20RHDHBugs%2C%20RHDHPLAN%2C%20RHDHSUPP%29%20AND%20fixVersion%20%3D%20%221.9.0%22%20and%20status%20%21%3D%20closed
```

## Slack template parsing

Verify that slack_templates.py parses all 4 templates from `references/slack-templates.md` and fills placeholders.

```python3
import sys; sys.path.insert(0, 'scripts')
import slack_templates as st
templates = st.list_templates()
print(f'Templates loaded: {len(templates)}')
for name in templates:
    print(f'  {name}')

```

```output
Templates loaded: 4
  code_freeze
  code_freeze_update
  feature_freeze
  feature_freeze_update
```

```python3
import sys; sys.path.insert(0, 'scripts')
import slack_templates as st
template = st.get_template('feature_freeze')
filled = st.fill_placeholders(template, {
    'RELEASE_VERSION': '1.9.0',
    'EPIC_ISSUE_COUNT': '5',
    'CVE_ISSUE_COUNT': '3',
    'OUTSTANDING_RELEASE_NOTES_ISSUE_COUNT': '12',
})
# Show first 3 lines
for line in filled.splitlines()[:3]:
    print(line)
print('...')
remaining = [p for p in ['EPIC_ISSUE_COUNT', 'CVE_ISSUE_COUNT', 'OUTSTANDING_RELEASE_NOTES_ISSUE_COUNT', 'RELEASE_VERSION'] if '{{' + p + '}}' in filled]
print(f'Unfilled placeholders: {remaining if remaining else "none"}')

```

```output
:rotating_light: *RHDH 1.9.0 [Feature Freeze](https://docs.google.com/document/d/1IjMH985f3XUhXl_6drfUKopLxTBoY0VMJ2Zpr_62K2g/edit?tab=t.0#bookmark=id.5a1n60q199qh)* :rotating_light:

Its Feature Freeze! To see the latest status use the [RHDH Release Tracking dashboard](https://issues.redhat.com/secure/Dashboard.jspa?selectPageId=12363303) and set fixversion to the current release.
...
Unfilled placeholders: none
```

## Unit tests

```bash
uv run pytest ../../tests/unit/test_release_cli.py --tb=short -q 2>&1
```

```output
....................................                                    [100%]
36 passed in 0.06s
```

## Workflow CLI integration

Verify all 13 workflows have been updated with CLI-first Step 1.

```bash
total=$(ls workflows/*.md | wc -l | tr -d ' '); with_cli=$(grep -l 'Step 1: Run CLI' workflows/*.md | wc -l | tr -d ' '); echo "Workflows with CLI step: $with_cli/$total"
```

```output
Workflows with CLI step: 13/13
```

```bash
grep -h 'release.py' workflows/*.md | sed 's/^[ ]*//' | sort -u
```

```output
python scripts/release.py --json blockers {{RELEASE_VERSION}}
python scripts/release.py --json cves {{RELEASE_VERSION}}
python scripts/release.py --json dates
python scripts/release.py --json epics {{RELEASE_VERSION}}
python scripts/release.py --json future-dates {{RELEASE_VERSION}}
python scripts/release.py --json notes {{RELEASE_VERSION}}
python scripts/release.py --json slack code-freeze {{RELEASE_VERSION}}
python scripts/release.py --json slack code-freeze-update {{RELEASE_VERSION}}
python scripts/release.py --json slack feature-freeze {{RELEASE_VERSION}}
python scripts/release.py --json slack feature-freeze-update {{RELEASE_VERSION}}
python scripts/release.py --json status {{RELEASE_VERSION}}
python scripts/release.py --json team-breakdown {{RELEASE_VERSION}}
python scripts/release.py --json teams
python scripts/release.py --json teams --category Engineering
```

---
name: rhdh-release
description: |
  Manages RHDH releases — dates, status tracking, team coordination,
  freeze announcements, blocker bugs, CVEs, and release notes. Trigger on
  "release dates", "release status", "feature freeze", "code freeze",
  "blocker bugs", "CVEs", "release notes", "team breakdown", or any
  RHDH release management question.
compatibility: "acli on PATH. Python 3 + gog CLI for Google Sheets/Docs."
---

<essential_principles>

<principle name="use_parse_issues_for_team_counts">
Always use `parse_issues.py --enrich` for team counts — never count manually. The Team custom field cannot be queried via JQL. Use `acli jira workitem search --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich` and filter by team in the output.
</principle>

<principle name="include_jira_links">
Include Jira search links for traceability in all outputs. Build links by URL-encoding the JQL: `https://issues.redhat.com/issues/?jql=<URL_ENCODED_JQL>`.
</principle>

<principle name="slack_code_blocks">
Always wrap Slack messages in triple-backtick code blocks (` ```slack `) for easy copy-paste. Tell the user they can copy-paste this directly into Slack.
</principle>

<principle name="risk_identification">
When analyzing release health, check these risk indicators:
1. Blocker bugs near freeze dates — query with `priority = Blocker`
2. High open issue count per team — use team breakdown to identify overloaded teams
3. Missing release notes — query issues with empty Release Note Type
4. Critical CVEs — query vulnerabilities with CVE in summary
5. EPICs not in Dev Complete — check epic status

Always provide: specific issue counts with Jira links, team-level breakdown if applicable, actionable recommendations (retriage, escalate, extend timeline), and impact assessment.
</principle>

<principle name="team_coordination">
For team coordination:
1. Retrieve team info from Google Sheets to get leads and Slack handles
2. Include team leads' Slack handles in all team communications
3. Provide Jira links scoped to each team's issues
4. Highlight teams at risk (high open counts, blockers)
5. Suggest follow-up actions per team
</principle>

<principle name="token_safety">
Never read `.jira-token` into context. Always use shell substitution: `"$(cat "$TOKEN_FILE")"`.
</principle>

</essential_principles>

<intake>

## RHDH Release Management

What would you like to do?

### Release Information

1. **Release dates** — Current release dates and key milestones
2. **Future release dates** — Upcoming release dates from schedule spreadsheet
3. **Release status** — Active release status by issue type
4. **Teams** — Teams and leads directory

### Release Tracking

5. **Team breakdown** — Issues by engineering team for a release
6. **Blocker bugs** — Open blocker bugs for a release
7. **EPICs** — Engineering EPICs not yet complete
8. **CVEs** — CVE/vulnerability list for a release
9. **Release notes** — Outstanding release notes (missing Release Note Type)

### Announcements

10. **Feature Freeze update** — Generate Feature Freeze status update for Slack
11. **Feature Freeze announcement** — Generate Feature Freeze milestone announcement
12. **Code Freeze update** — Generate Code Freeze status update for Slack
13. **Code Freeze announcement** — Generate Code Freeze milestone announcement

**Wait for response before proceeding.**

</intake>

<routing>

**Preferred:** Run the `release` CLI first (`python scripts/release.py --json <command>`). If the CLI fails, fall back to the workflow's manual steps.

| Response | CLI Command | Workflow (fallback) |
|----------|-------------|---------------------|
| 1, "release dates", "key dates", "freeze dates", "milestone dates" | `python scripts/release.py --json dates` | `workflows/release-dates.md` |
| 2, "future releases", "upcoming releases", "release roadmap", "future dates" | `python scripts/release.py --json future-dates VERSION` | `workflows/future-release-dates.md` |
| 3, "release status", "active releases", "release health", "release overview" | `python scripts/release.py --json status VERSION` | `workflows/release-status.md` |
| 4, "teams", "team leads", "team list", "team contacts", "team directory" | `python scripts/release.py --json teams` | `workflows/teams-and-leads.md` |
| 5, "team breakdown", "issues by team", "team workload", "team counts" | `python scripts/release.py --json team-breakdown VERSION` | `workflows/issues-by-team.md` |
| 6, "blocker bugs", "blockers", "critical issues", "blocking issues" | `python scripts/release.py --json blockers VERSION` | `workflows/blocker-bugs.md` |
| 7, "epics", "engineering epics", "open epics", "active epics" | `python scripts/release.py --json epics VERSION` | `workflows/engineering-epics.md` |
| 8, "cves", "vulnerabilities", "security issues", "security bugs" | `python scripts/release.py --json cves VERSION` | `workflows/cves.md` |
| 9, "release notes", "missing release notes", "release note gaps" | `python scripts/release.py --json notes VERSION` | `workflows/release-notes.md` |
| 10, "feature freeze update", "feature freeze status", "feature freeze progress" | `python scripts/release.py --json slack feature-freeze-update VERSION` | `workflows/announce-feature-freeze-update.md` |
| 11, "feature freeze announcement", "announce feature freeze", "feature freeze reached" | `python scripts/release.py --json slack feature-freeze VERSION` | `workflows/announce-feature-freeze.md` |
| 12, "code freeze update", "code freeze status", "code freeze progress" | `python scripts/release.py --json slack code-freeze-update VERSION` | `workflows/announce-code-freeze-update.md` |
| 13, "code freeze announcement", "announce code freeze", "code freeze reached" | `python scripts/release.py --json slack code-freeze VERSION` | `workflows/announce-code-freeze.md` |

</routing>

<reference_index>

| Reference | Purpose | Load when |
|-----------|---------|-----------|
| `references/jql-release.md` | 13 release-specific JQL templates | Any Jira query for release data |
| `references/slack-templates.md` | 4 Slack announcement templates | Generating freeze announcements |
| `references/config.md` | GDrive IDs, project keys, dashboards, gog setup | Looking up config values or links |
| `gog docs cat 13OkypJ3u_7Jq6kEhKhjEFwHQ12oPFDKXVzFjYW4XLdk` | Release process (live Google Doc) | Release process questions, onboarding |
| `../../rhdh-jira/references/auth.md` | Jira auth setup | Jira prerequisite fails |
| `../../rhdh-jira/references/acli-commands.md` | acli command reference | Building acli commands |

</reference_index>

<prerequisites>

**Run before any workflow:**

| Requirement | Check | Fix |
|-------------|-------|-----|
| **Jira CLI** | `acli jira workitem search --jql "project=RHIDP" --count` succeeds | Load `../../rhdh-jira/SKILL.md` Prerequisites |
| **gog CLI** (for Google Sheets/Docs) | `gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json` succeeds | Install gog and run `gog auth add <email>` |

</prerequisites>

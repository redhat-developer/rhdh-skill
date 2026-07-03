# JQL Release Queries

Release-specific JQL templates for RHDH release management. All queries tested against `redhat.atlassian.net`.

For general Jira queries, boards, and sprints, see `../../rhdh-jira/references/jql-patterns.md`.

## active_release

Find all active release features in RHDHPlan.

```jql
project=rhdhplan AND issuetype=feature AND component=release AND status != closed
```

- **Placeholders:** none
- **Notes:** Returns release tracking issues with key dates in description. Use `acli jira workitem view KEY --json` on each result to extract dates.

## open_issues

Find all open issues for a specific release version.

```jql
project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" and status != closed
```

- **Placeholders:** `{{RELEASE_VERSION}}` — e.g., `1.9.0`
- **Example:** `... AND fixVersion = "1.9.0" and status != closed`
- **Notes:** Base query for all open issues in a release.

## open_issues_by_type

Find open issues for a release filtered by issue type.

```jql
project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = "{{ISSUE_TYPE}}"
```

- **Placeholders:** `{{RELEASE_VERSION}}`, `{{ISSUE_TYPE}}`
- **Example:** `... AND fixVersion = "1.9.0" AND status != closed AND issuetype = "Bug"`
- **Notes:** Valid issue types: Feature, Epic, Story, Task, Sub-task, Bug, Vulnerability, Weakness.

## epics

Find open EPICs not in Dev Complete or Release Pending.

```jql
project IN (RHIDP) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype = epic and status not in (closed, "Release Pending", "Dev Complete")
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Example:** `... AND fixVersion = "1.9.0" and issuetype = epic and status not in (closed, "Release Pending", "Dev Complete")`
- **Notes:** Identifies EPICs that need attention before release.

## cves

Find all CVE issues (vulnerabilities and weaknesses).

```jql
project IN (RHIDP, rhdhbugs) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype in (weakness, Vulnerability, bug) and summary ~ "CVE*"
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Example:** `... AND fixVersion = "1.9.0" and issuetype in (weakness, Vulnerability, bug) and summary ~ "CVE*"`
- **Notes:** Critical for security tracking before release.

## feature_demos

Find features tagged for demonstration.

```jql
project in (RHDHPlan, RHIDP) AND issuetype = feature AND labels = demo AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Example:** `... AND labels = demo AND fixVersion = "1.9.0" AND status != closed`
- **Notes:** Features that need demo preparation.

## feature_subtasks

Find feature subtasks for acceptance criteria verification.

```jql
project in (RHDHPlan) AND issuetype = sub-task AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Example:** `... AND fixVersion = "1.9.0" AND status != closed`
- **Notes:** Tracks feature verification and demo creation tasks.

## test_day_features

Find features designated for Test Day.

```jql
Project in (RHDHPlan, rhidp) AND issuetype = feature AND labels = rhdh-testday AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Example:** `... AND labels = rhdh-testday AND fixVersion = "1.9.0" AND status != closed`
- **Notes:** Features ready for Test Day validation.

## features_added_to_release

Find features added to release in last 14 days.

```jql
project in (RHDHPlan, rhidp) AND issuetype = feature AND fixVersion = "{{RELEASE_VERSION}}" AND fixversion changed after -14d
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Example:** `... AND fixVersion = "1.9.0" AND fixversion changed after -14d`
- **Notes:** Tracks scope changes to release.

## release_notes

Find issues missing Release Note Type field.

```jql
project in (RHIDP, "Red Hat Developer Hub Bugs", "RHDH Support", rhdhplan) and issuetype in (Feature, bug) and ("Release Note Type" not in ("Release Note Not Required") or "release note type" is empty) and ("Release Note Status" not in ("In Progress", Proposed, Done) or "Release Note Text[Paragraph]" is empty or "Release Note Type[Dropdown]" is empty) and summary !~ "CVE-*" and (resolution not in (obsolete, duplicate, "Won't Do") or resolution is empty) and fixVersion = "{{RELEASE_VERSION}}"
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Example:** `... AND "Release Note Type" is EMPTY and fixVersion = "1.9.0"`
- **Notes:** Critical for documentation — must be filled before release.

## blockers

Find open blocker bugs for a release.

```jql
project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = bug AND priority = Blocker
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Example:** `... AND fixVersion = "1.9.0" AND status != closed AND issuetype = bug AND priority = Blocker`
- **Notes:** Critical path items that must be resolved before release.

## feature_freeze_issues

Find feature work outstanding at Feature Freeze.

```jql
project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" and resolution is EMPTY AND component not in ("AEM Migration", AI, "AI Demo", Conference, Build, Certification, "Continuous Improvement", Documentation, JTBD, Knowledge, Performance, Quality, Quickstart, Release, "RHDH Local", "RHDH Plugin Repo", Security, "Security Tooling", Segment, Serviceability, Support, "Team Operations", "Test Framework", "Test Infrastructure", "Upstream & Community", UX) AND Type not in (Bug, Vulnerability, sub-task) AND status not in ("Dev Complete", "Release Pending", Done, Closed) AND (labels is EMPTY OR labels != stretch-goal)
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Notes:** Excludes infrastructure/ops components and bugs. Use for Feature Freeze announcements. The component exclusion list filters out non-feature work that shouldn't block Feature Freeze.

## code_freeze_issues

Find all issues outstanding at Code Freeze.

```jql
project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype in (bug, Story, task, Vulnerability) AND status not in ("Release Pending", Closed) AND component not in ("AEM Migration", AI, "AI Demo", Conference, Documentation, JTBD, Knowledge, Performance, Release, "RHDH Plugin Repo", Security, "Security Tooling", Support, "Team Operations", "Upstream & Community") OR issuetype in (feature) AND status not in ("Release Pending", Closed) AND component not in ("AEM Migration", AI, "AI Demo", Conference, Documentation, JTBD, Knowledge, Performance, Release, "RHDH Plugin Repo", Security, "Security Tooling", Support, "Team Operations", "Upstream & Community") OR issuetype in (epic) AND status not in ("Dev Complete", "Release Pending", Closed) AND component not in ("AEM Migration", AI, "AI Demo", Conference, Documentation, JTBD, Knowledge, Performance, Release, "RHDH Plugin Repo", Security, "Security Tooling", Support, "Team Operations", "Upstream & Community")
```

- **Placeholders:** `{{RELEASE_VERSION}}`
- **Notes:** All open work. Same as `open_issues` — used for Code Freeze announcements.

## open_issues_by_team

Find all open issues for a release filtered by team using Cloud ID.

```jql
project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND "Team[Team]" = "{{CLOUD_ID}}"
```

- **Placeholders:** `{{RELEASE_VERSION}}`, `{{CLOUD_ID}}`
- **Example:** `... AND fixVersion = "2.1.0" AND status != closed AND "Team[Team]" = "ec74d716-af36-4b3c-950f-f79213d08f71-4403"`
- **Notes:** Cloud ID is the Jira Cloud team identifier from the RHDH Team Mapping spreadsheet (column "Cloud ID"). This is the fastest way to filter by team — no enrichment needed.

## feature_freeze_issues_by_team

Find feature work outstanding at Feature Freeze filtered by team.

```jql
project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" and resolution is EMPTY AND component not in ("AEM Migration", AI, "AI Demo", Conference, Build, Certification, "Continuous Improvement", Documentation, JTBD, Knowledge, Performance, Quality, Quickstart, Release, "RHDH Local", "RHDH Plugin Repo", Security, "Security Tooling", Segment, Serviceability, Support, "Team Operations", "Test Framework", "Test Infrastructure", "Upstream & Community", UX) AND Type not in (Bug, Vulnerability, sub-task) AND status not in ("Dev Complete", "Release Pending", Done, Closed) AND (labels is EMPTY OR labels != stretch-goal) AND "Team[Team]" = "{{CLOUD_ID}}"
```

- **Placeholders:** `{{RELEASE_VERSION}}`, `{{CLOUD_ID}}`
- **Notes:** Same as `code_freeze_issues` but scoped to a single team by Cloud ID.

## code_freeze_issues_by_team

Find all issues outstanding at Code Freeze filtered by team.

```jql
project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype in (bug, Story, task, Vulnerability) AND status not in ("Release Pending", Closed) AND component not in ("AEM Migration", AI, "AI Demo", Conference, Documentation, JTBD, Knowledge, Performance, Release, "RHDH Plugin Repo", Security, "Security Tooling", Support, "Team Operations", "Upstream & Community") OR issuetype in (feature) AND status not in ("Release Pending", Closed) AND component not in ("AEM Migration", AI, "AI Demo", Conference, Documentation, JTBD, Knowledge, Performance, Release, "RHDH Plugin Repo", Security, "Security Tooling", Support, "Team Operations", "Upstream & Community") OR issuetype in (epic) AND status not in ("Dev Complete", "Release Pending", Closed) AND component not in ("AEM Migration", AI, "AI Demo", Conference, Documentation, JTBD, Knowledge, Performance, Release, "RHDH Plugin Repo", Security, "Security Tooling", Support, "Team Operations", "Upstream & Community") AND "Team[Team]" = "{{CLOUD_ID}}"
```

- **Placeholders:** `{{RELEASE_VERSION}}`, `{{CLOUD_ID}}`
- **Notes:** Same as `code_freeze_issues` but scoped to a single team by Cloud ID.

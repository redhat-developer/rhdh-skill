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

- **Source:** Rich Filter — "demo" static filter
- **Placeholders:** `{{RELEASE_VERSION}}`
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

- **Source:** Rich Filter — "Test Day" static filter
- **Placeholders:** `{{RELEASE_VERSION}}`
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

- **Source:** Rich Filter — "RNs Unclassified" rich queue
- **Placeholders:** `{{RELEASE_VERSION}}`
- **Notes:** Critical for documentation — must be filled before release.

## release_notes_proposed

Find issues with proposed or in-progress release notes and non-empty text.

- **Source:** Rich Filter — "RNs Proposed" rich queue
- **Placeholders:** `{{RELEASE_VERSION}}`

## release_notes_done

Find issues with completed release notes and non-empty text.

- **Source:** Rich Filter — "RNs Done" rich queue
- **Placeholders:** `{{RELEASE_VERSION}}`

## release_notes_with_text

Find release-scoped issues that have release-note text.

- **Source:** Rich Filter — "Has RN Text" rich queue
- **Placeholders:** `{{RELEASE_VERSION}}`

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

- **Source:** Rich Filter — "Feature Freeze" static filter
- **Placeholders:** `{{RELEASE_VERSION}}`
- **Notes:** Excludes infrastructure/ops components and bugs. Use for Feature Freeze announcements.

## code_freeze_issues

Find all issues outstanding at Code Freeze.

- **Source:** Rich Filter — "Code Freeze" static filter
- **Placeholders:** `{{RELEASE_VERSION}}`
- **Notes:** All open work scoped to the release. Use for Code Freeze announcements.

## post_code_freeze_issues

Find release-scoped work requiring attention after Code Freeze.

- **Source:** Rich Filter — "Post Code Freeze" static filter
- **Placeholders:** `{{RELEASE_VERSION}}`

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

- **Source:** Rich Filter — "Feature Freeze" static filter + Cloud ID
- **Placeholders:** `{{RELEASE_VERSION}}`, `{{CLOUD_ID}}`
- **Notes:** Same as `feature_freeze_issues` but scoped to a single team by Cloud ID.

## code_freeze_issues_by_team

Find all issues outstanding at Code Freeze filtered by team.

- **Source:** Rich Filter — "Code Freeze" static filter + Cloud ID
- **Placeholders:** `{{RELEASE_VERSION}}`, `{{CLOUD_ID}}`
- **Notes:** Same as `code_freeze_issues` but scoped to a single team by Cloud ID.

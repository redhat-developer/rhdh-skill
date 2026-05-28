---
name: rhdh-jira
description: |
  Interacts with RHDH Jira projects (RHIDP, RHDHPLAN, RHDHBUGS, RHDHSUPP) using acli, GraphQL, and REST API. Covers the full Jira lifecycle: create issues, assign, refine, plan sprints, report, track releases, and update status. Trigger on Jira keys (RHIDP-1234), "create a feature/epic/story/task/bug", "who should take this", "refine this", "plan the sprint", "sprint report", "release status", "update jira", or any sprint ceremony prep.
compatibility: "acli (Atlassian CLI) on PATH. Python 3 for scripts. Windows, macOS, Linux."
---

<essential_principles>

# RHDH Jira

Foundational skill for interacting with RHDH's Jira instance via the Atlassian CLI (`acli`). Covers all four active projects, issue types, workflows, custom fields, and JQL patterns.

</essential_principles>

<intake>

## Commands

| Command | Description | Reference |
|---------|-------------|-----------|
| `assign [issue key(s) or JQL]` | Recommend and assign team members using expertise, capacity, and context proximity analysis | [references/assign.md](references/assign.md) |
| `refine [issue key(s), JQL, or 'sprint']` | Check issues against exit criteria, identify duplicates, missing fields, unaddressed comments, and readiness | [references/refine.md](references/refine.md) |
| `plan [team]` | Sprint planning prep: carryover, velocity, capacity, ready queue, sprint fill suggestions | [references/plan.md](references/plan.md) |
| `sprint-report [team]` | Sprint review summary: committed vs completed, per-member breakdown, demo checklist | [references/sprint-report.md](references/sprint-report.md) |
| `release [version]` | Release readiness: feature matrix, PI funnel, dependency map, blocker bugs, risk assessment | [references/release.md](references/release.md) |
| `to-feature [description]` | Create a RHDHPLAN Feature with grill, duplicate check, and optional Epic decomposition | [references/to-feature.md](references/to-feature.md) |
| `to-epic [description]` | Create an RHIDP Epic with grill, duplicate check, and optional Story/Task decomposition | [references/to-epic.md](references/to-epic.md) |
| `to-issue [description]` | Create a Story, Task, Bug, or Spike with automatic type inference and grill | [references/to-issue.md](references/to-issue.md) |
| `update-jira-status [key]` | Update issue with session progress, status comment, transition, and upward cascade | [references/update-jira-status.md](references/update-jira-status.md) |

Single source of truth for command descriptions: `scripts/command-metadata.json`

**Wait for response before proceeding.**

</intake>

<routing>

### Routing rules

1. **No argument**: Show the command menu. Ask what to do.
2. **First word matches a command**: Load its reference file and follow it.
3. **First word doesn't match**: General Jira invocation using the full argument as context — use the reference files table below to decide what to load.

</routing>

## Prerequisites

Run `scripts/setup.py` to verify everything is configured:

```bash
python scripts/setup.py
```

The script checks:

1. `acli` binary on PATH
2. Jira API token auth configured (`~/.config/acli/jira_config.yaml`)
3. `.jira-token` file next to `acli` executable (for REST API fallback)
4. Smoke test against `redhat.atlassian.net`

If `acli` is not installed, download from [Atlassian CLI](https://developer.atlassian.com/cloud/acli/) and follow the [Getting Started guide](https://developer.atlassian.com/cloud/acli/guides/how-to-get-started/) for installation and authentication setup. Use API token authentication, not OAuth — OAuth sessions expire and `acli auth status` gives false negatives with token auth (see Gotchas).

### API preference order

All operations follow this priority: **acli → GraphQL → REST API**.

- **acli** — default for simple, single-issue operations (view, edit, assign, transition).
- **GraphQL** — for bulk reads where acli would be too slow (expertise profiles, capacity, refinement checks). Skip acli entirely for bulk.
- **REST API** — for writes when already in an authenticated API context (avoids shelling out to acli mid-workflow), or as fallback when acli fails for custom field updates.

Sub-commands (`assign`, `refine`) document which API they use. When a sub-command's workflow already has `AUTH` set from GraphQL reads, prefer REST for writes.

### REST/GraphQL capability gate

Before attempting any REST API or GraphQL call:

1. Run `python scripts/setup.py --json` and check `token_file_found`
2. If missing, state: "REST API/GraphQL fallback unavailable — `.jira-token` not configured. Run `setup.py` for instructions." Continue with acli-only workflow.
3. If the user needs REST/GraphQL, load `references/auth.md` for setup instructions

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup.py` | Verify acli install + auth. Run with `--json` for structured output. |
| `scripts/parse_issues.py` | Flatten, enrich, and filter acli JSON output. Solves the core problem: `acli search --json` can't return custom fields (team, story points, sprint). Pipe search results in, get clean data out. Use `--enrich` to fetch full fields, `-f team="X"` to filter by team. |
| `scripts/command-metadata.json` | Single source of truth for sub-command descriptions and argument hints. |
| `scripts/validate_components.py` | Validate `references/fields.md` component catalog against live Jira projects (RHIDP + RHDHPLAN). Reports drift in both directions. Run with `--json` for structured output. |
| `scripts/jira-wiki-to-adf.py` | Convert a filled Jira wiki markup template to Atlassian Document Format JSON for use with `acli --description-file`. Handles `hN.` headings, `* ` bullets, `# ` ordered lists, `(?)` / `(/)` task items, `*bold*`, `_italic_`, `{{monospace}}`, backtick code. Usage: `python scripts/jira-wiki-to-adf.py input.txt > output.adf.json` |

## Projects

| Key | Purpose | Issue Types |
|-----|---------|-------------|
| RHIDP | Engineering work | Epic, Story, Task, Sub-task, Vulnerability |
| RHDHPLAN | Program planning | Feature, Outcome, Feature Request, Sub-task |
| RHDHBUGS | Product defects | Bug, Sub-task |
| RHDHSUPP | Support-engineering interactions | Bug |

RHDHPAI (Plugins and AI) is **archived** — JQL queries against it will fail.

### Issue type selection

- **Story** — end-user facing work (API, UI changes)
- **Task** — not end-user facing (tests, CI/CD, refactoring, code organization)
- **Epic** — collection of Stories/Tasks toward a deliverable
- **Feature** — program-level planning item in RHDHPLAN
- **Bug** — product defect (RHDHBUGS) or support case tracking (RHDHSUPP)
- **Sub-task** — child of any issue type above
- **Vulnerability** — CVE tracking in RHIDP (Product Security)

<reference_index>

## Reference Files

Load only what the current task requires.

| File | Load when... |
|------|-------------|
| `references/acli-commands.md` | Running an acli command you haven't used before, or hitting unexpected flag behavior. Quick reference for syntax, flag differences, and output formats. |
| `references/fields.md` | Need to know a field name, custom field ID, accepted values, or label conventions. Custom fields, labels, link types, components, priorities. |
| `references/workflows.md` | Transitioning issues, checking exit criteria, or verifying readiness for the next status. |
| `references/templates.md` | Creating new issues. Also load `references/workflows.md` for required fields at entry status. |
| `references/support.md` | Handling support cases, filing bugs from customer cases, or creating feature requests from support. Full RHDHSUPP workflow, SLA, and anti-patterns. |
| `references/feature-exploration.md` | Feature Exploration Process checklist: component validation, labels (demo, rhdh-testday), Doc Epic automation, cross-team dependencies, rescoping. Load when creating Features, refining Features, or checking Feature readiness. |
| `references/jql-patterns.md` | Building a JQL query, finding a board ID, or looking up sprint information. JQL cookbook with 23+ tested queries. |
| `references/auth.md` | Setting up authentication for REST API or GraphQL calls. Token file format, path discovery, security, instance config, common auth errors. |
| `references/rest-api-fallback.md` | `acli` failed to update a custom field (Team, Size, Story Points, Release Note Type). Curl examples, response handling, OpenAPI spec discovery. |
| `references/graphql-queries.md` | Complex read queries needing multiple fields, relationships, or custom field data in one call. Schema introspection, JQL search via GraphQL, field type fragments. Also for bulk operations where acli would be too slow. |
| `references/assign.md` | Recommending assignees for unassigned issues. Team roster lookup, expertise profiling, sprint capacity analysis, context proximity scoring. Also for applying assignments after user confirmation. |
| `references/refine.md` | Checking issues against exit criteria per status, identifying duplicates, missing fields, unaddressed comments, and readiness for the next workflow status. |
| `references/plan.md` | Sprint planning prep: carryover report, velocity trend, per-member capacity, ready-for-planning queue, sprint fill suggestions. |
| `references/sprint-report.md` | Sprint review summary: committed vs completed, per-member breakdown, epic progress, demo checklist with naming conventions, velocity trend. |
| `references/release.md` | Release readiness report: feature matrix, PI funnel states, epic roll-up, cross-team dependency map, blocker bugs, RN readiness, risk assessment. |
| `references/to-feature.md` | Create a RHDHPLAN Feature from conversation context with grill and optional Epic decomposition. |
| `references/to-epic.md` | Create an RHIDP Epic from conversation context with grill and optional Story/Task decomposition. |
| `references/to-issue.md` | Create a Story, Task, Bug, or Spike with automatic type inference and grill. |
| `references/update-jira-status.md` | Update a Jira issue with session progress, status comment, transitions, and upward cascade to parent Epic/Feature. |
| `references/duplicates.md` | Duplicate detection for pre-creation checks and refinement audits. Shared across creation commands and refine. |
| `references/grill.md` | Shared challenging behavior for issue creation grills: sizing, completeness, scope, risks, cross-referencing. |
| `references/sizing.md` | T-shirt sizing guide for Features/Epics and Fibonacci story points for Stories/Tasks. Used during grills and refinement. |

</reference_index>

## Common Gotchas

1. **`acli auth status` lies.** It checks OAuth, not API token auth. Always returns "unauthorized" with token auth even when Jira works fine. Use `acli jira project list --recent 1` as a smoke test instead.
2. **`view` uses positional arg, everything else uses `--key`.** `acli jira workitem view RHIDP-123` but `acli jira workitem edit --key RHIDP-123 ...`.
3. **`--yes` is mandatory for mutations.** All `edit`, `transition`, `assign`, and `link create` commands prompt interactively without it. Always pass `--yes`.
4. **`--fields` is restrictive on search.** Only accepts `key`, `summary`, `status`, `assignee`, `issuetype`, `priority`, `description`, `labels`. For components, sprint, fixVersions, and all custom fields — use `--json` or `scripts/parse_issues.py --enrich`.
5. **Team field has two JQL syntaxes.** `customfield_10001` cannot be used in JQL WHERE clauses. However, `"Team[Team]" = {teamId}` (using the team UUID, not display name) works. Use the UUID syntax for JQL filtering; use `customfield_10001.name` in post-processing only when you need the display name from JSON output.
6. **ADF is required for formatted descriptions.** Reading descriptions via `--json` returns Atlassian Document Format (nested JSON). Jira Cloud's editor is ADF-native — plain text and Jira wiki markup (`h1.`, `*bold*`) both render as literal characters in the UI. For formatted descriptions, fill a wiki markup template then run `scripts/jira-wiki-to-adf.py <input.txt> <output.json>` to convert to ADF, then pass via `--description-file`. Both `acli create` and `acli edit` accept ADF JSON via `--description-file`. Do not use Jira wiki markup in description files expecting it to render.
7. **Acceptance Criteria field is almost always null.** Scan the description for "Requirements", "Acceptance Criteria", or bullet-style criteria instead of checking `customfield_10718`.
8. **`--enrich` is MANDATORY for custom fields AND labels.** Both `acli search --json` and `acli view KEY --json` (without `--fields "*all"`) return only basic fields (assignee, issuetype, priority, status, summary). Labels, story points, team, sprint, size, and components will all appear as empty/null — looking like the data isn't set when it actually is. Always use `scripts/parse_issues.py --enrich` to get custom field data. Skipping `--enrich` is the #1 cause of false "missing data" reports.
9. **`acli` cannot set arbitrary custom fields.** `acli jira workitem edit` does not have a `--custom` flag. Fields like Team, Size, Story Points, and Release Note Type can only be updated via the Jira REST API. Use `PUT /rest/api/3/issue/{key}` with the field payload (see `references/rest-api-fallback.md` for curl examples and payload formats). Find the token file at `.jira-token` next to the `acli` executable (discover the path with `readlink -f "$(which acli)"` or `where acli`). Never read the token file into context.
10. **`acli sprint list-workitems --json` wraps results in `{"issues": [...]}`.**  The output is NOT a flat array — it's an object with an `issues` key. Extract the array before piping to `parse_issues.py`. See `references/acli-commands.md` for the workaround command.
11. **GraphQL search is beta.** `issueSearchStable` requires `X-ExperimentalApi: JiraIssueSearch` header. Load `references/graphql-queries.md` before attempting GraphQL queries.
12. **`.jira-token` format is `email:token`, not bare token.** A file containing only the API token without the email prefix will cause 401 errors on REST/GraphQL calls. The `setup.py` script validates the format.
13. **`acli search` silently truncates results.** The default page size is 30. If your JQL matches more than 30 issues, you get the first 30 with no warning. Always pass `--limit 200` for bulk queries, or use `--count` first to check the total, then `--paginate` to fetch all pages. This is the #2 cause of incorrect reports after skipping `--enrich`.
14. **"Feature Exploration" vs "Feature Refinement."** The meeting/process is called **Feature Exploration**. The Jira workflow status is **Refinement**. These are different things. When referring to the meeting or process, always use "Feature Exploration." When referring to the Jira status, use "Refinement." The meeting is sometimes mislabeled as "Feature Refinement" in calendar invites — this is incorrect.
15. **Don't remove `rhdh-X.Y-candidate` labels.** Candidate labels track release targeting. Removing them without PM approval can silently drop a feature from release tracking.
16. **Feature→Epic child links use Parent Link, not issuelinks.** Cross-project parent-child relationships (RHDHPLAN Feature → RHIDP Epic) use the `Parent Link` field (`customfield_10018`), not `issuelinks`. To find child Epics of a Feature, use JQL: `project = RHIDP AND type = Epic AND "Parent Link" = RHDHPLAN-XXX`. Checking `issuelinks` will show zero results and produce false "no child Epics" reports.
17. **REST `/rest/api/3/search` returns 410 Gone.** This endpoint has been removed. Use POST to `/rest/api/3/search/jql` with body `{"jql": "...", "fields": [...], "maxResults": N}` instead. This only affects direct REST calls — `acli search` still works.
18. **`acli workitem create` does not support `--priority`, `--component`, or `--yes`.** These flags exist on `edit`, `transition`, and `assign` but not on `create` — passing them causes "unknown flag" errors. After creating an issue, set priority, components, size (`customfield_10795`), and parent link (`customfield_10018`) together in a single `PUT /rest/api/3/issue/{key}` call.

## Error Handling

| Error | Action |
|-------|--------|
| `acli` not on PATH | Run `scripts/setup.py`. Install from Atlassian if missing. See [Getting Started](https://developer.atlassian.com/cloud/acli/guides/how-to-get-started/). |
| "unauthorized" from `auth status` | Ignore. Check `jira_config.yaml` exists. Run smoke test. |
| "required flag(s) not set" | Command syntax wrong. Run `acli jira <subcommand> --help`. |
| "field X is not allowed" | Use `--json` instead of `--fields` for that field. |
| "the value X does not exist for the field 'project'" | Project key is wrong or project is archived (e.g., RHDHPAI). |
| Rate limiting (429) | Wait 5 seconds, retry once. |
| Interactive prompt hangs | Missing `--yes` flag on a mutating command. |
| Custom field update fails via `acli` | Fall back to Jira REST API using `.jira-token` file. See Gotcha #9. |
| `issueSearchStable` returns errors | Fall back to `acli` search (not REST — `/rest/api/3/search` returns 410 Gone on this instance). Warn that the beta API failed. |

## Team Conventions

These apply across all sub-commands:

- **Release Pending counts as completed.** Release Pending items remain in the sprint and count toward velocity and capacity. They represent done work awaiting release.
- **Confirmation flow.** Sub-commands that modify Jira issues use a standard prompt: `"Apply changes? [y/N/edit]"` — **y** applies all, **N** cancels, **edit** steps through each change individually.
- **Closure requires rationale.** When closing or descoping issues, always add a comment documenting the reason and set the resolution field (`Won't Do`, `Duplicate`, `Done`). Preserves the decision trail.
- **Comments over description bloat.** Issue descriptions use the structured template sections. Decision trail, elaboration, abandoned approaches, and customer context go in comments. Creation commands proactively suggest comments for context that emerged during the grill.

## Common Workflows

> Sub-commands share data. `plan` reuses roster/capacity/expertise from `assign`. `sprint-report` uses the same velocity query pattern as `plan`. `release` references exit criteria from `workflows.md` and can invoke `assign` for unassigned Features.

### Creating an issue

1. Load `references/templates.md` for the body template
2. Load `references/workflows.md` for required fields at New status
3. Run `acli jira workitem create` (see `references/acli-commands.md` if unsure of syntax)

### Searching with custom fields (team, story points, sprint)

1. Build JQL using patterns from `references/jql-patterns.md`
2. Pipe results through `scripts/parse_issues.py --enrich` for full field data
3. Use `-f team="X"` to filter by team (not possible in JQL)

### Transitioning an issue

1. Load `references/workflows.md` for exit criteria at the target status
2. Verify required fields are set before transitioning
3. Run `acli jira workitem transition --key KEY --status "X" --yes`

### Complex queries (many fields, relationships)

1. Load `references/graphql-queries.md`
2. Use `issueByKey` for single issues or `issueSearchStable` (beta) for JQL search
3. Fall back to `acli` + `parse_issues.py --enrich` if GraphQL returns errors

### Recommending and assigning issues

1. Load `references/assign.md`
2. Identify unassigned issues (single key, JQL query, or passed-in list)
3. Determine the team (from issue field, parent epic, or user input)
4. Run deep or quick analysis per the reference
5. Present recommendations, get user confirmation, then assign

### Refining issues

1. Load `references/refine.md`
2. Identify issues to refine (specific keys, JQL, `sprint`, or `backlog`)
3. Run all 6 checks: missing fields, duplicates, hierarchy, comments, staleness, sprint readiness
4. Present refinement report with actionable recommendations
5. Optionally apply auto-fixable changes and prompt for manual decisions

### Sprint planning prep

1. Load `references/plan.md`
2. Resolve team, board, and sprint context
3. Generate carryover report, velocity trend, capacity snapshot, and ready-for-planning queue
4. Auto-generate sprint fill suggestions with expertise matching
5. Surface critical customer bugs (exempt from capacity) and retro action items

### Sprint review summary

1. Load `references/sprint-report.md`
2. Resolve sprint (active or previous)
3. Partition completed vs carried over, compute completion rate
4. Per-member breakdown, epic progress, demo checklist with naming conventions
5. Optionally save as markdown file

### Release readiness

1. Load `references/release.md`
2. Fetch Features for the target version/label
3. Quick mode: PI funnel, feature matrix, readiness score
4. Deep mode: adds epic roll-up, dependency map, coherence analysis, RN readiness, risk assessment
5. Optionally remediate (assign owners, create Epics, transition statuses)

### Creating Features, Epics, and Issues

1. Load the appropriate creation reference (`to-feature.md`, `to-epic.md`, or `to-issue.md`)
2. Load `references/grill.md` for challenging behavior
3. Load the template + example pair from `assets/templates/` and `assets/examples/`
4. Grill the user on scope, AC, sizing (reference `references/sizing.md`)
5. Run duplicate check per `references/duplicates.md`
6. Create the issue, suggest comments for decision trail
7. Offer chained decomposition (Feature → Epics → Stories/Tasks)

### Updating Jira from a session

1. Load `references/update-jira-status.md`
2. Detect related issue (conversation → git → PR → commits → keyword search)
3. Compose status comment, propose transition
4. Check upward cascade (sibling completion → parent transition)
5. Suggest reaching out to Feature Owner if Feature-level work is complete

### Discovering unknown fields or endpoints

1. For REST: load `references/rest-api-fallback.md` — use the OpenAPI spec or `/rest/api/3/field` endpoint
2. For GraphQL: load `references/graphql-queries.md` — use `__type` introspection queries
3. Do not guess field IDs or types — always verify against the live schema

## When NOT to Use

- **Non-RHDH Jira projects** — this skill's field mappings, workflows, and JQL patterns are specific to RHIDP/RHDHPLAN/RHDHBUGS/RHDHSUPP
- **Jira REST API directly** — use `acli` first, then GraphQL for bulk reads. REST API is the last resort for writes when acli fails and for schema discovery via OpenAPI spec (see Gotcha #9)
- **GraphQL for simple lookups** — use `acli` for single-issue views and simple searches. GraphQL is for bulk operations, complex queries needing relationships or many custom fields in one call, team roster lookups, and schema introspection

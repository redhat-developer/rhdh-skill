# Jira authenticated API fallback

Use this seam only when `acli` cannot read or update a required Jira field. This reference defines
payload semantics; it never owns credentials or raw HTTP authentication.

## Capability gate

1. Try the supported `acli` operation first. For broad reads, use paginated search; for a single
   issue, use `acli jira workitem view KEY --fields '*all' --json`.
2. Use REST only through an already-authenticated host Atlassian adapter. The adapter owns the site,
   credential store, request headers, retries, and secret redaction.
3. If that adapter is unavailable, say which field could not be set and tell the human to run
   `/setup-rhdh-skills atlassian-mcp`.

Do not create token files, shell `AUTH` variables, Authorization headers, or credential-bearing
request previews. Do not fall back from a native tool to raw `curl`.

## Supported semantic operations

| Operation | Request semantics | Expected result |
|---|---|---|
| Read all fields | Get issue by key with `fields=*all` | Issue object |
| Discover fields | List Jira fields | Field IDs, types, and names |
| Check editability | Get edit metadata for an issue | Allowed operations and values |
| Update fields | Partial issue update with a `fields` object | No-content success or updated issue |
| Add comment | Add an ADF comment, with visibility when required | Comment receipt |
| Add remote link | Attach a web link to an issue key with `{"object": {"url": ..., "title": ...}}` | Created link with an id, or the id of the link it replaced |
| Sprint report (best-effort) | GET Greenhopper `sprintreport` with `rapidViewId` and `sprintId` | Per-sprint completed / not-completed issues and `issueKeysAddedDuringSprint` |
| Scope-change burndown (best-effort) | GET Greenhopper `scopechangeburndownchart` with `rapidViewId` and `sprintId` | Timestamped estimate and scope-change events |

The host adapter may expose these as tools instead of URL paths. Select by semantic capability, not
by tool name, and keep transport-specific response metadata out of what you report.

## Remote links

A remote link is the "web link" shown on a Jira issue. It is the supported way to record an
external URL — a pull request, a design document, a support case — against an issue, and `acli`
has no equivalent, so the authenticated adapter owns it.

```json
{"object": {"url": "https://github.com/redhat-developer/rhdh/pull/1234", "title": "GitHub PR: Fix plugin loader"}}
```

The target is the issue key; `object.url` and `object.title` are the whole payload. A second link
carrying the same URL replaces the first rather than creating a duplicate, so re-running after a
partial failure is safe. Report the link id the adapter returns.

A caller handing over a pull request usually wants three writes at once — a comment, a transition
to `Review`, and a remote link to the PR URL. Present all three together so a single approval
covers the set. `/rhdh-jira-update` owns that flow.

## Custom-field payloads

These are payload fragments for an authenticated adapter. They are not standalone HTTP commands.

```json
{"fields": {"customfield_10028": 5}}
```

Story Points is numeric.

```json
{"fields": {"customfield_10795": {"value": "M"}}}
```

Size is a select value: `XS`, `S`, `M`, `L`, or `XL`.

```json
{"fields": {"customfield_10001": {"id": "TEAM_ID"}}}
```

Team uses an Atlassian team ID. Discover it from an existing issue through the authenticated
adapter; never guess it.

```json
{"fields": {"customfield_10785": {"value": "Enhancement"}}}
```

Release Note Type is a select value. Allowed values include `Feature`, `Enhancement`,
`Developer Preview`, `Deprecated Functionality`, `Removed Functionality`, and
`Release Note Not Required`.

## Write boundary

A REST-backed write is an external write, so the skill that owns the verb invokes
`/mutation-gate` and follows it. Two details are specific to REST here: the operation's
preview is the full JSON payload rather than a command line, and the outcome is read back from the
changed fields rather than taken from the response, because a request the API accepts can still
leave a field unset.

## Response handling

| Result | Action |
|---|---|
| Validation failure | Re-read field metadata, correct the payload, and re-confirm if it changed |
| Unauthenticated | Name `/setup-rhdh-skills atlassian-mcp`; do not inspect or repair credentials here |
| Forbidden | Report the missing permission; do not retry with another identity |
| Not found | Verify the issue key before retrying |
| Rate limited | Honor the adapter retry delay and retry once |

REST search is not a fallback for bulk JQL in this skill. Use `acli --paginate` or the authenticated
GraphQL adapter instead.

## Greenhopper sprint report and burndown

These endpoints power the board UI at
`https://redhat.atlassian.net/jira/software/c/projects/RHIDP/boards/{boardId}/reports/burndown-chart?sprint={sprintId}`.
They are **not** a public Jira Cloud API. `acli` has no equivalent. Treat them as
best-effort and unstable: Cloud may 404 or 403 them, the JSON may drift, and a
host adapter that cannot GET an authenticated path cannot use them.

Capability gate, in addition to the seam rules above:

1. The host adapter must be able to GET an authenticated Jira path. If it cannot,
   skip Greenhopper in one line and reconstruct.
2. Never `curl`, never an Authorization header, never a credential in context.
3. On 404, 403, or a body that lacks the keys below, skip in one line and
   reconstruct. Do not retry as raw REST.

```
GET /rest/greenhopper/1.0/rapid/charts/sprintreport?rapidViewId={boardId}&sprintId={sprintId}
GET /rest/greenhopper/1.0/rapid/charts/scopechangeburndownchart?rapidViewId={boardId}&sprintId={sprintId}
```

A live probe through the host adapter was not available when this was written, so
reconstruction is the documented happy path. When a probe succeeds, record the
live keys here and keep using them; until then, callers should accept this shape
and ignore unknown fields:

```json
{
  "rapidViewId": 11374,
  "sprint": {
    "id": 47486,
    "name": "RHDH COPE 3289",
    "state": "CLOSED",
    "startDate": "18/Mar/26 12:00 PM",
    "endDate": "8/Apr/26 12:00 PM"
  },
  "contents": {
    "completedIssues": [
      {
        "key": "RHIDP-1001",
        "statusName": "Closed",
        "currentEstimate": 5,
        "estimateStatistic": {
          "statFieldId": "customfield_10028",
          "statFieldValue": {"value": 5.0, "text": "5"}
        }
      }
    ],
    "issuesNotCompletedInCurrentSprint": [],
    "puntedIssues": [],
    "issueKeysAddedDuringSprint": {"RHIDP-1002": true},
    "completedIssuesEstimateSum": {"value": 5, "text": "5.0"}
  }
}
```

`issueKeysAddedDuringSprint` is the grey scope-change on the burndown chart —
issues whose Sprint field joined after sprint start. That is interrupt work.

`/rhdh-release-capacity-plan` consumes this. It never copies these paths into its
own files.

### Reconstruction when Greenhopper is skipped

Same numbers the chart is drawn from, without the chart API:

1. `acli jira sprint view --id SPRINT_ID --json` for `startDate`.
2. Paginated `acli` search for every issue in the sprint, enriched for story
   points and status. Prefer `--paginate`.
3. An issue is interrupt when changelog (or the Greenhopper added-keys set)
   shows its Sprint field joined after `startDate`. If changelog cannot be
   fetched, report interrupt as unretrieved — do not treat that as zero.
4. Completed is status Closed or Release Pending.
5. Always include the human chart URL in the report so a person can open the
   same view.

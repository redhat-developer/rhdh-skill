# Release capacity planning

Forecast whether a named team can take the `rhdh-X.Y-candidate` Features for a
release: sample-sprint velocity and interrupt, Epic-first demand, and two
capacity ledgers through Code Freeze.

Use paginated `acli` for bulk reads and the authenticated host adapter only for
fields `acli` cannot return, including the optional Greenhopper sprint report.
`/rhdh-jira-api` owns both. This workflow is read-only.

Feed the gathered snapshot to `uv run scripts/capacity.py`. Do not re-implement
the arithmetic in prose.

## Input

1. **Team** — name or Jira team UUID. Resolve Cloud ID and board through
   `/rhdh-release-teams` and `/rhdh-jira-api`. Never infer a team from member
   names.
2. **Release version** — e.g. `2.2`. Builds the candidate label
   `rhdh-2.2-candidate`. Ask if missing.
3. **Availability** — default every `FULL_MEMBER` to 100%. Ask for PTO or a
   percent available and apply it per person.
4. **Meeting factor** — default `0.4` (keep 60% of theoretical capacity for
   implementation). Override only when the user names another fraction.
5. **History window** — last 6 closed sprints on the team's board, unless the
   user names a sample range.
6. **SP per person per sprint** — omit to infer from sample completions (the
   script backs out meetings and interrupt before re-applying them). If the user
   supplies a full-focus rate, pass it through as `sp_per_person_sprint`.

## Step 1 — Resolve team, board, roster, and dates

Invoke `/rhdh-release-teams` for Cloud ID. Look up the board in `/rhdh-jira-api`
(the board table). Fetch `FULL_MEMBER` only via the `GetTeamRoster` query;
drop `INVITED` and `ALUMNI`.

Invoke `/rhdh-release-schedule` for Feature Freeze and Code Freeze. Remaining
sprints are two-week slots from today through Code Freeze; also print Feature
Freeze. If the user already gave `remaining_sprints`, keep that number.

## Step 2 — Sample closed sprints

```bash
acli jira board list-sprints --id BOARD_ID --state closed --json
```

`acli` has no `--recent`. Take the last 6 closed sprints whose names match the
team (sprint numbers are shared across teams on some boards). For each:

```bash
acli jira sprint view --id SPRINT_ID --json
```

Record `startDate`. Include the human chart URL:

`https://redhat.atlassian.net/jira/software/c/projects/RHIDP/boards/{boardId}/reports/burndown-chart?sprint={sprintId}`

## Step 3 — Velocity and interrupt

Try Greenhopper first, through `/rhdh-jira-api` (the sprint-report seam in its
REST fallback):

```
GET /rest/greenhopper/1.0/rapid/charts/sprintreport?rapidViewId={boardId}&sprintId={sprintId}
```

If the host adapter cannot GET an authenticated path, or Cloud returns 404/403,
or the body lacks `contents`, skip in one line and reconstruct. Never `curl`.
Never put a credential in context.

**Reconstruction** — paginated search, then enrich story points and status:

```bash
acli jira workitem search \
  --jql 'project in (RHIDP, RHDHPLAN, RHDHSUPP, RHDHBUGS) AND sprint = SPRINT_ID AND "Team[Team]" = TEAM_ID' \
  --fields "key,summary,status,issuetype,assignee,storypoints,sprint" --paginate --json
```

An issue is interrupt when changelog (or Greenhopper `issueKeysAddedDuringSprint`)
shows its Sprint field joined after `startDate`. If changelog cannot be fetched,
report interrupt as unretrieved — do not treat that as zero.

Completed is Closed or Release Pending. Put each sprint into the snapshot as
either `greenhopper_sprintreport` or `issues` with `added_after_start`, plus
`burndown_url`. The script computes completed, interrupt, and planned-completed
points.

## Step 4 — Candidate demand

```jql
project = RHDHPLAN AND issuetype = Feature AND labels = 'rhdh-VERSION-candidate'
ORDER BY priority ASC
```

Enrich Size, labels (`stretch`), and Team. For each Feature, query child Epics:

```jql
issuetype = Epic AND parent = FEATURE_KEY
```

If that returns 0, retry `"Epic Link" = FEATURE_KEY`. Keep Epics whose Team is
the specified team. For each kept Epic, sum child Story Points:

```jql
parent = EPIC_KEY
```

Demand rules (Epic-first):

- Team Epic with child Story Points → use that sum.
- Team Epic with no child points but a T-shirt → placeholder Fibonacci from
  the script. Print `demand.tshirt_placeholder_note`.
- No team Epic → Feature T-shirt the same way.
- No size and no child points → unsized. Do not invent a number.

Never treat the Size field's 1–5 as story points. Never convert T-shirt
through sprint-effort × team velocity.

## Step 5 — Run the arithmetic

Write the snapshot (team, version, board, dates, members with availability,
sprints, features, meeting factor, optional `sp_per_person_sprint`) and run:

```bash
uv run scripts/capacity.py --input snapshot.json
```

Pretty JSON on a TTY, compact when piped. Exit 1 on a bad snapshot.

The script shows two ledgers:

- **Historical** — mean planned-completed (interrupt excluded) × remaining
  sprints × availability factor.
- **Theoretical** — available people × remaining sprints × SP/person/sprint ×
  (1 − meeting factor) × (1 − interrupt rate). If SP/person/sprint was inferred
  from Jira completions, it is backed out of the 40% and interrupt before those
  haircuts are applied again, so observed velocity is not double-discounted.

If sample story-point coverage is under 50%, the script switches the unit to
issue counts and sets `coverage_warning`. Say that out loud.

## Output

```markdown
## Release capacity — {team} {version}

Horizon: today → Code Freeze {code_freeze} ({remaining} two-week sprints)
Feature Freeze: {feature_freeze}

### Sample velocity
| Sprint | Source | Completed | Interrupt | Planned completed | Chart |
|--------|--------|-----------|-----------|-------------------|-------|

Avg planned: {mean} {unit}/sprint | Interrupt rate: {rate} | Coverage: {coverage}

### Demand ({total} {unit}, {required} required, {stretch} stretch)
Placeholder T-shirt→SP: {demand.tshirt_placeholder_note or not used}

| Feature | Size | Basis | {unit} | Placeholder | Stretch | Team epics |
|---------|------|-------|--------|-------------|---------|------------|

Unsized: {keys or none}

### Ledgers
| Ledger | Arithmetic | Net | Required fit | All-candidates fit |
|--------|------------|-----|--------------|--------------------|
| Historical | {historical.arithmetic} | {net} | {fits} ({slack}) | {fits} ({slack}) |
| Theoretical | {theoretical.arithmetic} | {net} | {fits} ({slack}) | {fits} ({slack}) |

Meeting factor {meeting} (keep {1-meeting} for implementation). Theoretical
SP/person/sprint source: {inferred_backed_out or user_full_focus}.

### First cuts
Stretch Features, in priority order: {keys}
```

## Error handling

| Error | Action |
|---|---|
| Team or version missing | Ask. Do not guess a release from the newest label you have seen. |
| Board ID not found | Ask. List boards with `acli jira board search --project RHIDP`. |
| No closed sprints | Stop velocity. Say historical data is unavailable. |
| Greenhopper 404/403 or adapter missing | Skip in one line; reconstruct. Name `/setup-rhdh-skills atlassian-mcp` only when the host adapter itself is the missing piece. |
| Changelog unretrieved | Interrupt is unretrieved, not zero. |
| Bulk search truncated | Report a floor, not a total. Retry once with `--paginate`. |
| Code Freeze TBD | Ask for a remaining-sprint count rather than inventing dates. |
| Story-point coverage under 50% | Keep the script's issue-count unit and say why. |

## Caveats

1. **Meetings already sit inside Jira velocity.** Historical planned-completed
   already reflects meetings and interrupt. The theoretical ledger is the one
   that applies the 40% haircut, and only after backing out an inferred rate.
   Print both arithmetic lines so that cannot be missed.
2. **T-shirt→SP is a placeholder.** The script owns the Fibonacci map. That
   map is not calibrated, not the Size field's 1–5, and not sprint-effort ×
   team velocity (which treats extra-small as whole-team sprints). Child
   story points are real; T-shirt rows are not. Print
   `demand.tshirt_placeholder_note` whenever it is set.
3. **Greenhopper is unofficial and may vanish.** Reconstruction is the
   documented happy path. The chart URL is for humans.
4. **Scope-change detection from changelog is approximate.** Issues moved
   between sprints can look like interrupt.
5. **Release Pending counts as completed**, matching sprint-plan convention.

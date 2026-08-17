# Workflow: Teams and leads

<prerequisites>

`gog` must reach the RHDH Team Mapping spreadsheet:

```bash
gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json
```

If that fails, run `uv run scripts/release.py --json check` and follow its
`next_steps`, or direct the user to `/setup-rhdh-skills google-workspace`. Do not
install or authenticate anything here.

</prerequisites>

<process>

## Step 1: Run the CLI

```bash
uv run scripts/release.py --json teams
uv run scripts/release.py --json teams --category Engineering
```

Only active teams are returned; the CLI filters on the sheet's status column.
Where the Rich Filter export defines a `Scrum Team` clause for a team, its Cloud
ID wins over the spreadsheet column — the export is what Jira actually matches.

## Step 2: Present the roster

| Category | Team Name | Team ID | Cloud ID | Leads | Slack Handles |
|---|---|---|---|---|---|

Link the source: [RHDH Team Mapping](https://docs.google.com/spreadsheets/d/1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM/edit).

Include the Cloud ID whenever the question is about querying Jira; omit it when
the question is about people.

## Step 3 (fallback): CLI unavailable

```bash
gog sheets get 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM Team --json --results-only
```

Filter to `Status = Active`, then to the requested category. This path returns the
spreadsheet's Cloud ID column with no Rich Filter override, so say so.

</process>

<gotchas>

- The Cloud ID is the Jira Cloud team identifier used as
  `"Team[Team]" = "{{CLOUD_ID}}"` — for example
  `ec74d716-af36-4b3c-950f-f79213d08f71-4403` for COPE. Team names do not work in
  that clause.
- Inactive teams are excluded by default. Say so rather than letting the roster
  read as complete.
- Team names in the sheet may carry an `RHDH` prefix that Jira and the Rich
  Filter drop. Match on the normalised name, not the literal string.

</gotchas>

<success_criteria>

- [ ] Active teams only, unless the user asked for the full history
- [ ] Leads and Slack handles per team, with the spreadsheet linked
- [ ] Cloud IDs included when the answer will be used in JQL, with their origin
      named

</success_criteria>

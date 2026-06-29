# Workflow: Retrieve Future Release and Key Dates

Table of future release versions with critical dates from the RHDH release schedule spreadsheet.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **gog CLI** | `gog sheets metadata 1knVzlMW0l0X4c7gkoiuaGql1zuFgEGwHHBsj-ygUTnc --json` succeeds |

If gog check fails: run `gog auth add <email>`.

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json future-dates {{RELEASE_VERSION}}
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Fetch schedule from Google Sheets via gog

First, find the schedule tab:

```bash
gog sheets metadata 1knVzlMW0l0X4c7gkoiuaGql1zuFgEGwHHBsj-ygUTnc --json
```

Look for a tab containing the current year and "schedule" in the name.

Then fetch the tab contents:

```bash
gog sheets get 1knVzlMW0l0X4c7gkoiuaGql1zuFgEGwHHBsj-ygUTnc "{{TAB_NAME}}" --json --results-only
```

Search the rows for the target version's GA row, then walk backward to find Feature Freeze and Code Freeze dates.

If a specific version is not given, ask the user which version they want, or fetch for each known active release (from the `release-dates` workflow).

## Step 3 (fallback): Format output

Present as a table:

| Release | Feature Freeze | Code Freeze | GA Date | Source |
|---------|---------------|-------------|---------|--------|
| {{VERSION}} | {{DATE}} | {{DATE}} | {{DATE}} | [Schedule Sheet](https://docs.google.com/spreadsheets/d/1knVzlMW0l0X4c7gkoiuaGql1zuFgEGwHHBsj-ygUTnc/edit) |

</process>

<gotchas>

- The script currently reads only the first matching schedule tab (by year).
- If `{"error": "version_not_found"}`: ask the user for the exact version string as it appears in the sheet.
- If `{"error": "spreadsheet_not_found"}`: ask the user to share the sheet URL.

</gotchas>

<success_criteria>

- [ ] Table with future release dates from the schedule spreadsheet
- [ ] Dates include at least GA target per release

</success_criteria>

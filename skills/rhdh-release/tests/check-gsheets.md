# Google Sheets Smoke Checks — rhdh-release

Requires `gog` CLI with authenticated Google account. All checks are read-only.

## How to run

```
read @skills/rhdh-release/tests/check-gsheets.md
```

Then follow the checks below, reporting PASS/FAIL for each.

## Prerequisites

```bash
gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json
```

If this fails, run `gog auth add <email>` and retry.

## Checks

### 1. Team mapping fetch

```bash
python3 skills/rhdh-release/scripts/release.py --json teams
```

- [ ] Exits 0
- [ ] Returns valid JSON
- [ ] JSON contains at least 3 teams
- [ ] Each team has `team_name`, `leads`, and `category` fields

### 2. Team mapping filtered by category

```bash
python3 skills/rhdh-release/scripts/release.py --json teams --category Engineering
```

- [ ] Returns fewer or equal teams compared to check 1
- [ ] All returned teams have `category: Engineering`

### 3. Release schedule access

Verify the release schedule spreadsheet is accessible via gog:

```bash
gog sheets metadata 1knVzlMW0l0X4c7gkoiuaGql1zuFgEGwHHBsj-ygUTnc --json
```

- [ ] Returns valid JSON (exit 0)
- [ ] Response contains sheet/tab metadata (not an auth error)

Then verify schedule data can be fetched via the release CLI:

```bash
python3 skills/rhdh-release/scripts/release.py --json future-dates 1.10
```

- [ ] Returns valid JSON with `version`, `tab`, and date fields

## Report format

```
Google Sheets Smoke Checks — rhdh-release
===========================================
 1. Team mapping fetch:        PASS/FAIL (N teams found)
 2. Team mapping active filter: PASS/FAIL (N active teams)
 3. Release schedule access:   PASS/FAIL (details)

Result: X/3 passed
```

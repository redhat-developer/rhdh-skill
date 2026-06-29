# Structural Checks — rhdh-release

Read-only, no external dependencies. Verifies file integrity and cross-references.

## How to run

```
read @skills/rhdh-release/tests/check-structural.md
```

Then follow the checks below, reporting PASS/FAIL for each.

## Checks

### 1. SKILL.md structure

Read `skills/rhdh-release/SKILL.md` and verify:

- [ ] YAML frontmatter has `name: rhdh-release`
- [ ] YAML frontmatter has `description` (length > 20 chars)
- [ ] Contains `<essential_principles>` ... `</essential_principles>`
- [ ] Contains `<intake>` ... `</intake>` with numbered options 1–13
- [ ] Contains `<routing>` ... `</routing>` with a markdown table
- [ ] Contains `<reference_index>` ... `</reference_index>`
- [ ] Contains `<prerequisites>` ... `</prerequisites>`

### 2. Routing → workflow consistency

Parse the `<routing>` table in SKILL.md. For each row that references `workflows/<name>.md`:

- [ ] The file `skills/rhdh-release/workflows/<name>.md` exists

List any broken references.

### 3. Workflow file structure

For every `.md` file in `skills/rhdh-release/workflows/`:

- [ ] Contains `<prerequisites>` or `<required_reading>`
- [ ] Contains `<process>` ... `</process>`
- [ ] Contains `<success_criteria>` ... `</success_criteria>`

List any files missing required sections.

### 4. Workflow count

- [ ] Exactly 13 workflow files exist in `skills/rhdh-release/workflows/`

### 5. JQL template coverage

Read `skills/rhdh-release/references/jql-release.md`. Extract all `## <query_name>` headings.

- [ ] Exactly 13 query templates exist

Then grep all workflow files for references to each query name. Verify:

- [ ] Every JQL query name is referenced by at least one workflow

List any orphaned queries.

### 6. Slack template coverage

Read `skills/rhdh-release/references/slack-templates.md`. Extract all `## <template_name>` headings.

- [ ] Exactly 4 Slack templates exist

Then check that each template is referenced by a matching workflow file in `workflows/`:

- [ ] `Feature Freeze Update` → `announce-feature-freeze-update.md`
- [ ] `Feature Freeze Announcement` → `announce-feature-freeze.md`
- [ ] `Code Freeze Update` → `announce-code-freeze-update.md`
- [ ] `Code Freeze Announcement` → `announce-code-freeze.md`

### 7. Reference file existence

Verify all local files listed in `<reference_index>` exist:

- [ ] `references/jql-release.md`
- [ ] `references/slack-templates.md`
- [ ] `references/config.md`

Note: The release process reference uses `gog docs cat` (live Google Doc) — no local file to check.

### 8. Config cross-references

Read `skills/rhdh-release/references/config.md`:

- [ ] Contains `jira_default_base_jql`
- [ ] Contains `team_mapping_gdrive_id`
- [ ] Contains `release_schedule_gdrive_id`
- [ ] Contains `release_process_doc_id`
- [ ] Contains gog CLI setup instructions

### 9. Script files (no symlinks)

- [ ] `scripts/formatters.py` exists and is a regular file (not a symlink)
- [ ] No symlinks remain in `scripts/` (`find scripts/ -type l` returns empty)
- [ ] Exactly 4 Python scripts: `release.py`, `formatters.py`, `jql.py`, `slack_templates.py`

### 10. Release CLI existence

- [ ] `scripts/release.py` exists and is executable
- [ ] `scripts/jql.py` exists
- [ ] `scripts/slack_templates.py` exists
- [ ] `python scripts/release.py --help` exits 0

### 11. Version consistency

Read `pyproject.toml`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and verify:

- [ ] All three files contain the same version string

## Report format

```
Structural Checks — rhdh-release
=================================
 1. SKILL.md structure:          PASS/FAIL (details)
 2. Routing → workflow:          PASS/FAIL (details)
 3. Workflow file structure:     PASS/FAIL (details)
 4. Workflow count:              PASS/FAIL (N/13)
 5. JQL template coverage:       PASS/FAIL (details)
 6. Slack template coverage:     PASS/FAIL (details)
 7. Reference file existence:    PASS/FAIL (details)
 8. Config cross-references:     PASS/FAIL (details)
 9. Script symlinks:             PASS/FAIL (details)
10. Release CLI existence:       PASS/FAIL (details)
11. Version consistency:         PASS/FAIL (version)

Result: X/11 passed
```

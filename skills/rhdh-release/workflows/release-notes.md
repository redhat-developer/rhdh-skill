# Workflow: Review Release Note Lifecycle

Report unclassified, proposed, done, and populated release-note work.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json notes {{RELEASE_VERSION}}
```

Use the CLI output directly. If it reports that `release_notes` is unavailable,
run `python scripts/release.py --json check`, configure the Rich Filter as shown
in `references/config.md`, and retry. Do not substitute a hardcoded query: the
Rich Filter is the source of truth for release-note classification.

Also include the Release Notes Dashboard returned by the CLI.

The lifecycle keys map to `release_notes`, `release_notes_proposed`,
`release_notes_done`, and `release_notes_with_text` in
`references/jql-release.md`.

</process>

<gotchas>

- Release Notes must be filled before release — this is a documentation blocker.
- Refer to [RHDH Release Notes Process](https://docs.google.com/document/d/1KFMkRVTkbDIhyZviZcuVn9UfJp64lKmokzT4ftMrj4w/edit) for the full process.

</gotchas>

<success_criteria>

- [ ] Counts for unclassified, proposed, done, and issues with release-note text
- [ ] Jira search link for every lifecycle stage
- [ ] Link to Release Notes Dashboard

</success_criteria>

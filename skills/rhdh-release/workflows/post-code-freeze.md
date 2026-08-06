# Workflow: Review Post Code Freeze Work

Identify release-scoped issues selected by the operational Post Code Freeze filter.

<prerequisites>

Run `python scripts/release.py --json check` and require the Rich Filter contract check to pass.

</prerequisites>

<process>

```bash
python scripts/release.py --json post-freeze {{RELEASE_VERSION}}
```

Use the returned count and Jira link. The query is composed from the exported
`Post Code Freeze` static filter; do not reproduce its JQL locally.

</process>

<success_criteria>

- [ ] Post Code Freeze count is reported
- [ ] A release-scoped Jira search link is included

</success_criteria>

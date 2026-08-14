# Jira capability check

Detect capability here. Creating, storing, or repairing a credential belongs to
the human-invoked `/setup-rhdh-skills`, and this skill never duplicates it.

## Check

Run the local detector without reading credential contents into context:

```bash
uv run scripts/setup.py --json
```

Use its boolean capability fields.

**The smoke check outranks `acli auth status`.** With API-token authentication
`acli auth status` reports unauthorized while the session works perfectly well.
Confirm with a real call before believing it:

```bash
acli jira project list --recent 1
```

If that succeeds, the session is good and the `auth status` line is a false
negative — ignore it. Do not send the user to setup on the strength of
`auth status` alone.

## API preference

1. `acli` for ordinary and bulk reads and for the mutations it supports.
2. An authenticated host Atlassian adapter for relationship-heavy GraphQL reads.
3. That same host-managed boundary for fields or writes `acli` cannot handle.

Never read, print, copy, transform, or repair credential material in model
context. Never construct an Authorization header, a token file, an `AUTH` shell
variable, or a raw `curl` call.

## Missing capability

If required Jira capability is absent, stop the affected branch, say which
capability is missing, and tell the human to run `/setup-rhdh-skills jira` — or
`/setup-rhdh-skills atlassian-mcp` when the missing piece is the host REST or
GraphQL adapter rather than `acli` itself. After setup completes, rerun
`scripts/setup.py --json` and resume only when the capability passes.

## Non-auth errors

| Symptom | Interpretation |
|---|---|
| `acli auth status` says unauthorized but the smoke check succeeds | False negative — ignore it |
| Host REST/GraphQL adapter unavailable | Name `/setup-rhdh-skills atlassian-mcp`; `acli` branches still work |
| 429 response | Wait briefly and retry once; this is not a setup failure |

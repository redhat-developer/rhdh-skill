---
name: setup-rhdh-skills
description: Install, configure, diagnose, or repair the complete RHDH skills environment.
disable-model-invocation: true
compatibility: "Python 3 and npx. Detects and configures acli, gh, gog, oc, and podman or docker; it needs none of them present to run."
---

# Set Up RHDH Skills

Bootstrap the complete pack, then configure the capabilities needed by its model skills. This is a
human entry point because installation, credentials, and external mutations require human agency.

## Choose a setup branch

| Request | Load |
|---|---|
| Install, upgrade, or repair the complete skill collection | [references/install.md](references/install.md) |
| Configure Jira CLI, REST, or GraphQL access | [references/jira.md](references/jira.md) |
| Configure Google Workspace access for schedules and test plans | [references/google-workspace.md](references/google-workspace.md) |
| Configure the RHDH private-data checkout | [references/private-data.md](references/private-data.md) |
| Authenticate Atlassian MCP in Cursor | [references/atlassian-mcp.md](references/atlassian-mcp.md) |
| Discover or configure RHDH repositories | [references/repositories.md](references/repositories.md) |
| Configure containers and the local RHDH runtime | [references/local-runtime.md](references/local-runtime.md) |
| Authenticate the OpenShift CI Gangway adapter | [references/openshift-ci.md](references/openshift-ci.md) |

With no branch in the request, show this table and wait for the user's selection.

## Preflight

Run the setup doctor before every branch:

```bash
uv run scripts/setup.py doctor --json
```

Consume the complete report. Reuse it during the session unless setup changes. The doctor lists
installed skills, the skills still missing, capability status, and configuration locations; it does
not read credentials.

## Write gate

Installing skills and configuring capabilities writes to the user's machine and accounts. Invoke the
named skill `mutation-gate` and follow it.

`scripts/setup.py install-plan` states the ordered install operations, and
`scripts/setup.py apply --plan <file> --confirm` runs the approved plan and reports one outcome per
operation. Configuration branches state their own operations the same way.

Credentials remain in the owning tool's credential store or OS keyring. Pass secrets directly to
the tool without placing them in conversation, configuration JSON, plans, outcome reports, or pack
content.

## Completion

A branch is complete when the doctor reports every promoted skill in `assets/catalog.json` plus
`grilling` and `humanizer` as installed, the branch's own capability reads as present in that same
doctor report, and the branch reference's smoke check has been run with its output shown. An
install branch additionally requires one reported outcome for every operation in the approved plan,
and the user told to restart or rescan the agent. When a model skill sent the user here because a
capability was missing, every capability it named must report installed before the branch closes.
Name any capability still missing as unresolved instead of closing on it.

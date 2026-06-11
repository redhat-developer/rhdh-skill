---
name: fullsend
description: |
  Work with fullsend agent platform: groom Jira tickets for agent-readiness,
  bridge them to GitHub Issues for fullsend processing. Trigger on "fullsend",
  "groom ticket", "bridge ticket", "send to fullsend", or any Jira key with
  agent/fullsend intent.
---

# fullsend

Support the team's fullsend workflow: prepare work in Jira, feed it to
fullsend agents via GitHub Issues.

Invoke with `/fullsend <command>`. Default (no args): show the command table below.

## Commands

| Command | Description | Reference |
|---------|-------------|-----------|
| `groom <KEY>` | Score + improve Jira ticket for agent-readiness | `references/groom.md` |
| `bridge <KEY>` | Create GitHub Issue from groomed ticket | `references/bridge.md` |

### Modes

- `groom <KEY>` — interactive grooming session
- `groom <KEY> --quick` — score only, no conversation
- `groom --batch <JQL>` — score multiple tickets
- `bridge <KEY>` — bridge single ticket to GitHub
- `bridge <KEY> --dry-run` — preview without mutation
- `bridge <KEY> --repo owner/name` — explicit target repo

## Routing

1. No argument → show the command table above.
2. First word is `groom` → read `references/groom.md` and follow it.
3. First word is `bridge` → read `references/bridge.md` and follow it.
4. Bare Jira key (e.g. `RHCLOUD-1234`) without command → ask: "Groom or bridge?"

## Reference Index

| File | Load when... |
|------|-------------|
| `references/groom.md` | `groom` command |
| `references/bridge.md` | `bridge` command |
| `references/repo-mapping.md` | `bridge` needs repo detection |

## Shared Context

This skill builds on existing rhdh-skill references — it does not duplicate them:

- **Repo catalog**: `../rhdh/references/rhdh-repos.md` (full ecosystem map)
- **Jira components**: `../rhdh-jira/references/fields.md` (component catalog, labels, priorities)
- **JQL patterns**: `../rhdh-jira/references/jql-patterns.md` (queries, boards, sprints)
- **Jira CLI**: `../rhdh-jira/references/acli-commands.md` (acli usage)

## Relationship to Other Skills

- **`rhdh-jira`**: Provides Jira CLI tooling (`acli`, `jira`), workflow fields, and JQL patterns. fullsend uses the same tooling but checks agent-readiness, not sprint-readiness.
- **`rhdh-jira refine`**: Complementary — run `refine` for process compliance, `fullsend groom` for agent readiness.
- **`rhdh`**: Provides the repo map and GitHub reference. fullsend's `bridge` uses it for repo detection.

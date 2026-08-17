---
name: rhdh-context
description: >-
  Resolves the environment the other RHDH skills start from and hands back one
  JSON document: which RHDH repositories are checked out and where — rhdh,
  rhdh-operator, rhdh-plugins, rhdh-plugin-export-overlays, rhdh-plugin-catalog,
  rhdh-cli, rhdh-chart, rhdh-local, backstage and the rest — which tools are on
  PATH, and the target RHDH and Backstage versions with the source that produced
  them. Also owns the `rhdh` CLI behind workspace status, worklogs, and todos.
  Use for RHDH orientation, "where is my rhdh checkout", "which Backstage version
  goes with RHDH 1.10", `rhdh status`, `rhdh doctor`, `rhdh config`,
  `rhdh workspace`, `rhdh log`, `rhdh todo`, and for the read-only context
  another RHDH skill needs before it starts. Read-only — implementation work
  belongs to the domain skill that owns the requested outcome.
compatibility: "Python 3.9+ and uv. git optional; the CLI reports a repository as unconfigured rather than failing."
---

# RHDH Context

The environment facts every other RHDH skill starts from: which repositories are checked out and
where, which tools are on PATH, which RHDH and Backstage versions this checkout targets, and where
its configuration lives. Callers invoke this skill by name and read what it reports; they never
inspect its files or import its Python package.

## What this skill hands back

Run this before another skill needs repository, tool, version, or configuration facts:

```bash
python scripts/context.py --project-root <repo> --json
```

It prints one JSON object and nothing else: `repositories` is an array of `{name, path}`, `tools`
maps each probed tool to `installed`, `missing`, or `not-probed`, and `configuration` carries the
config paths plus `targetRhdh`, `targetBackstage`, and `source`. The source is `user` when
`--target-rhdh` is given, `repository` when the checkout pins a version in `backstage.json`, and
`rhdh-context` when the answer comes from the checked-in compatibility matrix.

Consume the whole object. Reuse it within the session unless configuration or repository state
changes. When a required capability is missing, name that capability and tell the human to run
`/setup-rhdh-skills`; a model skill cannot invoke that human-only entry point.

## Preserved CLI

Run the CLI from this skill directory as `uv run scripts/rhdh <command>`. It is a
bundled wrapper, not an installed executable: `npx skills add` copies skill
directories and installs no console script. The wrapper declares no
dependencies — the `rhdh` package beside it is stdlib-only.

| Outcome | Interface |
|---|---|
| Environment orientation and diagnostics | `uv run scripts/rhdh status`, `uv run scripts/rhdh doctor` |
| Layered project/user configuration | `uv run scripts/rhdh config ...` |
| Repository submodule setup | `uv run scripts/rhdh setup submodule ...` |
| Overlay workspace inspection | `uv run scripts/rhdh workspace ...` |
| Worklog state | `uv run scripts/rhdh log ...` |
| Todo state | `uv run scripts/rhdh todo ...` |

Config, worklog, todo, JSON output shapes, exit codes, and existing `.rhdh` state remain compatible.
Local runtime actions belong to `/rhdh-local`. The compatibility command
`uv run scripts/rhdh local ...` delegates to the standalone `rhdh-local` executable; this skill
does not import or locate another skill's files.

## Handoffs

Handoffs stay in the conversation. This skill prints its context as JSON; the caller reads it and
carries what it needs.

When the human needs context to survive into a *later session*, tell them to run `/handoff`, which
writes a summary to the operating system temporary directory. That is a human-invoked skill and a
deliberate action, not something this skill does on their behalf.

## Conditional references

- Read [references/rhdh-repos.md](references/rhdh-repos.md) when identifying an RHDH repository or
  explaining ecosystem relationships.
- Read [references/versions.md](references/versions.md) when a workflow needs the checked-in
  compatibility matrix. Prefer live repository facts when they disagree with cached prose.

## Completion

Complete when the answer names the resolved repositories and their paths, the tool status, the
target RHDH and Backstage versions with the source that produced them, and every capability the
caller still has to set up. A repository that is not configured is reported with a null path, never
guessed. The caller receives the facts themselves, not a path to a file it has to open.

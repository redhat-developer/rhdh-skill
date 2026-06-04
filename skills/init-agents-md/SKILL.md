---
name: init-agents-md
description: >-
  Use when asked to bootstrap, create, initialize, or generate an AGENTS.md or
  context file for a repository. Also use when asked to "set up AI agent
  context", "create repo context file", "add AGENTS.md", "scaffold context
  file", "init agents md", "create CLAUDE.md for a repo", "make my repo
  AI-friendly", or "help agents understand this codebase".
---

## Goal

Write a minimal `AGENTS.md` and `CLAUDE.md` in the current working directory.
The output is a starting point — the human must review and edit before committing.

**Research finding (ETH Zurich, Feb 2026):** Auto-generated context files shipped
as-is reduce agent success rates by ~3% and increase costs by 20-23%. This skill
generates a draft. The human edits it aggressively before committing.

## Step 1: Check for existing files

If `AGENTS.md` already exists in the CWD, ask:

> "AGENTS.md already exists. Overwrite it? (yes/no)"

If no: stop. Tell the user to delete it first and re-run the skill.  
If yes: proceed.

## Step 2: Detect commands

Scan these files in the CWD:

| File | What to extract |
|------|-----------------|
| `package.json` | `scripts` entries matching build, test, lint, typecheck, dev/start |
| `Makefile` / `GNUmakefile` | Targets: build, test, lint, check, run |
| `pyproject.toml` | `[tool.pytest]`, `[tool.ruff]`, `[tool.mypy]`, `[project.scripts]` |
| `setup.cfg`, `tox.ini` | test commands |
| `Taskfile.yml` | task definitions |
| `go.mod` | signals Go project — look for `go test`, `go build`, `go vet` in Makefile or CI |
| `Cargo.toml` | signals Rust — look for `cargo test`, `cargo build`, `cargo clippy` |
| `.github/workflows/*.yml` | `run:` steps containing test/lint/build/typecheck keywords |
| `.gitlab-ci.yml` | `script:` entries |
| `Jenkinsfile` | `sh` steps |

**Cross-reference rule:** If a `package.json` script and a CI `run:` step agree, use
that form. If they differ, prefer the CI form — it's what actually runs in the
pipeline. If a command cannot be found or confidently inferred, omit it. Do not guess.

Look for these command categories:

- **Build** — compiles, bundles, or packages the project
- **Test all** — runs the full test suite without external dependencies
- **Test single file/package** — runs tests for one module
- **Lint** — runs the linter across the project
- **Lint single file** — lints one file in isolation
- **Type check** — static type checking
- **Run/dev** — starts the dev server or app locally

## Step 3: Interactive prompting

Ask these questions **one at a time**. Wait for each answer before asking the
next. Accept "skip" or a blank answer to omit that section entirely.

**Question 1 — Key Conventions:**
> "What are 2-3 project conventions an AI agent couldn't discover by reading the
> code? For example: a required wrapper type for API responses, a naming rule for
> files, a directory that must never be imported directly, or where generated
> files live. Skip if none come to mind."

**Question 2 — Architecture:**
> "Are there any non-obvious places where things live — for example, a feature
> configured in one place but evaluated elsewhere, or a shared internal API that
> shouldn't be called directly? Skip if the directory names make it obvious."

**Question 3 — PR Conventions:**
> "Any commit message format, required CI checks, or PR conventions agents should
> know? For example: Conventional Commits format, a required sign-off, or a label
> that blocks merge. Skip if standard."

## Step 4: Write the files

Infer the project name from `package.json` (`name` field), `go.mod` (module path,
last segment), `pyproject.toml` (`[project] name`), `Cargo.toml` (`[package] name`),
or the CWD directory name as a fallback.

Write `AGENTS.md` using only the content that was found or provided. Omit any
section — including its header — where you have nothing to say:

```markdown
# [Project name]

## Build & Test Commands
- Build: `[command]`
- Test all: `[command]`
- Test single file: `[command]`
- Lint: `[command]`
- Lint single file: `[command]`
- Type check: `[command]`
- Run: `[command]`

## Key Conventions
- [convention from Q1 answer]

## Architecture
- [note from Q2 answer]

## PR Conventions
- Agent-assisted commits should include an `Assisted-by: <model>` footer
- [convention from Q3 answer]
```

Write `CLAUDE.md` with exactly this content:

```markdown
@AGENTS.md
```

## Step 5: Review gate

After writing the files, say this exactly:

> **Review before committing.**
>
> `AGENTS.md` and `CLAUDE.md` have been written to this directory. Before committing:
>
> 1. Open `AGENTS.md` in your editor
> 2. Run each listed command to confirm it actually works
> 3. Delete anything an agent could figure out by reading the code
> 4. Apply this test to every line: *"Would removing this cause an agent to make a
>    mistake it wouldn't otherwise make?"* If not, delete it.
>
> Target: under 150 lines. Every unnecessary line makes agents slightly worse at
> following the lines that matter.

Do not offer to commit the files. Do not suggest the files are ready to use.

## Gotchas

- If no commands are found at all, still write the file and tell the user which
  files you looked in and found nothing useful
- Do not invent commands not present in config or CI — a hallucinated command is
  worse than an omitted one
- If a script name is ambiguous (e.g., `npm run check` could be lint or typecheck),
  add a brief inline note: `- Lint: \`npm run check\` (appears to run ESLint)`
- Omit the `## Architecture` and `## Key Conventions` sections entirely when the
  user skips those questions — don't leave placeholder comment lines
- Always include the `Assisted-by` footer line in `## PR Conventions` even if the
  user skips Q3 — it applies to any repo where agents contribute
- If `CLAUDE.md` already exists and contains more than `@AGENTS.md`, ask before
  overwriting it

---
name: agent-ready
description: |
  Assesses a git repository's readiness for use by AI coding agents using the agentready CLI, then walks through and addresses each gap. RHDH-aware: detects RHDH repositories and uses rhdh-repos.md context to pre-fill AGENTS.md and skip inapplicable findings. Use when asked to "assess agent readiness", "run agentready", "check how agent-ready this repo is", "make this repo agent-ready", "improve agent readiness score", "assess all RHDH repos", "batch agent readiness", or "onboard this repo for agents".
---

## Prerequisites

`uvx` is a hard dependency. Verify it is available before any other step:

```bash
uvx --version
```

If missing, stop: "`uvx` is required. Install via `pip install uv` or see [uv installation](https://docs.astral.sh/uv/getting-started/installation/)."

## Step 1: Mode selection

If no path was provided, present a structured choice:

- **Single repo** — assess the current working directory (default)
- **Batch** — assess all RHDH repositories (see Batch mode below)

If a path was provided, skip this and proceed to Step 2.

## Step 2: Setup

**Path:** Use the provided path, or `.` for the current directory. Validate it is a git repository:

```bash
git -C . rev-parse --is-inside-work-tree  # replace . with path if provided
```

If not a git repository, stop and tell the user.

**RHDH detection:** Check the repo's git remote URL:

```bash
git -C <path> remote get-url origin 2>/dev/null
```

Attempt to read `~/.claude/skills/rhdh/references/rhdh-repos.md`. If the file does not exist, skip RHDH detection and proceed with generic assessment — do not stop or warn the user. If found, check whether the remote URL matches any repo's upstream URL. If matched, note the repo name, tech stack, key paths, and conventions — these inform AGENTS.md generation and finding triage. Store as `rhdh_context`.

**Config file:** Only use a config file if the user explicitly provided one. Do not ask.

## Step 3: Run the assessment

```bash
REPORT_DIR=$(mktemp -d)  # on Windows: use %TEMP% or Python tempfile
uvx --from git+https://github.com/ambient-code/agentready agentready -- assess \
  -o "$REPORT_DIR" \
  <path>
```

Append `-c <config-path>` if the user provided a config file.

Note the value of `$REPORT_DIR` — shell variables do not persist across tool calls.

Parse `$REPORT_DIR/assessment-latest.json`. Extract:
- `overall_score`, `certification_level`
- `findings` — each with `attribute.id`, `attribute.tier`, `attribute.default_weight`, `attribute.name`, `status`, `score`, `evidence`, `remediation`

## Step 4: Present summary

```
Score: <overall_score>/100 — <certification_level>
Failing: <N> findings (<N1> Tier 1, <N2> Tier 2, ...)
```

If no failing findings, congratulate the user and stop.

Otherwise ask:

> "Fix applicable findings automatically, or review each one individually?
> **auto** (default) — apply self-contained fixes immediately; prompt only when input is needed
> **review** — prompt yes/skip/defer/quit for every finding"

Default to **auto** if the user says yes, presses Enter, or says "fix everything".

## Step 5: Work through findings

Work only through `status == "fail"` findings. Skip `not_applicable` and `pass` silently.

**Sort order:** ascending tier, then descending `attribute.default_weight` within each tier.

If `rhdh_context` is set, skip findings that clearly don't apply to the detected tech stack (e.g., lock file checks for a Bash-only repo, `src/` layout for a GitOps YAML repo) — note them in the summary.

### Auto mode

Apply each fix without prompting **unless**:

- The fix requires project-specific input (CI platform, package ecosystem)
- The finding might not apply to this repo type — present it and ask whether to apply or skip

**Skip without prompting:** ADRs, design intent, architecture decisions — these require human rationale. Note them in the final summary.

For the `agent_instructions` finding, follow the inline AGENTS.md generation in the `agent_instructions` section below — this applies in both auto and review modes.

After processing, list what was applied, prompted, and skipped, then proceed to Step 6.

### Review mode

For each finding:

```
[Tier <N>] <attribute.name> — <score>/100
Evidence: <evidence items>

Remediation: <remediation.summary>

Apply this fix? [yes / skip / defer / quit]
```

**yes** — apply the fix, then move to the next finding.
**skip** — move on; do not revisit. Use this if the finding doesn't apply to this repo.
**defer** — note it; surface again after re-run.
**quit** — stop immediately.

**ADR and design intent findings:** Do not use JSON remediation. Ask instead:

> "Do you have any architectural decisions worth capturing? Describe the decision and rationale — I'll write the ADR. Skip to add manually later."

Write only if the user provides input. Never invent rationale.

### `agent_instructions` finding (both modes)

Generate `AGENTS.md` and `CLAUDE.md` inline — do not delegate to another skill.

**Scan the repo for commands:**
- `package.json` → `scripts` entries (build, test, lint, typecheck, dev)
- `Makefile` / `GNUmakefile` → targets
- `pyproject.toml` → `[tool.pytest]`, `[tool.ruff]`, `[tool.mypy]`, `[project.scripts]`
- `.github/workflows/*.yml` → `run:` steps containing test/lint/build/typecheck keywords

**If `rhdh_context` is set:** pull key paths, tech stack, conventions, and branching model directly from the matched `rhdh-repos.md` entry — use these to pre-fill AGENTS.md sections and skip generic questions where RHDH context already answers them.

**If not RHDH (or RHDH context doesn't cover it):** ask these three questions one at a time:
1. "What are 2-3 conventions an agent couldn't discover by reading the code? Skip if none."
2. "Any non-obvious architectural decisions or places where things live unexpectedly? Skip if obvious."
3. "Any commit format, CI checks, or PR conventions agents should know? Skip if standard."

Write `AGENTS.md`:

```markdown
# <repo-name>

## Build & Test Commands
- Build: `<command>`
- Test all: `<command>`
- Test single file: `<command>`
- Lint: `<command>`
- Type check: `<command>`

## Key Conventions
<from scan + questions/rhdh_context>

## Architecture
<from questions/rhdh_context — omit if nothing to say>

## PR Conventions
- Agent-assisted commits should include an `Assisted-by: <model>` footer
<from questions>
```

Write `CLAUDE.md` with exactly: `@AGENTS.md`

Omit any section — including its header — where there is nothing to say. Do not invent content.

### Applying other fixes (both modes)

Use `remediation.steps`, `remediation.commands`, and `remediation.examples` from the JSON. Do not invent steps beyond what the JSON provides.

## Step 6: Re-run and present results

```bash
REPORT_DIR=$(mktemp -d)  # on Windows: use %TEMP% or Python tempfile
uvx --from git+https://github.com/ambient-code/agentready agentready -- assess \
  -o "$REPORT_DIR" \
  <path>
```

Show before/after:

```
Before: <old_score>/100 (<old_certification_level>)
After:  <new_score>/100 (<new_certification_level>)

Remaining failures: <N> findings
```

If remaining failures (including deferred), ask: "Would you like to continue addressing the remaining findings?" If yes, repeat Step 5.

## Batch mode

When the user selects batch assessment:

1. Ask: "What directory are your RHDH repos cloned into? (e.g. `~/git`)"
2. Find subdirectories that are git repos:

```bash
find <dir> -maxdepth 2 -name ".git" -type d | sed 's|/.git||'
```

3. For each, check if the remote URL matches a repo in `rhdh-repos.md`. Assess only matching repos.
4. Run the assessment on each matched repo (Step 3) and collect results.
5. Present a summary table:

```
Repo                        Score   Level              Failing
rhdh                        72/100  Bronze             4
rhdh-operator               45/100  Needs Improvement  11
rhdh-plugins                88/100  Silver             1
```

6. Ask: "Would you like to address findings for any of these repos?" If yes, the user picks one — run Step 3 (assessment) on that repo to get fresh findings, then run Steps 4–6 for it.

## Gotchas

- The first `uvx` run fetches and builds agentready from GitHub — this can take 30–60 seconds. Subsequent runs use the cache. If the fetch fails, stop — do not proceed without a valid report.
- Do not output the report to the repository directory — use the temp dir to avoid polluting the working tree.
- `not_applicable` findings reflect the detected language stack; do not mention them unless the user asks.
- Deferred findings surface again after the re-run.
- Never invent rationale for ADRs or design docs. In auto mode, skip them. In review mode, ask for rationale before writing anything.
- In batch mode, only assess repos whose remote URL matches `rhdh-repos.md` — do not assess unrelated repos in the same directory.
- `rhdh-repos.md` is expected at `~/.claude/skills/rhdh/references/rhdh-repos.md` — the default install path when using `npx skills add redhat-developer/rhdh-skill`. If the `rhdh` skill was installed to a different prefix, RHDH detection will silently degrade to generic mode. This is by design — no error, no warning.

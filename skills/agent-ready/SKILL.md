---
name: agent-ready
description: |
  Assesses a git repository's readiness for use by AI coding agents using the agentready CLI, then walks through and addresses each gap. Use when asked to "assess agent readiness", "run agentready", "check how agent-ready this repo is", "make this repo agent-ready", "improve our agent readiness score", "run the agent ready CLI", "assess this repo for AI agents", or "what's our agentready score".
---

## Prerequisites

`uvx` is a hard dependency. Verify it is available before any other step:

```bash
uvx --version
```

If missing, stop: "`uvx` is required. Install via `pip install uv` or see [uv installation](https://docs.astral.sh/uv/getting-started/installation/)."

## Step 1: Setup

**Path:** Default to the current working directory. If the user provided a path, use that instead. Validate it is a git repository:

```bash
git -C . rev-parse --is-inside-work-tree  # replace . with the user-provided path if one was given
```

If not a git repository, stop and tell the user.

**Config file:** Only use a config file if the user explicitly provided one. Do not ask. If a path was given, verify it exists before proceeding.

## Step 2: Run the assessment

Create a temp directory and run the assessment:

```bash
REPORT_DIR=$(mktemp -d)  # on Windows: use %TEMP% or Python tempfile
uvx --from git+https://github.com/ambient-code/agentready agentready -- assess \
  -o "$REPORT_DIR" \
  .  # replace . with the user-provided path if one was given
```

Append `-c <config-path>` to the command if the user provided a config file.

Note the value of `$REPORT_DIR` — shell variables do not persist across tool calls and Step 5 will need it.

Parse `$REPORT_DIR/assessment-latest.json`. Extract:
- `overall_score`, `certification_level`
- `findings` — each with `attribute.id`, `attribute.tier`, `attribute.default_weight`, `attribute.name`, `status`, `score`, `evidence`, `remediation`

## Step 3: Present summary

Show a brief summary before diving into findings:

```
Score: <overall_score>/100 — <certification_level>
Failing: <N> findings (<N1> Tier 1, <N2> Tier 2, ...)
```

If there are no failing findings, congratulate the user and stop — do not ask to work through anything.

Otherwise ask:

> "Fix applicable findings automatically, or review each one individually?
> **auto** (default) — apply self-contained fixes immediately; prompt only when input is needed
> **review** — prompt yes/skip/defer/quit for every finding"

Default to **auto** if the user just says yes, presses Enter, or says "fix everything".

## Step 4: Work through findings

Work only through findings where `status == "fail"`. Skip `not_applicable` and `pass` findings silently.

**Sort order:** ascending tier (Tier 1 first), then descending `attribute.default_weight` within each tier.

### Auto mode

Apply each fix without prompting **unless** any of the following are true — in which case, pause and prompt:

- The fix requires project-specific input (CI platform, package ecosystem, project name, language)
- The finding might not apply to this repo type (e.g., `src/` layout for a GitOps YAML repo, lock files for a repo with no package dependencies) — present it and ask whether to apply or skip
- It is the `agent_instructions` finding — always delegate to `init-agents-md` interactively

**Skip without prompting** findings that require human rationale to be meaningful — ADRs, design intent, and architecture decisions. These cannot be generated without fabricating context the agent doesn't have.

After processing all findings, list what was applied, what was prompted, and what was skipped, then proceed to Step 5.

### Review mode

For each finding, present:

```
[Tier <N>] <attribute.name> — <score>/100
Evidence: <evidence items, one per line>

Remediation: <remediation.summary>

Apply this fix? [yes / skip / defer / quit]
```

**yes** — apply the fix (see special cases below), then move to the next finding.  
**skip** — move on; do not revisit. Use this if the finding doesn't apply to this repo.  
**defer** — note it; present again after the re-run.  
**quit** — stop immediately.

**ADR and design intent findings in review mode:** Do not present the JSON remediation. Instead ask:

> "Do you have any architectural decisions worth capturing here? If so, describe the decision and why it was made — I'll write the ADR. Skip if you'd prefer to add these manually later."

If the user provides input, write the ADR or design doc using their rationale. If they skip, move on.

### Special case: `agent_instructions` finding (both modes)

Do not apply the JSON remediation. Instead, invoke the `init-agents-md` skill:

> "Invoking the `init-agents-md` skill to create AGENTS.md for this repository."

Use the Skill tool: `init-agents-md`. After it completes, return to this skill and continue with the next finding.

### Applying fixes (auto and review modes)

Use the `remediation.steps`, `remediation.commands`, and `remediation.examples` from the JSON as the implementation guide. Do not invent steps beyond what the JSON provides.

## Step 5: Re-run and present results

Re-run the assessment (shell variables from Step 2 do not persist — create a new temp dir):

```bash
REPORT_DIR=$(mktemp -d)  # on Windows: use %TEMP% or Python tempfile
uvx --from git+https://github.com/ambient-code/agentready agentready -- assess \
  -o "$REPORT_DIR" \
  .  # or user-provided path
```

Include `-c <config-path>` if the user provided a config file.

Show before/after:

```
Before: <old_score>/100 (<old_certification_level>)
After:  <new_score>/100 (<new_certification_level>)

Remaining failures: <N> findings
```

If there are remaining failures (including deferred ones), ask:

> "Would you like to continue addressing the remaining findings?"

If yes, repeat Step 4 with the remaining failures. If no, stop.

## Gotchas

- The first `uvx` run fetches and builds agentready from GitHub — this can take 30–60 seconds. Subsequent runs use the cache and are much faster. If the fetch fails (network error, build error), tell the user and stop — do not attempt to proceed without a valid report.
- Do not output the report to the repository directory — use the temp dir to avoid polluting the working tree.
- `not_applicable` findings reflect the detected language stack; do not mention them unless the user asks.
- Deferred findings are not lost — they surface again after the re-run.
- Never invent rationale for ADRs, design docs, or architecture decisions — these require human context the agent doesn't have. In auto mode, skip them. In review mode, ask the user for the rationale before writing anything.

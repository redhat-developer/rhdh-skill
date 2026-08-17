# Assess a repository

Load this reference for a single-repository assessment, whether the user wants
only the report or wants to improve the repository afterward.

## Prerequisite

Verify `uvx` before any other step:

```bash
uvx --version
```

If it is unavailable, stop and tell the user that `uv` is required. Do not
produce an assessment without a valid agentready report.

## Select and inspect the repository

Use the provided path or the current directory. Verify that it is a git worktree
with `git -C <path> rev-parse --is-inside-work-tree` and stop if validation
fails.

Read the origin remote. If it identifies an RHDH repository, use
`/rhdh-context` to obtain repository-specific technology, paths, and
conventions. If RHDH context is unavailable, continue with a generic assessment
without warning.

Use a configuration file only when the user explicitly supplied one.

## Run agentready

Create a fresh directory under the operating system's temporary directory and
retain its absolute path across tool calls. Run:

```bash
uvx --from git+https://github.com/ambient-code/agentready agentready -- assess \
  -o <temporary-report-directory> \
  <repository-path>
```

Add `-c <config-path>` only for a user-supplied configuration.

Parse `assessment-latest.json`. Extract the overall score, certification level,
and each finding's id, tier, weight, name, status, score, evidence, and
remediation.

## Present the assessment

Show:

```text
Score: <score>/100 — <certification>
Failing: <count> findings (<count by tier>)
Report: <absolute report path>
```

If nothing fails, finish. Otherwise ask whether to apply self-contained fixes
automatically or review every finding. Treat "yes", "fix everything", or an
empty choice as automatic mode.

Return to the skill router when the user wants fixes; the remediation branch
loads after the assessment is complete.

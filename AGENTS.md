# AGENTS.md

Agent skills for Red Hat Developer Hub (RHDH) plugin development, overlay management, and local testing. Orchestrator skill (`rhdh`) routes to specialized sub-skills (`overlay`, `rhdh-local`, `create-*`). Skills follow the [Agent Skills open standard](https://agentskills.io/specification). See `CONTEXT.md` for domain language and `docs/adr/` for architectural decisions.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- If you write 200 lines and it could be 50, rewrite it.

CLIs in this project use stdlib-only Python (see `docs/adr/0002-stdlib-only-python-clis.md`). Don't introduce dependencies.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to what was asked.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

Run `uv run pytest` before reporting any task complete. Do not report completion based on code existing — verify it works.

## 5. No Irreversible Commands Without Confirmation

Never force push, reset HEAD, merge branches, or run destructive commands without asking. If unsure whether a command is destructive, ask.

## 6. Learn From Corrections

If told an implementation was wrong, apply the correction and then record what went wrong so the same mistake is not repeated. Patterns and gotchas specific to this project belong in the relevant `references/` file under each skill.

---

## Versioning

Single version kept in sync across three files:

- `pyproject.toml` — Python package version
- `.claude-plugin/plugin.json` — plugin manifest
- `.claude-plugin/marketplace.json` — marketplace listing (2 occurrences)

### When to bump

Include a **patch** version bump (`x.y.Z`) in any PR that changes skill behavior, scripts, or SKILL.md files. Use **minor** (`x.Y.0`) for new skills/features, **major** (`X.0.0`) for breaking changes. Do NOT bump for docs-only or CI-only changes.

### How to bump

1. Read the current version from `pyproject.toml`.
2. Compute the new version (patch/minor/major as appropriate).
3. Update all three files (4 occurrences total) in the same commit.
4. The PR title should include the new version, e.g., `feat: add foo skill (v0.4.0)`.

### Git tags

The `skills` CLI (`npx skills add`) resolves versions via git tags, not from the JSON version fields. After merging a version-bump PR, create a tag: `git tag v<VERSION> && git push origin v<VERSION>`.

## Shared modules (lifecycle ↔ prow)

`skills/prow/scripts/rhdh_prow/repo.py` and `skills/prow/scripts/rhdh_prow/yaml.py` are copies of `skills/lifecycle/scripts/rhdh_lifecycle/repo.py` and `skills/lifecycle/scripts/rhdh_lifecycle/yaml.py`. The only difference is the internal import path (`rhdh_prow.repo` vs `rhdh_lifecycle.repo`). When modifying either copy, update both to keep them in sync.

`skills/prow/scripts/rhdh_prow/utils.py` is a subset of `skills/lifecycle/scripts/rhdh_lifecycle/utils.py`. When modifying either copy, update both to keep them in sync.

## Agent skills

### Issue tracker

GitHub Issues via `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context (`CONTEXT.md` + `docs/adr/` at root). See `docs/agents/domain.md`.

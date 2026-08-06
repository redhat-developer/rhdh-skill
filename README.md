# RHDH Skill

Agent skills for the Red Hat Developer Hub team. Covers plugin development, overlay management, local testing, Jira workflows, and day-to-day RHDH engineering — so your agent knows the ecosystem instead of hallucinating through it.

> **Quick start:** `npx skills add -g redhat-developer/rhdh-skill` — works with [50+ coding agents](https://github.com/vercel-labs/skills#supported-agents).

## Why This Exists

RHDH spans a dozen repositories, four Jira projects, version-specific Backstage compatibility, overlay CI pipelines, and a copy-sync customization system for local testing. Without guidance, agents hallucinate version numbers, use the legacy backend system, construct OCI URLs by hand, and miss project-specific conventions that are impossible to learn from training data alone.

These skills encode the gotchas, workflows, and tribal knowledge so you don't re-explain them every session.

## How It Works

The [`rhdh`](./skills/rhdh/SKILL.md) skill is the primary entry point. It detects your environment (tools, repos, auth), runs doctor checks, and routes to the right sub-skill based on what you're doing — overlay management, plugin creation, local testing, Jira, CI, and so on. You don't need to remember which skill to invoke; just describe your task and `rhdh` figures it out.

Under the hood, `rhdh` maintains a config file (`~/.config/rhdh-skill/config.json`) that maps short keys to your local git checkouts. Once configured, any skill can locate the right repo without you specifying paths each time:

| Key | Repository | Key | Repository |
|-----|-----------|-----|-----------|
| `rhdh` | rhdh | `overlay` | rhdh-plugin-export-overlays |
| `downstream` | rhdh (midstream) | `export-utils` | rhdh-plugin-export-utils |
| `cli` | rhdh-cli | `catalog` | rhdh-plugin-catalog |
| `plugins` | rhdh-plugins | `operator` | rhdh-operator |
| `chart` | rhdh-chart | `local` | rhdh-local |
| `factory` | rhdh-dynamic-plugin-factory | `backstage` | backstage |

Run `rhdh doctor` at any time to check your environment — missing tools, unconfigured repos, and auth issues are flagged with fix instructions.

## What's Inside

### Plugin Development

Build dynamic plugins from scratch — backend or frontend — and get them deployed.

- **[create-plugin](./skills/create-plugin/SKILL.md)** — Full plugin lifecycle: scaffold, implement, export, package, and wire RHDH dynamic plugins. Sub-commands for `backend`, `frontend`, `export`, and `wiring`.
  - **[backend](./skills/create-plugin/references/backend.md)** — Backend plugins (APIs, scaffolder actions, catalog processors) using the new backend system.
  - **[frontend](./skills/create-plugin/references/frontend.md)** — Frontend plugins (pages, entity cards, themes) with Scalprum federation.
  - **[export](./skills/create-plugin/references/export.md)** — Export, package (OCI/tgz/npm), and push to a container registry.
  - **[wiring](./skills/create-plugin/references/wiring.md)** — Analyze plugin source and generate `dynamic-plugins.yaml` wiring config.

### NFS Migration

Migrate your plugins from the legacy Backstage frontend system to the New Frontend System (NFS).

- **[nfs-migration](./skills/nfs-migration/SKILL.md)** -- Analyzes your existing plugin, applies the right Blueprint patterns, updates exports, and verifies the result. Two approaches: alpha (default, NFS at `./alpha`) or colocated (NFS + legacy both from root). Reference files cover every extension type, mount point mapping, operator config, gotchas, and verification.

### Backstage Upgrade

Upgrade `@backstage/*` dependencies in your plugin to align with a target RHDH or Backstage release.

- **[backstage-upgrade](./skills/backstage-upgrade/SKILL.md)** -- Discovers current versions, determines the target using the RHDH→Backstage version matrix, runs `backstage-cli versions:bump`, migrates moved packages, guides through breaking changes from upstream changelogs, and verifies the result. Composable — the NFS migration skill chains into it automatically when deps are outdated.

### Extensions Catalog

Manage plugins in the [rhdh-plugin-export-overlays](https://github.com/redhat-developer/rhdh-plugin-export-overlays) repository.

- **[overlay](./skills/overlay/SKILL.md)** — Onboard new plugins, update versions, fix CI failures, triage and analyze PRs, trigger `/publish`. Covers both plugin-owner and core-team workflows.

### Konflux / Tekton

Update Konflux task digests and apply `MIGRATION.md` pipeline changes in [rhdh-plugin-catalog](https://gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog) or [rhdh](https://gitlab.cee.redhat.com/rhidp/rhdh) midstream.

- **[konflux-tekton-updates](./skills/konflux-tekton-updates/SKILL.md)** — Run `.tekton/updateDigests.sh --minor --no-push`, apply task migrations from [build-pipeline-tasks](https://github.com/konflux-ci/build-pipeline-tasks) (and related repos; see [migration-urls](./skills/konflux-tekton-updates/references/migration-urls.md)), update shared pipelines/templates and PLR generators. Repo-specific file lists: [plugin-catalog](./skills/konflux-tekton-updates/references/plugin-catalog.md), [RHDH midstream](./skills/konflux-tekton-updates/references/rhdh-midstream.md).

```bash
npx skills add redhat-developer/rhdh-skill --skill konflux-tekton-updates
```

### Platform Lifecycle

Check version support status for platforms and integrations used by RHDH.

- **[lifecycle](./skills/lifecycle/SKILL.md)** — Check version lifecycle and support status for OCP, AKS, EKS, GKE, RHDH releases, RHBK, Quay, PostgreSQL, and any Red Hat product via the Product Life Cycles API.

### CI / Prow

Manage Prow CI job configurations and trigger nightly E2E tests.

- **[prow](./skills/prow/SKILL.md)** — Manage Prow CI job configurations for RHDH in the openshift/release repository. List, generate, add, and remove OCP test entries and cluster pools. List K8s platform test entries (AKS, EKS, GKE). Analyze coverage gaps. Commission new release branches and decommission end-of-life ones.
- **[prow-trigger-nightly](./skills/prow-trigger-nightly/SKILL.md)** — Trigger RHDH nightly ProwJobs on demand via the OpenShift CI Gangway REST API. Supports both rhdh and rhdh-plugin-export-overlays repos with Gangway overrides for catalog index image, chart version, and Playwright version.

### Base image

Bump UBI / RHEC base image tags, refresh RPM lockfiles, and align node headers / go.mod in **rhdh**, **rhdh-operator**, and **rhdh-must-gather** (see [rhdh-repos](./skills/rhdh/references/rhdh-repos.md)).

- **[base-images-and-rpms](./skills/base-images-and-rpms/SKILL.md)** — Weekly upstream maintenance: `updateBaseImages.sh`, `rpm-lockfile-prototype`, node headers, and go.mod (main only). Use `--analyze` for read-only Containerfile/Dockerfile scan before updating. Requires `skopeo login registry.redhat.io`.

```bash
npx skills add redhat-developer/rhdh-skill --skill base-images-and-rpms
```

### Local Testing

Test plugins in a local RHDH instance before deploying.

- **[rhdh-local](./skills/rhdh-local/SKILL.md)** — Enable/disable plugins, switch between customized and pristine configs, run health checks, backup/restore configurations via the `rhdh-local-setup` customization system.

### Jira

Track work across the four RHDH Jira projects.

- **[rhdh-jira](./skills/rhdh-jira/SKILL.md)** — Search, create, view, edit, transition, link, assign, and refine issues across RHIDP, RHDHPLAN, RHDHBUGS, and RHDHSUPP. Uses `acli` for simple operations, GraphQL for bulk reads, and REST API as fallback. Sub-commands:
  - **[assign](./skills/rhdh-jira/references/assign.md)** — Recommend assignees using team expertise profiling, sprint capacity analysis, and context proximity scoring. Supports deep mode (5-layer analysis via GraphQL) and quick mode (match from existing context). Assigns after user confirmation.
  - **[refine](./skills/rhdh-jira/references/refine.md)** — Check issues against RHDH workflow exit criteria, detect duplicates, verify parent/child hierarchy, flag unaddressed comments, identify stale issues, and validate sprint readiness.
  - **[plan](./skills/rhdh-jira/references/plan.md)** — Sprint planning prep: carryover report, velocity trend, per-member capacity, ready-for-planning queue, and sprint fill suggestions with expertise matching.
  - **[sprint-report](./skills/rhdh-jira/references/sprint-report.md)** — Sprint review summary: committed vs completed, per-member breakdown, epic progress, demo checklist with naming conventions, and velocity trend.
  - **[release](./skills/rhdh-jira/references/release.md)** — Release readiness: feature matrix, Program Increment funnel, epic roll-up, cross-team dependency map, blocker bugs, release notes readiness, and risk assessment.
  - **[to-feature](./skills/rhdh-jira/references/to-feature.md)** — Create a RHDHPLAN Feature from conversation context. Grills on scope, customer value, and acceptance criteria. Optionally chains into Epic decomposition.
  - **[to-epic](./skills/rhdh-jira/references/to-epic.md)** — Create an RHIDP Epic. Grills on delivery scope, dependencies, and acceptance criteria. Optionally chains into Story/Task decomposition.
  - **[to-issue](./skills/rhdh-jira/references/to-issue.md)** — Create a Story, Task, Bug, or Spike with automatic type inference. Grills on implementation details and story points.
  - **[update-jira-status](./skills/rhdh-jira/references/update-jira-status.md)** — Update an issue with session progress. Detects the related issue, adds a status comment, proposes transitions, and checks upward cascade to parent Epic/Feature.

### PR Workflow

Automate the full PR lifecycle — build, changeset, commit, push, and create — for plugin monorepos.

- **[raise-pr](./skills/raise-pr/SKILL.md)** — Full PR workflow for `rhdh-plugins` and `community-plugins`: detect workspace from staged changes, run build/validation, generate changesets, commit with sign-off, push, and create the GitHub PR. Auto-detects which repo you're in. Supports `--a` auto-approve mode to skip all approval gates. Accepts an optional Jira key or URL to link the PR — adds Web Link, comment, and transitions the issue to Review.

### Bug Fix

Reproduce, diagnose, fix, and PR RHDH plugin bugs from Jira tickets with automated Playwright-based before/after screen recordings.

- **[bug-fix](./skills/bug-fix/SKILL.md)** — End-to-end bug fix workflow: fetch Jira issue, map component to workspace, write Playwright reproduction test with video recording, diagnose root cause, apply fix, verify, and create PR with before/after recordings embedded. Chains into `raise-pr` for the full PR lifecycle including post-PR Jira updates.

### PR Review

- **[rhdh-pr-review](./skills/rhdh-pr-review/SKILL.md)** — PR code review with inline comments (GitHub, GitLab planned) and live cluster testing for rhdh-operator PRs. Layered architecture: fetch → analyze → post.

### Test Plan

- **[rhdh-test-plan-review](./skills/rhdh-test-plan-review/SKILL.md)** — Reviews an RHDH test plan Jira ticket and suggests platform/integration version updates based on support lifecycle pages and RHDH release milestones

### Backport

Automate or semi-automate backporting changes to RHDH release branches. Uses `release-x.y/{plugin}` branches directly — supports concurrent backports without conflicts.

- **[backport-auto](./skills/backport-auto/SKILL.md)** — Fully automated end-to-end backport workflow. Detects plugin, cherry-picks with AI conflict resolution, creates and merges PRs, handles Version Packages, updates overlays, and creates changelog PR. Zero intervention required.

- **[backport-create](./skills/backport-create/SKILL.md)** — Semi-manual workflow for controlled backports. Creates backport PR and stops for user review. You manually review and merge, then run `backport-finish` to complete.

- **[backport-finish](./skills/backport-finish/SKILL.md)** — Completes the backport workflow after manual PR merge. Handles Version Packages detection/merge, overlays update, and changelog PR.

```bash
# Full automation
/backport-auto 1.10 3456

# Step-by-step with control
/backport-create 1.10 3456
# ... manually review and merge PR ...
/backport-finish 1.10 3456
```

### Test Placement

Decide where a test belongs across the RHDH ecosystem — which repo, which layer, and how to scaffold it.

- **[test-placement](./skills/test-placement/SKILL.md)** — Given a change, bug, or feature, proposes the right repo (`rhdh-plugins` / `rhdh-plugin-export-overlays` / `rhdh`), the right test layer (L1 unit → L4b cluster e2e), the location, and scaffolding steps. Guiding rule: the cheapest environment that catches the bug wins. Encodes the RHIDP-13501 responsibility split and researched dead-ends so devs don't burn time on them.

### Orchestration

- **[rhdh](./skills/rhdh/SKILL.md)** — Entry point and router. Detects your environment, runs `doctor` checks, maintains a cross-session worklog, and routes to the right skill. Start here if you're not sure what you need.

### Repository Readiness

- **[agent-ready](./skills/agent-ready/SKILL.md)** — Assess RHDH repositories against agentready criteria and address each gap. RHDH-aware: detects the repo from its remote URL, uses `rhdh-repos.md` context to pre-fill `AGENTS.md` and skip inapplicable findings. Supports single-repo and batch modes (assess all RHDH repos in one pass).

### Meta

- **[skill-maker](./skills/skill-maker/SKILL.md)** — Create new skills or consolidate existing ones following the [Agent Skills open standard](https://agentskills.io/specification). Interviews you about scope and edge cases before drafting.

## Getting Started

1. **Install globally** (recommended — `rhdh` manages paths across multiple repos):

   ```bash
   npx skills add -g redhat-developer/rhdh-skill
   ```

2. **Talk to your agent.** Mention what you're working on and `rhdh` takes care of the rest — including first-time setup:

   ```
   You: "I need to onboard the aws-appsync plugin to the Extensions Catalog"

   Agent: runs rhdh doctor, detects missing config
   Agent: runs rhdh config init, finds your local repos
   Agent: routes to the overlay skill, starts the onboard workflow
   ```

   On the first run, `rhdh` auto-detects your local checkouts and creates `~/.config/rhdh-skill/config.json`. If a repo isn't found automatically, the agent will ask you for its path.

## Installation

### Global install (recommended)

```bash
npx skills add -g redhat-developer/rhdh-skill
```

Global install is the right default — `rhdh` manages paths across multiple repos via its config, so it doesn't need to live inside any single project.

### Project-scope install

For single-repo use (e.g., only the `create-plugin` skill inside one plugin repo):

```bash
npx skills add redhat-developer/rhdh-skill
```

Supports Claude Code, Cursor, Codex, Pi, and [50+ more](https://github.com/vercel-labs/skills#supported-agents).

```bash
# List available skills without installing
npx skills add redhat-developer/rhdh-skill --list

# Install a specific skill only
npx skills add redhat-developer/rhdh-skill --skill create-plugin

# Target a specific agent
npx skills add redhat-developer/rhdh-skill -a claude-code
```

### Update

```bash
npx skills add -g redhat-developer/rhdh-skill -y
```

### Local Checkout (development)

```bash
npx skills add ./path/to/rhdh-skill
```

## Development

```bash
uv sync --extra dev                  # Install dev dependencies
git config core.hooksPath .githooks  # Enable pre-commit hooks (one-time)
uv run pytest                        # Run tests
```

The `core.hooksPath` setting points git at the checked-in `.githooks/` directory. If `pre-commit` is installed, linting and tests run automatically on every commit. If not, commits proceed with a warning.

See [AGENTS.md](./AGENTS.md) for contribution guidelines and architectural decisions.

## License

Apache-2.0 — see [LICENSE](./LICENSE).

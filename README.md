# RHDH Skill

Agent skills for the Red Hat Developer Hub team. Covers plugin development, overlay management, local testing, Jira workflows, and day-to-day RHDH engineering — so your agent knows the ecosystem instead of hallucinating through it.

> **Quick start:** `npx skills add redhat-developer/rhdh-skill` — works with [50+ coding agents](https://github.com/vercel-labs/skills#supported-agents).

## Why This Exists

RHDH spans a dozen repositories, four Jira projects, version-specific Backstage compatibility, overlay CI pipelines, and a copy-sync customization system for local testing. Without guidance, agents hallucinate version numbers, use the legacy backend system, construct OCI URLs by hand, and miss project-specific conventions that are impossible to learn from training data alone.

These skills encode the gotchas, workflows, and tribal knowledge so you don't re-explain them every session.

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

Start with the **[NFS Migration Guide](./docs/nfs-migration-guide.md)** -- it covers what NFS is, why you need to migrate, the deprecation timeline, and walks through every migration pattern with code examples.

When you're ready to migrate, use the Agent Skill to automate it:

- **[nfs-migration](./skills/nfs-migration/SKILL.md)** -- Analyzes your existing plugin, applies the right Blueprint patterns, updates exports, and verifies the result. Two approaches: direct-to-GA (recommended) or phased with backward compatibility.

### Backstage Upgrade

Upgrade `@backstage/*` dependencies in your plugin to align with a target RHDH or Backstage release.

- **[backstage-upgrade](./skills/backstage-upgrade/SKILL.md)** -- Discovers current versions, determines the target using the RHDH→Backstage version matrix, runs `backstage-cli versions:bump`, migrates moved packages, guides through breaking changes from upstream changelogs, and verifies the result. Composable — the NFS migration skill chains into it automatically when deps are outdated.

### Extensions Catalog

Manage plugins in the [rhdh-plugin-export-overlays](https://github.com/redhat-developer/rhdh-plugin-export-overlays) repository.

- **[overlay](./skills/overlay/SKILL.md)** — Onboard new plugins, update versions, fix CI failures, triage and analyze PRs, trigger `/publish`. Covers both plugin-owner and core-team workflows.

### Konflux / Tekton

Update Konflux task digests and apply `MIGRATION.md` pipeline changes in [rhdh-plugin-catalog](https://gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog) or [rhdh](https://gitlab.cee.redhat.com/rhidp/rhdh) midstream.

- **[konflux-tekton-updates](./skills/konflux-tekton-updates/SKILL.md)** — Run `.tekton/updateDigests.sh --minor --no-push`, apply [build-definitions](https://github.com/konflux-ci/build-definitions) task migrations, update shared pipelines/templates and PLR generators. Repo-specific file lists: [plugin-catalog](./skills/konflux-tekton-updates/references/plugin-catalog.md), [RHDH midstream](./skills/konflux-tekton-updates/references/rhdh-midstream.md).

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

Bump UBI / RHEC base image tags and refresh `@sha256` digests in **rhdh** and **rhdh-operator** (see [rhdh-repos](./skills/rhdh/references/rhdh-repos.md)).

- **[update-base-image](./skills/update-base-image/SKILL.md)** — Analyze and update Containerfile / Dockerfile using [rhdh-downstream](./skills/rhdh/references/rhdh-repos.md#rhdh-downstream) scripts (`build/scripts/`). Tags must be `major.minor-buildid` or `x.y.z-buildid`; bare numeric registry tags are ignored. Bundled `analyze-base-images.sh`; run `updateBaseImages.sh` per repo. Requires `skopeo login registry.redhat.io`.

```bash
npx skills add redhat-developer/rhdh-skill --skill update-base-image
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

### PR Review

- **[rhdh-pr-review](./skills/rhdh-pr-review/SKILL.md)** — PR code review with inline comments (GitHub, GitLab planned) and live cluster testing for rhdh-operator PRs. Layered architecture: fetch → analyze → post.

### Test Plan

- **[rhdh-test-plan-review](./skills/rhdh-test-plan-review/SKILL.md)** — Reviews an RHDH test plan Jira ticket and suggests platform/integration version updates based on support lifecycle pages and RHDH release milestones

### Orchestration

- **[rhdh](./skills/rhdh/SKILL.md)** — Entry point and router. Detects your environment, runs `doctor` checks, maintains a cross-session worklog, and routes to the right skill. Start here if you're not sure what you need.

### Repository Readiness

- **[agent-ready](./skills/agent-ready/SKILL.md)** — Assess RHDH repositories against agentready criteria and address each gap. RHDH-aware: detects the repo from its remote URL, uses `rhdh-repos.md` context to pre-fill `AGENTS.md` and skip inapplicable findings. Supports single-repo and batch modes (assess all RHDH repos in one pass).

### Meta

- **[skill-maker](./skills/skill-maker/SKILL.md)** — Create new skills or consolidate existing ones following the [Agent Skills open standard](https://agentskills.io/specification). Interviews you about scope and edge cases before drafting.

## Getting Started

Install the skills, then just talk to your agent. Mention what you're working on — onboarding a plugin, triaging PRs, creating a new backend module, checking Jira issues — and the right skill activates automatically.

If your agent doesn't pick up the right skill, or you want to start from the top, the `rhdh` orchestrator skill runs environment checks and routes you:

```
Tell my agent: "I need to onboard a new plugin to the Extensions Catalog"
```

Not everything needs every tool. Each skill checks for its own prerequisites and tells you what's missing.

## Installation

### Skills CLI (any agent)

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

### Claude Code Plugin Marketplace

```bash
claude plugin marketplace add redhat-developer/rhdh-skill
claude plugin install --scope project rhdh
```

### Local Checkout (development)

```bash
npx skills add ./path/to/rhdh-skill
```

> **Note:** Always install in project scope. The skills reference repository-specific paths.

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

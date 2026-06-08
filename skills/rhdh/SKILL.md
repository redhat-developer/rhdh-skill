---
name: rhdh
description: >-
  Handles all RHDH-related work — "RHDH", "Red Hat Developer Hub", or "Developer
  Hub". Primary entry point for plugin development, overlay management,
  environment setup, repo navigation, version compatibility, CI/CD,
  configuration, debugging, and general RHDH ecosystem knowledge. Routes to
  specialized sub-skills as needed. Use when asked about RHDH version
  compatibility, RHDH CI pipeline, RHDH configuration, which RHDH repo to use,
  RHDH release status, RHDH debugging, or any Developer Hub question.
---

<cli_setup>
**Locate and set the CLI variable:**

The CLI script is at `scripts/rhdh` **relative to this SKILL.md file** (not the working directory).

When you read this file, note its path and derive the script location:

- If SKILL.md is at `/path/to/skills/rhdh/SKILL.md`
- Then the CLI is at `/path/to/skills/rhdh/scripts/rhdh`

```bash
RHDH="/path/to/skills/rhdh/scripts/rhdh"  # Use the actual path
```

**Get oriented (run first):**

```bash
$RHDH
```

This shows environment status, discovered repos, and available tools.
</cli_setup>

<essential_principles>

<principle name="track_activity">
Use `$RHDH log` and `$RHDH todo` to maintain context across sessions.
Log milestones with tags. Create todos when blocked on external input.
This enables resuming work without re-explaining context and builds an audit trail.
See the `<tracking_system>` section for details.
</principle>

<principle name="consult_tool_references">
**Before using GitHub CLI**, read the reference file:
- **GitHub:** `references/github-reference.md` — PR queries, CI analysis, `/publish` triggers

Contains critical gotchas (jq escaping, assignee format) that prevent common errors.
</principle>

<principle name="understand_rhdh_repos">
**Before any RHDH-related work**, consult `references/rhdh-repos.md` for a reference of all RHDH-related repositories, what each one is used for, and how they relate to each other.
Use this when navigating between projects or understanding the overall RHDH ecosystem.
Use `$RHDH config set` to set the path to the local checkout of the RHDH repositories.
</principle>

</essential_principles>

<context_scan>
**Run on invocation to understand current state:**

```bash
$RHDH
```

This checks:

- Overlay repo location and status
- rhdh-local availability
- gh CLI authentication
- Container runtime (podman/docker)

**If repos not found:** Run `$RHDH config init` to auto-detect or configure paths.
</context_scan>

<intake>
## Step 1: Run CLI

```bash
$RHDH
```

**If `needs_setup: true`:** Stop and run `$RHDH doctor` to fix setup issues.

---

## Step 2: Identify Task Type

What would you like to do?

### Overlay Repository Tasks

*For working with the rhdh-plugin-export-overlays repository*

1. **Onboard a new plugin** — Add upstream plugin to Extensions Catalog
2. **Update plugin version** — Bump to newer upstream commit/tag
3. **Fix build failure** — Debug CI/publish issues
4. **Triage overlay PRs** — Prioritize open PRs by criticality
5. **Analyze specific PR** — Check assignment, compatibility, merge readiness

### Plugin Creation Tasks

*For creating new RHDH dynamic plugins from scratch*

6. **Create plugin** — Bootstrap, export, package, or wire a dynamic plugin (backend or frontend)

### Local Testing Tasks

*For testing plugins in a local RHDH instance using rhdh-local-setup*

7. **Local testing** — Enable/disable/test plugins in local RHDH

### Review & Testing Tasks

*For testing PR changes on a live RHDH cluster*

8. **Review operator PR** — Deploy PR operator bundle on cluster and get review checklist

### Test Plan Tasks

*For rhdh test plan review in jira*

9. **Review Test Plan content** — Reviews an RHDH test plan Jira ticket and suggests platform/integration version updates based on support lifecycle pages and RHDH release milestones

### Release Management Tasks

*For RHDH release tracking, status, announcements*

10. **Release management** — Release dates, status, team breakdown, freeze announcements, blocker bugs, CVEs, release notes

### General Tasks

11. **Check environment** — Run doctor, configure paths
12. **View/search activity** — Review worklog, todos

**Wait for response before proceeding.**
</intake>

<routing>
### Doctor Route (Priority)

| Condition | Action |
|-----------|--------|
| `needs_setup: true` in CLI output | Run `$RHDH doctor` |

**Always check this first.**

### Overlay Repository Routes

| Response | Skill |
|----------|-------|
| 1-5, "onboard", "update", "fix", "triage", "PR", "overlay", "plugin", "workspace" | Route to `@overlay` skill |

**To route:** Read `../overlay/SKILL.md` and follow its intake process.

### Plugin Creation Routes

| Response | Skill |
|----------|-------|
| 6, "backend plugin", "create backend", "frontend plugin", "create frontend", "export", "package", "OCI", "publish plugin", "wiring", "mount points", "routes", "entity tabs" | Route to `@create-plugin` skill |

**To route:** Read `../create-plugin/SKILL.md` and follow its routing rules (backend, frontend, export, wiring sub-commands).

### Local Testing Routes

| Response | Skill |
|----------|-------|
| 7, "local", "test locally", "enable plugin", "disable plugin", "local testing", "rhdh-local-setup" | Route to `@rhdh-local` skill |

**To route:** Read `../rhdh-local/SKILL.md` and follow its intake process.

### Review & Testing Routes

| Response | Skill |
|----------|-------|
| 8, "review PR", "code review", "PR review", "test PR", "operator PR", "review this PR", "rhdh-pr-review" | Route to `@rhdh-pr-review` skill |

**To route:** Read `../rhdh-pr-review/SKILL.md` and follow its intake process.

### Test Plan Routes

| Response | Skill |
|----------|-------|
| 9, "review test plan", "update test plan", "check platform versions in test plan", "review RHDH test plan" | Route to `@rhdh-test-plan-review` skill |

**To route:** Read `../rhdh-test-plan-review/SKILL.md` and follow its intake process.

### Release Management Routes

| Response | Skill |
|----------|-------|
| 10, "release", "release manager", "release dates", "release status", "feature freeze", "code freeze", "blocker bugs", "CVEs", "release notes", "team breakdown", "freeze announcement" | Route to `@rhdh-release` skill |

**To route:** Read `../rhdh-release/SKILL.md` and follow its intake process.

### Backstage Upgrade Routes

| Response | Skill |
|----------|-------|
| "upgrade backstage", "bump backstage", "update @backstage", "backstage version", "align deps", "versions:bump" | Route to `backstage-upgrade` skill |

**To route:** Read `../backstage-upgrade/SKILL.md` and follow its intake process.

### General Routes

| Response | Action |
|----------|--------|
| 11, "doctor", "setup", "config" | Use CLI commands below |
| 12, "log", "todo", "activity" | Use tracking commands below |

</routing>

<cli_commands>
**Environment status (no args):**

```bash
$RHDH
```

Shows overlay repo, rhdh-local, tools status, and next steps.

**Full environment check:**

```bash
$RHDH doctor
```

**Configuration:**

```bash
$RHDH config init                  # Create config with auto-detection
$RHDH config show                  # Show resolved paths
$RHDH config set overlay /path     # Set rhdh-plugin-export-overlays location
$RHDH config set local /path       # Set rhdh-local location
$RHDH config set rhdh /path        # Set main rhdh repo location
$RHDH config set downstream /path  # Set rhdh-downstream location
$RHDH config set cli /path         # Set rhdh-cli location
$RHDH config set plugins /path     # Set rhdh-plugins location
$RHDH config set operator /path    # Set rhdh-operator location
$RHDH config set chart /path       # Set rhdh-chart location
$RHDH config set catalog /path     # Set rhdh-plugin-catalog location
```

**Workspace operations:**

```bash
$RHDH workspace list           # List all plugin workspaces
$RHDH workspace status <name>  # Show workspace details
```

</cli_commands>

<tracking_system>

## Activity Tracking (Recommended)

The CLI includes worklog and todo tracking to maintain context across sessions. **Use is recommended but not required.**

### Why Track?

- **Cross-session memory** — Pick up where you left off without re-explaining context
- **Audit trail** — "When did we onboard X?" / "What happened with PR #123?"
- **Follow-up reminders** — Don't lose track of blocked items waiting on external input

### Worklog Commands

Append-only activity log stored in `.rhdh/worklog.jsonl`:

```bash
# Log activity with tags for searchability
$RHDH log add "Started onboard: aws-appsync" --tag onboard --tag aws-appsync
$RHDH log add "PR #1234 merged" --tag aws-appsync --tag pr

# View recent entries
$RHDH log show --limit 10

# Search past activity
$RHDH log search "aws-appsync"
$RHDH log search "onboard"
```

### Todo Commands

Section-based markdown todos stored in `.rhdh/TODO.md`:

```bash
# Create todo when blocked
$RHDH todo add "Check license with legal" --context "aws-appsync"
$RHDH todo add "Follow up on stale PR #1234" --context "triage"

# List and manage
$RHDH todo list              # All todos
$RHDH todo list --pending    # Only open items

# Update progress
$RHDH todo note <slug> "Sent email to legal@redhat.com"
$RHDH todo done <slug>

# View raw file
$RHDH todo show
```

### When to Track

**Log these milestones:**

- Starting/completing a workflow (onboard, update, triage)
- PR actions (opened, published, merged)
- Significant decisions or findings

**Create todos for:**

- Blocked items waiting on external response (legal, upstream, team)
- Post-merge follow-ups (verify in staging, remove workarounds)
- Items that span multiple sessions

### Writing Effective Todos

Todos must be **self-contained**—a new session should understand the task without re-investigating.

| ❌ Too vague | ✅ Actionable |
|-------------|---------------|
| Fix #1875 version mismatch | Fix #1875 (lightspeed): bump `1.3.0→1.4.0` in `workspace.yaml` like #1903 |
| Add /ok-to-test to #1921 | Add /ok-to-test to #1921 (techdocs) — smoke tests ready, needs external trigger |
| Review #1906 SonarCloud | Review #1906 (catalog): SonarCloud blocked on coverage — check if test file missing |

**Include:** PR number, plugin name, specific action, and *why* it's needed.

</tracking_system>

<reference_index>
**RHDH Repos:** references/rhdh-repos.md — repository map, ecosystem relationships, key paths
**GitHub CLI (PRs, CI, workflows):** references/github-reference.md
**Version Matrix:** references/versions.md — RHDH/Backstage version compatibility, create-app versions
**Slack Notifications:** references/slack-notification.md — Slack ping templates, handle mapping, channel routing
</reference_index>

<skills_index>

### Specialized Skills

| Skill | Purpose | Path |
|-------|---------|------|
| overlay | Manage plugins in rhdh-plugin-export-overlays | `../overlay/SKILL.md` |
| create-plugin | Create, export, package, and wire RHDH dynamic plugins | `../create-plugin/SKILL.md` |
| rhdh-local | Enable/disable/test plugins in local RHDH | `../rhdh-local/SKILL.md` |
| rhdh-pr-review | PR code review and live cluster testing | `../rhdh-pr-review/SKILL.md` |
| rhdh-test-plan-review | Reviews an RHDH test plan Jira ticket and suggests platform/integration version updates | `../rhdh-test-plan-review/SKILL.md` |
| rhdh-release | Release dates, status tracking, team coordination, freeze announcements, blocker bugs, CVEs, release notes | `../rhdh-release/SKILL.md` |

### Shared References

| Reference | Purpose | Path |
|-----------|---------|------|
| rhdh-repos | Repository map, ecosystem relationships, key paths | `references/rhdh-repos.md` |
| versions | RHDH/Backstage version compatibility matrix | `references/versions.md` |

</skills_index>

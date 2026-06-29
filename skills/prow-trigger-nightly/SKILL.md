---
name: prow-trigger-nightly
description: >-
  Trigger RHDH nightly ProwJobs on demand via the OpenShift CI Gangway REST API.
  Supports both rhdh and rhdh-plugin-export-overlays repos. Use when the user
  wants to trigger, run, kick off, or start a nightly CI job, run an on-demand
  E2E nightly test, list available nightly jobs, or trigger an overlay nightly.
  Also use when the user mentions Gangway, "nightly job", "periodic-ci",
  RC verification, testing a custom image, running CI against a fork, or
  checking available image tags on quay.io.
---
# Trigger Nightly ProwJobs

Trigger RHDH nightly ProwJobs via the OpenShift CI Gangway REST API.

Supports two repositories:

- **rhdh** — the main RHDH application (`periodic-ci-redhat-developer-rhdh-*-nightly`)
- **rhdh-plugin-export-overlays** — plugin export overlays (`periodic-ci-redhat-developer-rhdh-plugin-export-overlays-*-nightly`)

## Script Location

All commands below use paths relative to this skill's directory:
`skills/prow-trigger-nightly/scripts/trigger_nightly_job.py`

## Prerequisites

- Python 3.9+
- `oc` CLI installed (for authentication to OpenShift CI)

## Flow

1. Fetch available jobs and let the user pick one
2. Ask about image override and additional options (fork, alerts)
3. Show the command, confirm, execute, report results

## Step 1: Fetch Jobs and Select

List configured nightly jobs:

```bash
uv run scripts/trigger_nightly_job.py --list
```

Present the jobs in a table with columns: short name and which branches have it. Derive the short name from the job name part after the branch segment (e.g. `e2e-ocp-helm-nightly` -> "OCP Helm"):

| Repo | Job | main | release-1.9 | release-1.8 |
|------|-----|------|-------------|-------------|
| rhdh | OCP Helm | x | x | x |
| rhdh | AKS Helm | x | x | |
| overlays | OCP Helm | x | | |

Then ask the user to describe which job and branch they want in natural language.

### Natural Language Mapping

Map the user's description to the matching full job name from the fetched list. If no branch is mentioned, default to `main`:

**RHDH repo jobs:**

- "ocp helm" / "openshift helm" -> `e2e-ocp-helm-nightly` (not upgrade, not versioned)
- "operator" / "ocp operator" -> `e2e-ocp-operator-nightly` (not auth-providers)
- "helm upgrade" / "upgrade test" -> `e2e-ocp-helm-upgrade-nightly`
- "auth providers" / "authentication" -> `e2e-ocp-operator-auth-providers-nightly`
- "4.17", "4.19", "4.20", "4.21" -> `e2e-ocp-v4-{VERSION}-helm-nightly`
- "aks helm" / "azure helm" -> `e2e-aks-helm-nightly`
- "aks operator" / "azure operator" -> `e2e-aks-operator-nightly`
- "eks helm" / "aws helm" -> `e2e-eks-helm-nightly`
- "eks operator" / "aws operator" -> `e2e-eks-operator-nightly`
- "gke helm" / "google helm" -> `e2e-gke-helm-nightly`
- "gke operator" / "google operator" -> `e2e-gke-operator-nightly`
- "osd" / "osd gcp" -> `e2e-osd-gcp-helm-nightly` or `e2e-osd-gcp-operator-nightly`
- Branch: "1.9", "release 1.9", "1.8 branch" -> match from that branch
- Multiple: "all AKS jobs", "all Operator jobs on main" -> offer to trigger them in sequence

**Overlay repo jobs:**

- "overlay nightly" / "overlay helm" / "overlays nightly" -> `periodic-ci-redhat-developer-rhdh-plugin-export-overlays-main-e2e-ocp-helm-nightly`

### Shared Cluster Constraint (GKE / OSD-GCP only)

GKE and OSD-GCP each share a single cluster — never run two jobs on the same platform simultaneously. Before triggering, warn the user.

## Step 2: Options

### Overlay repo jobs

Overlay jobs support fork overrides (`--org`, `--repo`, `--branch`), catalog index override (`--catalog-index-image`), and Playwright version override (`--playwright-version`).

Image overrides (`--image-registry`, `--image-repo`, `--tag`), `--chart-version`, and `--send-alerts` are NOT supported — the script will error if these are passed for an overlay job.

If the user doesn't need any overrides, skip this step and go directly to Step 3.

### RHDH repo jobs

Present all options together. The user picks by number — multiple selections allowed (e.g. "2, 5"):

**Image override:**

1. **Default image** — no image flags, use whatever the job is configured with
2. **Custom tag only** — override just the tag, keep default registry and repo
3. **Custom repo + tag** — override image repository and tag, keep default registry (`quay.io`)
4. **Fully custom image** — override registry, repo, and tag

**Catalog & chart override:**
5. **Catalog index image** — override the plugin catalog index image (`--catalog-index-image`)
6. **Chart version** — override the Helm chart version (`--chart-version`)

**Additional options:**
7. **Fork override** — run against a fork instead of `redhat-developer/rhdh`
8. **Send Slack alerts** — notify via `--send-alerts`

Constraint: `--image-repo` requires `--tag`, but `--tag` works on its own. `--playwright-version` is overlay-only and will error for RHDH jobs.

### Follow-up based on selections

**If 2 or 3 selected (quay.io registry)** — fetch available tags and present as numbered options. For `release-*` branches, derive `--tag-filter` by stripping the `release-` prefix. For `main`, omit `--tag-filter` to show all available versions:

```bash
# For release-1.10 branch:
uv run scripts/trigger_nightly_job.py --list-tags --tag-filter 1.10

# For main branch (show all versions):
uv run scripts/trigger_nightly_job.py --list-tags
```

Use `--image-repo <REPO>` to query a different image repository (default: `rhdh/rhdh-hub-rhel9`). Present the numbered results with a final option to enter a custom tag (e.g. `next`, `latest`). For option 3, also ask for the image repository.

**If 4 selected (non-quay registry)** — ask for all three values (tag fetching not available):

- Registry (e.g. `brew.registry.redhat.io`)
- Image repo (e.g. `rhdh/rhdh-hub-rhel9`)
- Tag (e.g. `1.9`)

**If 5 selected** — ask for catalog index image (e.g. `quay.io/rhdh/plugin-catalog-index:1.9-60` for RC, `registry.access.redhat.com/rhdh/plugin-catalog-index:1.9.4` for GA).

**If 6 selected** — ask for chart version (e.g. `1.9-227-CI`).

**If 7 selected** — ask for:

- GitHub org (`--org`): e.g. `my-github-user`
- Repo name (`--repo`): e.g. `rhdh`
- Branch (`--branch`): e.g. `my-feature-branch`

## Step 3: Confirm and Execute

Show the full command and present final options:

```bash
uv run scripts/trigger_nightly_job.py \
  --job <FULL_JOB_NAME> \
  [--image-registry <REGISTRY>] \
  [--image-repo <REPO>] \
  [--tag <TAG>] \
  [--catalog-index-image <IMAGE>] \
  [--chart-version <VERSION>] \
  [--playwright-version <VERSION>] \
  [--org <ORG>] \
  [--repo <REPO>] \
  [--branch <BRANCH>] \
  [--send-alerts] \
  [--dry-run]
```

1. **Execute** — run the command as shown
2. **Change something** — go back and modify parameters

After execution, show the API response. If a job URL or ID is returned, display it prominently. On error, help diagnose (common issues: expired token, invalid job name).

### RC Verification Example

```bash
uv run scripts/trigger_nightly_job.py \
  --job periodic-ci-redhat-developer-rhdh-main-e2e-ocp-helm-nightly \
  --image-repo rhdh/rhdh-hub-rhel9 --tag 1.9-227 \
  --catalog-index-image quay.io/rhdh/plugin-catalog-index:1.9 \
  --chart-version 1.9-227-CI
```

### GA Verification Example

```bash
uv run scripts/trigger_nightly_job.py \
  --job periodic-ci-redhat-developer-rhdh-main-e2e-ocp-helm-nightly \
  --image-registry registry.redhat.io --image-repo rhdh/rhdh-hub-rhel9 --tag 1.9.4 \
  --catalog-index-image registry.access.redhat.com/rhdh/plugin-catalog-index:1.9.4
```

## Reference

- Script flags: `-j/--job`, `-l/--list`, `-T/--list-tags`, `--tag-filter`, `-I/--image-registry`, `-q/--image-repo`, `-t/--tag`, `--catalog-index-image`, `--chart-version`, `--playwright-version`, `-o/--org`, `-r/--repo`, `-b/--branch`, `-S/--send-alerts`, `-n/--dry-run`, `--json`
- Dedicated kubeconfig at `~/.config/openshift-ci/kubeconfig` — won't interfere with your current cluster context
- If auth is needed, the script opens a browser for SSO login
- RHDH jobs list: <https://prow.ci.openshift.org/configured-jobs/redhat-developer/rhdh>
- Overlay jobs list: <https://prow.ci.openshift.org/configured-jobs/redhat-developer/rhdh-plugin-export-overlays>
- Image tags: <https://quay.io/repository/rhdh/rhdh-hub-rhel9?tab=tags>

## Related Skills

- **`overlay`**: Manage the rhdh-plugin-export-overlays repository

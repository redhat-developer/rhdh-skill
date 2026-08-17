# Konflux release-data RPA updates

## Goal

Given a target RHDH version (for example `1.9.7`), update the matching stream
ReleasePlanAdmission files under
`config/stone-prod-p02.hjvn.p1/product/ReleasePlanAdmission/rhdh/` so tag values
use the new patch version, then push a branch and open a GitLab merge request.

## Prerequisites

- Local clone of [konflux-release-data](https://gitlab.cee.redhat.com/releng/konflux-release-data)
- `git`, `glab` (GitLab CLI authenticated to `gitlab.cee.redhat.com`)
- Push access to `origin` (`git@gitlab.cee.redhat.com:releng/konflux-release-data.git`)
- Optional: `tox` when using `--validate`

Run from the user's konflux-release-data checkout — **never assume a fixed path**.
Pass `--repo-dir` or `cd` into the target folder before invoking the script.

Working directory resolution (in order):

1. `--repo-dir PATH` when provided
2. `KONFLUX_RELEASE_DATA_REPO` when set
3. Current working directory (`$PWD`)

`PATH` may be the **repository root**, or the **rhdh ReleasePlanAdmission folder** (the script resolves the standard path
`config/stone-prod-p02.hjvn.p1/product/ReleasePlanAdmission/rhdh/` from there).

## Run the bundled script

**Execute** [scripts/update-rpa-tags.sh](../scripts/update-rpa-tags.sh); do not
reimplement the workflow inline. Always run it against the folder the user
specified.

```bash
SKILL_DIR=/absolute/path/to/installed/rhdh-konflux-tasks
SCRIPT="${SKILL_DIR}/scripts/update-rpa-tags.sh"
chmod +x "${SCRIPT}"
REPO=/path/to/konflux-release-data    # user-provided checkout

# From repo root
cd "${REPO}" && "${SCRIPT}" 1.9.7

# Or pass the checkout explicitly
"${SCRIPT}" 1.9.7 --repo-dir "${REPO}"

# Preview only
"${SCRIPT}" 1.9.7 --repo-dir "${REPO}" --dry-run
```

## Which files change

For version `MAJOR.MINOR.PATCH`, the script updates the `MAJOR-MINOR` stream only:

| Version example | Stream | Files updated |
|-----------------|--------|---------------|
| `1.9.7` | `1.9` | `rhdh-1-9-prod.yaml`, `rhdh-1-9-stage.yaml`, `rhdh-plugin-catalog-1-9-prod.yaml`, `rhdh-plugin-catalog-1-9-stage.yaml` |
| `1.10.2` | `1.10` | `rhdh-1-10-*.yaml`, `rhdh-plugin-catalog-1-10-*.yaml` (prod + stage) |

**Not** updated by this script: `-fbc-` RPAs, `1.next` / `1-stage` catalog files,
builder RPAs, or other streams.

## Tag replacement rules

1. Auto-detect stale patch versions from tag strings in the target files
   (for example `1.9.6` when bumping to `1.9.7`).
2. Replace every occurrence of each stale patch with the target version.
3. Keep the stream tag unchanged (`"1.9"` stays `"1.9"`).
4. Composite plugin catalog tags are updated in the RHDH prefix only
   (`1.9.6--1.20.2` → `1.9.7--1.20.2`); upstream plugin semver suffixes are
   preserved unless a separate plugin-catalog bump MR is needed.

Hub/operator RPAs (`rhdh-1-9-*.yaml`) only carry tags under `defaults.tags`.
Plugin catalog RPAs also update per-component `tags` lists.

## Merge request workflow

On success the script:

1. Fetches and checks out `main`
2. Creates branch `chore/rhdh-update-rpa-<VERSION>`
3. Commits with signed-off message:
   `chore: update rhdh-<stream>-*.yaml RPAs for upcoming release <VERSION>`
4. Pushes to `origin` (`releng/konflux-release-data`)
5. Creates a GitLab MR in **`releng/konflux-release-data`** via `glab api` on the upstream project (not `glab mr create`, which may route through the `rhdh-bot` fork and produce an empty diff)
6. MR description starts with **`Generated-by: cursor`**
7. Verifies the MR includes file changes before opening the browser
8. Opens the MR URL in the first available browser: **Brave → Chrome → Firefox**

Use `--dry-run` to preview tag changes without modifying files or opening an MR.

## Validation

Run schema tests after editing when CI credentials are available:

```bash
"${SCRIPT}" 1.9.7 --repo-dir "${REPO}" --validate
```

Or from the repo root: `tox -e test`.

## Related manual steps

This script handles **RHDH patch tag bumps** in konflux-release-data only. It
does **not**:

- Bump upstream plugin semver suffixes in composite tags (see historical MRs
  titled `chore(rhdh): update plugin catalog … RPAs to … tags`)
- Update Konflux tenant snapshots or components in `tenants-config/`
- Trigger releases in Konflux

For Tekton digest bumps in midstream repositories, follow
[konflux-task-update.md](konflux-task-update.md) instead.

## Anti-patterns

- Assuming a hardcoded checkout path; always use the user's folder via `--repo-dir` or `cd`.
- Pushing to `rhdh-bot` or any fork remote; push is always to `origin`.
- Creating cross-project MRs from a fork when the branch exists only on `origin`.
- Editing FBC or `1.next` RPAs as part of a stream patch bump.
- Pushing directly to `main`; always use an MR.
- Running with a dirty working tree (uncommitted changes block the script).

## Additional resources

- Example hub bump: `8e378a51be` — `rhdh-1-9-*.yaml` to `1.9.7`
- Example catalog bump: `50445ad9f1` — all plugin catalog component tags
- Repo guide: `konflux-release-data` `AGENTS.md` and `.cursor/rules/konflux-release-data.mdc`

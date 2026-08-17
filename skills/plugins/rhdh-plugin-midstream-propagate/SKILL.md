---
name: rhdh-plugin-midstream-propagate
description: >-
  Propagates an rhdh-plugins workspace change through overlays and
  rhdh-plugin-catalog (midstream): changeset + npm publish, overlays source.json
  to the Version Packages SHA, then a surgical catalog MR (overlay-repo/,
  workspaces/, plugin_builds/, .tekton PLR tags like 2.0.0--0.0.3) without a full
  sync-midstream --force-clone. Use when promoting plugin versions, waiting on
  npm @red-hat-developer-hub packages, bumping overlays repo-ref, or midstream
  Hermeto/lock/PLR updates for one workspace. For an overlays workspace edit
  outside this promotion chain, use /rhdh-overlay.
compatibility: >-
  Git, jq, npm, the skills CLI for repos.* config, GitHub CLI, and glab
  authenticated against gitlab.cee.redhat.com; checkouts of rhdh-plugins,
  rhdh-plugin-export-overlays, and rhdh-plugin-catalog.
---

# RHDH plugin → overlays → catalog propagate

Three-step chain after a fix or feature in [`redhat-developer/rhdh-plugins`](https://github.com/redhat-developer/rhdh-plugins):

1. Update **rhdh-plugins** with the change, including a **changeset**; wait until merged and new package(s) are published to npmjs.com (e.g. [`@red-hat-developer-hub/backstage-plugin-app-defaults`](https://www.npmjs.com/package/@red-hat-developer-hub/backstage-plugin-app-defaults) `0.0.3` and other packages published at the same time).
2. Update the **overlays** repo (`rhdh-plugin-export-overlays`) to fetch the commit SHA for the **Version Packages** PR related to the above change.
3. Grab the specific changes from that SHA and push them into **rhdh-plugin-catalog**, updating `overlay-repo/`, `workspaces/`, and other paths that `sync-midstream.sh` would touch for a full clone of **just that workspace**; open an MR that applies the updated files and bumps associated PLR(s) in `.tekton/` to the appropriate tags (e.g. `2.0.0--0.0.3`).

Prefer a **surgical** catalog MR over `build/ci/sync-midstream.sh --force-clone <workspace>` (minutes vs a long full re-clone/export). Fall back to scoped `--force-clone` only when export / `plugin_builds` annotations / workspace transform must be regenerated.

## Repos and config

| Step | Repo | Config key |
|------|------|------------|
| 1 | [`redhat-developer/rhdh-plugins`](https://github.com/redhat-developer/rhdh-plugins) | `repos.plugins` |
| 2 | [`redhat-developer/rhdh-plugin-export-overlays`](https://github.com/redhat-developer/rhdh-plugin-export-overlays) | `repos.overlay` |
| 3 | [`gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog`](https://gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog) | `repos.catalog` |

Resolve checkouts by invoking `/rhdh-context` by name and reading the paths it reports. To run its CLI directly instead, set `RHDH` to that skill's `scripts/rhdh` wrapper and use dot-notation keys: `"$RHDH" --json config get repos.<key> | jq -r '.data.value'` (see [`references/catalog-surgical-update.md`](references/catalog-surgical-update.md)). Use `glab` against **`gitlab.cee.redhat.com`** for catalog MRs (not `gitlab.com`).

Confirm a Jira key before opening PRs/MRs. To attach the issue link, invoke the named skill `/rhdh-jira-link`. To open the PR or MR itself, invoke the named skill `/rhdh-pr-create`. Use `gh` / `glab` directly only when neither skill is installed.

---

## Step 1 — rhdh-plugins (+ changeset → npm)

Follow [Creating changesets](https://github.com/redhat-developer/rhdh-plugins/blob/main/CONTRIBUTING.md#creating-changesets): land the fix with a changeset, merge the bot **Version Packages** PR, and wait until every package in that release is on npmjs.com.

**Gate before Step 2:** published npm versions match the Version Packages bump; `npm view <pkg>@<ver> gitHead` equals the Version Packages merge SHA.

Optional: invoke the named skill `/rhdh-pr-create` for the build, changeset, and PR on rhdh-plugins.

---

## Step 2 — overlays (`source.json` → Version Packages SHA)

After npm is live, follow [Metadata synchronization](https://github.com/redhat-developer/rhdh-plugin-export-overlays/blob/main/user-guide/04-metadata-synchronization.md) in `workspaces/<ws>/`: set `source.json` `repo-ref` to the **Version Packages** merge SHA (not the earlier fix commit), align `repo-backstage-version`, and bump `metadata/*.yaml` versions and `dynamicArtifact` OCI tags for every package published in the same release.

Merge the overlays PR before catalog work. Catalog midstream must target overlays `main` (or your release branch) after this lands.

**Note:** `/rhdh-overlay` owns the overlays repository, including generic `source.json` bumps; invoke it by name to make the workspace edit. What this chain adds is the constraint that `repo-ref` must be the Version Packages SHA. Prefer this skill over a plain overlay update when the ask mentions Version Packages, promote-to-catalog, or midstream.

---

## Step 3 — catalog surgical midstream MR

**Read** [`references/catalog-surgical-update.md`](references/catalog-surgical-update.md) before editing (SSOT for paths, config capture, PLR regen, and scoped sync flags).

Goal: same file set `sync-midstream.sh --force-clone '<ws>'` would refresh for **one** workspace, without cloning every workspace.

### Preferred (surgical)

1. Sync `overlay-repo/workspaces/<ws>/` from overlays main (`source.json`, `plugins-list.yaml`, `metadata/`, overlays/patches if present).
2. Apply upstream deltas at `$SHA` into `workspaces/<ws>/` — at minimum root `package.json` / `yarn.lock` (the tree that owns the lockfile) and any plugin `package.json` version bumps; expand to plugin sources when the Version Packages change is not lock/metadata-only. Do not apply lock/resolution pins only under `plugins/<name>/`.
3. Align `plugin_builds/<ws>/*.json` `registryReference` tags (`quay.io/rhdh/...:<rhdh>--<pluginVer>`, e.g. `2.0.0--0.0.3`).
4. Bump associated `.tekton/` PLRs / Containerfiles:
   - `konflux.additional-tags` → `<xy>--<ver>,<x.y.z>--<ver>` (e.g. `2.0--0.0.3,2.0.0--0.0.3`)
   - `DESCRIPTION` plugin version fragment
   - `UPSTREAM_REPO` overlays tree SHA when known
   - Or regenerate the affected PLRs via `.tekton/updatePLRs.sh` (see reference: nested `--path '<ws>/plugins/<plugin>'` vs flat `--package`; gate on `source.json` `repo-flat`)
5. Open the catalog MR by invoking the named skill `/rhdh-pr-create`, or with `glab` against CEE GitLab. Cite sibling package versions in the body.

**Who owns `.tekton`:** this skill owns only the per-workspace PLR and Containerfile tag bumps that ride the surgical catalog MR for the workspace being promoted. Full-stream PipelineRun regeneration across the catalog belongs to `/rhdh-konflux-tasks`; invoke it by name rather than regenerating the stream from here.

### Fallback (scoped sync)

When export / annotations / `update-workspace.js` transforms are required, use the command in [`references/catalog-surgical-update.md`](references/catalog-surgical-update.md#scoped-sync-midstream-fallback) (do not invent alternate flag sets here). Prefer surgical when the delta is known (pin, lock, versions).

---

## External writes

Pushing a branch, commenting, opening the overlays PR, and opening the catalog MR are external writes: invoke the named skill `mutation-gate` and follow the gate it owns rather than restating it here. A request to promote a plugin is intent, not approval of a specific push.

---

## Checklist

- [ ] rhdh-plugins change includes a changeset; Version Packages merged
- [ ] npm packages published; `gitHead` == Version Packages SHA
- [ ] overlays `repo-ref` + metadata versions/OCI tags updated and merged
- [ ] catalog `overlay-repo/workspaces/<ws>/` matches overlays
- [ ] catalog `workspaces/<ws>/` reflects `$SHA` at the yarn.lock-owning root (lock/resolutions/versions as needed)
- [ ] `plugin_builds/` + `.tekton/` tags match new plugin versions (`x.y.z--<pluginVer>`)
- [ ] Catalog MR on CEE GitLab; Jira linked

## Example (RHIDP-16097 / app-defaults)

| Step | Artifact |
|------|----------|
| 1 | rhdh-plugins fix + changeset → Version Packages → `@…/app-defaults@0.0.3` (`gitHead` `18f4229…`) |
| 2 | overlays PR bumping `workspaces/app-defaults/source.json` + metadata |
| 3 | catalog MR syncing `overlay-repo/…/app-defaults` + workspace **root** lock pin (surgical; no `--force-clone`) |

## Completion

The chain is done when every box in the checklist above is ticked and each step verifies on its own, without relying on the step before it having been reported correctly.

Report the published package versions and the SHA they resolve to, the overlays PR and catalog MR URLs, the Jira key they are linked to, and whether the catalog change was surgical or fell back to a scoped `--force-clone`. Name anything left open: a merge still pending, an npm publish still in flight, a stream-wide PipelineRun regeneration handed to `/rhdh-konflux-tasks`, or an external write that was stated but not approved.

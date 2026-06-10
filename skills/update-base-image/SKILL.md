---
name: update-base-image
description: >-
  Analyze and update Red Hat UBI / RHEC base images in Containerfile / Dockerfile using
  updateBaseImages.sh and analyze-base-images.sh. Use when bumping ubi9,
  nodejs-24, go-toolset, or other registry.access.redhat.com images, refreshing
  @sha256 digests, scanning Containerfile FROM lines, or fixing UBI minor-version
  skew in the same file. Also use when the user mentions update-base-image,
  update base images, base image maintenance, RHDH release prep, or weekly
  base image refresh. Scripts live in rhdh-downstream build/scripts; scan rhdh and
  rhdh-operator upstream checkouts for Containerfile / Dockerfile.
disable-model-invocation: true
---

# Update base images (RHDH)

Discover latest tags from the registry, analyze Containerfiles, apply updates, and flag UBI version skew—without opening catalog.redhat.com.

## Workspace layout

Consult [`../rhdh/references/rhdh-repos.md`](../rhdh/references/rhdh-repos.md) for upstream URLs, descriptions, and base-image file paths (`rhdh`, `rhdh-operator`).

You need **three local checkouts** — often separate git clones on disk:

| Role           | Env var              | Repo (rhdh-repos)   |
| -------------- | -------------------- | ------------------- |
| Build scripts  | `RHDH_BUILD_SCRIPTS` | **rhdh-downstream** |
| App image      | `RHDH_REPO`          | **rhdh**            |
| Operator image | `RHDH_OPERATOR_REPO` | **rhdh-operator**   |

`RHDH_BUILD_SCRIPTS` must point at `build/scripts/` in the downstream clone. `-w` targets the **upstream repo root** you scan and update (`rhdh` or `rhdh-operator`).

Set paths before running (adjust to your machine):

```bash
export RHDH_BUILD_SCRIPTS=/path/to/rhidp/rhdh/build/scripts       # rhdh-downstream
export RHDH_REPO=/path/to/redhat-developer/rhdh                   # rhdh
export RHDH_OPERATOR_REPO=/path/to/redhat-developer/rhdh-operator # rhdh-operator
```

## Setup (non-optional)

| Gate          | Check                                                                                            | If fail                                                                                      |
| ------------- | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Scripts       | `$RHDH_BUILD_SCRIPTS/getLatestImageTags.sh` is executable                                        | Clone **rhdh-downstream** (see rhdh-repos); set `RHDH_BUILD_SCRIPTS` to its `build/scripts/` |
| Target repos  | `$RHDH_REPO` and `$RHDH_OPERATOR_REPO` exist (or pass `-w` to analyze)                           | Clone **rhdh** and **rhdh-operator** (see rhdh-repos); set env vars or pass `-w`             |
| Registry auth | `skopeo inspect docker://registry.access.redhat.com/ubi9/nodejs-24:9.8 2>&1 \| head -1` succeeds | Run `skopeo login registry.redhat.io`                                                        |
| Tools         | `command -v skopeo jq gh git`                                                                    | Install missing tools                                                                        |

## Install this skill

```bash
npx skills add redhat-developer/rhdh-skill --skill update-base-image
```

## Quick run (automated update + PR)

Run **`updateBaseImages.sh` once per repo** from `$RHDH_BUILD_SCRIPTS`:

```bash
"$RHDH_BUILD_SCRIPTS/updateBaseImages.sh" \
  -w "$RHDH_REPO" \
  -b release-1.y \
  -f "Containerfile Dockerfile" \
  -maxdepth 5 \
  --pr

"$RHDH_BUILD_SCRIPTS/updateBaseImages.sh" \
  -w "$RHDH_OPERATOR_REPO" \
  -b release-1.y \
  -f "Containerfile Dockerfile" \
  -maxdepth 5 \
  --pr
```

**Update files only** (no commit, no push, no PR):

```bash
"$RHDH_BUILD_SCRIPTS/updateBaseImages.sh" \
  -w "$RHDH_REPO" \
  -f "Containerfile Dockerfile" \
  -maxdepth 5 \
  -px 'e2e-tests/' -px '\.ci/' \
  --no-commit

"$RHDH_BUILD_SCRIPTS/updateBaseImages.sh" \
  -w "$RHDH_OPERATOR_REPO" \
  -f "Containerfile Dockerfile" \
  -maxdepth 5 \
  --no-commit
```

**Required flags:**

| Flag                            | Why                                                                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `-maxdepth 5`                   | Default script value is 2; depth 2 **skips** `build/containerfiles/Containerfile`. Always pass 5 for RHDH. |
| `-w`                            | Upstream repo root to scan (**rhdh** or **rhdh-operator** checkout)                                        |
| `-f "Containerfile Dockerfile"` | **rhdh** uses `Containerfile`; **rhdh-operator** uses `Dockerfile` (see rhdh-repos for paths)              |
| `--pr`                          | Opens one PR with all commits (protected branches)                                                         |
| `--no-commit`                   | Writes file changes only; no git commit, push, or PR                                                       |

**Tag format:** RHEC tags may use `major.minor-buildid` (e.g. `9.8-1780434037`) or bare numeric build ids (e.g. `1780432632`). Analysis queries all matching registry tags via `getLatestImageTags.sh --tag .` (built-in excludes still apply).

## Analyze without committing

The bundled script reads `$RHDH_BUILD_SCRIPTS`, `$RHDH_REPO`, and `$RHDH_OPERATOR_REPO` when `-w` is omitted:

```bash
# Scan both repos (requires env vars above)
~/.agents/skills/update-base-image/scripts/analyze-base-images.sh

# Explicit repos
~/.agents/skills/update-base-image/scripts/analyze-base-images.sh \
  -w "$RHDH_REPO" \
  -w "$RHDH_OPERATOR_REPO"

# Single file
~/.agents/skills/update-base-image/scripts/analyze-base-images.sh \
  -w "$RHDH_REPO" \
  build/containerfiles/Containerfile
```

Auto-discovery finds `Containerfile` and `Dockerfile` (maxdepth 5) under each `-w` repo. For **rhdh** (`$RHDH_REPO`), paths under `e2e-tests/` and `.ci/` are skipped (see rhdh-repos for the main Containerfile path).

## Containerfile requirements

Each **registry** `FROM` must have a **comment URL** on the line above (script convention):

```containerfile
# https://registry.access.redhat.com/ubi9/nodejs-24
FROM registry.access.redhat.com/ubi9/nodejs-24:9.8-...@sha256:... AS skeleton

# https://registry.access.redhat.com/ubi9/nodejs-24-minimal
FROM registry.access.redhat.com/ubi9/nodejs-24-minimal:9.8-...@sha256:... AS runner
```

Stage-only lines (`FROM skeleton AS deps`) are ignored.

## Agent workflow

1. **Verify setup gates** (scripts path, both repos, registry login, tools).
2. **Scan** with `scripts/analyze-base-images.sh` (set env vars or pass `-w`).
3. **Explain** any mismatch (e.g. `nodejs-24` on 9.8 but `nodejs-24-minimal` still on 9.7).
4. **Update** each repo:
   - Prefer: `"$RHDH_BUILD_SCRIPTS/updateBaseImages.sh" -w "$RHDH_REPO" ...` and `-w "$RHDH_OPERATOR_REPO"`.
   - Or: edit `FROM` lines using `current` / `latest` from analyze output.
5. **Verify** UBI minors align across all `ubi9*` images in the same file after edits.
6. **Commit** with `[skip-build] [skip-e2e]` when matching project convention.

**Success criteria:** Every registry `FROM` in scope either matches latest tag or has a documented reason to stay pinned; no UBI minor-version skew within a single Containerfile unless intentionally documented.

## Gotchas

| Cause                                   | Fix                                                                                            |
| --------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Scripts not in target repo              | Point `RHDH_BUILD_SCRIPTS` at **rhdh-downstream** `build/scripts/`, not the repo being updated |
| Only scanned one repo                   | Run analyze/update for both **rhdh** and **rhdh-operator**                                     |
| rhdh e2e/ci Dockerfiles                 | Analyze skips `e2e-tests/` and `.ci/` under `$RHDH_REPO`                                       |
| `-maxdepth` too low                     | Use `-maxdepth 5`                                                                              |
| Wrong `-f` pattern                      | Use `-f "Containerfile Dockerfile"` when covering both repos                                   |
| Missing `# https://registry...` comment | Add comment above `FROM`                                                                       |
| Registry not logged in                  | `skopeo login registry.redhat.io`                                                              |
| Current tag already newest              | Script skips; confirm with `getLatestImageTags.sh -n 5`                                        |

## UBI mismatch warnings

`updateBaseImages.sh` warns when one file has multiple UBI images with different **minor** versions (9.7 vs 9.8). `analyze-base-images.sh` prints the same check during analysis.

## Related scripts

| Script                   | Location                                       |
| ------------------------ | ---------------------------------------------- |
| `updateBaseImages.sh`    | `$RHDH_BUILD_SCRIPTS/`                         |
| `getLatestImageTags.sh`  | `$RHDH_BUILD_SCRIPTS/`                         |
| `analyze-base-images.sh` | This skill's `scripts/` (installed with skill) |

## References

| Reference                                      | Purpose                                                                |
| ---------------------------------------------- | ---------------------------------------------------------------------- |
| [rhdh-repos](../rhdh/references/rhdh-repos.md) | Upstream URLs, repo descriptions, base-image file paths, ecosystem map |

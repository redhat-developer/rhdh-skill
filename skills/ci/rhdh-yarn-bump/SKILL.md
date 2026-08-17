---
name: rhdh-yarn-bump
description: >-
  Bumps Yarn Berry across the RHDH repos — rhdh-plugins, rhdh midstream,
  rhdh-plugin-export-overlays, rhdh-cli, and GitLab CEE rhidp/rhdh and
  rhdh-plugin-catalog — with `yarn set version` plus install, and rewrites the
  pins Yarn cannot see: `packageManager`, `yarnPath`, `ENV YARN=`, and
  Containerfile lines. Use for "bump yarn to 4.17.1", "upgrade Yarn Berry across
  the repos", "which Yarn version is each repo pinned to", or scanning yarn pins.
compatibility: "Node, yarn, and git on PATH; glab authenticated against gitlab.cee.redhat.com for the GitLab CEE merge requests."
---

# RHDH multi-repo Yarn bump

## Goal

Propagate a Yarn Berry bump (e.g. [rhdh-plugins#2918](https://github.com/redhat-developer/rhdh-plugins/pull/2918), [RHIDP-16074](https://redhat.atlassian.net/browse/RHIDP-16074)) across:

| Repo | Notes |
|------|--------|
| [`redhat-developer/rhdh-plugins`](https://github.com/redhat-developer/rhdh-plugins) | root workspace (+ Fullsend if hardcoded) |
| [`redhat-developer/rhdh`](https://github.com/redhat-developer/rhdh) | root + nested workspaces + Containerfile |
| [`redhat-developer/rhdh-plugin-export-overlays`](https://github.com/redhat-developer/rhdh-plugin-export-overlays) | many `packageManager` pins |
| [`redhat-developer/rhdh-cli`](https://github.com/redhat-developer/rhdh-cli) | root `packageManager` / `yarnPath` (now Yarn 4.17.1) |
| [`gitlab.cee.redhat.com/rhidp/rhdh`](https://gitlab.cee.redhat.com/rhidp/rhdh) | distgit binary + `ENV YARN=` (copy binary from GH bump) |
| [`gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog`](https://gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog) | per-workspace pins + Containerfiles |

## What actually changes

For each matching workspace:

```bash
yarn set version <to>                 # packageManager + yarnPath + .yarn/releases
chmod +x .yarn/releases/yarn-<to>.cjs
yarn install --mode=update-lockfile
```

Plus pins Yarn cannot see: `ENV YARN=`, Containerfile / Dockerfile / embedded `yarn set version`.

**No binary download.** Bump GitHub repos first (`yarn set version` produces `yarn-<to>.cjs`). For **GitLab CEE** midstream/distgit trees (`gitlab.cee.redhat.com/rhidp/rhdh`, `…/rhdh-plugin-catalog`) that only ship a checked-in release + `ENV YARN=`, copy that same `yarn-<to>.cjs` into `.yarn/releases/` (and remove the old `yarn-<from>.cjs`), then run the script so text pins update. Use `glab` against `gitlab.cee.redhat.com` (not `gitlab.com`) when opening MRs for those roots.

Use an **exact** `--to` (not `stable`) so every repo matches the Renovate/reference PR.

## Script

```bash
SKILL=<this skill's directory>
# GH first (4.12/4.14 defaults), then GL CEE (after copying yarn-<to>.cjs into distgit if needed)
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 \
  --root /path/to/rhdh-plugins \
  --root /path/to/rhdh \
  --root /path/to/overlays \
  --root /path/to/rhdh-cli \
  --root /path/to/rhdh-downstream \
  --root /path/to/rhdh-plugin-catalog
```

Defaults:

- `--from 4.12.0,4.14.1` — only those move (`4.8.1` / `4.9.2` / dcm `4.15.0` stay). Repos already on `--to` (e.g. rhdh-cli at 4.17.1) are no-ops.
- Lock refresh for every `yarn.lock` under `--to` (incl. inherited root pin); skip `dist-dynamic` and explicit older pins. Full multi-repo regen can take **>45 minutes**; use `--no-refresh-locks` to skip

```bash
node "$SKILL/scripts/bump-yarn.js" --scan --root /path/to/repo
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 --root /path/to/repo --dry-run
node "$SKILL/scripts/bump-yarn.js" --to 4.17.1 --root /path/to/repo --no-refresh-locks
```

## Agent workflow

1. Confirm `--to` / `--from`.
2. Resolve local `--root` checkouts; bump **GitHub** roots first.
3. For GitLab CEE midstream/distgit (`gitlab.cee.redhat.com/rhidp/rhdh`, `…/rhdh-plugin-catalog`): copy `yarn-<to>.cjs` from a GH bump into `.yarn/releases/` (drop old `--from` binary).
4. `--scan`, then bump (`--dry-run` first if unfamiliar).
5. Summarize set-version dirs, extras, lock refresh.
6. Commit, push, or open a PR·MR only when the user asks, following
   `/mutation-gate` with the repository and branch as each target. To attach
   the work to its Jira issue, invoke `/rhdh-jira-link` by name and use what it
   returns.

## Completion

A bump is done when every requested `--root` has been scanned and each
workspace matching `--from` sits on `--to`, leaving behind:

- updated `packageManager`, `yarnPath`, and `.yarn/releases/yarn-<to>.cjs` at
  mode `100755`, with the old `--from` binary removed;
- rewritten pins Yarn cannot see: `ENV YARN=`, Containerfile / Dockerfile, and
  embedded `yarn set version` lines;
- refreshed `yarn.lock` files, or a stated `--no-refresh-locks` skip.

Report the set-version directories, the extras rewritten, the lock-refresh
result, and every root left untouched with its reason: already on `--to`,
pinned outside `--from`, or not checked out locally. Working trees stay
uncommitted; if the user asked for a commit, PR, or MR, report the outcome of
each of those writes too.

---
name: rhdh-backstage-upgrade
description: >-
  Moves the @backstage/* dependency versions of a Backstage plugin, workspace,
  or app forward to a chosen release, staying within what a Red Hat Developer
  Hub version ships: read backstage.json and package.json, pick the target from
  the RHDH compatibility matrix or an explicit version, run backstage-cli
  versions:bump and versions:migrate, work through the release changelogs for
  breaking changes, and re-verify with yarn tsc, yarn build, and yarn test. Use
  for "upgrade @backstage dependencies", "versions:bump", "which Backstage
  version does RHDH 1.8 ship", moved package namespaces, or a plugin whose
  dependencies are too old for the API it needs.
compatibility: "Node.js 22+, Yarn or npm, @backstage/cli available directly or through npx, and network access to fetch release manifests."
---

# RHDH Backstage Upgrade

Own **version numbers**. Which `@backstage/*` release a checkout sits on, which
release it should move to, and everything that breaks in between.

## Start here

1. Read `package.json` and `backstage.json` before changing any dependency.
2. Establish the target RHDH version. Prefer an explicit user or repository
   value; otherwise invoke `/rhdh-context` for the checked-in compatibility
   matrix. If it is unavailable, ask the user for the target RHDH and Backstage
   versions rather than guessing.
3. Report current versions and the proposed target before running a bump.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Run the whole upgrade | `workflows/upgrade-backstage.md` |
| Find the current versions and any misalignment | `references/discover-versions.md` |
| Choose the target release | `references/determine-target.md` |
| Bump the dependency set | `references/bump-deps.md` |
| Move imports off renamed or relocated packages | `references/migrate-packages.md` |
| Work through the breaking changes between releases | `references/fix-breaking-changes.md` |
| Verify the upgrade | `references/verify-upgrade.md` |

## Boundaries

- This skill owns **version numbers**. It does not change what a plugin's
  extensions are or how they attach.
- `/rhdh-plugin-nfs-migration` owns **extension shape**: converting a legacy
  frontend plugin's extensions into New Frontend System Blueprints. The two
  skills meet whenever an upgrade is a prerequisite for a migration, or a
  migration surfaces an outdated dependency set. Bump the versions here; change
  the extensions there.
- `/backstage-api-changes` owns the NFS API deltas between the early alpha
  and the current GA surface. Invoke it by name when an upgrade breaks NFS code
  — a removed `NavItemBlueprint`, a `config.schema` block that must become
  `configSchema`, or a renamed blueprint param.
- `/rhdh-context` owns the RHDH-to-Backstage compatibility matrix.
- `/rhdh-plugin-authoring` owns non-mechanical source changes the upgrade
  exposes.
- `/rhdh-pr-create` owns staging, commits, and pull requests.

Invoke a named skill and describe the handoff in the conversation. Never open
another skill's files.

## Invariants

- Never upgrade past the Backstage version the target RHDH release ships. The
  resolved compatibility answer wins over the newest available release.
- Use `backstage-cli versions:bump` for aligned resolution rather than editing
  version ranges by hand, and review the resulting `package.json` diff before
  continuing.
- Read the changelog for every release between the old and new version, then
  search the source for each affected API. Do not assume a range is
  breaking-change free.
- If current and target match, say "already on target" and stop.
- `yarn tsc`, `yarn build`, and `yarn test` must pass before the upgrade is
  reported complete.
- Do not stage, commit, push, or open a pull request here.

## Completion

Report the versions found, the target chosen and where the answer came from,
the commands run, the breaking changes fixed and the files they touched, the
verification results, and any dependency left misaligned with a reason.

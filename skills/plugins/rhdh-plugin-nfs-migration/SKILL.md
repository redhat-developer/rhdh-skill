---
name: rhdh-plugin-nfs-migration
description: >-
  Converts a legacy Backstage frontend plugin used by Red Hat Developer Hub to
  the New Frontend System (NFS): replace createPlugin and
  createRoutableExtension with createFrontendPlugin, PageBlueprint,
  EntityContentBlueprint, AppDrawerContentBlueprint and createFrontendModule;
  map RHDH app-config.dynamic.yaml mount points onto extensions; add the
  ./alpha export to package.json without breaking legacy consumers; and verify
  the migrated dynamic plugin in a real RHDH instance. Use for "migrate my
  plugin to NFS", Blueprint migration, createFrontendPlugin, compatWrapper,
  alpha versus colocated exports, translations moved into a
  createFrontendModule with pluginId app, RHDH operator app.extensions and
  app.routes.bindings, and ENABLE_STANDARD_MODULE_FEDERATION testing.
compatibility: "Node.js 22+ and Yarn, with a checkout of the plugin's workspace; an RHDH instance (local or cluster) for the migration test route."
---

# RHDH Plugin NFS Migration

Own the shape of a frontend plugin's extensions as it moves from the legacy
frontend system to NFS. Discover what the plugin exports before changing
anything, migrate one extension type at a time, and keep legacy consumers
compiling until the user explicitly approves a breaking change.

## Start here

1. Read the plugin's `package.json`, `src/plugin.ts` or `src/plugin.tsx`, route
   refs, API factories, exported components, and `app-config.dynamic.yaml`.
2. Read the workspace's own `AGENTS.md` or `CLAUDE.md`; repository rules beat
   anything written here.
3. List every discovered extension to the user before editing.
4. Inspect branch and status before modifying files, and protect uncommitted
   work.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Migrate a plugin to NFS | `workflows/migrate-nfs.md` |
| Test a migrated plugin in RHDH | `workflows/test-nfs-plugin.md` |
| Explain NFS before migrating | `references/overview.md` |
| Migrate pages or API factories | `references/migrate-page.md` |
| Migrate entity tabs or cards | `references/migrate-entity-content.md` |
| Migrate translations | `references/migrate-translations.md` |
| Migrate RHDH drawers, header items, homepage widgets | `references/migrate-rhdh-extensions.md` |
| Migrate app-level wrappers or root elements | `references/migrate-app-level.md` |
| Translate a legacy dynamic mount point into an extension | `references/mount-point-mapping.md` |
| Update package exports | `references/package-json.md` |
| Set up or update the NFS dev app | `references/app-setup.md` |
| Verify the migration | `references/verification.md` |
| Reach RHDH operator `app.extensions` or `app.routes.bindings` | `references/operator-config.md` |
| Troubleshoot a failed migration | `references/gotchas.md`, then `references/support.md` |
| Find a real migrated plugin to copy | `references/reference-prs.md` |

## Boundaries

- This skill owns **extension shape**: which Blueprint replaces which legacy
  extension, where it attaches, and what the package exports. It does not
  choose `@backstage/*` version numbers.
- `/rhdh-backstage-upgrade` owns **version numbers**: which Backstage release
  to move to and how to get the dependency set there. When the plugin's
  `@backstage/*` dependencies are too old for the Blueprints this migration
  needs, invoke it by name first, then return here.
- `/backstage-api-changes` owns the NFS API deltas between the early alpha
  and the current GA surface — removed `NavItemBlueprint`, the `configSchema`
  replacement for `config.schema`, renamed blueprint params. Invoke it by name
  when migrating a plugin that was already migrated against an older NFS API,
  or when a Blueprint param produces a TypeScript error.
- `/rhdh-plugin-export` owns exporting and packaging the migrated plugin.
- `/rhdh-plugin-wiring` owns generating `dynamic-plugins.yaml` configuration.
- `/rhdh-local` owns running a local RHDH instance and applying plugin
  configuration to it.
- `/rhdh-pr-create` owns staging, commits, and pull requests. Leave changed
  files unstaged and list them when you finish.

Invoke a named skill and describe the handoff in the conversation. Never open
another skill's files.

## Invariants

- NFS is not GA. Default to the alpha approach: NFS at `./alpha`, legacy
  untouched at the root export. Use the colocated approach only when the user
  wants both APIs from one import path.
- Keep component-level imports (`useApi`, `useRouteRef`) on
  `@backstage/core-plugin-api` so the same components serve both export paths.
  Reach for `compatWrapper()` only when a component needs a legacy context
  provider that NFS does not supply.
- Core blueprints come from `@backstage/frontend-plugin-api`. RHDH-only
  blueprints such as `AppDrawerContentBlueprint` and
  `GlobalHeaderMenuItemBlueprint` come from `@red-hat-developer-hub/*`. Do not
  mix the two namespaces.
- Put entity content and cards directly in the plugin's `extensions` array.
  Use `createFrontendModule` only to target a different plugin — translations
  at `pluginId: 'app'`, homepage widgets at `pluginId: 'home'`.
- Legacy exports stay available. A breaking change to a legacy consumer needs
  explicit user approval.
- Run `yarn tsc` from the workspace root, not the plugin directory, so consumer
  import breakage surfaces.
- Do not stage, commit, push, or open a pull request here.

## Completion

Report the extensions discovered and their NFS equivalents, the export approach
chosen, the files changed and left unstaged, the verification commands run and
their results, any legacy consumer risk, and the named skill to invoke next for
export, wiring, local testing, or publication.

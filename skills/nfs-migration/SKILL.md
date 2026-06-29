---
name: nfs-migration
description: >
  Migrate Backstage frontend plugins from the legacy system to the New Frontend
  System (NFS). Use when asked to "migrate to NFS", "new frontend system",
  "convert plugin to NFS", "createFrontendPlugin", "PageBlueprint",
  "ApiBlueprint", "SubPageBlueprint", "alpha to GA", "legacy to NFS",
  "frontend migration", "extension blueprints", "migrate frontend plugin",
  "NFS support", "graduate alpha", or mentions migrating a Backstage plugin
  to the new frontend system for RHDH.
---

> **Human-readable guide:** `docs/nfs-migration-guide.md` is the authoritative source for migration patterns. These reference files are optimized for agent consumption. When patterns diverge, the guide takes precedence.

<essential_principles>

<principle name="discover_first">
Always read the plugin's `package.json`, `src/plugin.ts` (or `src/plugin.tsx`), route refs, API factories, and exported components before making any changes. Understand what exists before migrating.
</principle>

<principle name="nfs_as_default">
NFS should be the root export (`.`). Legacy goes to `./legacy` with `@deprecated` tags if kept. This is the GA pattern.
</principle>

<principle name="upstream_apis">
Use `@backstage/frontend-plugin-api` for core blueprints. RHDH-specific blueprints (`AppDrawerContentBlueprint`, `GlobalHeaderMenuItemBlueprint`) come from `@red-hat-developer-hub/*` packages. Don't mix them up.
</principle>

<principle name="modules_not_plugins">
Entity content and cards can go directly in the plugin's `extensions` array — the blueprint declares its own attach point. Use `createFrontendModule` only for extensions that target a different plugin (translations → `pluginId: 'app'`, homepage widgets → `pluginId: 'home'`) or when injecting content from outside a plugin you don't own.
</principle>

<principle name="shared_components">
Keep component imports (`useApi`, `useRouteRef`, etc.) on `@backstage/core-plugin-api` — they work in both legacy and NFS contexts. This lets the same components serve both the root export (NFS) and `./legacy` export. Only use `compatWrapper()` when a component depends on legacy context providers (e.g. old `SidebarContext`) that aren't available in NFS. Don't migrate component imports to `@backstage/frontend-plugin-api` if you need to support legacy consumers.
</principle>

<principle name="keep_legacy_optional">
Ask the user if they want to keep legacy exports at `./legacy`. If yes, move old `plugin.ts` code there with `@deprecated` JSDoc. If no, remove it.
</principle>

</essential_principles>

<intake>

## What would you like to do?

1. **Migrate a plugin to NFS** — Analyze your existing plugin and convert it to the New Frontend System
2. **Test a migrated plugin in RHDH** — Deploy and verify in a local or cluster RHDH instance
3. **Learn about NFS migration** — Read the migration guide

**Wait for response before proceeding.**

</intake>

<routing>

| Response | Action |
|----------|--------|
| 1, "migrate", "convert", "NFS" | Follow the migration workflow below |
| 2, "test", "verify", "deploy" | Read `workflows/test-nfs-plugin.md` |
| 3, "learn", "guide", "overview" | Read `../../docs/nfs-migration-guide.md` and present key sections to the user |

</routing>

<migration_workflow>

### Step 1: Discover

Read `package.json` and `src/plugin.ts` (or `src/plugin.tsx`). Identify:
- Plugin ID
- Routes and route refs
- API factories
- Routable extensions (pages)
- Component extensions (entity cards, tabs)
- Sidebar/nav items
- Translations
- RHDH-specific extensions (drawers, header items, homepage widgets)
- RHDH dynamic plugin mount points (`app-config.dynamic.yaml` — see `references/mount-point-mapping.md`)

List all findings to the user before proceeding.

If the plugin's `@backstage/*` dependencies are outdated, upgrade them first using the `backstage-upgrade` skill (`../backstage-upgrade/SKILL.md`) before proceeding with migration.

### Step 2: Choose Approach

Use **Direct to GA** by default: NFS becomes root export (`.`), legacy at `./legacy`.

Only ask about the **Phased** approach (`./alpha`) if the user says they have external consumers that can't migrate yet.

### Step 3: Migrate Extensions

For each extension type found in Step 1, load the appropriate reference:

| Extension type | Reference to load |
|----------------|-------------------|
| Pages, API factories | `references/migrate-page.md` |
| Entity content tabs or cards | `references/migrate-entity-content.md` |
| Translations / i18n | `references/migrate-translations.md` |
| RHDH drawers, header items, homepage widgets | `references/migrate-rhdh-extensions.md` |
| App-level wrappers or root elements | `references/migrate-app-level.md` |

Apply each reference's patterns to the discovered extensions. For page plugins, create NFS variants of page components without the page shell (dual header pattern in `migrate-page.md`).

### Step 4: Update package.json

Load `references/package-json.md` and apply the export configuration matching the chosen approach (GA or phased).

### Step 5: Update App Wiring

Load `references/app-setup.md` and:
- Convert `dev/index.tsx` to use the NFS dev app pattern (`createDevApp` from `@backstage/frontend-dev-utils`)
- Move the old legacy dev app to `dev/legacy.tsx` with a `start:legacy` script
- If `packages/app` imports legacy APIs from the plugin root, update those imports to use the `./legacy` subpath (or create a separate `packages/app-legacy` for the old frontend system, keeping `packages/app` as NFS)

### Step 6: Verify

Load `references/verification.md` and run all checks. Run `yarn tsc` from the **workspace root** (not just the plugin directory) to catch consumer import issues.

</migration_workflow>

<reference_index>

| Reference | Load when... |
|-----------|-------------|
| `references/migrate-page.md` | Plugin has pages or API factories |
| `references/api-changes.md` | Updating a plugin migrated against an older NFS version |
| `references/migrate-entity-content.md` | Plugin has entity tabs or cards |
| `references/migrate-translations.md` | Plugin has i18n/translations |
| `references/migrate-rhdh-extensions.md` | Plugin uses RHDH drawer, header, or homepage widgets |
| `references/mount-point-mapping.md` | Plugin uses RHDH dynamic plugin mount points (legacy config) |
| `references/migrate-app-level.md` | Plugin has app-level wrappers or root elements |
| `references/package-json.md` | Updating package.json exports |
| `references/app-setup.md` | Setting up or updating the NFS dev app |
| `references/verification.md` | Verifying the migration |
| `references/testing-rhdh.md` | Testing with a real RHDH instance |
| `references/gotchas.md` | Troubleshooting migration issues |
| `references/reference-prs.md` | Looking for real migration examples |
| `references/support.md` | User needs help beyond what the skill covers |
| `../../docs/nfs-migration-guide.md` | User wants to learn about NFS |

</reference_index>

<success_criteria>

- Plugin default-exports a `createFrontendPlugin` result
- All legacy extensions have NFS Blueprint equivalents
- Pages that need nav entries have `title` and `icon` set (on `PageBlueprint` or `createFrontendPlugin`)
- `package.json` exports NFS at `.` (direct-to-GA) or `./alpha` (phased)
- Translations are in a `createFrontendModule` with `pluginId: 'app'`
- Entity content extensions are in the plugin's `extensions` array (or a catalog module if injecting from outside)
- `yarn tsc` and `yarn build` pass
- Legacy code is at `./legacy` with `@deprecated` tags (if kept)

</success_criteria>

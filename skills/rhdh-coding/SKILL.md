---
name: rhdh-coding
description: >-
  Backstage and RHDH plugin development patterns. Use when writing, modifying,
  or reviewing code in a Backstage or RHDH plugin — frontend components, backend
  services, API clients, styling, testing, entity pages, scaffolder actions,
  catalog processors, NFS Blueprints, dynamic plugin configuration. Also use
  when asked to "add a feature to a plugin", "implement a Backstage component",
  "create an API client", "write plugin tests", "add a backend route", "create
  a scaffolder action", "what plugin type should I use", or any coding task in
  a Backstage or RHDH codebase.
---

# RHDH Coding

Patterns for Backstage and RHDH plugin development that agents need but can't
reliably get from training data or codebase discovery alone. This covers what
you'd learn after six months of getting burned by non-obvious conventions.

## Before You Write Code

### 1. Check for existing specs

Look for a spec, PRD, or OpenSpec design for this work — in `docs/plans/**/`,
`specifications/`, `openspec/changes/*/`, or linked from the issue. If found,
use the component list and acceptance criteria as your implementation blueprint.
Read `references/frontend-specs.md` for what good frontend specs include.

### 2. Discover the plugin context

Run the detection script to understand what you're working with:

```bash
python scripts/detect-rhdh-context.py --path <plugin-dir>
```

This reports: Backstage role, frontend system (legacy/NFS/dual), existing
extensions, MUI version, dynamic plugin status, plugin ID, scalprum name.

### 3. Read workspace instructions

```bash
test -f AGENTS.md && cat AGENTS.md
test -f CLAUDE.md && cat CLAUDE.md
```

These contain repo-specific rules that override general patterns.

### 4. Check version compatibility

Consult `../rhdh/references/versions.md` for the RHDH → Backstage version
matrix. Your `@backstage/*` dependency versions must match the target RHDH
version. Mismatched versions cause runtime errors — most commonly "Cannot
read properties of undefined."

## Styling: BUI First

**For new plugins,** use Backstage UI (`@backstage/ui`) with CSS Modules and
BUI CSS variables. **In existing plugins,** match whatever the workspace already
uses — if it's MUI v4, stay consistent rather than mixing libraries. Only
introduce BUI in a workspace that has already adopted it or is actively migrating.

**Priority for new plugins:**
1. **BUI** (`@backstage/ui`) — default for new plugins and new workspaces
2. **MUI v5** (`@mui/material`) — when BUI lacks the component you need
3. **MUI v4** (`@material-ui/core`) — legacy maintenance only

When using MUI v5 alongside BUI, add the class name generator to prevent
collisions in dynamic plugin bundles:

```typescript
// src/index.ts
import { unstable_ClassNameGenerator as ClassNameGenerator } from '@mui/material/className';
ClassNameGenerator.configure(name => name.startsWith('v5-') ? name : `v5-${name}`);
```

**Icons:** Use `@remixicon/react` (not `@material-ui/icons`).

Read `references/bui.md` for the component mapping table and CSS variable reference.

## Frontend Implementation

### Verify BUI component APIs before use

The `references/bui.md` mapping table is a quick-start guide, not the source
of truth. Before using any BUI component for the first time, check the actual
type definitions in `node_modules/@backstage/ui/dist/index.d.ts`. Patterns
that differ from what you might expect:

- `Card` uses a discriminated union (href/onPress/static) — no `onClick`
- `Select` multi-mode uses `value`/`onChange`, not `selectedKeys`/`onSelectionChange`
- `Table` requires `isRowHeader: true` on at least one column config
- `Badge` has no `variant` prop

### Follow existing repo conventions

Before creating any configuration, fixture path, or utility pattern, check
2–3 other workspaces in the repo for the established convention. Discoveries
that save debugging time:

- Catalog `type: file` paths resolve from `packages/backend/` CWD — use
  `../../` to reach workspace root files
- Frontend plugin `.eslintrc.js` may need `root: true` to avoid monorepo
  plugin conflicts — check sibling packages before changing
- `import React from 'react'` is blocked — use named imports

### Use CLI tools when specs say to

If the task spec says "scaffold via backstage-cli" or "run create-app", use
those tools. Do not silently substitute manual file creation. If the CLI fails,
report the error and ask for guidance.

### Keep hooks simple

Data-fetching hooks should fetch once and apply filters via `useMemo`. Do not
split server-side and client-side filter concerns unless the spec explicitly
identifies a dataset size that requires server-side pagination. Do not suppress
`react-hooks/exhaustive-deps` as a first approach — if you need a suppression,
the hook design is probably too complex.

### Build incrementally, not in bulk

Do not write all components in one pass and then run CI. Write one component
or hook, run `yarn tsc:full` to verify types, and if it's visual, start the
dev server and verify it renders correctly. Fix issues before moving to the
next component.

### Verify visual output

After writing visual components, verify they render correctly before
presenting to the human. Start the dev server, navigate to the page, and
compare against design screenshots if provided. Do not rely solely on
tsc + test passing — compiled code that looks wrong is still wrong.

### Self-review before presenting

Before telling the human the work is done, review your own changes as if
reviewing someone else's PR. Check for: duplicated utility functions across
files, dead or stub code, hardcoded strings that should use translations,
unnecessary complexity the spec did not ask for. Verify the public API
surface (what hooks return, what props components accept) matches what
consumers actually need.

### PR workflow awareness

Before writing code, know what branch you are on and whether it matches the
target PR. If there is existing uncommitted work, protect it before starting
new changes. When stashing, always use `--include-untracked` to capture new
files. When committing a subset of changes, use `git add <specific files>`.

### Automated review bot suggestions

Do not blindly apply automated review bot suggestions. Before making any
change a bot suggests: understand why the current code is the way it is,
test the suggested change locally, and if it breaks something, dismiss the
suggestion with an explanation.

## Frontend System: NFS for New Plugins

New plugins targeting RHDH 1.5+ should use the **new frontend system (NFS)**
with Blueprints (`createFrontendPlugin`, `PageBlueprint`, `EntityCardBlueprint`,
etc.).

Legacy system (`createPlugin` + `createRoutableExtension`) is for existing
plugins not yet migrated. For migration, use the `nfs-migration` sibling skill.

Read `references/nfs.md` for Blueprint patterns, alpha export structure, and
compatWrapper decisions.

## Plugin Types

Not sure whether to build a page, a card, an entity tab, or a backend module?
Read `references/plugin-types.md` for the decision guide.

## Backend: New System Only

All backend code MUST use:
- `createBackendPlugin` — new standalone backend capabilities
- `createBackendModule` — extensions to existing plugins (catalog, scaffolder, auth)

From `@backstage/backend-plugin-api`. Never the legacy backend system.

Core services: `httpRouter`, `logger`, `rootConfig`, `httpAuth`, `database`,
`scheduler`, `permissions`, `discovery`.

**Default export is required** from the entry point (`src/index.ts`). Missing
default export is the #1 cause of "plugin not loading" in RHDH.

## RHDH Dynamic Plugins

Key gotchas (read `references/rhdh.md` for full details):

- **Default export required** from `src/index.ts` — missing this is the #1 cause of "plugin not loading"
- **Scalprum name** must match the key in `dynamic-plugins.yaml` wiring (derived from package name)
- **MUI v5 class name generator** required when using `@mui/material` in dynamic bundles
- **Auth:** use `fetchApi` — it includes auth headers automatically. Don't implement custom auth.
- **RHDH-only Blueprints:** `AppDrawerContentBlueprint`, `GlobalHeaderMenuItemBlueprint` — not upstream

`references/rhdh.md` covers all RHDH-specific patterns including backend modules,
extension points, theming, i18n, and the common package pattern.

## Analytics

BUI components (`Link`, `ButtonLink`, `Tab`, `MenuItem`, `Tag`, `Table` rows)
have built-in click analytics via the Backstage Analytics API. Don't add manual
`captureEvent('click', ...)` for these — it produces duplicates. Use `noTrack`
prop to suppress the built-in event only when replacing it with a domain-specific
verb (e.g., `deploy`, `approve`). For detailed instrumentation guidance, install
the official `plugin-analytics-instrumentation` skill from backstage.io.

## Testing

Backstage has its own test infrastructure that differs from standard React testing.
Read `references/testing.md` for: TestApiProvider setup, renderInTestApp,
entity context mocking, async component testing, accessibility testing, and
common gotchas.

## Before You Commit

Run these commands **in order** from the workspace root (e.g., `workspaces/boost/`).
Stop on first failure — fix it before continuing. This sequence catches every CI
gate locally.

```bash
yarn prettier:fix          # format code
yarn tsc:full              # full TypeScript type check
yarn build:all             # build all packages in the workspace
yarn test --watchAll=false  # run tests (disable watch mode)
yarn build:api-reports:only # generate/update API report files
```

### API reports

`build:api-reports:only` generates `report.api.md` files for packages with
public exports. These files **must be committed** — CI checks them. All public
exports need `/** @public */` JSDoc with a description (not just the bare tag).

### Changesets

Changesets are required for published package changes. Rules:
- Only cover plugins under `plugins/` — **never `packages/*`** (those are
  private app/backend packages that are never published)
- Only include a plugin if it has changes in `src/` or other published paths
  (root `index.ts`, `config.d.ts`, `package.json`)
- Changes only in `dev/`, `tests/`, `__fixtures__/`, or stories do NOT need
  a changeset for that plugin
- Write the changeset file directly to `<workspace>/.changeset/<id>.md` —
  don't run `yarn changeset` interactively

### Commits

All commits must be signed off (`git commit -s`) per DCO requirements.

## Reference Index

| Reference | Load when... |
|-----------|-------------|
| `references/frontend-specs.md` | Writing specs, PRDs, or OpenSpec proposals for frontend features |
| `references/bui.md` | Using BUI components — mapping table, CSS variables, icons |
| `references/plugin-types.md` | Deciding what type of plugin or extension to build |
| `references/nfs.md` | Writing NFS code — Blueprints, package exports, compatWrapper |
| `references/dev-app.md` | Plugin dev mode, full Backstage app setup, sidebar, app-config |
| `references/testing.md` | Writing tests — TestApiProvider, entity mocking, a11y |
| `references/rhdh.md` | RHDH-specific patterns — dynamic plugins, backend modules, i18n |
| `references/ecosystem-skills.md` | Complementary open-source and official Backstage.io skills |

## Sibling Skills (rhdh-skill)

| Skill | Use when... |
|-------|------------|
| `create-plugin` | Scaffolding a new plugin from scratch |
| `nfs-migration` | Migrating an existing plugin from legacy to NFS |
| `overlay` | Managing overlay packaging for the Extensions Catalog |
| `backstage-upgrade` | Upgrading Backstage dependency versions |
| `rhdh-local` | Running and testing plugins locally |
| `rhdh` | RHDH version matrix, repo navigation, ecosystem context |

## Ecosystem & Official Backstage Skills

Read `references/ecosystem-skills.md` for complementary open-source skills
(frontend quality from skills.sh) and official Backstage.io skills (migration
and instrumentation workflows).

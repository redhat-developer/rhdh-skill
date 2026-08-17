# NFS Overview

## What is the New Frontend System

The Backstage New Frontend System (NFS) replaces the legacy frontend plugin API. Instead of manually wiring plugins into an app with `createPlugin`, `createRoutableExtension`, `FlatRoutes`, and imperative JSX route trees, NFS uses declarative extension **Blueprints** (`PageBlueprint`, `ApiBlueprint`, `EntityContentBlueprint`, etc.) and `createFrontendPlugin` from `@backstage/frontend-plugin-api`.

Plugins declare what they provide. The app assembles itself from features:

```ts
import { createApp } from '@backstage/frontend-defaults';
const app = createApp({ features: [myPlugin, catalogPlugin, ...] });
```

## Why migrate

- **Declarative**: plugins describe their own routes, nav items, and APIs — no manual wiring in the app
- **Configurable**: extensions can be enabled, disabled, or reordered via `app-config.yaml`
- **Auto-discoverable**: apps detect installed plugins automatically via `app.packages: all`
- **Composable**: modules can inject extensions into other plugins (e.g. entity tabs into catalog)
- **Required**: the legacy APIs are being deprecated and will be removed

## Deprecation timeline

| Phase | Status | What happens |
|-------|--------|-------------|
| Current (RHDH 1.10) | NFS available as `./alpha` | Add NFS exports alongside legacy. Both work side-by-side. |
| Next | NFS becomes default | NFS moves to root (`.`), legacy moves to `./legacy`. |
| GA + 2 releases | Legacy removed | `./legacy` subpath is removed. Only NFS remains. |

## Key concepts

| Legacy | NFS equivalent |
|--------|---------------|
| `createPlugin` | `createFrontendPlugin` (default export) |
| `createRoutableExtension` | `PageBlueprint` |
| `createComponentExtension` | `EntityContentBlueprint`, `EntityCardBlueprint`, etc. |
| `createApiFactory` in plugin `apis` array | `ApiBlueprint` with `defineParams` wrapper |
| Manual route wiring in `App.tsx` | Auto-discovered from `PageBlueprint` `routeRef` |
| `menuItem` in dynamic routes config | Auto-discovered from `PageBlueprint` `title` + `icon` |
| `mountPoints` in `app-config.yaml` | Extension blueprints with built-in attach points |
| `routeBindings` in plugin config | `externalRoutes` on plugin + `app.routes.bindings` |

## Two migration approaches

- **Alpha (default)** — NFS at `./alpha`, legacy unchanged at root. No breaking changes for consumers.
- **Colocated** — NFS as default export in `index.ts`, legacy re-exported from `index.ts` for backward compat.

See `package-json.md` for the export configuration for each approach.

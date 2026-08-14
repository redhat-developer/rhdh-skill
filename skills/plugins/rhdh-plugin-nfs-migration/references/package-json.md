# Package.json Export Configuration

## Alpha approach (default)

NFS at `./alpha`, legacy stays at root. No breaking changes for consumers. This is the recommended approach while NFS is not GA.

```json
{
  "exports": {
    ".": "./src/index.ts",
    "./alpha": "./src/alpha.tsx",
    "./package.json": "./package.json"
  },
  "typesVersions": {
    "*": {
      "alpha": ["src/alpha.tsx"],
      "package.json": ["package.json"]
    }
  }
}
```

### File layout

- `src/index.ts` — existing legacy exports (unchanged)
- `src/alpha.tsx` — default-exports `createFrontendPlugin(...)`, named-exports modules. Use `.tsx` since blueprint loaders return JSX

## Colocated approach

NFS as default export in `index.ts`, legacy source in `legacy.ts` but re-exported from `index.ts` for backward compatibility. Use when you want both APIs available from the same import path.

```json
{
  "exports": {
    ".": "./src/index.ts",
    "./package.json": "./package.json"
  }
}
```

### File layout

- `src/index.ts` — default-exports `createFrontendPlugin` from `plugin.tsx`, AND re-exports legacy named exports from `legacy.ts` for backward compatibility
- `src/plugin.tsx` — NFS plugin definition (`createFrontendPlugin` with blueprints, default export). Use `.tsx` since blueprint loaders return JSX
- `src/legacy.ts` — old `createPlugin(...)` result with `@deprecated` JSDoc tags

```tsx
// src/index.ts (colocated approach)
export { default } from './plugin';
export { isMyPluginAvailable } from './utils';

// Re-export legacy APIs for backward compatibility
export { myPlugin, MyPage, MyCard } from './legacy';
```

## Module entry points for auto-discovery

Modules targeting `pluginId: 'app'` (translations, init logic) are not auto-discovered by `app.packages: all`. To enable auto-discovery in RHDH dynamic plugins, add each module as a separate entry point with a default export:

```tsx
// src/myTranslationsModuleExport.ts
export { myTranslationsModule as default } from './index';
```

```json
{
  "exports": {
    ".": "./src/index.ts",
    "./alpha": "./src/alpha.tsx",
    "./my-translations-module": "./src/myTranslationsModuleExport.ts",
    "./package.json": "./package.json"
  }
}
```

Module federation treats each entry point as a separate remote, so it gets loaded without explicit `features` array changes. See `migrate-translations.md` for the full pattern.

## Required backstage fields

Ensure these exist in `package.json`:

```json
{
  "backstage": {
    "role": "frontend-plugin",
    "pluginId": "my-plugin",
    "pluginPackages": [
      "@scope/backstage-plugin-my-plugin"
    ]
  }
}
```

- `role`: must be `frontend-plugin`
- `pluginId`: must match the `pluginId` passed to `createFrontendPlugin`
- `pluginPackages`: array of all packages in this plugin family (frontend, backend, common, etc.)

## Scalprum configuration (dual-export period)

RHDH dynamic plugins use a `scalprum` section in the derived package's `package.json` for the legacy Webpack module-federation container. Keep this working during migration.

```json
{
  "scalprum": {
    "name": "my-plugin-package",
    "exposedModules": {
      "PluginRoot": "./src/index.ts",
      "FooModule": "./src/foo.ts"
    }
  }
}
```

- **`scalprum.name`** — Webpack container name. This is also the key under `dynamicPlugins.frontend` in operator YAML — it may differ from the npm package name.
- **`scalprum.exposedModules`** — maps module names to source entrypoints. Each key becomes a loadable entrypoint in the dynamic plugin bundle.

Legacy wiring resolves modules via `module` (which `exposedModules` key to load, defaults to `PluginRoot`) and `importName` (which named export to render, defaults to default export):

```yaml
dynamicPlugins:
  frontend:
    my-plugin-package:
      mountPoints:
        - mountPoint: entity.page.overview/cards
          module: FooModule
          importName: MyCard
```

The RHDH CLI `--scalprum-config` option can override this at export time.

### Dual-export checklist

- [ ] Legacy `scalprum.exposedModules` resolves all `importName`/`module` references in existing operator config
- [ ] `./alpha` export added for NFS (`createFrontendPlugin` default export)
- [ ] As each feature moves to NFS extensions, delete the corresponding `dynamicPlugins.frontend` YAML keys
- [ ] Re-export with a CLI version from the RHDH version matrix

## Checklist

- [ ] `exports` field has `./alpha` (alpha approach) or `.` (colocated approach) pointing to NFS entry
- [ ] `typesVersions` mirrors any sub-path exports
- [ ] Legacy exports remain accessible (unchanged root for alpha; re-exported from `index.ts` for colocated)
- [ ] `backstage.role` is `frontend-plugin`
- [ ] `backstage.pluginId` matches `createFrontendPlugin({ pluginId: '...' })`

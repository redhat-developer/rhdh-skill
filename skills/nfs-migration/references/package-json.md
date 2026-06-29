# Package.json Export Configuration

## Direct to GA (recommended)

NFS is the root export. Legacy moves to `./legacy`.

```json
{
  "exports": {
    ".": "./src/index.ts",
    "./legacy": "./src/legacy.ts",
    "./package.json": "./package.json"
  },
  "typesVersions": {
    "*": {
      "legacy": ["src/legacy.ts"],
      "package.json": ["package.json"]
    }
  },
  "publishConfig": {
    "access": "public",
    "legacy": {
      "types": "dist/legacy.d.ts",
      "default": "dist/legacy.esm.js"
    }
  }
}
```

### File layout

- `src/index.ts` — re-exports default from `plugin.tsx`, plus shared utilities (e.g. `isMyPluginAvailable`). **Do not re-export legacy APIs here** — they are only reachable via the `./legacy` subpath
- `src/plugin.tsx` — NFS plugin definition (`createFrontendPlugin` with blueprints, default export). Use `.tsx` since blueprint loaders return JSX
- `src/legacy.ts` — old `createPlugin(...)` result with `@deprecated` JSDoc tags

## Phased approach

NFS at `./alpha`, legacy stays at root.

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
- `src/alpha.tsx` — default-exports `createFrontendPlugin(...)`, named-exports modules

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

## Checklist

- [ ] `exports` field has `.` pointing to NFS entry
- [ ] `typesVersions` mirrors any sub-path exports
- [ ] `publishConfig` has types/default for each sub-path (GA approach)
- [ ] `backstage.role` is `frontend-plugin`
- [ ] `backstage.pluginId` matches `createFrontendPlugin({ pluginId: '...' })`

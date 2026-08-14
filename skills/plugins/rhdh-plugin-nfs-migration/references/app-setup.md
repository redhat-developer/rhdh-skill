# NFS App Setup

## App entry point

```tsx
import { createApp } from '@backstage/frontend-defaults';
import catalogPlugin from '@backstage/plugin-catalog/alpha';
import myPlugin, { myTranslationsModule, myCatalogModule } from '@scope/my-plugin';

const app = createApp({
  features: [
    catalogPlugin,
    myPlugin,
    myTranslationsModule,
    myCatalogModule,
  ],
});

export default app;
```

## index.tsx

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(App.createRoot());
```

## Import rules

| Approach | Plugin import | Module imports |
|----------|--------------|----------------|
| Alpha (default) | `import myPlugin from '@scope/my-plugin/alpha'` | `import { myTranslationsModule } from '@scope/my-plugin/alpha'` |
| Colocated | `import myPlugin from '@scope/my-plugin'` | `import { myTranslationsModule } from '@scope/my-plugin'` |

- The default export is always the plugin (`createFrontendPlugin` result)
- Named exports are modules (`createFrontendModule` results)
- Each module must be listed individually in `features`

## Dev app setup

Add an NFS dev app alongside the existing legacy dev app. Keep the legacy dev app as the default `yarn start` entry point (since NFS is not GA). Add the NFS dev app at `dev/nfs.tsx` with a `start:nfs` script, or at `dev/index.tsx` if you prefer NFS as default during development.

### NFS dev app (`dev/index.tsx`)

Use `createApp` from `@backstage/frontend-defaults` with `createFrontendModule` for mock APIs:

```tsx
import ReactDOM from 'react-dom/client';
import { createApp } from '@backstage/frontend-defaults';
import { ApiBlueprint, createFrontendModule } from '@backstage/frontend-plugin-api';
import catalogPlugin from '@backstage/plugin-catalog/alpha';
import myPlugin from '../src/plugin';

const myDevModule = createFrontendModule({
  pluginId: 'my-plugin',
  extensions: [
    ApiBlueprint.make({
      name: 'my-api-mock',
      params: defineParams => defineParams({
        api: myApiRef,
        deps: {},
        factory: () => new MockApiClient(),
      }),
    }),
  ],
});

const app = createApp({
  features: [catalogPlugin, myPlugin, myDevModule],
});

ReactDOM.createRoot(document.getElementById('root')!).render(app.createRoot());
```

To redirect `/` to a default page, add to `app-config.yaml`:

```yaml
app:
  extensions:
    - app/routes:
        config:
          redirects:
            - from: /
              to: /catalog
```

### Legacy dev app (`dev/legacy.tsx`)

Move the old `createDevApp` from `@backstage/dev-utils` code here. Add to `package.json`:

```json
"start:legacy": "backstage-cli package start --entrypoint dev/legacy"
```

## Consumer imports

Since NFS is not GA, legacy exports must remain accessible from the package root:

- **Alpha approach:** No consumer changes needed — legacy stays at root, NFS is at `./alpha`.
- **Colocated approach:** Legacy is re-exported from `index.ts` — existing imports continue to work. NFS consumers use the default import.

## Dynamic plugin considerations (RHDH)

When running as a dynamic plugin in RHDH:

- The app loads plugins automatically from `dynamic-plugins.yaml`
- No manual `features` array needed — RHDH handles registration
- Ensure the plugin's `package.json` has correct `backstage.role` and `pluginId`
- Modules must be exported and declared in the dynamic plugin config
- Test with `APP_CONFIG_app_packageName=app-next` and `ENABLE_STANDARD_MODULE_FEDERATION=true` to use NFS app

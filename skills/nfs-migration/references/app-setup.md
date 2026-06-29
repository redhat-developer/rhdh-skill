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
| Direct to GA | `import myPlugin from '@scope/my-plugin'` | `import { myTranslationsModule } from '@scope/my-plugin'` |
| Phased | `import myPlugin from '@scope/my-plugin/alpha'` | `import { myTranslationsModule } from '@scope/my-plugin/alpha'` |

- The default export is always the plugin (`createFrontendPlugin` result)
- Named exports are modules (`createFrontendModule` results)
- Each module must be listed individually in `features`

## Dev app setup

For direct-to-GA, `dev/index.tsx` should be the NFS dev app (it's the default `yarn start` entry point). Keep the old legacy dev app at `dev/legacy.tsx` and add a `start:legacy` script.

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

## Consumer migration (packages/app)

If the workspace has a `packages/app` that imports legacy APIs from the plugin's root, those imports will break after the GA migration (legacy is no longer at the root export). Two approaches:

1. **Update imports** — Change `import { MyPage } from '@scope/my-plugin'` to `import { MyPage } from '@scope/my-plugin/legacy'`
2. **Create a separate legacy app** — Keep `packages/app` as the NFS app and create `packages/app-legacy` for the old frontend system. This is the pattern used in `rhdh-plugins`.

## Dynamic plugin considerations (RHDH)

When running as a dynamic plugin in RHDH:
- The app loads plugins automatically from `dynamic-plugins.yaml`
- No manual `features` array needed — RHDH handles registration
- Ensure the plugin's `package.json` has correct `backstage.role` and `pluginId`
- Modules must be exported and declared in the dynamic plugin config
- Test with `APP_CONFIG_app_packageName=app-next` and `ENABLE_STANDARD_MODULE_FEDERATION=true` to use NFS app

# Translation Migration

Translations target the **app plugin** (`pluginId: 'app'`), so they must use `createFrontendModule`, **not** be included in your plugin's extensions array.

## TranslationBlueprint

```tsx
import { TranslationBlueprint } from '@backstage/plugin-app-react';
import { myTranslationResource } from './translations';

const translationExtension = TranslationBlueprint.make({
  params: {
    resource: myTranslationResource,
  },
});
```

## Register as an app module

```tsx
import { createFrontendModule } from '@backstage/frontend-plugin-api';

export const myTranslationsModule = createFrontendModule({
  pluginId: 'app',
  extensions: [translationExtension],
});
```

## Export separately

In your plugin's `src/index.ts`:

```tsx
export { default as default } from './plugin';
export { myTranslationsModule } from './modules';
```

## Auto-discovery via separate entry point (RHDH dynamic plugins)

Modules targeting `pluginId: 'app'` are not auto-discovered by `app.packages: all` because they are not part of `createFrontendPlugin`. To make them auto-discoverable without explicit code changes in the consuming app, re-export the module as a **default export** from a separate file and add it as its own entry point in `package.json`:

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
  },
  "typesVersions": {
    "*": {
      "alpha": ["src/alpha.tsx"],
      "my-translations-module": ["src/myTranslationsModuleExport.ts"],
      "package.json": ["package.json"]
    }
  }
}
```

Module federation treats each entry point as a separate remote. This lets the Backstage app load the module automatically without adding it to the `features` array.

This pattern works for any `createFrontendModule` that targets a different plugin (init logic modules, translation modules, etc.). See the [quickstart plugin](https://github.com/redhat-developer/rhdh-plugins/tree/main/workspaces/quickstart/plugins/quickstart) for a real example.

## Key rules

- **Always** `pluginId: 'app'` — translations are app-level, not plugin-level
- Each language gets its own `createTranslationResource` call
- Export the module as a named export from `index.ts` for direct consumers
- For auto-discovery in RHDH, add a separate entry point with a default export

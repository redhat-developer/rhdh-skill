# RHDH-Specific Patterns

Patterns that apply only to Red Hat Developer Hub, not upstream Backstage.

## Dynamic Plugin Entry Points

### Frontend
Named exports from `src/index.ts` become `importName` values in wiring YAML:
```typescript
export { MyPage } from './plugin';        // importName: "MyPage"
export { MyCard } from './plugin';        // importName: "MyCard"
```

### Backend
Default export is required:
```typescript
// src/index.ts
export { default } from './plugin';
```
Missing default export = plugin won't load. This is the #1 backend plugin issue.

## Scalprum Name

Derived from package name: `@red-hat-developer-hub/backstage-plugin-foo` →
`red-hat-developer-hub.backstage-plugin-foo`

Override via `scalprum.name` in `package.json`. Must match the key under
`dynamicPlugins.frontend.<key>` in `dynamic-plugins.yaml`.

## MUI v5 Class Name Generator

Required for any plugin using `@mui/material` in RHDH dynamic plugin bundles:
```typescript
// src/index.ts
import { unstable_ClassNameGenerator as ClassNameGenerator } from '@mui/material/className';
ClassNameGenerator.configure(name => name.startsWith('v5-') ? name : `v5-${name}`);
```

## Auth

Use `fetchApi` for all HTTP requests — auth headers are included automatically.
Access user identity via `identityApi.getCredentials()`. Don't implement custom
auth flows in plugins.

## Theming

- Dev harness: `getAllThemes()` from `@red-hat-developer-hub/backstage-plugin-theme`
- Production: RHDH app shell provides theming automatically
- Custom themes: `createUnifiedTheme` from `@backstage/theme`, register via `themes` wiring

## i18n / Translations

```tsx
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { TranslationBlueprint } from '@backstage/plugin-app-react';

const translationModule = createFrontendModule({
  pluginId: 'app',  // targets the app, NOT your plugin
  modules: {
    translations: TranslationBlueprint.make({
      namespace: 'plugin.my-plugin',
      resources: [{ locale: 'en', messages: enMessages }],
    }),
  },
});
```

## RHDH-Only Blueprints

| Blueprint | Package | Purpose |
|-----------|---------|---------|
| `AppDrawerContentBlueprint` | `@red-hat-developer-hub/backstage-plugin-dynamic-plugins-react` | App drawer panels |
| `GlobalHeaderMenuItemBlueprint` | `@red-hat-developer-hub/backstage-plugin-global-header` | Global header menu items |

These are NOT upstream Backstage. If the plugin must work outside RHDH, gate
these behind a separate package or conditional check.

## Backend Module Patterns

### Catalog processor
```typescript
import { catalogProcessingExtensionPoint } from '@backstage/plugin-catalog-node';

export default createBackendModule({
  pluginId: 'catalog',
  moduleId: 'my-processor',
  register(reg) {
    reg.registerInit({
      deps: { catalog: catalogProcessingExtensionPoint },
      async init({ catalog }) {
        catalog.addProcessor(new MyProcessor());
      },
    });
  },
});
```

### Scaffolder action
```typescript
import { scaffolderActionsExtensionPoint } from '@backstage/plugin-scaffolder-node';

export default createBackendModule({
  pluginId: 'scaffolder',
  moduleId: 'my-action',
  register(reg) {
    reg.registerInit({
      deps: { scaffolder: scaffolderActionsExtensionPoint },
      async init({ scaffolder }) {
        scaffolder.addActions(createMyAction());
      },
    });
  },
});
```

## Common Package Pattern

When a feature spans frontend and backend, share types via `-common`:
```
@scope/backstage-plugin-foo           # frontend
@scope/backstage-plugin-foo-backend   # backend  
@scope/backstage-plugin-foo-common    # shared types, API ref, constants
```

Common package role: `common-library`. Export types with `/** @public */` JSDoc.
Use `import type` for type-only imports to avoid bundling common into backend.

## Namespace Conventions

| Scope | Pattern |
|-------|---------|
| RHDH plugins | `@red-hat-developer-hub/backstage-plugin-<name>` |
| Community plugins | `@backstage-community/plugin-<name>` |
| Custom plugins | `@<org>/backstage-plugin-<name>` |

Plugin ID: kebab-case, no `backstage-plugin-` prefix. Must match `backstage.pluginId`
in `package.json`.

## Version Compatibility

Consult `../rhdh/references/versions.md` for the full matrix.

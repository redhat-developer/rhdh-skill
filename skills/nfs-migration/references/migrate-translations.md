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

## App integration

The consuming app must include the module in its `features` array:

```tsx
import myPlugin, { myTranslationsModule } from '@scope/my-plugin';

createApp({
  features: [myPlugin, myTranslationsModule],
});
```

## Key rules

- **Always** `pluginId: 'app'` — translations are app-level, not plugin-level
- Each language gets its own `createTranslationResource` call
- Export the module as a named export alongside the default plugin export
- The app must explicitly opt in by adding the module to `features`

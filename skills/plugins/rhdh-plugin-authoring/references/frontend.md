# Create Frontend Plugin

Scaffold and implement a frontend dynamic plugin for Red Hat Developer Hub (RHDH).

## When to Use

- New pages and routes
- Entity page cards and tabs
- Sidebar menu items
- Custom themes
- Scaffolder field extensions
- TechDocs addons
- Search result types and filters
- Any UI component for RHDH

**Not for backend plugins** — use the `backend` command instead.

## Workflow

1. Determine RHDH version
2. Scaffold app and plugin
3. Configure RHDH themes (optional)
4. Implement plugin components
5. Export and package (see `export` command)
6. Configure plugin wiring (see `wiring` command)

## Step 1: Determine RHDH Version

Use the target RHDH version established in `SKILL.md`. Ask the user for it if it is still unresolved.

## Step 2: Scaffold App and Plugin

Run the scaffold script:

```bash
python scripts/scaffold.py \
  --type frontend \
  --rhdh-version 1.9 \
  --plugin-id my-plugin
```

Add `--with-theme` to install the RHDH theme package. Run `python scripts/scaffold.py --help` for all options.

Generated structure:

```
plugins/<plugin-id>/
├── src/
│   ├── index.ts              # Public exports
│   ├── plugin.ts             # Plugin definition
│   ├── routes.ts             # Route references
│   └── components/
│       └── ExampleComponent/
├── package.json
└── dev/
    └── index.tsx             # Development harness
```

## Step 3: Configure RHDH Themes (Optional)

### Install Theme Package

```bash
cd plugins/<plugin-id>
yarn add @red-hat-developer-hub/backstage-plugin-theme
```

### Configure Development Harness

Update `dev/index.tsx`:

```typescript
import { getAllThemes } from '@red-hat-developer-hub/backstage-plugin-theme';
import { createDevApp } from '@backstage/dev-utils';
import { myPlugin, MyPage } from '../src';

createDevApp()
  .registerPlugin(myPlugin)
  .addPage({
    element: <MyPage />,
    title: 'My Plugin',
    path: '/my-plugin',
  })
  .addThemes(getAllThemes())
  .render();
```

### Available Theme APIs

- `getThemes()` / `useThemes()` — Latest RHDH light and dark themes
- `getAllThemes()` / `useAllThemes()` — All themes including legacy versions
- `useLoaderTheme()` — Returns Material-UI v5 theme object

> When deployed to RHDH, the application shell provides theming automatically. This configuration is only for local development.

## Step 4: Implement Plugin Components

### Page Component

```typescript
// src/components/MyPage/MyPage.tsx
import React from 'react';
import { Page, Header, Content } from '@backstage/core-components';

export const MyPage = () => (
  <Page themeId="tool">
    <Header title="My Plugin" />
    <Content>
      <h1>Hello from My Plugin</h1>
    </Content>
  </Page>
);
```

### Entity Card Component

```typescript
// src/components/MyCard/MyCard.tsx
import React from 'react';
import { InfoCard } from '@backstage/core-components';
import { useEntity } from '@backstage/plugin-catalog-react';

export const MyEntityCard = () => {
  const { entity } = useEntity();
  return (
    <InfoCard title="My Plugin Info">
      <p>Entity: {entity.metadata.name}</p>
    </InfoCard>
  );
};
```

### Export Components

```typescript
// src/index.ts
export { myPlugin } from './plugin';
export { MyPage } from './components/MyPage';
export { MyEntityCard } from './components/MyCard';
```

Build and verify:

```bash
cd plugins/<plugin-id>
yarn build
```

## Step 5: Export and Package

Use the `export` command for the full pipeline. Quick version:

```bash
cd plugins/<plugin-id>
npx @red-hat-developer-hub/cli@latest plugin export
npx @red-hat-developer-hub/cli@latest plugin package \
  --tag quay.io/<namespace>/<plugin-name>:v0.1.0
podman push quay.io/<namespace>/<plugin-name>:v0.1.0
```

For advanced options, use the `export` command reference.

## Step 6: Configure Plugin Wiring

Use the `wiring` command to auto-generate configuration from plugin source. Or configure manually:

```yaml
plugins:
  - package: oci://quay.io/<namespace>/<plugin-name>:v0.1.0!my-plugin
    disabled: false
    pluginConfig:
      dynamicPlugins:
        frontend:
          my-org.plugin-my-plugin:
            dynamicRoutes:
              - path: /my-plugin
                importName: MyPage
                menuItem:
                  icon: dashboard
                  text: My Plugin
```

### Key Wiring Options

| Option | Purpose |
|--------|---------|
| `dynamicRoutes` | Full page routes with optional sidebar menu items |
| `mountPoints` | Entity page cards, tabs, and other integrations |
| `menuItems` | Sidebar ordering and nesting |
| `appIcons` | Custom icons for routes and menus |
| `entityTabs` | New tabs on entity pages |

For complete wiring options, invoke `/rhdh-plugin-wiring` by name. It owns
`dynamic-plugins.yaml` generation and the full mount-point reference.

## Known Issues

### MUI v5 Styles Missing

Add class name generator to `src/index.ts`:

```typescript
import { unstable_ClassNameGenerator as ClassNameGenerator } from '@mui/material/className';
ClassNameGenerator.configure(componentName =>
  componentName.startsWith('v5-') ? componentName : `v5-${componentName}`
);
export * from './plugin';
```

### Grid Spacing Missing

Apply spacing manually to MUI v5 Grid:

```tsx
<Grid container spacing={2}>
  <Grid item>...</Grid>
</Grid>
```

### Scalprum Name Mismatch

The `scalprum.name` in `package.json` (auto-generated during export) must match the key under `dynamicPlugins.frontend.<key>` in `dynamic-plugins.yaml`. Default derivation: `@my-org/backstage-plugin-foo` → `my-org.backstage-plugin-foo`.

### New vs Legacy Frontend System

Plugins using the new Backstage frontend system (`createPlugin` from `@backstage/frontend-plugin-api`) have different export patterns than the legacy system (`createPlugin` from `@backstage/core-plugin-api`). Check which system the plugin uses.

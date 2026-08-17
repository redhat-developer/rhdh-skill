# Generate Frontend Wiring

Analyze an existing Backstage frontend plugin and generate the RHDH dynamic plugin wiring configuration.

## When to Use

- User has an existing Backstage frontend plugin
- User wants to deploy it to RHDH as a dynamic plugin
- User needs the wiring configuration for `dynamic-plugins.yaml`

## Prerequisites

The plugin directory must contain:

- `package.json` with plugin metadata
- `src/plugin.ts` or `src/plugin.tsx` with plugin definition
- `src/index.ts` exporting plugin components

## Workflow

### Step 1: Locate Plugin Files

Find and read:

1. **`package.json`** — Get package name
2. **`src/plugin.ts`** or **`src/plugin.tsx`** — Find exported extensions
3. **`src/index.ts`** — Find public exports
4. **`dist-dynamic/dist-scalprum/plugin-manifest.json`** — Get scalprum name if built

### Step 2: Determine Scalprum Name

1. **If `plugin-manifest.json` exists**: Use the `name` field
2. **If `scalprum` in `package.json`**: Use `scalprum.name`
3. **Otherwise derive from package name**:
   - `@my-org/backstage-plugin-foo` → `my-org.backstage-plugin-foo`
   - `@internal/backstage-plugin-foo` → `internal.backstage-plugin-foo`
   - Unscoped packages: use as-is (no dot transformation)

### Step 3: Identify Exports

Analyze plugin source for:

**Routable Extensions** (pages):

- Look for `createRoutableExtension` in `plugin.ts`
- These become `dynamicRoutes` entries

**Entity Cards/Content**:

- Look for `createComponentExtension` in `plugin.ts`
- These become `mountPoints` entries
- Check if they use `useEntity` (entity-scoped)

**API Factories**:

- Look for `createApiFactory` and `createApiRef`
- These become `apiFactories` entries

**Icons**:

- Look for icon exports (React components returning SVG/Icon)
- These become `appIcons` entries

### Step 4: Generate Configuration

Output complete wiring configuration in YAML:

```yaml
dynamicPlugins:
  frontend:
    <scalprum-name>:
      dynamicRoutes:
        - path: /<plugin-id>
          importName: <PageComponentName>
          menuItem:
            icon: <icon-name>
            text: <Plugin Display Name>

      mountPoints:
        - mountPoint: entity.page.overview/cards
          importName: <CardComponentName>
          config:
            if:
              allOf:
                - isKind: component

      apiFactories:
        - importName: <apiRefName>

      appIcons:
        - name: <iconName>
          importName: <IconComponentName>
```

### Step 5: Present to User

Show:

1. The YAML configuration block
2. A table explaining each entry and its source
3. Notes about optional configurations
4. Ask if it should be saved to a file

## Example Output

For a plugin with package `@internal/backstage-plugin-demoplugin`, page `DemopluginPage`, and API `todoApiRef`:

```yaml
dynamicPlugins:
  frontend:
    internal.backstage-plugin-demoplugin:
      dynamicRoutes:
        - path: /demoplugin
          importName: DemopluginPage
          menuItem:
            icon: extension
            text: Demo Plugin
      apiFactories:
        - importName: todoApiRef
```

## Common Patterns

### Page Plugin

```yaml
dynamicRoutes:
  - path: /my-plugin
    importName: MyPluginPage
    menuItem:
      icon: extension
      text: My Plugin
```

### Entity Card Plugin

```yaml
mountPoints:
  - mountPoint: entity.page.overview/cards
    importName: MyEntityCard
    config:
      if:
        allOf:
          - isKind: component
```

### Page + Card Plugin

```yaml
dynamicRoutes:
  - path: /my-plugin
    importName: MyPluginPage
    menuItem:
      icon: myIcon
      text: My Plugin

mountPoints:
  - mountPoint: entity.page.overview/cards
    importName: MyEntityCard

appIcons:
  - name: myIcon
    importName: MyIcon
```

## Wiring Options Reference

| Option | Purpose |
|--------|---------|
| `dynamicRoutes` | Full page routes with optional sidebar |
| `mountPoints` | Entity page cards, tabs, integrations |
| `menuItems` | Sidebar ordering and nesting |
| `appIcons` | Custom icons |
| `routeBindings` | External route bindings between plugins |
| `apiFactories` | Utility API registrations |
| `entityTabs` | New tabs on entity pages |
| `scaffolderFieldExtensions` | Custom scaffolder form fields |
| `techdocsAddons` | TechDocs extensions |
| `themes` | Light/dark theme providers |
| `signInPage` | Custom auth sign-in page |
| `providerSettings` | Auth provider settings in preferences |

For complete details on each option, read `frontend-wiring.md` (in this directory).
For entity page customization patterns, read `entity-page.md` (in this directory).

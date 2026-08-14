# Frontend Plugin Wiring Reference

Complete reference for wiring frontend dynamic plugins into RHDH.

## Configuration Structure

All frontend plugin configuration lives under `pluginConfig.dynamicPlugins.frontend`:

```yaml
plugins:
  - package: oci://quay.io/example/my-plugin:v1.0.0!my-plugin
    disabled: false
    pluginConfig:
      dynamicPlugins:
        frontend:
          <scalprum-name>:  # Must match package.json scalprum.name
            dynamicRoutes: []
            mountPoints: []
            menuItems: {}
            appIcons: []
            routeBindings: {}
            apiFactories: []
            entityTabs: []
            scaffolderFieldExtensions: []
            techdocsAddons: []
            themes: []
            signInPage: {}
            providerSettings: []
```

## Dynamic Routes

Add full-page routes to the application.

### Basic Route

```yaml
dynamicRoutes:
  - path: /my-plugin
    importName: MyPage
```

### Route with Sidebar Menu

```yaml
dynamicRoutes:
  - path: /my-plugin
    importName: MyPage
    menuItem:
      icon: dashboard
      text: My Plugin
```

### Route with Custom Sidebar Component

```yaml
dynamicRoutes:
  - path: /my-plugin
    importName: MyPage
    menuItem:
      importName: MySidebarItem
      config:
        props:
          text: My Plugin
```

### Route Options

| Property | Type | Description |
|----------|------|-------------|
| `path` | string | URL path (unique, can override `/` for home) |
| `module` | string | Scalprum module name (default: `PluginRoot`) |
| `importName` | string | Exported component name (default: `default`) |
| `menuItem.icon` | string | System icon name |
| `menuItem.text` | string | Menu label |
| `menuItem.enabled` | boolean | Show/hide menu item |
| `menuItem.importName` | string | Custom SidebarItem component |
| `config.props` | object | Props passed to component |

### Override Home Page

```yaml
dynamicRoutes:
  - path: /
    importName: CustomHomePage
```

## Mount Points

Extend existing pages with additional components.

### Available Mount Points

| Mount Point | Description | Visibility |
|-------------|-------------|------------|
| `entity.page.overview` | Entity overview tab | Always |
| `entity.page.topology` | Topology tab | When plugins enabled |
| `entity.page.issues` | Issues tab | When plugins enabled |
| `entity.page.pull-requests` | PR tab | When plugins enabled |
| `entity.page.ci` | CI tab | When plugins enabled |
| `entity.page.cd` | CD tab | When plugins enabled |
| `entity.page.kubernetes` | K8s tab | When plugins enabled |
| `entity.page.monitoring` | Monitoring tab | When plugins enabled |
| `entity.page.api` | API tab | Service/Component |
| `entity.page.dependencies` | Dependencies tab | Component |
| `entity.page.docs` | Docs tab | TechDocs available |
| `entity.page.definition` | Definition tab | API kind |
| `entity.page.diagram` | Diagram tab | System kind |
| `entity.context.menu` | Context menu | Always |
| `search.page.types` | Search types | Always |
| `search.page.filters` | Search filters | Always |
| `search.page.results` | Search results | Always |
| `admin.page.plugins` | Admin plugins | When enabled |
| `admin.page.rbac` | Admin RBAC | When enabled |

### Mount Point Variants

Each `entity.page.*` has two variants:

- `entity.page.overview/cards` - Regular components
- `entity.page.overview/context` - React context providers

### Basic Mount Point

```yaml
mountPoints:
  - mountPoint: entity.page.overview/cards
    importName: MyCard
```

### With Layout

```yaml
mountPoints:
  - mountPoint: entity.page.overview/cards
    importName: MyCard
    config:
      layout:
        gridColumn: '1 / -1'      # Full width
        gridRowStart: 1           # First row
```

### With Conditions

```yaml
mountPoints:
  - mountPoint: entity.page.overview/cards
    importName: MyCard
    config:
      if:
        allOf:
          - isKind: component
          - isType: service
          - hasAnnotation: my-plugin/enabled
```

### Condition Types

| Condition | Description | Example |
|-----------|-------------|---------|
| `isKind` | Entity kind | `isKind: component` |
| `isType` | Entity spec.type | `isType: service` |
| `hasAnnotation` | Has annotation key | `hasAnnotation: github.com/project` |
| Custom function | Imported from plugin | `isMyPluginAvailable` |

### Condition Operators

```yaml
# All conditions must match
if:
  allOf:
    - isKind: component
    - isType: service

# At least one must match
if:
  anyOf:
    - isKind: component
    - isKind: resource

# Exactly one must match
if:
  oneOf:
    - isType: service
    - isType: website
```

### Context Menu

```yaml
mountPoints:
  - mountPoint: entity.context.menu
    importName: MyContextMenuDialog
    config:
      props:
        title: Open My Dialog
        icon: myIcon
```

Component must accept `open` and `onClose` props:

```typescript
export type MyDialogProps = {
  open: boolean;
  onClose: () => void;
};
```

## Menu Items

Configure sidebar menu ordering and hierarchy.

### Basic Configuration

```yaml
menuItems:
  my-plugin:          # Matches path in dynamicRoutes
    priority: 10      # Higher = appears first
```

### Parent-Child Hierarchy

```yaml
menuItems:
  my-plugin:
    priority: 10
    parent: tools     # Nest under 'tools' parent

  tools:              # Parent menu item
    icon: build
    title: Tools
    priority: 50
```

### Menu Item Options

| Property | Type | Description |
|----------|------|-------------|
| `icon` | string | System icon name |
| `title` | string | Display text |
| `priority` | number | Sort order (higher first, default: 0) |
| `parent` | string | Parent menu item name |
| `enabled` | boolean | Show/hide (default: true) |

### Path to Name Mapping

| Path | Menu Item Name |
|------|----------------|
| `/my-plugin` | `my-plugin` |
| `/metrics/users/info` | `metrics.users.info` |
| `/docs` | `docs` |

## App Icons

Register custom icons for use in menus and routes.

```yaml
appIcons:
  - name: myCustomIcon
    importName: MyCustomIcon
    module: PluginRoot
```

Then reference in routes:

```yaml
dynamicRoutes:
  - path: /my-plugin
    menuItem:
      icon: myCustomIcon
      text: My Plugin
```

### Built-in Icons

RHDH includes Backstage system icons plus additional icons. See [CommonIcons.tsx](https://github.com/redhat-developer/rhdh/blob/main/packages/app/src/components/DynamicRoot/CommonIcons.tsx).

## Route Bindings

Bind external routes between plugins.

### Define Targets

```yaml
routeBindings:
  targets:
    - name: myPlugin
      importName: myPlugin
      module: PluginRoot
```

### Create Bindings

```yaml
routeBindings:
  targets:
    - importName: myPlugin
  bindings:
    - bindTarget: catalogPlugin.externalRoutes
      bindMap:
        viewTechDoc: myPlugin.routes.docs
```

### Available Static Targets

- `catalogPlugin.externalRoutes`
- `catalogImportPlugin.externalRoutes`
- `techdocsPlugin.externalRoutes`
- `scaffolderPlugin.externalRoutes`

## Entity Tabs

Add or customize entity page tabs.

### Add New Tab

```yaml
entityTabs:
  - path: /my-tab
    title: My Tab
    mountPoint: entity.page.my-tab
```

### Customize Existing Tab

```yaml
entityTabs:
  - path: /
    title: General           # Rename Overview
    mountPoint: entity.page.overview
```

### Tab Priority

```yaml
entityTabs:
  - path: /my-tab
    title: My Tab
    mountPoint: entity.page.my-tab
    priority: 100            # Higher = appears first
```

### Hide Default Tab

```yaml
entityTabs:
  - path: /
    title: Overview
    mountPoint: entity.page.overview
    priority: -1             # Negative hides tab
```

## API Factories

Register Utility APIs.

```yaml
apiFactories:
  - importName: myApiFactory
    module: PluginRoot
```

If plugin exports its plugin object with API factories, they're registered automatically - no configuration needed.

## Scaffolder Field Extensions

Custom form fields for software templates.

```yaml
scaffolderFieldExtensions:
  - importName: MyCustomField
    module: PluginRoot
```

## TechDocs Addons

Extend TechDocs functionality.

```yaml
techdocsAddons:
  - importName: MyTechDocsAddon
    config:
      props:
        setting: value
```

## Themes

Provide or override application themes.

```yaml
themes:
  - id: light              # 'light' or 'dark' override defaults
    title: Light Theme
    variant: light
    icon: brightness5
    importName: lightThemeProvider
  - id: dark
    title: Dark Theme
    variant: dark
    icon: brightness2
    importName: darkThemeProvider
```

Theme provider signature:

```typescript
export const myThemeProvider = ({ children }: { children: ReactNode }) => (
  <UnifiedThemeProvider theme={myTheme} children={children} />
);
```

## Sign-In Page

Custom authentication sign-in page.

```yaml
signInPage:
  importName: CustomSignInPage
  module: PluginRoot
```

## Provider Settings

Authentication provider settings in user preferences.

```yaml
providerSettings:
  - title: My Auth Provider
    description: Sign in with My Provider
    provider: core.auth.my-provider
```

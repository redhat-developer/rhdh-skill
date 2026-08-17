# Plugin Type Decision Guide

## Decision Table

| I want to... | Type | Extension / Blueprint |
|--------------|------|----------------------|
| Add a standalone page with sidebar link | Page | `PageBlueprint` |
| Show a summary card on entity overview | Entity card | `EntityCardBlueprint` |
| Add a full tab to entity pages | Entity content | `EntityContentBlueprint` |
| Add sub-tabs within my page | Page (tabbed) | `PageBlueprint` + `SubPageBlueprint` |
| Create a custom template form field | Scaffolder field | `ScaffolderFieldBlueprint` |
| Provide custom branding/colors | Theme | `themes` wiring section |
| Add a REST API backend | Backend plugin | `createBackendPlugin` |
| Add a catalog processor or entity provider | Backend module | `createBackendModule` (pluginId: `catalog`) |
| Add a scaffolder action | Backend module | `createBackendModule` (pluginId: `scaffolder`) |
| Add an auth provider | Backend module | `createBackendModule` (pluginId: `auth`) |
| Add content to the RHDH app drawer | RHDH extension | `AppDrawerContentBlueprint` |
| Add a global header menu item | RHDH extension | `GlobalHeaderMenuItemBlueprint` |

## Page Plugin

Standalone feature with its own URL path. Examples: dashboard, admin panel, cost explorer.

- Mount: `/my-plugin` (top-level route with optional sidebar entry)
- NFS: `PageBlueprint` with `path`, `title`, `routeRef`, `loader`
- Legacy: `createRoutableExtension` bound to `createRouteRef`
- Wiring: `dynamicRoutes` with optional `menuItem`
- Tabbed pages: use `SubPageBlueprint` for tabs within the page

## Entity Card

Summary widget on an entity overview page. Examples: build status, health score, link list.

- Mount: `entity.page.overview/cards` (or other tab's `/cards`)
- NFS: `EntityCardBlueprint` with `filter` and `loader`
- Legacy: `createComponentExtension`
- Wiring: `mountPoints` with `config.if` for entity conditions
- Sizing: `config.layout.gridColumn` controls card width (`span 1`, `1 / -1` for full width)
- Entity conditions: `isKind('component')`, `isType('service')`, `hasAnnotation('key')`

## Entity Tab / Content

Full-page detail view on an entity page. Examples: CI pipeline view, API docs, topology.

- Appears as a tab in the entity page header
- NFS: `EntityContentBlueprint` with `path`, `title`, `filter`, `loader`
- Legacy: `createRoutableExtension` mounted via `EntityLayout.Route`
- Wiring: `mountPoints` for content + `entityTabs` for tab definition
- Uses `useEntity()` for entity context

## Backend Plugin

Standalone backend with HTTP routes. Examples: REST API, proxy, data aggregator.

- `createBackendPlugin` with `coreServices.httpRouter`
- Core services: `httpRouter`, `logger`, `rootConfig`, `httpAuth`, `database`
- Default export required from `src/index.ts`
- Package role: `backend-plugin`

## Backend Module

Extends an existing backend plugin via extension points. Examples: catalog processor, scaffolder action, auth provider.

- `createBackendModule` with `pluginId` of the target plugin
- Package role: `backend-plugin-module`

| Target | Extension point | Package |
|--------|----------------|---------|
| Catalog | `catalogProcessingExtensionPoint` | `@backstage/plugin-catalog-node` |
| Scaffolder | `scaffolderActionsExtensionPoint` | `@backstage/plugin-scaffolder-node` |
| Auth | `authProvidersExtensionPoint` | `@backstage/plugin-auth-node` |
| Permissions | `permissionPolicyExtensionPoint` | `@backstage/plugin-permission-node` |
| Search | `searchIndexRegistryExtensionPoint` | `@backstage/plugin-search-backend-node` |

## Common Combinations

- **Page + Entity card**: Page for detail, card on overview linking to it
- **Entity content + Entity card**: Tab for detail, card on overview
- **Frontend + Backend + Common**: Three-tier with shared types in `-common` package

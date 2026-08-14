# Operator Configuration Reference (New Frontend System)

Operators and platform admins customize NFS apps through `app-config.yaml` keys, not plugin code. This reference covers the configuration surface. For plugin-author migration, see the other reference files.

## `app.extensions`

The primary tool for enabling, disabling, reordering, and configuring extensions.

### Resolution rules

1. All extensions from installed plugins are **auto-discovered** and loaded by default.
2. Entries in `app.extensions` **override** matching extensions by ID.
3. Extensions **listed** in `app.extensions` are **reordered** to appear first, in list order. Unlisted extensions keep their default order afterward.

You typically list only extensions you want to customize — not the full inventory.

### Extension ID format

`[kind:]namespace[/name]` — for example `page:catalog`, `entity-card:catalog/about`, `entity-content:techdocs`.

### Syntax

```yaml
app:
  extensions:
    # Shorthand: enable with defaults
    - entity-card:catalog/about

    # Shorthand: disable
    - page:catalog-unprocessed-entities: false

    # Full form with config
    - entity-card:catalog/links:
        config:
          filter:
            kind: component
          type: info
```

### Config merging caveat

Backstage merges config files by **replacing entire arrays**. If `app.extensions` appears in multiple config files, the higher-priority file's array **replaces** the lower-priority one — entries are not merged entry-by-entry. Individual extension `config` objects are also replaced wholesale when overridden.

Because unlisted extensions are still auto-discovered, a local override file can contain only the extensions you want to change.

## `app.routes.bindings`

Replaces legacy `routeBindings` in `dynamicPlugins.frontend`. Uses `pluginId.routeName` syntax:

```yaml
app:
  routes:
    bindings:
      catalog.viewTechDoc: techdocs.docRoot
      catalog.createComponent: scaffolder.index
      scaffolder.registerComponent: false  # disable a binding
```

See [Frontend Routes](https://backstage.io/docs/frontend-system/architecture/routes/#binding-external-route-references) for details.

## `app.packages`

Controls which frontend plugin packages are auto-discovered:

```yaml
app:
  packages: all
```

Or restrict explicitly:

```yaml
app:
  packages:
    include:
      - '@backstage/plugin-catalog'
      - '@backstage/plugin-techdocs'
    exclude: []
```

Dynamic plugins loaded at runtime through the frontend feature loader are discovered separately from this setting.

## Scaffolder template grouping

Group templates on the scaffolder page using `sub-page:scaffolder/templates`:

```yaml
app:
  extensions:
    - sub-page:scaffolder/templates:
        config:
          groups:
            - title: Recommended Services
              filter:
                spec.type: service
            - title: Internal Tools
              filter:
                spec.type: tool
```

## Operator cheat sheet

| Task | Legacy RHDH | New frontend system |
|------|-------------|---------------------|
| Install a plugin | `dynamic-plugins.yaml` entry | Same — `enabled: true` |
| Disable a plugin page | Remove route or `menuItem.enabled: false` | `page:my-plugin: false` |
| Rename sidebar item | `menuItem.text` | `page:my-plugin` → `config.title` |
| Reorder sidebar | `menuItems.*.priority` | Order in `app.extensions` |
| Hide entity overview card | Remove mount point entry | `entity-card:*: false` |
| Change card visibility filter | `mountPoints[].config.if` | `entity-card:*` → `config.filter` |
| Rename entity tab | `entityTabs[].title` | `entity-content:*` → `config.title` |
| Reorder / group entity tabs | `entityTabs` + `priority` | `page:catalog/entity` → `config.groups` |
| Hide entity tab | Negative `entityTabs` priority | `entity-content:*: false` |
| Bind cross-plugin routes | `routeBindings` | `app.routes.bindings` |
| Disable route binding | Omit binding | `app.routes.bindings.<name>: false` |

## What you cannot do from configuration alone

- **Attach arbitrary exported components** to mount points without a matching NFS extension from the plugin.
- **Replicate `mountPoints[].config.layout`** grid column positioning — use card `type: info`/`type: content` or adjust the component layout.
- **Add a new entity tab** without a plugin that exports `entity-content:*`.
- **Add cards to General settings** until upstream exposes extension inputs on `sub-page:user-settings/general`.
- **Use RHDH-only mount points** (some global header slots) until equivalent NFS extensions exist. Application drawers have `AppDrawerContentBlueprint` — see `migrate-rhdh-extensions.md`.

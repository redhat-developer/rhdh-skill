# Official Backstage skills

Migration and instrumentation workflows maintained by the Backstage team, in a
registry separate from this pack. Several references here name one of these
skills; this file is where their source lives, so a reader who is told to use one
can actually install it.

```bash
npx skills add https://backstage.io
```

| Skill | Use when |
|-------|----------|
| `mui-to-bui-migration` | Migrating a plugin from MUI to BUI, component by component |
| `plugin-new-frontend-system-support` | Adding NFS support while keeping legacy working, from a dual entry point |
| `plugin-full-frontend-system-migration` | Fully migrating a plugin to NFS and dropping legacy |
| `app-frontend-system-migration` | Migrating an entire Backstage app to the new frontend system |
| `plugin-analytics-instrumentation` | Adding analytics events through the Backstage Analytics API |
| `onboard-to-openapi-server` | Moving a backend router onto typed OpenAPI tooling |

For RHDH plugin migration, prefer `/rhdh-plugin-nfs-migration`: it covers the
same ground plus the RHDH mount points, operator config, and dynamic-plugin
packaging that the upstream skills do not.

URLs and registry contents change. Verify before installing.

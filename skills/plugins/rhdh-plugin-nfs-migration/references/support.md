# Getting Help

## Resources

- **[RHDH Plugins GitHub Issues](https://github.com/redhat-developer/rhdh-plugins/issues)** — Plugin-specific questions, bug reports, and feature requests for RHDH plugins
- **[Backstage Discord](https://discord.gg/backstage-687207715902193673)** — Community support, real-time help from maintainers and other developers
- **[Backstage GitHub Discussions](https://github.com/backstage/backstage/discussions)** — Upstream questions about Backstage core, NFS architecture, and API design
- **[RHDH Documentation](https://docs.redhat.com/en/documentation/red_hat_developer_hub/)** — Official Red Hat Developer Hub documentation
- **[Backstage NFS Docs](https://backstage.io/docs/frontend-system/)** — Upstream New Frontend System documentation, API reference, and migration guides

## Upstream Backstage docs

- [Frontend System Introduction](https://backstage.io/docs/frontend-system/)
- [Migrating Plugins](https://backstage.io/docs/frontend-system/building-plugins/migrating/)
- [Migrating Apps](https://backstage.io/docs/frontend-system/building-apps/migrating/)
- [Configuring Extensions](https://backstage.io/docs/frontend-system/building-apps/configuring-extensions/)
- [Common Extension Blueprints](https://backstage.io/docs/frontend-system/building-plugins/common-extension-blueprints/)
- [Example `app-config.yaml`](https://github.com/backstage/backstage/blob/master/app-config.yaml)

## When to escalate

- **Build failures after migration** — Check `references/gotchas.md` first, then file an issue
- **Blueprint not behaving as expected** — Check upstream Backstage docs for the latest API, then ask on Discord
- **RHDH-specific blueprint issues** — File an issue on `rhdh-plugins` repo with the `nfs` label
- **Dynamic plugin loading failures** — Check module federation config, then consult RHDH docs

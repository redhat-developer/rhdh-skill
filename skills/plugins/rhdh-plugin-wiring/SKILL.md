---
name: rhdh-plugin-wiring
description: >-
  Generates the Red Hat Developer Hub dynamic-plugins.yaml configuration that
  makes an exported Backstage frontend plugin appear in RHDH: derive the
  Scalprum name from plugin-manifest.json or the package name, and write the
  pluginConfig.dynamicPlugins.frontend block with dynamicRoutes, menuItems,
  mountPoints, appIcons, apiFactories, routeBindings, entity tabs, cards,
  context menu items, and provider components. Use for "generate the wiring for
  this plugin", "which mount point does this card need", entity page
  customization, importName, or a plugin that installs but never renders. To
  apply the configuration to a running instance instead, use /rhdh-local.
compatibility: "A checkout of the frontend plugin, and its dist-dynamic/dist-scalprum output when already built."
---

# RHDH Plugin Wiring

Own the configuration that connects an exported frontend dynamic plugin to
RHDH's extension points. Read the plugin's real exports, derive the Scalprum
name the same way RHDH does, and emit configuration whose every `importName`
corresponds to something the plugin actually exports.

## Scope against /rhdh-local

This skill **generates** wiring configuration from plugin source. `/rhdh-local`
**applies** configuration to a running local RHDH instance, enables and
disables plugins there, and restarts containers. Producing the YAML is here;
loading it into an instance is there.

## Start here

1. Read `package.json` for the package name and any `scalprum` block.
2. Read `src/plugin.ts` or `src/plugin.tsx` and `src/index.ts` for the
   extensions and public exports.
3. Read `dist-dynamic/dist-scalprum/plugin-manifest.json` when the plugin has
   been exported; its `name` field is authoritative for the Scalprum name.
4. Report the exports you found before generating configuration.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Generate wiring for a frontend plugin | `references/wiring.md` |
| Configure a specific wiring option in depth | `references/frontend-wiring.md` |
| Place content on a catalog entity page | `references/entity-page.md` |

`references/frontend-wiring.md` is the complete option reference: dynamic
routes, mount points and their configs, entity tabs and cards, search result
types, themes, scaffolder field extensions, API factories, and route bindings.
`references/entity-page.md` covers the entity page structure itself — default
tabs, card placement, context menu items, and context providers.

## Boundaries

- This skill emits configuration. It does not modify plugin source, export
  artifacts, or run RHDH.
- `/rhdh-plugin-authoring` owns plugin source. If a needed `importName` does
  not exist, the fix belongs there, not in the configuration.
- `/rhdh-plugin-export` owns producing the artifact and its
  `plugin-manifest.json`.
- `/rhdh-plugin-nfs-migration` owns converting legacy mount points into New
  Frontend System extensions. This skill writes the legacy dynamic-plugin
  configuration that RHDH consumes today.
- `/rhdh-local` owns applying the configuration and restarting an instance.
- `/rhdh-overlay` owns the catalog metadata for a published plugin.

Invoke a named skill and describe the handoff in the conversation. Never open
another skill's files.

## Invariants

- The Scalprum name must match the deployed artifact exactly. Prefer
  `plugin-manifest.json`, then `package.json` `scalprum.name`, and only then
  derive it from the package name.
- Every `importName` must name a real export. Verify against `src/index.ts`
  rather than assuming a naming convention.
- Do not invent a mount point. Use the ones the target RHDH version defines and
  say so when a requested placement has no mount point.
- Emit complete, runnable YAML. A fragment that the user has to reassemble is
  the most common source of a plugin that installs and never renders.
- Configuration alone changes nothing until it is applied and the instance
  restarts. Say which restart the change needs.

## Completion

Report the resolved Scalprum name and where it came from, the exports found and
the configuration entry each produced, the complete YAML block, any requested
placement you could not wire and why, and the named skill to invoke next to
apply or publish it.

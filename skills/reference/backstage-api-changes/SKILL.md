---
name: backstage-api-changes
description: >-
  Names the breaking and notable changes between the early Backstage New
  Frontend System alpha and the current GA surface, for Red Hat Developer Hub
  plugins: NavItemBlueprint removed in favour of nav auto-discovery from
  PageBlueprint, config.schema replaced by top-level configSchema with direct
  zod/v4 imports, AppRootWrapperBlueprint Component renamed to component and
  moved to @backstage/plugin-app-react, defaultPath/defaultTitle/defaultGroup
  renamed, SubPageBlueprint added, useRouteRef returning undefined, and
  AppDrawerContentBlueprint taking element rather than loader. Use when NFS
  code that used to compile now fails, a Blueprint param produces a TypeScript
  error, or a plugin migrated against an older alpha needs bringing forward.
compatibility: "None; this skill is prose that other RHDH skills invoke by name."
---

# RHDH Backstage API Changes

A single home for the NFS API deltas. Two skills need this material and neither
owns it, so it lives here and both invoke it by name.

## Who invokes this

- `/rhdh-backstage-upgrade` owns **version numbers**. It arrives here when a
  bump moves a checkout across one of these deltas and NFS code stops
  compiling.
- `/rhdh-plugin-nfs-migration` owns **extension shape**. It arrives here when a
  plugin was already migrated against an older alpha, or when a Blueprint param
  from an older guide produces a TypeScript error.

That is also the boundary between those two skills. A version number is the
upgrade skill's business; which Blueprint an extension becomes and where it
attaches is the migration skill's. This skill sits under both and belongs to
neither: it says only what changed in the API, not which change you should
make.

## Interface

Read `references/api-changes.md`. It is organized one section per change, each
with the old form, the new form, and the package the symbol now comes from.

Consume it as a checklist against the code in front of you. Two cautions:

- It describes the delta from the early alpha to current GA. It is not a
  release-by-release changelog, and it does not replace reading the changelogs
  for the specific releases an upgrade spans.
- The upstream surface keeps moving. When this prose and the type definitions
  in `node_modules/@backstage/frontend-plugin-api` disagree, the type
  definitions win — report the disagreement rather than following the prose.

## Completion

Report which of these changes apply to the code in hand, the exact symbol and
package each one moves to, any occurrence you could not resolve, and hand the
result back to the skill that invoked this one.

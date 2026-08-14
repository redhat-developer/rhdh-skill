---
name: rhdh-plugin-authoring
description: >-
  Writes Backstage plugin source for Red Hat Developer Hub in rhdh-plugins or
  community-plugins: scaffold a backend dynamic plugin with createBackendPlugin
  or createBackendModule from @backstage/backend-plugin-api, scaffold a
  frontend dynamic plugin, and implement features against Backstage UI
  (@backstage/ui), MUI, Scalprum bundles, fetchApi, i18n, and the Backstage
  test utilities. Use for "scaffold a backend dynamic plugin", "create a
  frontend dynamic plugin", "implement this plugin feature", entity cards,
  scaffolder actions, catalog processors, backend extension points,
  renderInTestApp and TestApiProvider tests, dev app setup, and the local
  build gates yarn tsc:full and yarn build:api-reports:only.
compatibility: "Node.js 22+, Yarn, and Python 3 for the bundled scaffold and context-detection scripts."
---

# RHDH Plugin Authoring

Own plugin source code: creating a new Backstage dynamic plugin for RHDH and
implementing features inside an existing one. Backend and frontend are branches
of the same job — the same conventions, the same build gates, the same repo — so
choose the branch from the request rather than asking for a skill.

## Start here

1. Read the target repository's `AGENTS.md` or `CLAUDE.md` and any linked
   specification or issue. Repository rules beat anything written here.
2. Run `python scripts/detect-rhdh-context.py --path <plugin-or-workspace>` in
   an existing checkout. Record role, frontend system, plugin ID, dynamic
   status, MUI version, and package manager.
3. Establish the target RHDH and Backstage versions. Prefer an explicit user or
   repository value; otherwise invoke `/rhdh-context` for repository, tool, and
   version facts. If it is unavailable, ask the user instead of guessing.
4. Inspect branch and status before modifying files, and protect uncommitted
   work.

For a new plugin or a change to a public API where materially different designs
are valid and the request does not settle the choice, invoke `/grilling` as a
design gate, use the constraints it produces, and show the design before
implementing. If `/grilling` is not installed, say so, name
`/setup-rhdh-skills install` as the human's next step, and pause that branch.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Scaffold a backend dynamic plugin | `references/backend.md`; run `scripts/scaffold.py` |
| Scaffold a frontend dynamic plugin | `references/frontend.md`; run `scripts/scaffold.py` |
| Decide what kind of extension to build | `references/plugin-types.md` |
| Implement or review plugin code | `references/development-patterns.md`, then only the relevant reference below |
| Style with Backstage UI or MUI | `references/bui.md` |
| Write NFS code in a new plugin | `references/nfs.md` |
| Apply RHDH-specific patterns | `references/rhdh.md` |
| Run or extend the plugin dev app | `references/dev-app.md` |
| Write tests for plugin code | `references/testing.md` |
| Write or read a frontend feature spec | `references/frontend-specs.md` |

Infer the branch from the request. Ask only when the missing choice changes the
implementation, such as backend versus frontend.

## Boundaries

- This skill writes plugin source. It does not export artifacts, generate
  deployment configuration, or publish anything.
- `/rhdh-plugin-export` owns exporting and packaging a plugin for RHDH.
- `/rhdh-plugin-wiring` owns generating `dynamic-plugins.yaml` configuration
  and mount points for a finished frontend plugin. Reach for it by name rather
  than writing wiring configuration here.
- `/rhdh-plugin-nfs-migration` owns converting an existing legacy frontend
  plugin to the New Frontend System. This skill writes NFS code in a plugin
  that is already on it.
- `/rhdh-backstage-upgrade` owns moving `@backstage/*` dependency versions.
- `/rhdh-test-placement` advises which repository and layer a permanent test
  belongs in, before you write it here.
- `/rhdh-pr-create` owns changesets, staging, signed-off commits, and pull
  requests. Leave changed files unstaged and list them when you finish.

Invoke a named skill and describe the handoff in the conversation. Never open
another skill's files.

## Invariants

- Backend code uses the new backend system only — `createBackendPlugin` or
  `createBackendModule` from `@backstage/backend-plugin-api`. Never the legacy
  backend system.
- A default export from `src/index.ts` is required. Its absence is the most
  common cause of a dynamic plugin that will not load in RHDH.
- The Scalprum name must match the key used in `dynamic-plugins.yaml` wiring.
- Match the neighbouring implementation: check two or three sibling workspaces
  before inventing a configuration, fixture path, or utility pattern.
- Build incrementally. Write one component or hook, type check, and verify a
  visual change in a running app before writing the next.
- Mirror a current neighbouring test rather than recalling a Backstage test API
  from memory; that surface moves between releases.
- Run the workspace build gates in order and stop at the first failure:
  `yarn prettier:fix`, `yarn tsc:full`, `yarn build:all`,
  `yarn test --watchAll=false`, `yarn build:api-reports:only`.
- Do not stage, commit, push, or open a pull request here.

## Completion

Report the branch taken, the files created or changed and left unstaged, the
build gates run and their results, any public API surface added, the remaining
risks, and the named skill to invoke next for wiring, export, testing, or
publication.

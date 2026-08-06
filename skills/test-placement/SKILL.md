---
name: test-placement
description: >-
  Propose where to test a change in the RHDH dynamic-plugin ecosystem: which
  repo (rhdh-plugins, rhdh-plugin-export-overlays, rhdh), which test layer
  (unit, integration, component, cluster-free E2E, cluster E2E), where the
  test lives, and how to create it — then write it by mirroring an existing
  test in that repo. Use when asked "where should I test this", "does this
  need a cluster", "should this be an e2e test", "which repo does this test
  belong in", "what test layer", "test placement", "how do I write a test
  for this", "write a test for X", "add a unit/integration/component test",
  or when reviewing a test added at the wrong layer.
---

# Test Placement Advisor

Given the context of a change, bug, or new feature in the RHDH dynamic-plugin ecosystem, propose **where** it should be tested: which repository, which test layer, where the test lives, and how to create it. The guiding rule: **pick the cheapest environment that can actually catch the bug — most plugin validation does not need a cluster, and an increasing part doesn't need Docker either.**

Conventions in this skill: paths are prefixed with the repo they live in — `rhdh:`, `overlays:` (= rhdh-plugin-export-overlays), `plugins:` (= rhdh-plugins). For broader repo context, consult `../rhdh/references/rhdh-repos.md` (requires the `rhdh` core skill installed alongside; skip if the file is not found). Some harnesses referenced here are **still in review** (see References for PR status). Before recommending a harness or script, verify its path exists on the target repo's `main`; if it doesn't, tell the developer it is pending in the corresponding PR instead of asserting it exists.

## When to Use

- A new plugin, plugin version bump, or plugin config change needs test coverage.
- A bug escaped to a cluster e2e run and the team wants a cheaper regression test.
- Reviewing a PR that adds a test at the wrong layer (e.g. a cluster e2e for pure UI logic).

## Step 1 — Gather context (ask if missing)

Before recommending, establish:

1. **What is being validated?** Plugin logic/UI component · packaging/published artifact · plugin loading/rendering inside RHDH · platform behavior (Helm/Operator/ingress/auth).
2. **Where did the change happen?** Plugin source (`rhdh-plugins` or another source repo) · packaging metadata (`rhdh-plugin-export-overlays`) · the RHDH app itself (`rhdh`).
3. **Does verifying it require a rendered UI?** (clicks, headings, navigation)
4. **Does it require real external services?** (GitHub, Keycloak, LDAP, managed DBs)
5. **Does it require cluster infrastructure?** (ConfigMap reload, routes, operator, pod logs, port-forward)

## Step 2 — Decision table

| The dev wants to verify… | Repo | Test type / harness | Cluster? | Docker? |
| --- | --- | --- | --- | --- |
| Plugin logic / components / API | `rhdh-plugins` (or the plugin's source repo) | unit + component tests, dev app (`yarn start`) | no | no |
| The plugin still builds as a dynamic plugin | `rhdh-plugins` | `npx @red-hat-developer-hub/cli plugin export` | no | no |
| The **published OCI artifact** installs and the **backend plugin boots** | `rhdh-plugin-export-overlays` | native smoke harness (`overlays: smoke-tests-native/`) | no | **no** |
| All plugins of a **workspace** boot together | `rhdh-plugin-export-overlays` | native smoke with a `dynamic-plugins.yaml` listing the workspace's `oci://` refs | no | **no** |
| A frontend artifact ships its bundle (`dist-scalprum/`, `plugin-manifest.json`) | `rhdh-plugin-export-overlays` | native smoke presence check | no | **no** |
| The plugin **loads inside the real RHDH app** and the **UI renders** | `rhdh` | cluster-free E2E harness (`rhdh: e2e-tests/playwright.legacy-local.config.ts`, script `e2e:legacy-local`) | no | no |
| Every plugin in the **catalog index** is sane | `rhdh` | catalog-index plugin sanity check (nightly) | no | no |
| RHDH **container** behavior (image entrypoint, install script inside the image) | `rhdh-plugin-export-overlays` (artifacts) / any (manual) | Docker smoke (`overlays: smoke-tests/` + workflow `run-workspace-smoke-tests.yaml`) · manual: [rhdh-local](https://github.com/redhat-developer/rhdh-local) | no | yes |
| Helm chart / Operator / ingress / real Keycloak / RBAC on OCP | `rhdh` e2e or `overlays: workspaces/*/e2e-tests` | cluster e2e | **yes** | n/a (cluster) |

Rule of thumb: **source bugs → rhdh-plugins · artifact bugs → overlays · integration/render bugs → rhdh · platform bugs → cluster e2e.** If a bug is catchable in more than one place, test it in the cheapest one and don't duplicate downstream.

## Step 3 — Layer ladder (cheapest that catches the bug wins)

| Layer | Scope | Tooling | Cluster | Typical time |
| --- | --- | --- | --- | --- |
| **L1** Unit | Pure functions / logic | Jest/Vitest | no | ms–s |
| **L2** Integration | Backend module + plugin API, mocked external deps | `startTestBackend` + supertest | no | s |
| **L3** Component | React component/page with a test harness | RTL + dev server | no | s–min |
| **L4a** E2E cluster-free | Full app, no managed infra | Playwright + local harness | no | min |
| **L4b** E2E full | Real OCP/K8s, managed DBs, real IdPs | Playwright + cluster | **yes** | min–h |

The full per-spec classification of the RHDH e2e suite lives in `rhdh: docs/e2e-tests/layer-migration-matrix.md` (see References) — consult it before adding or migrating an e2e spec.

## Step 4 — How to create the test (per placement)

### `rhdh-plugins` (or other source repo) — plugin correctness

- **Where:** `plugins: workspaces/<workspace>/plugins/<plugin>/src/**` next to the code, following that workspace's existing test setup (Jest/RTL; MSW for API mocks).
- **How:** copy the pattern of a neighboring `*.test.ts(x)`; run with the workspace's `yarn test`. Manual verification via the workspace dev app (`yarn start`).
- Also validate packaging when the plugin's build config changed: `npx @red-hat-developer-hub/cli plugin export` must produce `dist-dynamic/` (+ `dist-scalprum/` for frontend).
- **Cannot do here:** validate the *published* OCI artifact, or integration with RHDH's app shell/shared deps.

### `rhdh-plugin-export-overlays` — the published artifact

- **Where:** the native smoke harness, `overlays: smoke-tests-native/`. It installs plugins from OCI with the real `install-dynamic-plugins` CLI and boots backend plugins via `startTestBackend`.
- **How:** write a `dynamic-plugins.yaml` listing the `oci://` artifact refs to validate (a workspace's refs are the `spec.dynamicArtifact` values in `overlays: workspaces/<name>/metadata/*.yaml`), then run `yarn smoke --dynamic-plugins <file> [--out results.json]`. Exit code 0 = pass; non-zero writes `results.json` detailing `fail-load` / `fail-start`. CI: `overlays: .github/workflows/native-smoke.yaml`.
- **Known gaps (don't fight them):** catalog-extending backend modules don't boot in a minimal `startTestBackend` (upstream `catalog-backend` registration issue — stay on the Docker smoke until fixed); plugins whose `dynamicArtifact` is a local `./dynamic-plugins/dist/...` path ship inside the RHDH image and have no OCI artifact to validate here.
- **Never add UI-render tests here** — this repo has no app to render into. Delegate rendering to the `rhdh` cluster-free harness.
- The Docker smoke it replaces (backend scope) lives at `overlays: smoke-tests/` + workflow `run-workspace-smoke-tests.yaml`.
- `overlays: workspaces/*/e2e-tests` (cluster, Playwright + `e2e-test-utils`) exists for plugins whose value *is* cluster integration (topology, tekton, argocd…). Don't add one for UI-only behavior.

### `rhdh` — the real app

Authoring reference for L1–L3: **`rhdh: docs/testing.md`** — which utilities to import per layer, what to assert, and the current worked examples. It lives next to the code, so prefer it over any API name written here.

Listed cheapest-first, matching the ladder in Step 3.

**L1 unit** (`rhdh: plugins/*/src/**`, `rhdh: packages/app/src/**`) — pure logic, or a router you construct by hand and drive with `supertest`; no backend boot. Template to copy: `rhdh: plugins/scalprum-backend/src/service/router.test.ts` (table-driven, mock directory for on-disk plugin content).

**L2 backend integration** (`rhdh: plugins/*/src/**`, named `*.integration.test.ts`) — boots the **real plugin** via `startTestBackend` and asserts over HTTP. This is the layer that proves the plugin's wiring — routes, service dependencies, auth policy — which L1 cannot show. Template to copy: `rhdh: plugins/scalprum-backend/src/service/router.integration.test.ts`. Assert the HTTP contract (status, body shape, what an unauthenticated caller gets), *not* that the plugin booted — a successful request already implies that. Booting is slow; allow a generous per-test timeout.

**L3 component tests** (`rhdh: packages/app/src/**/*.test.tsx`) — page-level RTL compositions, pattern established under RHIDP-13235 in [rhdh#4864](https://github.com/redhat-developer/rhdh/pull/4864). Existing templates to copy: `InfoCard.test.tsx`, `LearningPathsPage.test.tsx`, `CustomSidebarItem.test.tsx` (component compositions) and `getMountPointData.test.ts` (dynamic-UI helper). Prefer L3 over L4a when no dynamic-plugin loading is involved.

**L4a cluster-free harness** (config `rhdh: e2e-tests/playwright.legacy-local.config.ts`, docs `rhdh: docs/e2e-tests/local-e2e-harness.md`) — the only cheap place a frontend dynamic plugin can be *rendered*. To enable a spec/test:

1. Plugin not yet installed by the harness? Add its OCI entry to `rhdh: e2e-tests/local-harness/dynamic-plugins.yaml` (tags on `ghcr.io/redhat-developer/rhdh-plugin-export-overlays/<package>`). If its mount-point config is not in the repo's static `app-config.dynamic-plugins.yaml`, attach the plugin's **canonical `pluginConfig`** (source of truth: `plugins: workspaces/<ws>/plugins/<plugin>/app-config.dynamic.yaml`) — the harness loads the generated `dynamic-plugins-root/app-config.dynamic-plugins.yaml` last, exactly like the production container.
2. Config that only exists in CI config maps (`rhdh: .ci/pipelines/resources/config_map/*`)? Mirror just the needed keys into `rhdh: app-config.local-e2e.yaml` (objects deep-merge; arrays replace).
3. Tag the test `{ tag: "@cluster-free" }` and add its spec file to the config's `testMatch` allowlist.
4. Repopulate + validate: `./e2e-tests/local-harness/populate.sh`, then `yarn --cwd e2e-tests e2e:legacy-local` (CI runs this in ~4 min). Requires skopeo — preinstalled in CI; on macOS `brew install skopeo`.

**L4b cluster e2e** (`rhdh: e2e-tests/playwright/e2e/**`) — only when the subject *is* cluster/platform behavior or a real external service. Requirements: `component` annotation in `beforeAll` (see the repo's `ci-e2e-testing` rule), correct config map choice (RBAC vs non-RBAC), project registration in `e2e-tests/playwright/projects.json` if a new project is needed.

**Catalog-index-wide sanity** (nightly, in review — see References) — nothing to write per plugin; it sweeps the whole index.

## Step 5 — Write the test

Once Steps 2–4 have settled the repo and the layer, write it by **mirroring a real file**, never from memory of an API. The Backstage test surface moves (`@backstage/test-utils` was renamed to `@backstage/frontend-test-utils`), so a package or helper name recalled from training data is likely to be stale — a file on `main` cannot be.

1. **Open the template** named in Step 4 for the chosen layer and read it in full. If the path no longer exists, glob its directory for a sibling `*.test.ts(x)` and use that; if the directory is gone too, say so rather than inventing imports.
2. **Consult the repo's own authoring reference** — for `rhdh` L1–L3 that is `rhdh: docs/testing.md`, which lists the utilities per layer and what to assert. It is maintained next to the code, so it wins over anything written in this skill.
3. **Mirror, then adapt** — copy the template's imports, setup and teardown; replace the subject and the assertions. Keep the file next to the code, matching the neighbours' naming (`*.test.ts` for L1, `*.integration.test.ts` for L2).
4. **Run it** before reporting done:

| Placement | Command |
| --- | --- |
| `rhdh` L1 / L2 / L3 | `yarn test --filter=<package>` |
| `rhdh` L4a | `./e2e-tests/local-harness/populate.sh` then `yarn --cwd e2e-tests e2e:legacy-local` |
| `rhdh` L4b | `yarn --cwd e2e-tests playwright test --project=<project>` |
| `rhdh-plugins` | the workspace's `yarn test` |
| `overlays` native smoke | `yarn smoke --dynamic-plugins <file>` |

5. **Layer checklist** — L2: assert the HTTP contract, not that the plugin booted; allow a generous timeout. L4a: tag `{ tag: "@cluster-free" }` and add the spec to the config's `testMatch` allowlist. L4b: `component` annotation in `beforeAll`, correct RBAC vs non-RBAC config map, and register the project in `projects.json` if new.

**Justify the test by the failure it would catch, not by coverage.** Codecov is `informational: true` on both the project and patch statuses in `rhdh` and `rhdh-plugins`, so no coverage number can block a PR and there is no threshold to reach. A test whose only rationale is a coverage delta will be — and has been — rejected in review.

## Not possible today (researched — don't burn time)

- **Rendering a frontend dynamic plugin without an RHDH app** — the artifact is a legacy-frontend Scalprum bundle; no standalone host exists, and building one means maintaining a version-coupled "mini RHDH".
- **`@backstage/frontend-dynamic-feature-loader` for current plugins** — targets the new frontend system (alpha); our exported plugins are legacy-system bundles. Revisit when app-next matures (RHIDP-15082).
- **Catalog-extending modules in a minimal `startTestBackend`** — upstream `catalog-backend` issue (see overlays harness notes).

## Output format

Answer with a concrete recommendation:

- **Repo:** which of the three (or the plugin's own source repo).
- **Layer / harness:** L1–L4b + the specific harness or suite.
- **Location:** the directory/file where the test goes.
- **Scaffolding:** the minimal steps or files to create, referencing an existing neighbor as template.
- **Why not elsewhere:** one line on the layers you rejected (especially if the dev proposed a more expensive one).
- **Cost:** rough feedback time (seconds / ~4 min cluster-free / cluster job).

## References (PR statuses are as of the last edit — verify before citing as merged)

- Epic **RHIDP-13501** (E2E Test Optimization) — the per-repo responsibility split lives in the epic's comments and its Jira attachment `rhdh-dynamic-plugin-testing-guideline.md` (Jira-only; if unreachable, the decision table above is the summary).
- Layer matrix: [`rhdh: docs/e2e-tests/layer-migration-matrix.md`](https://github.com/redhat-developer/rhdh/blob/main/docs/e2e-tests/layer-migration-matrix.md) — merged in [rhdh#5044](https://github.com/redhat-developer/rhdh/pull/5044) (RHIDP-15076). This is a *migration* analysis of the existing e2e suite; for **how to write** an L1–L3 test see the next entry.
- L1–L3 authoring guide: [`rhdh: docs/testing.md`](https://github.com/redhat-developer/rhdh/blob/main/docs/testing.md) — merged in [rhdh#5140](https://github.com/redhat-developer/rhdh/pull/5140) (RHIDP-13234). Utilities per layer, what to assert, and the worked examples Step 4 points at.
- Cluster-free harness + docs: merged in [rhdh#5005](https://github.com/redhat-developer/rhdh/pull/5005) (RHIDP-15075); expanded to 10 specs / 14 test cases in [rhdh#5057](https://github.com/redhat-developer/rhdh/pull/5057) — the richest set of worked enablement examples (config mirrors, catalog file locations, OCI plugin additions).
- Overlays native smoke: merged in [overlays#2714](https://github.com/redhat-developer/rhdh-plugin-export-overlays/pull/2714); the per-workspace mode used in Step 4 merged in [overlays#2731](https://github.com/redhat-developer/rhdh-plugin-export-overlays/pull/2731).
- Catalog-index sanity check: in review in [rhdh#4967](https://github.com/redhat-developer/rhdh/pull/4967).
- L3 pattern: merged in [rhdh#4864](https://github.com/redhat-developer/rhdh/pull/4864) under RHIDP-13235.

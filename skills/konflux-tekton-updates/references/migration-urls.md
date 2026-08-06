# Konflux task migration URL map

Many tasks left `konflux-ci/build-definitions` ([commit 9f9f0a4](https://github.com/konflux-ci/build-definitions/commit/9f9f0a4c92c15a1c7c85b14b1758cd223056f5ac)).
`external-task/<name>/` stubs point at the upstream repo; **do not** open:

```text
https://github.com/konflux-ci/build-definitions/blob/main/task/<name>/<full-tag>/MIGRATION.md
```

Those paths 404 (e.g. `task/buildah-oci-ta/0.10.7/MIGRATION.md`).

## Resolve a task → migration doc

1. Task name = quay image after `task-` (e.g. `quay.io/konflux-ci/tekton-catalog/task-buildah-oci-ta` → `buildah-oci-ta`).
2. Tag = new image tag (e.g. `0.10.7`). Use **major.minor** (`0.10`) only when the upstream path is versioned.
3. Pick the URL from the table below (or the `migrationDocURL` function).
4. Fetch **raw** content for agents:
   - GitHub blob → `https://raw.githubusercontent.com/<org>/<repo>/main/<path>`
5. If `MIGRATION.md` is missing, read `CHANGELOG.md` in the same task directory and any `migrations/*.sh` scripts.

## Primary homes

| Task name pattern | Migration URL |
|-------------------|---------------|
| `buildah`, `buildah-oci-ta`, `buildah-remote`, `buildah-remote-oci-ta`, `buildah-*-min` | `build-pipeline-tasks` → `/task/<name>/MIGRATION.md` |
| `git-clone`, `git-clone-oci-ta`, `git-clone-oci-ta-min` | `build-pipeline-tasks` → `/task/<name>/MIGRATION.md` |
| `init` | https://github.com/konflux-ci/build-pipeline-tasks/blob/main/task/init/MIGRATION.md |
| `prefetch-dependencies`, `prefetch-dependencies-oci-ta`, `*-min` | `build-pipeline-tasks` → `/task/<name>/MIGRATION.md` |
| `build-image-index`, `build-image-index-min` | `build-pipeline-tasks` → `/task/<name>/MIGRATION.md` |
| `push-dockerfile`, `push-dockerfile-oci-ta` | `build-pipeline-tasks` → `/task/<name>/MIGRATION.md` |
| `source-build`, `source-build-oci-ta` | `build-pipeline-tasks` → `/task/<name>/MIGRATION.md` |
| `apply-tags` | https://github.com/konflux-ci/build-pipeline-tasks/blob/main/task/apply-tags/MIGRATION.md |
| `validate-fbc` | `konflux-operator-tasks` → `/task/validate-fbc/<major.minor>/MIGRATION.md` |
| `rpms-signature-scan` | `tekton-tools` → `/tasks/rpms-signature-scan/<major.minor>/MIGRATION.md` |
| `show-sbom`, `summary` | Still in `build-definitions`: `/task/<name>/<major.minor>/migrations/` (scripts remove the finally task). Also see `CHANGELOG.md`. |
| Other / unknown | Try `build-pipeline-tasks/task/<name>/MIGRATION.md` first; then `build-definitions/task/<name>/<major.minor>/MIGRATION.md` if still hosted there. |

Base URLs:

- https://github.com/konflux-ci/build-pipeline-tasks/blob/main/task/
- https://github.com/konflux-ci/konflux-operator-tasks/blob/main/task/
- https://github.com/konflux-ci/tekton-tools/blob/main/tasks/
- https://github.com/konflux-ci/build-definitions/tree/main/task/

Examples:

| Bump | Open this |
|------|-----------|
| `buildah-oci-ta` 0.10 → 0.10.7 | https://github.com/konflux-ci/build-pipeline-tasks/blob/main/task/buildah-oci-ta/MIGRATION.md |
| `prefetch-dependencies-oci-ta` 0.3.2 → 0.6.0 | https://github.com/konflux-ci/build-pipeline-tasks/blob/main/task/prefetch-dependencies-oci-ta/MIGRATION.md |
| `init` 0.4.2 → 0.4.3 | https://github.com/konflux-ci/build-pipeline-tasks/blob/main/task/init/MIGRATION.md |
| `validate-fbc` 0.1 → 0.3 | https://github.com/konflux-ci/konflux-operator-tasks/blob/main/task/validate-fbc/0.3/MIGRATION.md |
| `rpms-signature-scan` 0.2 → 0.2.1 | https://github.com/konflux-ci/tekton-tools/blob/main/tasks/rpms-signature-scan/0.2/MIGRATION.md |
| `show-sbom` 0.1 → 0.3 | https://github.com/konflux-ci/build-definitions/tree/main/task/show-sbom/0.3/migrations |

`build-pipeline-tasks` keeps a **single** `MIGRATION.md` per task (not per patch tag). Versioned dirs under `build-definitions/external-task/` are thin stubs only.

## `updateDigests.sh`

`.tekton/updateDigests.sh` should call `migrationDocURL` (not hard-code `build-definitions/.../<tag>/MIGRATION.md`). Expected call site on tag bumps:

```bash
task_name="${base#*/task-}"
url_frag="${task_name}/${newTag}"
MIGRATIONS["$url_frag"]="$(migrationDocURL "${task_name}" "${newTag}")"
```

If a branch still has the old hard-coded URL, apply the same `migrationDocURL` + call-site change (see midstream/plugin-catalog), then re-run. Until then, resolve printed 404s via the table above before fetching or opening a browser.

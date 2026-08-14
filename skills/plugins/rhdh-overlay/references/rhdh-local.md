# Reference: Local Verification Inputs

The overlay-side facts to hand `/rhdh-local` when asking it to verify a plugin
built by overlay CI.

> Invoke `/rhdh-local` by name for setup, file layout, operations,
> troubleshooting, and execution; do not load its implementation files. This
> reference deliberately carries no `rhdh-local` configuration templates — only
> what `rhdh-local` cannot know: what the overlay repo published and what the
> plugin needs in order to render.

## Artifact reference

Overlay CI publishes plugins as OCI images under the overlay repo's registry
namespace:

```
oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/<package>:<tag>!<package>
oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/<package>-backend:<tag>!<package>-backend
```

| Tag format | When used | Example |
|--------|-----------|---------|
| `pr_<number>__<version>` | PR artifacts (before merge) | `pr_1873__0.8.0` |
| `bs_<backstage>__<version>` | Released artifacts | `bs_1.45.3__0.8.0` |

Read the exact URLs from the PR's `/publish` comment rather than composing them:

```bash
gh pr view <number> --repo redhat-developer/rhdh-plugin-export-overlays --comments
```

## Plugin config

Frontend plugins need `pluginConfig` for their mount points. Copy it from
`appConfigExamples` in `workspaces/<plugin>/metadata/<package>.yaml` and pass
those values verbatim; do not paraphrase them. Backend plugins usually need no
`pluginConfig`.

## Test entity annotations

A plugin card only renders on a catalog entity that carries the annotation the
plugin looks for. Name the annotation and a test value when invoking
`/rhdh-local` so it can create the entity.

| Plugin family | Annotation key | Example value |
|---------------|----------------|---------------|
| AWS CodePipeline | `aws.amazon.com/aws-codepipeline-arn` | `arn:aws:codepipeline:us-east-1:000000000000:test` |
| AWS CodeBuild | `aws.amazon.com/aws-codebuild-project-arn` | `arn:aws:codebuild:us-east-1:000000000000:project/test` |
| Tekton | `janus-idp.io/tekton` | `<namespace>` |
| ArgoCD | `argocd/app-name` | `<app-name>` |

The table covers the common families, not all of them. Check the plugin's README
or metadata file for the annotations it actually requires.

## Extensions Catalog entities

Seeing the plugin in the Extensions Catalog UI requires the overlay repo's Plugin
entity directory. Its path is `<overlay-repo>/catalog-entities/extensions/plugins/`
— `extensions/plugins/`, not `marketplace/plugins/`. Name that path when
invoking `/rhdh-local`; it owns the mount and the catalog-location wiring.

## Checks to request

- `installation` — plugin loads with no errors in the RHDH logs
- `startup` and `health` — backend health endpoint responds
- `ui` — the test entity resolves in the catalog and the plugin card renders;
  errors about credentials inside the card are acceptable
- Extensions Catalog listing, when the plugin entity path was supplied

Take back one result per check and preserve skipped checks with their reason.

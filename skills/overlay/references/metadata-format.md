# Reference: Plugin Metadata Format

Metadata files register plugins in the RHDH Extensions Catalog.

<overview>
Two entity kinds work together:
- **Package** — represents a single npm package (frontend or backend)
- **Plugin** — user-facing catalog entry that groups packages
</overview>

<package_entity>
**Location:** `workspaces/<name>/metadata/<package>.yaml`

**Purpose:** Defines a single exportable package with its OCI artifact reference and configuration.

**Frontend plugin example:**

```yaml
apiVersion: extensions.backstage.io/v1alpha1
kind: Package
metadata:
  name: backstage-community-plugin-dynatrace
  namespace: rhdh
  title: "Dynatrace"
  links:
    - url: https://red.ht/rhdh
      title: Homepage
    - url: https://github.com/backstage/community-plugins/issues
      title: Bugs
    - title: Source Code
      url: https://github.com/backstage/community-plugins/tree/main/workspaces/dynatrace/plugins/dynatrace
  annotations:
    backstage.io/source-location: url:https://github.com/backstage/community-plugins/tree/main/workspaces/dynatrace/plugins/dynatrace
  tags: []
spec:
  packageName: "@backstage-community/plugin-dynatrace"
  dynamicArtifact: oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/backstage-community-plugin-dynatrace:bs_1.49.4__10.17.0!backstage-community-plugin-dynatrace
  version: 10.17.0
  backstage:
    role: frontend-plugin
    supportedVersions: 1.45.3
  author: Dynatrace
  support: community
  lifecycle: active
  partOf:
    - dynatrace-community
  appConfigExamples:
    - title: Default configuration
      content:
        dynamicPlugins:
          frontend:
            backstage-community.plugin-dynatrace:
              mountPoints:
                - mountPoint: entity.page.monitoring/cards
                  importName: DynatraceTab
                  config:
                    layout:
                      gridColumn: 1 / -1
                    if:
                      allOf:
                        - isDynatraceAvailable
```

**Backend plugin example (with config):**

```yaml
apiVersion: extensions.backstage.io/v1alpha1
kind: Package
metadata:
  name: backstage-community-plugin-redhat-argocd-backend
  namespace: rhdh
  title: "ArgoCD Backend"
  links:
    - url: https://red.ht/rhdh
      title: Homepage
    - url: https://github.com/backstage/community-plugins/issues
      title: Bugs
    - title: Source Code
      url: https://github.com/backstage/community-plugins/tree/main/workspaces/argocd/plugins/argocd-backend
  annotations:
    backstage.io/source-location: url:https://github.com/backstage/community-plugins/tree/main/workspaces/argocd/plugins/argocd-backend
  tags: []
spec:
  packageName: "@backstage-community/plugin-argocd-backend"
  dynamicArtifact: oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/backstage-community-plugin-argocd-backend:bs_1.49.4__1.4.0!backstage-community-plugin-argocd-backend
  version: 1.4.0
  backstage:
    role: backend-plugin
    supportedVersions: 1.48.3
  author: Red Hat
  support: community
  lifecycle: active
  partOf:
    - redhat-argocd
  appConfigExamples:
    - title: Default configuration
      content:
        argocd:
          username: ${ARGOCD_USERNAME}
          password: ${ARGOCD_PASSWORD}
          appLocatorMethods:
            - type: config
              instances:
                - name: argoInstance1
                  url: ${ARGOCD_INSTANCE1_URL}
                  token: ${ARGOCD_AUTH_TOKEN}
```

**Backend plugin example (no config):**

```yaml
spec:
  # ... other fields ...
  backstage:
    role: backend-plugin
    supportedVersions: 1.48.3
  appConfigNotRequired: true
  appConfigExamples: []
```

**Key fields:**

| Field | Source | Required |
|-------|--------|----------|
| `metadata.name` | Derived from `packageName`: strip `@`, replace `/` with `-`. Shorten if >63 chars. | Yes |
| `metadata.namespace` | Always `rhdh` | Yes |
| `spec.packageName` | npm package name from upstream `package.json` | Yes |
| `spec.dynamicArtifact` | OCI URL: `oci://ghcr.io/.../name:bs_<bsVer>__<ver>!name` | Yes |
| `spec.version` | From upstream `package.json` | Yes |
| `spec.backstage.role` | `frontend-plugin` or `backend-plugin` from upstream `package.json` | Yes |
| `spec.backstage.supportedVersions` | From overlay `backstage.json` override, or `source.json` `repo-backstage-version` | Yes |
| `spec.author` | From upstream `package.json` or copy from existing workspace metadata | Yes |
| `spec.support` | Typically `community` for new plugins | Yes |
| `spec.lifecycle` | Typically `active` | Yes |
| `spec.partOf` | References the Plugin entity `metadata.name` | Yes |
| `spec.appConfigNotRequired` | `true` when no config schema exists (backend only) | Conditional |
| `spec.appConfigExamples` | Config examples derived from `config.d.ts` + frontend wiring | Yes |

**Name shortening (when >63 chars):**

Apply rules from [shorten-component-name.sh](https://github.com/redhat-developer/rhdh-plugin-export-utils/blob/main/common/scripts/shorten-component-name.sh):
`backstage-community-plugin` → `bcp`, `backstage-plugin` → `bsp`, `red-hat-developer-hub-` → `rhdh-`, `catalog` → `ctlg`, `module` → `mod`, `kubernetes` → `k8s`, `bitbucket` → `bbckt`
</package_entity>

<plugin_entity>
**Location:** `catalog-entities/extensions/plugins/<name>.yaml`

**Purpose:** User-facing catalog entry that groups related packages.

```yaml
apiVersion: extensions.backstage.io/v1alpha1
kind: Plugin
metadata:
  name: <plugin-name>
  namespace: rhdh
  title: <Display Title>
  description: <Brief description for listing>
  annotations:
    extensions.backstage.io/icon: <icon-url>
spec:
  description: |
    ## Overview
    <What the plugin does>

    ## Features
    - Feature 1
    - Feature 2

    ## Configuration
    <How to configure>
  packages:
    - <package-metadata-name-1>
    - <package-metadata-name-2>
  categories:
    - CI/CD
    - Cloud
  highlights:
    - Build status visibility
    - Project history
  developer: <Author>
  supportLevel: community
```

**Registration:**
Add to `catalog-entities/extensions/plugins/all.yaml` (alphabetical order).
</plugin_entity>

<documentation_link>
Full annotated example: [catalog-entities/extensions/README.md](https://github.com/redhat-developer/rhdh-plugin-export-overlays/blob/main/catalog-entities/extensions/README.md)
</documentation_link>

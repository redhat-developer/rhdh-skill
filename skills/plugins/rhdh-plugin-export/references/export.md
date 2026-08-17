# Export and Package Plugin

Export and package Backstage plugins as RHDH dynamic plugins for deployment. Transforms a developed plugin into a deployable artifact (OCI image, tgz archive, or npm package).

## When to Use

- Export a plugin as a dynamic plugin package
- Package as OCI container image, tgz archive, or npm package
- Publish to a container or npm registry
- Bundle multiple plugins into a single image
- Generate integrity hashes for package verification

## Prerequisites

- Plugin builds without errors (`yarn build`)
- Container runtime (`podman`, `docker`, or `buildah`) for OCI images
- Registry access (e.g., quay.io) for publishing
- Backend plugins: new backend system with default export
- Frontend plugins: valid Scalprum configuration (auto-generated if absent)

## Quick Path

Use the automation script for the common case:

```bash
python scripts/export-plugin.py --plugin-dir plugins/my-plugin \
  --tag quay.io/ns/my-plugin:v0.1.0 --push --clean
```

Run `python scripts/export-plugin.py --help` for all options.

## Step-by-Step Workflow

### Step 1: Build Plugin

```bash
cd plugins/<plugin-id>  # or plugins/<plugin-id>-backend
yarn build
yarn tsc  # Verify no TypeScript errors
```

### Step 2: Export as Dynamic Plugin

```bash
npx @red-hat-developer-hub/cli@latest plugin export
```

Creates `dist-dynamic/` with compiled JavaScript optimized for dynamic loading.

#### Control Shared Dependencies

```bash
# Bundle a @backstage package instead of sharing
npx @red-hat-developer-hub/cli@latest plugin export \
  --shared-package '!/@backstage/plugin-notifications/'

# Mark a non-backstage package as shared
npx @red-hat-developer-hub/cli@latest plugin export \
  --shared-package @my-org/shared-utils
```

#### Embed Packages

```bash
npx @red-hat-developer-hub/cli@latest plugin export \
  --embed-package @my-org/plugin-common \
  --embed-package @my-org/utils
```

Read `export-options.md` (in this directory) for all available options.

### Step 3: Package as Artifact

#### OCI Image (Recommended for Production)

```bash
npx @red-hat-developer-hub/cli@latest plugin package \
  --tag quay.io/<namespace>/<plugin-name>:v0.1.0
```

Specify container tool if needed:

```bash
npx @red-hat-developer-hub/cli@latest plugin package \
  --container-tool docker \
  --tag quay.io/<namespace>/<plugin-name>:v0.1.0
```

#### tgz Archive

```bash
cd dist-dynamic
npm pack
npm pack --json | jq -r '.[0].integrity'  # Get integrity hash
```

#### npm Package

```bash
cd dist-dynamic
npm publish --registry https://your-private-registry.com
```

#### Multi-Plugin Image

```bash
# Export both plugins first
cd plugins/my-plugin && npx @red-hat-developer-hub/cli@latest plugin export
cd ../my-plugin-backend && npx @red-hat-developer-hub/cli@latest plugin export

# Package from monorepo root
cd ../..
npx @red-hat-developer-hub/cli@latest plugin package \
  --tag quay.io/<namespace>/my-plugin-bundle:v0.1.0
```

Read `packaging-formats.md` (in this directory) for detailed format comparison.

### Step 4: Push to Registry

```bash
# Podman
podman push quay.io/<namespace>/<plugin-name>:v0.1.0

# Docker
docker push quay.io/<namespace>/<plugin-name>:v0.1.0
```

Get the digest for reproducible deployments:

```bash
podman inspect --format='{{.Digest}}' quay.io/<namespace>/<plugin-name>:v0.1.0
```

### Step 5: Verify Locally (Optional)

```bash
cp -r dist-dynamic /path/to/rhdh/dynamic-plugins-root/<plugin-id>-dynamic
yarn workspace backend start
```

Check logs for `loaded dynamic backend plugin` (success) or error messages.

## Configuration Examples

### Backend Plugin

```yaml
plugins:
  - package: oci://quay.io/<namespace>/<plugin-name>:v0.1.0!<plugin-id>-backend-dynamic
    disabled: false
    pluginConfig:
      myPlugin:
        apiUrl: https://api.example.com
```

### Frontend Plugin

```yaml
plugins:
  - package: oci://quay.io/<namespace>/<plugin-name>:v0.1.0!<plugin-id>
    disabled: false
    pluginConfig:
      dynamicPlugins:
        frontend:
          my-org.plugin-my-plugin:
            dynamicRoutes:
              - path: /my-plugin
                importName: MyPage
```

### Multi-Plugin Bundle

```yaml
plugins:
  - package: oci://quay.io/<namespace>/my-bundle:v0.1.0!my-plugin
    disabled: false
  - package: oci://quay.io/<namespace>/my-bundle:v0.1.0!my-plugin-backend-dynamic
    disabled: false
```

See `examples/dynamic-plugins.yaml` for complete examples.

## Troubleshooting

### Export Fails

- Missing deps: `yarn add -D <missing-package>`
- TypeScript errors: `yarn tsc` then fix
- Stale artifacts: `rm -rf dist dist-dynamic && yarn build`

### Package Fails

- Container tool not found: use `--container-tool docker`
- Permission denied: `podman login quay.io`

### Plugin Not Loading in RHDH

1. Verify package path matches plugin ID
2. Check version compatibility with target RHDH
3. Ensure default export exists (backend plugins)
4. Verify Scalprum name matches (frontend plugins)

### Integrity Hash Mismatch

Regenerate: `cd dist-dynamic && npm pack --json | jq -r '.[0].integrity'`

Read `integrity-hashes.md` (in this directory) for complete hash reference.

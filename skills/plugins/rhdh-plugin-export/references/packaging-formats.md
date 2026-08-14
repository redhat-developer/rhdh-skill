# Dynamic Plugin Packaging Formats

Complete reference for packaging RHDH dynamic plugins in different formats.

## Format Comparison

| Format | Production Ready | Integrity | Versioning | Use Case |
|--------|-----------------|-----------|------------|----------|
| OCI Image | Yes | Digest | Tags | OpenShift/Kubernetes |
| tgz Archive | Yes | SHA-512 | Filename | HTTP distribution |
| npm Package | Yes | SHA-512 | Semver | Private npm registry |
| Local Directory | No | None | None | Development only |

## OCI Image (Recommended)

### Why OCI?

- Standard container format
- Works with existing container tooling
- Digest-based integrity verification
- Easy version management with tags
- Native to OpenShift/Kubernetes

### Creating the Image

From plugin source directory (not `dist-dynamic/`):

```bash
npx @red-hat-developer-hub/cli@latest plugin package \
  --tag quay.io/<namespace>/<plugin-name>:v0.1.0
```

### Container Tool Selection

```bash
# Use Docker instead of Podman (default)
npx @red-hat-developer-hub/cli@latest plugin package \
  --container-tool docker \
  --tag quay.io/<namespace>/<plugin-name>:v0.1.0

# Use Buildah
npx @red-hat-developer-hub/cli@latest plugin package \
  --container-tool buildah \
  --tag quay.io/<namespace>/<plugin-name>:v0.1.0
```

### Pushing to Registry

```bash
# Podman
podman push quay.io/<namespace>/<plugin-name>:v0.1.0

# Docker
docker push quay.io/<namespace>/<plugin-name>:v0.1.0
```

### Configuration Reference

Using tag:

```yaml
plugins:
  - package: oci://quay.io/<namespace>/<plugin-name>:v0.1.0!<plugin-id>-dynamic
    disabled: false
```

Using digest (recommended for production):

```yaml
plugins:
  - package: oci://quay.io/<namespace>/<plugin-name>@sha256:abc123...!<plugin-id>-dynamic
    disabled: false
```

### Version Inheritance

For configurations that include defaults:

```yaml
includes:
  - dynamic-plugins.default.yaml
plugins:
  - package: oci://quay.io/<namespace>/<plugin-name>:{{inherit}}!<plugin-id>-dynamic
    disabled: false
```

### Multi-Plugin Images

Bundle multiple plugins in one image:

```bash
# Export all plugins first
cd plugins/frontend && npx @red-hat-developer-hub/cli@latest plugin export
cd ../backend && npx @red-hat-developer-hub/cli@latest plugin export

# Package from monorepo root
cd ../..
npx @red-hat-developer-hub/cli@latest plugin package \
  --tag quay.io/<namespace>/plugin-bundle:v0.1.0
```

Reference individual plugins:

```yaml
plugins:
  - package: oci://quay.io/<namespace>/plugin-bundle:v0.1.0!frontend-plugin
    disabled: false
  - package: oci://quay.io/<namespace>/plugin-bundle:v0.1.0!backend-plugin-dynamic
    disabled: false
```

### Private Registries

Set authentication file:

```bash
export REGISTRY_AUTH_FILE=~/.config/containers/auth.json
# or
export REGISTRY_AUTH_FILE=~/.docker/config.json
```

Login before pushing:

```bash
podman login quay.io
# or
docker login quay.io
```

## tgz Archive

### Creating the Archive

```bash
cd dist-dynamic
npm pack
```

Output: `<package-name>-<version>.tgz`

### Integrity Hash

```bash
npm pack --json | jq -r '.[0].integrity'
# Output: sha512-9WlbgEda...
```

### Hosting Options

#### HTTP Server

Any web server accessible by RHDH:

```yaml
plugins:
  - package: https://plugins.example.com/my-plugin-1.0.0.tgz
    integrity: sha512-9WlbgEda...
    disabled: false
```

#### OpenShift httpd

```bash
# Pack plugins
npm pack --pack-destination ~/plugins/

# Create httpd service
oc project rhdh
oc new-build httpd --name=plugin-registry --binary
oc start-build plugin-registry --from-dir=~/plugins/ --wait
oc new-app --image-stream=plugin-registry
```

Configure RHDH:

```yaml
plugins:
  - package: http://plugin-registry:8080/my-plugin-1.0.0.tgz
    integrity: sha512-...
    disabled: false
```

## npm Package

### Publishing

```bash
cd dist-dynamic
npm publish --registry https://your-private-registry.com
```

Or configure in package.json:

```json
{
  "publishConfig": {
    "registry": "https://your-private-registry.com"
  }
}
```

### Configuration

```yaml
plugins:
  - package: '@my-org/my-plugin-dynamic@1.0.0'
    integrity: sha512-...
    disabled: false
```

### Custom Registry in OpenShift

Create `.npmrc` secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: dynamic-plugins-npmrc
type: Opaque
stringData:
  .npmrc: |
    registry=https://your-registry.com
    //your-registry.com:_authToken=<auth-token>
```

For Helm chart, name it `{{ .Release.Name }}-dynamic-plugins-npmrc`.

### Getting Integrity Hash

```bash
npm view --registry https://your-registry.com \
  @my-org/my-plugin-dynamic@1.0.0 dist.integrity
```

## Local Directory (Development)

### Setup

```bash
cp -r dist-dynamic /path/to/rhdh/dynamic-plugins-root/my-plugin-dynamic
```

### Configuration

```yaml
# app-config.yaml
dynamicPlugins:
  rootDirectory: dynamic-plugins-root
```

```yaml
# dynamic-plugins.yaml
plugins:
  - package: ./dynamic-plugins-root/my-plugin-dynamic
    disabled: false
```

### Pre-installed Plugins

RHDH container includes pre-installed plugins:

```yaml
plugins:
  - package: ./dynamic-plugins/dist/backstage-plugin-catalog-backend-module-github-dynamic
    disabled: false
```

## Integrity Hashes

### Purpose

Verify downloaded package hasn't been tampered with.

### Required For

- tgz archives: Always required
- npm packages: Always required
- OCI images: Use digest instead

### Generating Hashes

```bash
# For tgz
npm pack --json | jq -r '.[0].integrity'

# For npm package
npm view @package/name@version dist.integrity
```

### Format

SHA-512 base64 encoded:

```
sha512-9WlbgEdadJNeQxdn1973r5E4kNFvnT9GjLD627GWgrhCaxjCmxqdNW08cj+Bf47mwAtZMt1Ttyo+ZhDRDj9PoA==
```

## Best Practices

### 1. Use OCI for Production

Provides:

- Standard tooling
- Digest-based integrity
- Easy updates
- OpenShift integration

### 2. Semantic Versioning

```
quay.io/namespace/plugin:v1.0.0
quay.io/namespace/plugin:v1.0.1
quay.io/namespace/plugin:v1.1.0
```

### 3. Test Before Publishing

```bash
# Test locally first
cp -r dist-dynamic /path/to/rhdh/dynamic-plugins-root/my-plugin

# Verify it loads
yarn workspace backend start

# Then publish
podman push quay.io/namespace/plugin:v1.0.0
```

### 4. Document Configuration

Include example configuration:

```yaml
# Example dynamic-plugins.yaml entry
plugins:
  - package: oci://quay.io/namespace/my-plugin:v1.0.0!my-plugin-dynamic
    disabled: false
    pluginConfig:
      myPlugin:
        apiUrl: https://api.example.com
```

### 5. Use Digests in Production

Tags can be overwritten; digests are immutable:

```yaml
# Prefer this for production
- package: oci://quay.io/ns/plugin@sha256:abc123...!plugin-dynamic

# Not this
- package: oci://quay.io/ns/plugin:v1.0.0!plugin-dynamic
```

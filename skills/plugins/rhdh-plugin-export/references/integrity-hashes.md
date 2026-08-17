# Integrity Hashes for Dynamic Plugins

Reference for generating and using integrity hashes with RHDH dynamic plugins.

## Overview

Integrity hashes ensure downloaded plugin packages haven't been modified. They're cryptographic checksums that verify package authenticity.

## When Required

| Package Format | Integrity Method |
|---------------|------------------|
| OCI Image | Use digest (`@sha256:...`) instead of tag |
| tgz Archive | SHA-512 hash in config |
| npm Package | SHA-512 hash in config |
| Local Directory | Not applicable |

## Generating Hashes

### tgz Archive

```bash
cd dist-dynamic
npm pack --json | jq -r '.[0].integrity'
```

Example output:

```
sha512-9WlbgEdadJNeQxdn1973r5E4kNFvnT9GjLD627GWgrhCaxjCmxqdNW08cj+Bf47mwAtZMt1Ttyo+ZhDRDj9PoA==
```

### npm Package

After publishing:

```bash
npm view @my-org/my-plugin-dynamic@1.0.0 dist.integrity
```

For private registry:

```bash
npm view --registry https://your-registry.com \
  @my-org/my-plugin-dynamic@1.0.0 dist.integrity
```

### OCI Image Digest

After pushing:

```bash
# Podman
podman inspect --format='{{.Digest}}' quay.io/<namespace>/<plugin>:v1.0.0

# Docker
docker inspect --format='{{index .RepoDigests 0}}' quay.io/<namespace>/<plugin>:v1.0.0

# From registry
skopeo inspect docker://quay.io/<namespace>/<plugin>:v1.0.0 | jq -r '.Digest'
```

Example digest:

```
sha256:28036abec4dffc714394e4ee433f16a59493db8017795049c831be41c02eb5dc
```

## Using Hashes in Configuration

### tgz with Integrity

```yaml
plugins:
  - package: https://plugins.example.com/my-plugin-1.0.0.tgz
    integrity: sha512-9WlbgEdadJNeQxdn1973r5E4kNFvnT9GjLD627GWgrhCaxjCmxqdNW08cj+Bf47mwAtZMt1Ttyo+ZhDRDj9PoA==
    disabled: false
```

### npm with Integrity

```yaml
plugins:
  - package: '@my-org/my-plugin-dynamic@1.0.0'
    integrity: sha512-abc123def456...
    disabled: false
```

### OCI with Digest

```yaml
plugins:
  - package: oci://quay.io/<namespace>/<plugin>@sha256:28036abec4dffc714394e4ee433f16a59493db8017795049c831be41c02eb5dc!<plugin-id>-dynamic
    disabled: false
```

## Hash Format

### SHA-512 (tgz/npm)

Base64-encoded SHA-512 hash:

```
sha512-<base64-encoded-hash>
```

Length: ~88 characters after `sha512-`

### SHA-256 (OCI digest)

Hex-encoded SHA-256 hash:

```
sha256:<hex-encoded-hash>
```

Length: 64 hex characters after `sha256:`

## Verification

### Manual Verification (tgz)

```bash
# Calculate hash of downloaded file
shasum -a 512 my-plugin-1.0.0.tgz | awk '{print $1}' | xxd -r -p | base64

# Compare with expected hash
```

### RHDH Verification

RHDH automatically verifies integrity when:

1. Package is downloaded from URL
2. Integrity hash is provided in configuration
3. Calculated hash must match exactly

Mismatch results in plugin load failure with error in logs.

## Common Issues

### Integrity Mismatch

**Symptom:** Plugin fails to load with integrity error

**Causes:**

1. Package was modified after hash generated
2. Wrong version specified
3. Hash from different build

**Solution:**

```bash
# Regenerate hash
cd dist-dynamic
npm pack --json | jq -r '.[0].integrity'

# Update configuration with new hash
```

### Missing Integrity

**Symptom:** Warning or error about missing integrity

**Solution:** Always include integrity for tgz/npm packages:

```yaml
plugins:
  - package: https://example.com/plugin.tgz
    integrity: sha512-...  # Required!
    disabled: false
```

### Wrong Hash Algorithm

**Symptom:** Hash format not recognized

**Solution:** Use SHA-512 for tgz/npm:

```
sha512-<base64>
```

Not SHA-256 or MD5.

## Best Practices

### 1. Always Use Integrity

For tgz and npm packages, always include integrity hash:

```yaml
plugins:
  - package: https://example.com/plugin.tgz
    integrity: sha512-...
    disabled: false
```

### 2. Use Digests for OCI

Prefer digest over tag for production:

```yaml
# Recommended - immutable
- package: oci://quay.io/ns/plugin@sha256:abc123...!plugin

# Not recommended - mutable
- package: oci://quay.io/ns/plugin:v1.0.0!plugin
```

### 3. Automate Hash Generation

Add to CI/CD pipeline:

```bash
# Generate and store hash
INTEGRITY=$(npm pack --json | jq -r '.[0].integrity')
echo "integrity: $INTEGRITY" >> plugin-metadata.yaml
```

### 4. Version Control Hashes

Track hashes alongside version:

```yaml
# plugin-versions.yaml
my-plugin:
  v1.0.0:
    tgz: https://example.com/my-plugin-1.0.0.tgz
    integrity: sha512-abc123...
  v1.1.0:
    tgz: https://example.com/my-plugin-1.1.0.tgz
    integrity: sha512-def456...
```

### 5. Document Hash Sources

Include in release notes:

```markdown
## v1.0.0

Download: https://example.com/my-plugin-1.0.0.tgz
Integrity: sha512-9WlbgEdadJNeQxdn1973r5E4kNFvnT9GjLD627GWgrhCaxjCmxqdNW08cj+Bf47mwAtZMt1Ttyo+ZhDRDj9PoA==
```

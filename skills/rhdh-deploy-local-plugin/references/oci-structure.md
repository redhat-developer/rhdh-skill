# OCI Image Structure

## Expected Directory Layout

RHDH's dynamic plugin installer expects the OCI image to contain the
**extracted** plugin contents as a named directory — NOT a tarball.

```
/
└── <plugin-short-name>/
    ├── package.json
    ├── dist/
    │   └── *.js, *.js.map
    ├── dist-scalprum/
    │   └── *.js (module federation chunks)
    └── alpha.d.ts (optional)
```

## Common Failures

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| `ENOENT: no such file or directory, open '.../package.json'` | Image contains a `.tgz` archive instead of extracted directory | Use `FROM scratch` + `COPY . /<plugin-short-name>/` in Containerfile |
| `InstallException: No plugins found in OCI image` | Missing `io.backstage.dynamic-packages` annotation | Rebuild with `--annotation "io.backstage.dynamic-packages=<base64>"` and `--no-cache` |
| Plugin loads but features not discovered | Missing `backstage.features` in `dist-dynamic/package.json` | Run `npx @red-hat-developer-hub/cli plugin export` again (it generates the features field) |
| Push fails with `permission_denied` | Token missing `write:packages` scope | `gh auth refresh -h github.com -s write:packages` then re-login to GHCR |
| Image pulled but package not found | Wrong directory name in image | Must match the key in the annotation JSON object |

## Annotation Format

The annotation value is base64-encoded JSON:

```json
[
  {
    "<plugin-short-name>": {
      "name": "@scope/package-name-dynamic",
      "version": "1.2.3",
      "backstage": {
        "supported-versions": "1.52.0",
        "features": {
          "frontend": {
            "default": { "type": "FrontendModule" },
            "./alpha": { "type": "FrontendPlugin" }
          }
        }
      },
      "repository": { ... },
      "license": "Apache-2.0"
    }
  }
]
```

The JSON key (`<plugin-short-name>`) MUST match the directory name inside the image.
The `backstage.features` field is populated by `npx @red-hat-developer-hub/cli plugin export`.

## Containerfile Template

```dockerfile
FROM scratch
COPY --chmod=755 . /<plugin-short-name>/
```

`.dockerignore`:
```
Containerfile
.dockerignore
```

## Verifying a Working Image

```bash
# Check annotation exists
podman inspect <image> | jq '.[0].Annotations["io.backstage.dynamic-packages"]'

# Decode and pretty-print annotation
podman inspect <image> | jq -r '.[0].Annotations["io.backstage.dynamic-packages"]' | base64 -d | jq .

# Mount and check directory structure
ID=$(podman create <image>)
podman cp $ID:/<plugin-short-name>/package.json /dev/stdout | head -5
podman rm $ID
```

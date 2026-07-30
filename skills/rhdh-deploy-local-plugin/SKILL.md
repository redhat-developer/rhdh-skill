---
name: rhdh-deploy-local-plugin
description: >-
  Build, package, and deploy a local RHDH/BCP plugin as an OCI image to an
  OpenShift cluster for testing. Handles GHCR auth, OCI annotation generation,
  image build, push, ConfigMap update, and pod rollout. Use when the user asks
  to "test on cluster", "deploy plugin to cluster", "build OCI image",
  "push plugin to GHCR", "verify dynamic plugin on OpenShift",
  "test my changes on cluster", or "deploy local changes".
---

<essential_principles>

<principle name="skill_entry_banner">
As the very first action when the skill is invoked, echo a skill entry banner to the terminal:
```
echo "================ Using Deploy Local Plugin Skill ==========="
```
This must happen before any other work (reading references, gathering inputs, etc.).
</principle>

<principle name="step_echo_banners">
Before executing each numbered Step, echo a clearly visible banner to the terminal so the user can track progress:
```
echo "================ Step N — <Step title> ==========="
```
This applies to ALL steps including Step 0. Run the echo command in the terminal before doing anything else for that step.
</principle>

<principle name="fail_fast">
If any step fails validation, STOP immediately with a clear error message and documentation link. Do NOT proceed to the next step. The user must fix the issue before continuing.
</principle>

<principle name="directory_layout">
The OCI image must contain an extracted directory — NOT a `.tgz` archive.
Structure: `/<plugin-short-name>/package.json`, `/<plugin-short-name>/dist/`, etc.
Violating this causes: `ENOENT: no such file or directory, open '.../package.json'`
</principle>

<principle name="annotation_mandatory">
Every OCI image must carry the `io.backstage.dynamic-packages` annotation (base64-encoded JSON).
Without it: `InstallException: No plugins found in OCI image`.
Always use `--no-cache` to ensure the annotation is applied (podman caching can silently skip it).
</principle>

</essential_principles>

## Step 0 — Readiness Check

```
echo "================ Step 0 — Readiness Check ==========="
```

Verify all tools are present. Print a status table using `[PASS]` / `[FAIL]` / `[WARN]` indicators. If any must-have check fails, STOP with install instructions.

### Must-have tools

| Tool | Check command | Install link |
|------|--------------|--------------|
| `podman` | `podman --version` | https://podman.io/docs/installation |
| `oc` | `oc version --client` | https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html |
| `gh` | `gh --version` | https://cli.github.com/manual/installation |
| `npx` | `npx --version` | https://nodejs.org/en/download |
| `python3` | `python3 --version` | https://www.python.org/downloads/ |
| `yarn` | `yarn --version` | https://yarnpkg.com/getting-started/install |

### Must-have auth checks

| Check | Command | Fix |
|-------|---------|-----|
| gh authenticated | `gh auth status` | `gh auth login` — https://cli.github.com/manual/gh_auth_login |
| `write:packages` scope | `gh auth status 2>&1 \| grep write:packages` | `gh auth refresh -h github.com -s write:packages` — https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-with-a-personal-access-token-classic |
| GHCR login | `podman login ghcr.io --get-login` | `gh auth token \| podman login ghcr.io -u $(gh api user -q .login) --password-stdin` |

### Good-to-have (warn only)

| Check | Condition | What it enables | Link |
|-------|-----------|----------------|------|
| Cluster login | `oc whoami` | Deploy directly without re-login | `oc login <url> --username <u> --password <p>` |

### Output format

```
 [PASS]  podman — v5.4.0
 [PASS]  oc — v4.17.0
 [PASS]  gh — v2.70.0
 [PASS]  npx — v10.9.4
 [PASS]  python3 — v3.14.3
 [PASS]  yarn — v4.9.1
 [PASS]  gh auth — authenticated as its-mitesh-kumar
 [PASS]  write:packages — scope present
 [PASS]  GHCR login — active
 [WARN]  oc cluster — not logged in (will need login in Step 6)
```

**If ANY must-have check fails:** Print the fix command, documentation link, and STOP.

---

<intake>

## Step 1 — Gather Inputs

```
echo "================ Step 1 — Gather Inputs ==========="
```

Identify what to deploy. Gather from user or infer from current working directory:

| Variable | How to resolve |
|----------|----------------|
| `WORKSPACE` | Directory name under `workspaces/` (infer from cwd or ask) |
| `PLUGIN` | Directory name under `plugins/` (infer from cwd or ask) |
| `NAMESPACE` | Namespace where RHDH runs on the cluster (ask user) |
| `CLUSTER_API` | Cluster API URL (ask if `oc whoami` fails) |

Auto-derived variables (resolved later in Step 3):
- `GHCR_USER` — from `gh api user -q .login`
- `PLUGIN_SHORT` — from `dist-dynamic/package.json` (name without scope and `-dynamic`)
- `VERSION` — from `dist-dynamic/package.json`
- `TAG` — pattern: `bs_<backstage-version>__<plugin-version>-test`

**Wait for user response if workspace/namespace are not clear.**

</intake>

---

## Step 2 — Build & Export

```
echo "================ Step 2 — Build & Export ==========="
```

```bash
cd workspaces/${WORKSPACE}
echo "  Running yarn tsc..."
yarn tsc

cd plugins/${PLUGIN}
echo "  Running yarn build..."
yarn build

echo "  Exporting as dynamic plugin..."
npx @red-hat-developer-hub/cli plugin export
```

**Validation:** Check output for `detected backstage feature:` lines, e.g.:
```
detected backstage feature: ./alpha => @backstage/FrontendPlugin
detected backstage feature: ./<name>-translations-module => @backstage/FrontendModule
```

**If no features detected:** STOP — the plugin's `package.json` is missing `exports` entries or the plugin does not create Backstage features. See `references/oci-structure.md` for the expected package.json structure.

---

## Step 3 — Generate OCI Annotation

```
echo "================ Step 3 — Generate OCI Annotation ==========="
```

```bash
cd dist-dynamic

PLUGIN_SHORT=$(python3 -c "
import json
pkg = json.load(open('package.json'))
print(pkg['name'].replace('@red-hat-developer-hub/', '').replace('@backstage-community/', '').replace('-dynamic', ''))
")
VERSION=$(python3 -c "import json; print(json.load(open('package.json'))['version'])")
BS_VERSION=$(python3 -c "import json; print(json.load(open('package.json')).get('backstage',{}).get('supported-versions','unknown'))")
TAG="bs_${BS_VERSION}__${VERSION}-test"
GHCR_USER=$(gh api user -q .login)

echo "  Plugin short name: ${PLUGIN_SHORT}"
echo "  Version: ${VERSION}"
echo "  Backstage version: ${BS_VERSION}"
echo "  Tag: ${TAG}"
echo "  GHCR user: ${GHCR_USER}"

ANNOTATION=$(python3 -c "
import json, base64
pkg = json.load(open('package.json'))
short_name = pkg['name'].replace('@red-hat-developer-hub/', '').replace('@backstage-community/', '').replace('-dynamic', '')
annotation = [{short_name: {
    'name': pkg['name'],
    'version': pkg['version'],
    'backstage': pkg.get('backstage', {}),
    'repository': pkg.get('repository', {}),
    'license': pkg.get('license', 'Apache-2.0')
}}]
print(base64.b64encode(json.dumps(annotation).encode()).decode())
")

echo "  Annotation generated (${#ANNOTATION} chars)"
```

**Validation:** `ANNOTATION` must be non-empty. If empty, the `package.json` is malformed — check `backstage.features` field exists.

---

## Step 4 — Build OCI Image

```
echo "================ Step 4 — Build OCI Image ==========="
```

```bash
echo -e "Containerfile\n.dockerignore" > .dockerignore

cat <<EOF > Containerfile
FROM scratch
COPY --chmod=755 . /${PLUGIN_SHORT}/
EOF

echo "  Building image: ghcr.io/${GHCR_USER}/rhdh-plugin-export-overlays/${PLUGIN_SHORT}:${TAG}"

podman build --no-cache --platform linux/amd64 \
  --annotation "io.backstage.dynamic-packages=${ANNOTATION}" \
  -t ghcr.io/${GHCR_USER}/rhdh-plugin-export-overlays/${PLUGIN_SHORT}:${TAG} \
  -f Containerfile .
```

**Validation:** Exit code 0 and output contains `Successfully tagged`.

---

## Step 5 — Verify Image

```
echo "================ Step 5 — Verify Image ==========="
```

```bash
podman inspect ghcr.io/${GHCR_USER}/rhdh-plugin-export-overlays/${PLUGIN_SHORT}:${TAG} | \
  python3 -c "
import json, sys, base64
d = json.load(sys.stdin)
ann = d[0].get('Annotations', {}).get('io.backstage.dynamic-packages', '')
if not ann:
    print(' [FAIL]  io.backstage.dynamic-packages annotation MISSING')
    sys.exit(1)
decoded = json.loads(base64.b64decode(ann))
features = list(decoded[0].values())[0].get('backstage', {}).get('features', {})
print(' [PASS]  Annotation present')
print(f' [PASS]  Features: {json.dumps(features)}')
"
```

**Hard gate:** If annotation is missing, STOP. Rebuild with `--no-cache`.

---

## Step 6 — Push to GHCR

```
echo "================ Step 6 — Push to GHCR ==========="
```

```bash
podman push ghcr.io/${GHCR_USER}/rhdh-plugin-export-overlays/${PLUGIN_SHORT}:${TAG}
```

**If push fails with `permission_denied`:**
```
 [FAIL]  Push failed — token lacks required scopes
 Fix:
   1. gh auth refresh -h github.com -s write:packages
   2. gh auth token | podman login ghcr.io -u ${GHCR_USER} --password-stdin
   3. Retry the push
 Docs: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
```

**After successful push:**
```
echo ""
echo " [WARN]  If this is the FIRST push for this package, make it PUBLIC:"
echo "         https://github.com/users/${GHCR_USER}/packages/container/package/rhdh-plugin-export-overlays%2F${PLUGIN_SHORT}"
echo "         → Package settings → Change visibility → Public"
echo ""
```

---

## Step 7 — Deploy to Cluster

```
echo "================ Step 7 — Deploy to Cluster ==========="
```

### 7.1 — Ensure cluster login

```bash
if ! oc whoami &>/dev/null; then
  echo " [FAIL]  Not logged into cluster"
  echo " Fix: oc login ${CLUSTER_API} --username <user> --password <pass> --insecure-skip-tls-verify"
  echo " Docs: https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/getting-started-cli.html#cli-logging-in_cli-developer-commands"
  exit 1
fi
echo " [PASS]  Cluster: $(oc whoami --show-server)"
```

### 7.2 — Update ConfigMap

```bash
oc get configmap dynamic-plugins -n ${NAMESPACE} \
  -o jsonpath='{.data.dynamic-plugins\.yaml}' > /tmp/dynamic-plugins.yaml

# Replace official image with test image
sed -i.bak "s|ghcr.io/redhat-developer/rhdh-plugin-export-overlays/${PLUGIN_SHORT}:[^ '\"]*|ghcr.io/${GHCR_USER}/rhdh-plugin-export-overlays/${PLUGIN_SHORT}:${TAG}|g" /tmp/dynamic-plugins.yaml

oc create configmap dynamic-plugins \
  --from-file=dynamic-plugins.yaml=/tmp/dynamic-plugins.yaml \
  -n ${NAMESPACE} --dry-run=client -o yaml | oc apply -f -

echo "  ConfigMap updated"
```

### 7.3 — Restart pod

```bash
oc delete pod -n ${NAMESPACE} -l app.kubernetes.io/instance=redhat-developer-hub
echo "  Pod deleted, waiting for new pod..."
```

---

## Step 8 — Validate Deployment

```
echo "================ Step 8 — Validate Deployment ==========="
```

```bash
echo "  Waiting for rollout..."
oc rollout status deployment/redhat-developer-hub -n ${NAMESPACE} --timeout=180s

POD=$(oc get pods -n ${NAMESPACE} -l app.kubernetes.io/instance=redhat-developer-hub -o name | head -1)
echo "  Pod: ${POD}"

echo "  Checking init container logs..."
INSTALL_LOG=$(oc logs ${POD} -n ${NAMESPACE} -c install-dynamic-plugins 2>&1 | grep "${PLUGIN_SHORT}")
if echo "$INSTALL_LOG" | grep -q "Installed"; then
  echo " [PASS]  Plugin installed by init container"
else
  echo " [FAIL]  Plugin NOT found in init logs"
  echo "  Detail: ${INSTALL_LOG}"
  echo "  Fix: Check OCI annotation and image structure"
  exit 1
fi

echo "  Checking for runtime errors..."
ERRORS=$(oc logs ${POD} -n ${NAMESPACE} -c backstage-backend 2>&1 | grep -i "error" | grep "${PLUGIN_SHORT}")
if [ -z "$ERRORS" ]; then
  echo " [PASS]  No runtime errors"
else
  echo " [WARN]  Errors found:"
  echo "  ${ERRORS}"
fi

echo "  Verifying plugin directory..."
FILES=$(oc exec ${POD} -n ${NAMESPACE} -c backstage-backend -- ls /opt/app-root/src/dynamic-plugins-root/${PLUGIN_SHORT}/ 2>&1)
if echo "$FILES" | grep -q "package.json"; then
  echo " [PASS]  Plugin files present (package.json, dist/, dist-scalprum/)"
else
  echo " [FAIL]  Plugin directory empty or missing package.json"
  echo "  Got: ${FILES}"
  exit 1
fi

echo ""
echo "================ DONE ==========="
echo "  Image: ghcr.io/${GHCR_USER}/rhdh-plugin-export-overlays/${PLUGIN_SHORT}:${TAG}"
echo "  Cluster: $(oc whoami --show-server)"
echo "  Namespace: ${NAMESPACE}"
echo "  Pod: ${POD}"
echo ""
echo "  Next: Open the RHDH UI and verify your changes are visible."
echo "  App Visualizer: <rhdh-url>/_visualizer/tree"
```

---

## Rollback

```
echo "================ Rollback — Reverting to official image ==========="
```

```bash
cp /tmp/dynamic-plugins.yaml.bak /tmp/dynamic-plugins.yaml
oc create configmap dynamic-plugins \
  --from-file=dynamic-plugins.yaml=/tmp/dynamic-plugins.yaml \
  -n ${NAMESPACE} --dry-run=client -o yaml | oc apply -f -
oc delete pod -n ${NAMESPACE} -l app.kubernetes.io/instance=redhat-developer-hub
oc rollout status deployment/redhat-developer-hub -n ${NAMESPACE} --timeout=180s
echo " [PASS]  Rolled back to official image"
```

---

## When NOT to Use

- **Backend-only plugins** — this skill is for frontend dynamic plugins. Backend plugins follow a different OCI structure.
- **Plugins already in the overlay CI** — if the plugin is already published via `rhdh-plugin-export-overlays` CI and you just need to bump a version, use the `overlay` skill instead.
- **Local dev testing** — if you only need to test locally with `yarn start`, use `rhdh-local` skill or `packages: all` in `app-config.yaml`.
- **Helm chart changes** — this skill deploys plugin OCI images, not Helm value changes.

---

<reference_index>

## Reference Index

| Reference | Load when... |
|-----------|-------------|
| `references/oci-structure.md` | When debugging image build or annotation issues |

</reference_index>

# Test NFS Plugin in RHDH

<prerequisites>
- Migrated plugin with NFS exports (run the migration workflow first)
- Container runtime (podman or docker) for local testing
- Access to an RHDH instance (local or cluster) for end-to-end verification
</prerequisites>

<process>

## Phase 1: Export as Dynamic Plugin

1. Build the plugin: `yarn build`
2. Export for dynamic loading. If using the `create-plugin` skill's export command:
   ```bash
   python scripts/export-plugin.py --plugin-dir plugins/my-plugin --format tgz
   ```
   Otherwise, use `@janus-idp/cli` or `backstage-cli` to export.

## Phase 2: Local Testing

### Option A: NFS is the default app (GA and later)

1. Start local RHDH using the `rhdh-local` skill:
   Read `../rhdh-local/SKILL.md` and follow the "Enable a plugin" workflow.
2. Verify the plugin loads in the UI.

### Option B: NFS not yet default (pre-GA)

1. Set environment variables:
   ```bash
   APP_CONFIG_app_packageName=app-next
   ENABLE_STANDARD_MODULE_FEDERATION=true
   ```
2. Start local RHDH with these vars.
3. Verify the plugin loads in the NFS app shell.

### Verification Steps (Local)

- [ ] Plugin page is accessible at its declared path
- [ ] Nav item appears in the sidebar
- [ ] API calls succeed (check browser network tab)
- [ ] Entity tabs appear on matching entity pages (if applicable)
- [ ] Translations load correctly (if applicable)
- [ ] No console errors related to the plugin

## Phase 3: Cluster Testing (OpenShift / Kubernetes)

1. Package the plugin as OCI image or tgz archive.
2. Push to your container registry (e.g. quay.io).
3. Add to your RHDH deployment's `dynamic-plugins.yaml`:
   ```yaml
   plugins:
     - package: 'oci://quay.io/your-org/your-plugin:latest!your-plugin'
       disabled: false
   ```
4. If NFS is not the default, add to your RHDH Helm values or operator config:
   ```yaml
   extraEnvVars:
     - name: APP_CONFIG_app_packageName
       value: app-next
     - name: ENABLE_STANDARD_MODULE_FEDERATION
       value: "true"
   ```
5. Restart the RHDH pod and verify.

### Verification Steps (Cluster)

- [ ] Pod starts without errors
- [ ] Plugin appears in the RHDH UI
- [ ] All extension types render correctly
- [ ] No errors in pod logs related to the plugin

</process>

<success_criteria>
- Plugin loads successfully in the RHDH NFS app shell
- All extensions (pages, nav items, entity tabs, etc.) render correctly
- No console or pod log errors related to the plugin
- API calls from the plugin succeed
</success_criteria>

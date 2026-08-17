# Test NFS Plugin in RHDH

<prerequisites>
- Migrated plugin with NFS exports (run the migration workflow first)
- `/rhdh-plugin-export` for producing the artifact
- `/rhdh-local` for running a local instance, or access to a cluster RHDH
  instance for end-to-end verification
</prerequisites>

<process>

## Phase 1: Export as Dynamic Plugin

1. Build the plugin: `yarn build`
2. Export it for dynamic loading. Invoke `/rhdh-plugin-export` by name with the
   plugin directory and the format you want (tgz is enough for local testing).
   Record the exact artifact reference it reports back.

## Phase 2: Local Testing

### Option A: NFS is the default app (GA and later)

Invoke `/rhdh-local` by name. Give it the exact exported package reference, the
plugin configuration, the names of any required environment variables, and the
verification checks below. Consume the evidence it reports.

### Option B: NFS not yet default (pre-GA)

1. The instance needs these environment variables:

   ```bash
   APP_CONFIG_app_packageName=app-next
   ENABLE_STANDARD_MODULE_FEDERATION=true
   ```

2. Invoke `/rhdh-local` by name with the artifact reference, the plugin
   configuration, and those variable names and values. Consume the evidence it
   reports.
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

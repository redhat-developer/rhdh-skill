# Testing with RHDH

## Local testing (via rhdh-local skill)

1. **Export as dynamic plugin** — Ensure the plugin is packaged for dynamic loading (check `package.json` for dynamic plugin config)

2. **Enable NFS app** — If NFS is not yet the default, set these environment variables:
   ```
   APP_CONFIG_app_packageName=app-next
   ENABLE_STANDARD_MODULE_FEDERATION=true
   ```

3. **Deploy locally** — Use the `rhdh-local` skill to deploy and test:
   ```
   Read ../rhdh-local/SKILL.md and follow its instructions
   ```

4. **Verify** — Confirm the plugin appears in the NFS app:
   - Page loads at expected route
   - Nav item visible in sidebar
   - API calls succeed
   - Entity tabs appear (if applicable)

## Cluster testing (OpenShift/K8s)

1. **Package the plugin** — Build as OCI image or tgz archive:
   ```bash
   # OCI (preferred for OpenShift)
   yarn export-dynamic --tag my-registry/my-plugin:latest

   # Or tgz
   yarn pack
   ```

2. **Add to dynamic-plugins.yaml** in your RHDH deployment:
   ```yaml
   plugins:
     - package: 'oci://my-registry/my-plugin:latest'
       disabled: false
       pluginConfig: {}
   ```

3. **Set NFS env vars** (if NFS is not default):
   ```yaml
   env:
     - name: APP_CONFIG_app_packageName
       value: app-next
     - name: ENABLE_STANDARD_MODULE_FEDERATION
       value: 'true'
   ```

4. **Verify via RHDH UI** — Access the RHDH instance and confirm:
   - Plugin loads without console errors
   - All extensions render correctly
   - Dynamic plugin config is picked up

## Troubleshooting

- **Plugin not loading**: Check `dynamic-plugins.yaml` syntax and that the package reference is correct
- **Module federation errors**: Ensure `app-react` is shared as singleton in the webpack config
- **Missing context**: Wrap components with `compatWrapper()` if they need legacy providers
- **Blank page**: Check browser console for import errors — likely a missing export or wrong path

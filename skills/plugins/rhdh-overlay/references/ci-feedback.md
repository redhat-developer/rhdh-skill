# Reference: Working with CI Feedback

The publish workflow provides detailed feedback in PR comments. Learn to read it.

<success_comment>
Shows published OCI image URLs — copy these for testing in your RHDH instance.

**Full OCI format:**

```
oci://<registry>/<image>:<tag>!<package-name>
```

| Component | Description | Example |
|-----------|-------------|---------|
| `registry` | Container registry | `quay.io/rhdh-community` |
| `image` | Plugin image name | `backstage-plugin-todo` |
| `tag` | Version identifier | `pr_1738__0.7.1` or `bs_1.45.3__0.7.1` |
| `package-name` | npm package name | `@backstage/plugin-todo` |

**Tag formats:**

| Tag Pattern | Meaning | When Used |
|-------------|---------|-----------|
| `pr_<number>__<version>` | PR artifact | Testing before merge |
| `bs_<backstage-version>__<plugin-version>` | Release artifact | After merge, in RHDH releases |

**Example (testing a PR):**

```yaml
plugins:
  - package: oci://quay.io/rhdh-community/backstage-plugin-todo:pr_1738__0.7.1!@backstage/plugin-todo
    disabled: false
```

</success_comment>

<failure_comment>
Failure comments contain:

1. **Backstage Compatibility Check**
   - Shows version mismatches
   - Links to version history
   - Identifies which workspace is incompatible

2. **"How to fix" section**
   - Specific guidance for the error
   - Version override instructions
   - Alternative commit suggestions

3. **Failed exports**
   - Links to specific plugin that failed
   - Build logs for debugging
</failure_comment>

<common_errors>

<error name="incompatible_workspaces">
**Message:** "The following workspaces are incompatible..."

**Cause:** Upstream Backstage version doesn't match RHDH target.

**Fix:**

1. Add `backstage.json` with RHDH's target version (from PR comment)
2. Keep `source.json`'s `repo-backstage-version` as upstream's actual version

```json
// backstage.json
{
  "version": "1.45.3"
}
```

</error>

<error name="version_mismatch">
**Message:** "repo-backstage-version does not match..."

**Cause:** `source.json`'s `repo-backstage-version` doesn't match upstream's `backstage.json`.

**Fix:**

```bash
# Check upstream's actual version
curl -s https://raw.githubusercontent.com/<owner>/<repo>/<commit>/backstage.json | jq .version
```

Update `source.json` to match.
</error>

<error name="export_failed">
**Message:** "Export failed for..."

**Causes:**

- Missing dependencies
- Build errors in upstream
- Incompatible plugin format

**Debug:**

```bash
gh run view <run-id> --repo redhat-developer/rhdh-plugin-export-overlays --log | grep -i error
```

**Common fixes:**

- Use `--embed-package` for unpublished shared deps
- Add patches for build issues
- Check similar workspace for patterns
</error>

</common_errors>

<debugging_steps>

1. **Read the PR comment carefully** — it usually contains the fix
2. **Check similar workspaces** — see `references/overlay-repo.md`
3. **Read workflow logs:**

   ```bash
   gh run view <run-id> --repo redhat-developer/rhdh-plugin-export-overlays --log | grep -i error
   ```

4. **Copy patterns** — patches, backstage.json overrides, plugins-list.yaml structure from working workspaces
</debugging_steps>

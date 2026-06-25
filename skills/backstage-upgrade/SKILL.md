---
name: backstage-upgrade
description: >
  Upgrade @backstage/* dependencies in a plugin or app to a target version.
  Use when asked to "upgrade backstage", "bump backstage", "update @backstage",
  "align backstage deps", "backstage version bump", "upgrade dependencies",
  "backstage-cli versions:bump", "update to latest backstage", "fix version
  mismatch", "backstage version alignment", "upgrade before migration",
  or any request to update Backstage package versions in a project.
---

<essential_principles>

<principle name="discover_first">
Always read the plugin's `package.json` (and `backstage.json` if present) before changing anything. Understand the current version baseline before upgrading.
</principle>

<principle name="rhdh_alignment">
RHDH pins specific Backstage versions per release. If the plugin targets RHDH, use the version matrix from `../rhdh/references/versions.md` to determine the correct Backstage version. Don't blindly upgrade to the latest Backstage if it's ahead of what RHDH ships. **Note:** This path requires the `rhdh` core skill to be installed alongside. If the file is not found, ask the user for the target RHDH and Backstage versions directly.
</principle>

<principle name="cli_first">
Use `backstage-cli versions:bump` for dependency upgrades instead of manually editing package.json. The CLI resolves the correct version for every `@backstage/*` package from the release manifest.
</principle>

<principle name="composable">
This skill can be called standalone or chained from another skill (e.g., nfs-migration). When chained, the calling skill may pass additional breaking-change checklists. Apply those alongside the standard changelog review.
</principle>

</essential_principles>

<intake>

## What would you like to do?

1. **Upgrade to latest Backstage for my RHDH version** — Align deps to the Backstage version that your target RHDH release uses
2. **Upgrade to a specific Backstage version** — Bump to an exact Backstage release (e.g., 1.45.3)
3. **Check what version I'm on** — Discover current `@backstage/*` versions without making changes
4. **Fix issues after a version bump** — Resolve breaking changes, moved packages, or build failures after upgrading

**Wait for response before proceeding.**

</intake>

<routing>

| Response | Action |
|----------|--------|
| 1, "latest", "RHDH", "align" | Follow `workflows/full-upgrade.md` (RHDH-aligned) |
| 2, "specific", "version", number like "1.45" | Follow `workflows/full-upgrade.md` (user-specified version) |
| 3, "check", "current", "what version" | Read `references/discover-versions.md` and report findings |
| 4, "fix", "breaking", "issues", "errors" | Read `references/fix-breaking-changes.md` and `references/migrate-packages.md` |

</routing>

<reference_index>

| Reference | Load when... |
|-----------|-------------|
| `references/discover-versions.md` | Reading current Backstage versions from a project |
| `references/determine-target.md` | Figuring out what Backstage version to target |
| `references/bump-deps.md` | Running the version bump command |
| `references/migrate-packages.md` | Handling moved/renamed packages |
| `references/fix-breaking-changes.md` | Resolving breaking changes from changelogs |
| `references/verify-upgrade.md` | Verifying the upgrade succeeded |
| `../rhdh/references/versions.md` | Looking up RHDH → Backstage version mapping |

</reference_index>

<success_criteria>

- All `@backstage/*` deps align to the target release version
- No packages still reference old names (moved to `@backstage-community/*`)
- `yarn tsc` passes with no type errors
- `yarn build` succeeds
- `yarn test` passes (if tests exist)

</success_criteria>

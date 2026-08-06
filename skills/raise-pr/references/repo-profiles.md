# Repo Profiles

Auto-detect which repository you are in and load the matching profile. Read this file at the start of every `raise-pr` invocation.

## Detection

Run `git remote -v` and inspect all remote URLs (fetch lines). Match against the patterns below. If multiple remotes exist (e.g. `origin` pointing to a fork and `upstream` pointing to the canonical repo), prefer the canonical match.

| URL pattern | Profile |
|-------------|---------|
| Contains `rhdh-plugins` (but NOT `community-plugins`) | **rhdh-plugins** |
| Contains `community-plugins` | **community-plugins** |
| Neither matches | Ask the user: "Which repo are you targeting? (1) rhdh-plugins (2) community-plugins" |

## Profile: rhdh-plugins

| Field | Value |
|-------|-------|
| Upstream repo | `redhat-developer/rhdh-plugins` |
| npm scope | `@red-hat-developer-hub` |
| Changeset `fixed` group | `["@red-hat-developer-hub/*"]` |
| Changeset docs link | `https://github.com/redhat-developer/rhdh-plugins/blob/main/CONTRIBUTING.md#creating-changesets` |
| PR base branch | `main` |
| Commit signing | `-s` (Signed-off-by) |

### PR body template (rhdh-plugins)

The template has conditional sections. Include or omit them based on the resolved issue context and caller context from Step 1.5.

```
## Description
<generated description — 2-4 sentences explaining what changed and why>

<pr_description_extra — if provided by caller context, insert here (e.g., root cause analysis)>

## Fixed                              ← include only if issue_source is set
- [<JIRA-KEY>](<jira_url>) — <jira_summary>         ← if issue_source = jira
- Fixes <github_issue_url>                           ← if issue_source = github (triggers auto-close)

## UI before changes                  ← include only if recordings provided by caller
![Before fix](<before-gif-url>)       ← raw.githubusercontent.com URL from Step 10.2

## UI after changes                   ← include only if recordings provided by caller
![After fix](<after-gif-url>)         ← raw.githubusercontent.com URL from Step 10.2

## Test Plan                           ← include only if test_plan provided by caller
<test_plan — markdown checklist of verification steps>

## Checklist
- [x] A changeset describing the change and affected packages. ([more info](https://github.com/redhat-developer/rhdh-plugins/blob/main/CONTRIBUTING.md#creating-changesets))
- [ ] Added or Updated documentation
- [ ] Tests for new functionality and regression tests for bug fixes
- [ ] Screenshots attached (for UI changes)

## Note                                ← include whenever issue_source is present (bug-fix invoked raise-pr)
> This bug fix was identified and implemented using the [bug-fix](https://github.com/redhat-developer/rhdh-skill/blob/main/skills/bug-fix/SKILL.md) and [raise-pr](https://github.com/redhat-developer/rhdh-skill/blob/main/skills/raise-pr/SKILL.md) agent skills. Please verify the fix thoroughly before merging.
```

**When `issue_source` is null**: omit `## Fixed` and `## Note` entirely.
**When no recordings provided**: omit both `## UI before changes` and `## UI after changes`.
**When no test_plan provided**: omit `## Test Plan` entirely.
**When `issue_source` is set but `recordings` is null** (no-e2e mode): include `## Fixed` and `## Note`, omit UI before/after.
**When all optional sections are absent**: the template reduces to `## Description` + `## Checklist` (the minimal form).

**Note on image URLs**: The `<before-gif-url>` and `<after-gif-url>` placeholders are replaced with real `raw.githubusercontent.com` URLs after uploading the GIF files to the branch via GitHub Contents API (Step 10.2 in the main skill). These are NOT local file paths.

## Profile: community-plugins

| Field | Value |
|-------|-------|
| Upstream repo | `backstage/community-plugins` |
| npm scope | `@backstage-community` |
| Changeset `fixed` group | `[]` (no fixed versioning) |
| Changeset docs link | `https://github.com/backstage/backstage/blob/master/CONTRIBUTING.md#creating-changesets` |
| PR base branch | `main` |
| Commit signing | `-s` (Signed-off-by — DCO required) |

### PR body template (community-plugins)

```
## Description

<generated description — 2-4 sentences explaining what changed and why>

<pr_description_extra — if provided by caller context, insert here (e.g., root cause analysis)>

## Fixed                              ← include only if issue_source = github (NEVER include Jira info)
- Fixes <github_issue_url>            ← triggers auto-close on merge

## UI before changes                  ← include only if recordings provided by caller
![Before fix](<before-gif-url>)       ← raw.githubusercontent.com URL from Step 10.2

## UI after changes                   ← include only if recordings provided by caller
![After fix](<after-gif-url>)         ← raw.githubusercontent.com URL from Step 10.2

## Test Plan                           ← include only if test_plan provided by caller
<test_plan — markdown checklist of verification steps>

#### Checklist

- [x] A changeset describing the change and affected packages. ([more info](https://github.com/backstage/backstage/blob/master/CONTRIBUTING.md#creating-changesets))
- [ ] Added or updated documentation
- [ ] Tests for new functionality and regression tests for bug fixes
- [ ] Screenshots attached (for UI changes)
- [x] All your commits have a `Signed-off-by` line in the message. ([more info](https://github.com/backstage/backstage/blob/master/CONTRIBUTING.md#developer-certificate-of-origin))

## Note                                ← include whenever issue_source is present (bug-fix invoked raise-pr)
> This bug fix was identified and implemented using the agent skills. Please verify the fix thoroughly before merging.
```

**IMPORTANT: No Jira information in community-plugins PRs.** Jira keys, URLs, and summaries must NEVER appear in the PR body or commit trailers for community-plugins. If the bug was tracked in Jira, the Jira link stays internal only.

**Conditional rules (community-plugins specific):**
**When `issue_source` is `jira` or `null`**: omit `## Fixed` entirely (no Jira info in community-plugins PRs).
**When `issue_source` is `github`**: include `## Fixed` with `Fixes <github_issue_url>`.
**When `issue_source` is null**: omit `## Note` entirely.
**When no recordings provided**: omit both `## UI before changes` and `## UI after changes`.
**When no test_plan provided**: omit `## Test Plan` entirely.
**When all optional sections are absent**: the template reduces to `## Description` + `#### Checklist` (the minimal form).

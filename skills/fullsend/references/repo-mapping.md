# Repo Mapping

Maps Jira components and labels to GitHub repositories for `bridge` repo
detection. Works with existing rhdh-skill references rather than duplicating them.

## Existing References

This skill does NOT maintain its own repo catalog. Use these sibling references:

- **`../rhdh/references/rhdh-repos.md`** — full repo map with descriptions, tech
  stacks, and ecosystem relationships. Covers all `redhat-developer/rhdh-*` repos.
- **`../rhdh-jira/references/fields.md`** — Jira component catalog (RHDH Core,
  Backstage, Extension Plugins, Program) with freeze exclusion flags.
- **`../rhdh-jira/references/jql-patterns.md`** — JQL patterns, boards, sprint
  naming conventions, and team filtering.

## How Detection Works

The bridge tries these sources in order:

1. **`--repo` flag**: Use as-is.
2. **`repo:` label** on the Jira ticket (e.g., `repo:rhdh-plugins`) → resolve
   against the table below.
3. **Jira component** → resolve against the component-to-repo mapping below.
4. **Keywords in description** → fuzzy match against `../rhdh/references/rhdh-repos.md`.
5. **Ask the user** → present known repos from the table below, let them pick.

## Component-to-Repo Mapping

Maps Jira components (from `../rhdh-jira/references/fields.md`) to GitHub repos
where fullsend can create issues. Only repos with fullsend installed are listed.

<!-- Update this table when repos are added to or removed from fullsend -->

| Jira Component(s) | `repo:` label | GitHub Repo | Notes |
|--------------------|---------------|-------------|-------|
| Dynamic Plugins, RHDH CLI, Plugin Development | repo:rhdh-cli | redhat-developer/rhdh-cli | CLI + plugin export |
| UI, Authentication, Dynamic Plugins, Catalog | repo:rhdh | redhat-developer/rhdh | Core RHDH app |
| Operator | repo:rhdh-operator | redhat-developer/rhdh-operator | K8s/OCP operator |
| Helm Chart | repo:rhdh-chart | redhat-developer/rhdh-chart | Helm deployment |
| RHDH Local | repo:rhdh-local | redhat-developer/rhdh-local | Local dev env |
| Overlay, Extensions | repo:rhdh-plugin-export-overlays | redhat-developer/rhdh-plugin-export-overlays | Plugin packaging |
| Lightspeed, Bulk Import, Orchestrator, Homepage, Topology, Scorecard, Adoption Insights | repo:rhdh-plugins | redhat-developer/rhdh-plugins | Plugins monorepo |

**Ambiguous components** (may map to multiple repos): `Authentication`,
`Dynamic Plugins`, `Catalog`. When ambiguous, ask the user.

**Components NOT mappable to a single repo**: `Documentation`, `Quality`,
`Security`, `Support`, `Team Operations`, `UX` — these are program-level
components, not code repos. Flag to the user if a ticket only has these.

## Adding a New Repo

When your team adds a new repo to fullsend:

1. Add a row to the table above
2. Ensure the repo has the `fullsend` label created:
   `gh label create fullsend --repo owner/name`
3. Verify fullsend is installed on the repo (check GitHub App installations)
4. Update `../rhdh/references/rhdh-repos.md` if the repo is new to the ecosystem

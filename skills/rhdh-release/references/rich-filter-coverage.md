# Rich Filter Coverage

The configured export is the source of truth for all query-bearing data it
contains. `rich-filter inventory` exposes every static filter, smart-filter
clause, rich queue, time series, and custom ratio; `rich-filter query` composes
any fragment (including either side of a ratio) with optional release scope.

## First-class release mappings

| Release behavior | Export source |
|---|---|
| Base operational scope | complete `jiraFilter.jql`, excluding `ORDER BY` |
| Feature Freeze | static `Feature Freeze` |
| Code Freeze | static `Code Freeze` |
| Post Code Freeze | static `Post Code Freeze` |
| Feature demos | static `demo` |
| Test Day features | static `Test Day` |
| Team Cloud IDs | smart filter `Scrum Team` |
| Unclassified release notes | queue `RNs Unclassified` |
| Proposed release notes | queue `RNs Proposed` |
| Completed release notes | queue `RNs Done` |
| Release-note text present | queue `Has RN Text` |

The demo and Test Day migrations intentionally adopt the exported operational
scope instead of preserving the narrower legacy `RHDHPlan/RHIDP + Feature +
open` query. In a live comparison for release `2.1.0` on 2026-07-15, this
changed demo results from 31 to 34 and Test Day results from 27 to 52. The Jira
export is authoritative; these differences are expected, not parity defects.

## Intentionally local JQL

The remaining templates stay local because the export has no semantically
equivalent named entry: active release discovery, open issue totals/by type,
blockers, engineering EPICs, CVEs, feature subtasks, recently added features,
and the generic open-issues-by-team constraint. Exported entries with similar
words are not assumed equivalent.

## Non-query export data

Dynamic filter fields and rich views describe dashboard presentation. The
inventory reports field labels/clauses and view columns, but the CLI does not
execute them because they are not JQL. Time series and custom ratios do contain
JQL and are queryable. Administrative metadata, permissions, colors, layout,
and identifiers are not release logic.

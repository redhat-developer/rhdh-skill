# Code Review Perspectives

Examples of review perspectives and the signals that suggest them. These are starting points, not a fixed roster — choose perspectives that fit the PR's actual content. Invent new ones when the PR calls for it (e.g., devil's advocate, agile coach, skill expert, domain specialist).

## Common perspectives

| Perspective | Focus | Prompt guidance |
|-------------|-------|-----------------|
| **Correctness** | Logic bugs, edge cases, error handling, off-by-ones, null/undefined paths | "Find bugs that would reach production. Ignore style." |
| **Security** | Injection vectors, auth/authz gaps, secrets exposure, input validation | "Flag vulnerabilities with severity ratings." |
| **Requirements** | Coverage of linked issues, test adequacy, scope gaps | "Check every linked requirement. Note what's addressed, tested, and missing." |
| **Architecture** | Module boundaries, coupling, abstraction levels, extensibility | "Evaluate structural impact. Is this change in the right place?" |
| **Performance** | Hot paths, query patterns, algorithmic complexity, caching | "Flag measurable performance risks." |
| **Compatibility** | Public API surface, breaking changes, deprecations | "Determine if changed symbols are public-facing before flagging." |

## Signals that suggest a perspective

Use these as hints, not rules. A PR may need perspectives not listed here, or may not need ones that signal-match.

| Signal | Suggests | Example |
|--------|----------|---------|
| Changes span 2+ modules/packages | Architecture | `src/api/` + `src/worker/` |
| New files created | Architecture | New module, new component |
| Changed paths match DB/query patterns | Performance | `**/model*`, `**/migration*`, `**/schema*` |
| Keywords in title/body | Performance | `optimization`, `latency`, `cache`, `slow` |
| Changed paths match API surface | Compatibility | `**/api/**`, `**/proto/**`, `**/openapi*` |
| Package version changes | Compatibility | `package.json`, `pyproject.toml` version bumps |
| Labels | Varies | `refactor` → Architecture, `breaking` → Compatibility |
| Linked issues exist | Requirements | Any `Fixes #N` or Jira key in the body |

## Choosing perspectives

Read the PR's diff, metadata, and linked issues. Create perspectives based on what matters most for this specific change — the examples above are a starting point, not a menu to pick from.

## Reviewer coordination

When using multiple reviewers:

- Each gets the diff, linked requirements, and their focus area
- Instruct them to read source at HEAD, not just the diff
- Encourage cross-checking — reviewers should challenge overlapping or contradictory findings

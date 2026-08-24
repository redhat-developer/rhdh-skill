# Code Review Perspectives

Adversarial is always dispatched from `workflows/review-code.md` on a
`/code-review` run. This file holds that prompt and the optional extra lenses.
Spec coverage lives in `/code-review`; do not run a third Requirements pass.

Specialist domain knowledge lives in whatever skill the user already named. Do
not invent a default specialist list.

## Common perspectives

| Perspective | Focus | Prompt guidance |
|-------------|-------|-----------------|
| **Adversarial** | Abuse of the change: hostile input, confused deputy, path or auth bypass, a new script, hook, or parser | "Break the new surface. Assume hostile input." |
| **Correctness** | Logic bugs, edge cases, error handling, off-by-ones, null/undefined paths | "Find bugs that would reach production. Ignore style." |
| **Security** | Injection vectors, auth/authz gaps, secrets exposure, input validation | "Flag vulnerabilities with severity ratings." |
| **Architecture** | Module boundaries, coupling, abstraction levels, extensibility | "Evaluate structural impact. Is this change in the right place?" |
| **Performance** | Hot paths, query patterns, algorithmic complexity, caching | "Flag measurable performance risks." |
| **Compatibility** | Public API surface, breaking changes, deprecations | "Determine if changed symbols are public-facing before flagging." |

## Signals that suggest an extra perspective

Use these as hints for lenses **other than Adversarial**. A PR may need a
perspective not listed here, or may not need one that signal-matches.

| Signal | Suggests | Example |
|--------|----------|---------|
| Changes span 2+ modules/packages | Architecture | `src/api/` + `src/worker/` |
| New files created | Architecture | New module, new component |
| Changed paths match DB/query patterns | Performance | `**/model*`, `**/migration*`, `**/schema*` |
| Keywords in title/body | Performance | `optimization`, `latency`, `cache`, `slow` |
| Changed paths match API surface | Compatibility | `**/api/**`, `**/proto/**`, `**/openapi*` |
| Package version changes | Compatibility | `package.json`, `pyproject.toml` version bumps |
| Labels | Varies | `refactor` → Architecture, `breaking` → Compatibility |

## Choosing extras

Adversarial is already running; do not add a second Adversarial pass. Add
another row when you recommend it from these signals, or when the user named it.

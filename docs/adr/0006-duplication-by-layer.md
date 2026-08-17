# Duplication is a layer question

**Status:** Accepted.

## Context

Enforcing "skills never read each other's files" without saying what to do instead
produced copies. At the point this was measured, roughly 16% of the Python under
`skills/` was duplicated, four copy pairs had already diverged, and the mutation
protocol existed as eight prose copies in two incompatible serializations — three
of which omitted the rule that a receipt carries one outcome per planned operation.
Nothing detected any of it: no test, lint rule, or CI check compared two copies.

The obvious fix was to extract shared code into a versioned package. That was tried
and it cost more than it saved. A shared package meant a skill could no longer be
installed alone, so selective installation had to be retired to keep the pack
coherent. It also created a pinning hazard documented in `AGENTS.md`: the first
release tag has to land in the same change that pins the package in every PEP-723
block, or a script imports a runtime from a different commit than the skill calling
it. Both costs are paid by every skill to protect a handful of utility functions.

Re-reading the evidence shows the damage was concentrated in one layer. The eight
diverging prose copies were dangerous because three of them were *semantically
wrong* and no reader could tell which was authoritative. The duplicated utility
code was untidy, but no copy was wrong.

## Decision

Duplication is judged by layer, not by volume.

**Prompt duplication is forbidden.** Instructions, protocols, domain rules, and
workflow prose have exactly one home. When the same material would appear in two
skills, choose:

- **Extract** — nothing owns it; it exists only as N copies. Create a reference
  skill and invoke it by name.
- **Enforce** — a module already owns it and a caller copied past its interface.
  Delete the copy and cross the seam.
- **Document** — the material is a rule rather than a capability. State it once
  where it will be read: `AGENTS.md` for rules governing this repository,
  `skill-authoring` for rules governing skill authors. Note the asymmetry —
  `AGENTS.md` does not ship with the pack, so a rule an agent needs *while running
  the pack in someone else's repository* must be a reference skill instead.

**Code duplication is acceptable.** Bundled scripts are self-contained. A skill
carries its own helpers even when a sibling carries something similar, because a
skill is a distribution unit and self-containment is what makes it installable
alone. This restores selective installation and removes the pinning hazard.

There is no shared runtime package. `rhdh_common` is retired.

## Consequences

- A skill can be installed by itself again.
- Utility code appears in more than one place, and that is expected.
- The sharpest cost is data that looks like code: the Jira custom-field IDs now
  live in five scripts. A stale copy fails *silently* — the extractor reads a
  `customfield_*` key that is not there and yields an empty string, so the caller
  reports missing data rather than raising. Accepted deliberately, with a guard:
  `rhdh-jira-api/scripts/validate_field_ids.py` compares every copy against
  `references/fields.md` offline, and `--live` compares that table against Jira
  through `acli`. The offline half catches the real failure and needs no
  credentials, so it is the half worth running in CI. Each copy also names the
  script in a comment, because whoever edits an ID is reading the script rather
  than this decision.
- A reviewer who finds the same text in two skills asks which layer it is before
  asking what to do about it.
- Catalog validation enforces that a declared dependency is named in the owning
  `SKILL.md`, so an extraction nobody invokes fails the build rather than rotting.

# Skill naming

**Status:** Accepted.

## Context

Nearly every skill here carries an `rhdh-` prefix, and during the decomposition it
was proposed that the prefix be dropped as redundant with the folder structure:
`plugins/rhdh-plugin-export` says "plugin" twice and "rhdh" once more than the
path already does.

Two things came out of examining that, and only one of them was right.

**The folder is not a substitute for the name.** `npx skills add … -g` flattens
every skill into `~/.claude/skills/` with no category layer, verified directly
against an existing install. The validator names the host roots explicitly, and no
skill references a category path. So a name cannot lean on its folder for meaning
— by the time a caller sees it, the folder is gone.

**But the prefix is not what isolates a skill either.** The router matches
`description` text; it never sees the name in the first place. The first draft of
this decision claimed the prefix as "the only isolation the pack has", which is
simply wrong — a measured review found the sharpest collisions were between skills
that all had the prefix, and against previously installed copies that had it too.
Isolation is the description's job.

What remains true is narrower: a name is read by *people* — in a flat list, in a
review, in a `/` menu — and it should tell them what the skill is about.

Bare names that misdescribe their subject were also found:

- `plugin-development` — in Claude Code, "plugin" means a *Claude Code plugin*.
  Skills shipped with the host claim "create a plugin, build a plugin, scaffold a
  plugin". The bare name claims a subject this skill does not have.
- `refine`, `assign` — bare verbs naming no subject at all.
- `raise-pr` — sits beside `pr-writer`, `gh-stack`, and `pr-review-github` with
  nothing saying which PRs it means.

## Decision

**A name describes its subject.** `rhdh-` belongs on a skill that is genuinely
about Red Hat Developer Hub — its repositories, its Jira projects, its release
train, its plugins. Almost every skill here qualifies, which is why the prefix is
near-universal; that is a fact about this collection, not a rule about skills.

**A skill that is not about RHDH does not take the prefix.** `skill-authoring`
teaches the Agent Skills standard and is meant to be usable by someone authoring a
skill in an unrelated repository. Prefixing it would advertise a scope it does not
have and imply RHDH knowledge a caller would not get. A generic skill gets a
generic name.

The test is the skill's subject, not its publisher. Ask what the skill is *about*;
if the answer does not contain "RHDH", neither does the name.

Name by **domain then verb**, matching the trigger phrase the skill claims:
`rhdh-jira-create`, `rhdh-jira-refine`, `rhdh-pr-create`, `rhdh-prow-jobs`.
Sibling skills use the same word for the same thing — not `rhdh-pull-request`
beside `rhdh-pr-review`.

Two skills must not share a name prefix unless they share a domain.
`rhdh-test-plan` beside `rhdh-test-placement` reads as one family and is two
unrelated jobs; the first becomes `rhdh-test-plan-review` so the verb separates
them.

A description states the proper nouns it owns — project keys, repository names,
tool names — because a literal token is the strongest anchor available. Dropping
`RHIDP-1234` in favour of the phrase "Jira keys" measurably weakened routing for a
bare issue key, and was restored.

That anchoring cuts both ways, and the first draft of this decision got it wrong.
A literal token fires on **presence**, so putting one in a description to *deny*
it is self-defeating: `rhdh-jira-sprint-plan` saying "a bare key such as
RHIDP-1234 is not a sprint" makes itself a candidate for the very request it is
disclaiming. State the exclusion without the token — "works on a team and a board,
never on a single issue key".

## Consequences

- Names say what the skill is about, so a reader can tell scope from the name
  alone. The cost is that `skill-authoring` sits in an RHDH repository without an
  RHDH name, which looks inconsistent until you ask what it is about.
- The prefix is not a namespace-isolation mechanism, and this decision does not
  claim it as one. The router matches descriptions, so isolation is the
  description's job: distinct trigger phrases, literal proper nouns, and no two
  skills claiming the same utterance.
- A name change breaks installs, so subject drift is expensive. A skill that grows
  out of RHDH-specific scope needs the rename considered, not deferred.
- Nothing here prevents an external skill from colliding. Collisions are
  identified by reading the installed namespace, not prevented by the prefix.

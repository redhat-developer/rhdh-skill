# One prose skill, three registers

**Status:** Accepted.

## Context

Two skills carried `/humanizer` (blader/humanizer, MIT, its catalogue derived
from Wikipedia's CC BY-SA "Signs of AI writing") as a hard prerequisite:
`/rhdh-pr-review` and `/rhdh-release-announce`, both instructing the agent to
never show pre-humanizer prose. A separate proposal added a Simplified Technical
English skill with a bundled linter. The two looked like complements — one
removes the machine register, the other tightens technical writing — and were
scoped to sit beside each other.

Measuring them says otherwise. A sample containing seventeen distinct AI writing
tells scored 5.93 against the linter's 2.5 bar, so it failed. But every flagged
category was incidental — four contractions, passive voice, a nominalization,
one long paragraph — and **not one of the seventeen tells was detected**. An
agent told to repair every reported category fixes the contractions, re-lints
under the bar, and returns prose that is still obviously machine-written with a
passing score attached. That is worse than no score, because it certifies the
failure.

The bar has a second problem: it rejects prose this repository already treats as
good. `README.md` scores 2.68, `skill-authoring/SKILL.md` 3.15, and the proposed
skill's own `SKILL.md` 4.85 against the 2.5 bar it was proposing.

The two skills also claimed overlapping utterances. Both answer "clean up this
PR body" and "tighten this announcement", which
[ADR-0005](0005-one-skill-per-trigger-phrase.md) forbids.

## Decision

Merge them into one model-invoked reference skill, `/prose-editing`, with a
human-invoked wrapper, `/clean-prose`. The external dependency is removed.

**One skill, because the split test is the verb.** "Remove the AI tells" and
"tighten this runbook" are the same verb applied to different document types,
and a document type is a noun. Splitting by noun is what ADR-0005 rejects, and
for its usual reason: the user often does not know which treatment they want, so
choosing it is the skill's job. ADR-0005 also weights the split by the cost of a
misroute, and a misroute here produces a wrong *write* — an announcement
flattened into aircraft-manual English. That is the case that merges.

**The contradiction is about compression, not tells.** STE strips voice on
purpose; humanizer's personality guidance exists to keep it. That reads as
irreconcilable until you separate what the two systems actually score. They do
not disagree about tells; they disagree about compression. Three layers fall
out: mechanical tells, scored in every register; compression, scored only
where prose should be flat; voice, scored only where prose is allowed one. Those
give three registers — `strict`, `flavored`, `voiced` — inferred from document
purpose, plus a read-only `audit` route. A caller that knows names the register:
`/rhdh-pr-review` uses flavored, `/rhdh-release-announce` uses voiced.

**Intent chooses editing versus audit.** An explicit rewrite wins even when the
caller also asks for a score. Only an explicit no-change request selects
`audit`. Document ownership does not silently cancel a requested edit, though
quoted third-party spans stay protected.

**Mixed documents keep one primary score.** Document purpose outranks a byline.
A mixed document keeps one primary register and applies strict rules manually
to procedural or safety sections. It does not expose a numeric register map.

**The score is a delta, not a gate.** Violation density is a function of
document type, so an absolute bar across arbitrary prose is a promise the metric
cannot keep — the README and `skill-authoring` numbers are that promise breaking
on curated text. The skill reports before and after and leaves the judgement
with the reader. The fixed bar survives only as a `--fail-over N` knob a human
points at their own corpus in CI, where the text is uniform enough for one
number to mean something.

**A regex does not certify judgment.** High-confidence deterministic patterns
contribute to the density score. Context-sensitive patterns appear as markers
or manual checks and still block completion until the editor accounts for them.
Singleton transitions, curly quotes, em dashes, and short emphatic sentences
are weak evidence; repetition or a cluster can be scored. A supplied writing
sample governs the voiced register.

**Meaning preservation is bidirectional.** The editor inventories claims,
conditions, scope qualifiers, and modal force before rewriting. Completion
requires both that every source proposition survives and that every output
proposition came from the source or the user. A lower score cannot excuse a
lost limit or an invented detail.

**The capability comes in-pack.** Two skills hard-failing on a third-party
repository is a live failure mode on the path of every PR review, and owning the
capability removes it. It is also the extraction
[ADR-0006](0006-duplication-by-layer.md) asks for — a pattern catalogue is
prompt material, so it gets one home behind a named interface rather than a copy
in each caller, while the bundled linter is code and stays self-contained.
Owning it removes a licensing hazard too: reproducing humanizer's prose would
pull CC BY-SA text into an Apache-2.0 repository. The taxonomy is taken and
every rule restated independently, with a NOTICE at
`skills/reference/prose-editing/scripts/NOTICE` carrying the MIT terms of both
upstream projects.

**The wrapper is safe because the router cannot see it.**
[ADR-0008](0008-skill-naming-and-namespace-isolation.md) establishes that
isolation is the description's job, and two skills about editing prose would
collide by description whatever they were named.
`disable-model-invocation: true` takes `/clean-prose` out of the routing set
entirely, so it cannot compete with the reference skill it delegates to. That is
a structural guarantee rather than a convention, which is why the human-invoked
rule is stated as a class of skill rather than a roster of names. Neither skill
takes the `rhdh-` prefix: editing prose is not about Red Hat Developer Hub.

**Outbound prose is edited at the final composition seam.** A skill invokes
`/prose-editing` exactly once after it has assembled free-form GitHub, GitLab,
Jira, or Slack prose and before it shows, gates, or posts it. A helper does so
only when it directly returns the final prose; a transport layer never does.
Structured payloads, commands, checksums, generated reports, and local documents
with their own authoring skill are excluded from the automatic pass.

## Consequences

- One skill answers both utterances. `/rhdh-pr-review` and
  `/rhdh-release-announce` name a register instead of declaring a prerequisite,
  and no third-party repository sits on the path of a review.
- The pack maintains a pattern catalogue it previously rented, on a
  taxonomy-only footing: whoever adds a pattern restates it rather than quoting
  a source. The implementation does not promise compatibility with a pinned
  upstream version; a later source audit can adopt new behavior, including a
  breaking change, as one reviewed release.
- Three registers are more surface than two modes, and register inference is a
  new failure mode: a caller that names none gets the register the skill guesses.
  A wrong guess is a wrong write — the same cost that argued for merging.
- The reported score no longer answers "is this good enough" by itself. That
  question moves to a human, reading the delta or setting `--fail-over N`
  against a corpus they own.
- The human-invoked rule in `AGENTS.md` becomes a property of a class of skill
  rather than a list of two names, so a future wrapper needs no amendment.
- Every external prose producer records `/prose-editing` as a named dependency,
  while automation templates that cannot invoke a skill receive static lint
  coverage instead.

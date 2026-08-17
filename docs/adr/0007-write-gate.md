# A write gate, not an artifact protocol

**Status:** Accepted.

## Context

Cross-skill communication was designed as typed, versioned artifacts: an envelope
of `contract`, `id`, `createdAt`, and `data`, persisted under the operating system
temporary directory, validated by the consumer before use. The same machinery
carried two unrelated jobs.

The first was **data handoff** — `IssueContext/v1`, `ChangeHandoff/v1`, and the
rest. Inside a single session the agent already holds that context, so serializing
it to a temp file and reading it back is ceremony. Across sessions the store could
expire, which the design conceded and handled by naming the skill to re-run. The
`/handoff` skill already does this job better and is not ours to maintain.

The second was **write approval** — `MutationPlan/v1`, a SHA-256 material hash
binding the plan, and `MutationReceipt/v1` recording one outcome per operation.
That is not a handoff. It is the only thing standing between an agent and an
unreviewed write to Jira, GitHub, or GitLab.

Bundling them meant the safety mechanism inherited the ceremony: a JSON envelope
and a digest that no human reads, for a decision a human has to make in the
conversation.

## Decision

Handoff artifacts are removed. Skills that need to pass context to a later session
tell the user to run `/handoff`.

The write gate stays, as prose:

1. Before any external write, state every operation: target, exact command,
   preview of the change, the precondition it depends on, what happens to the
   remaining operations if it fails, and how to recover from it once it has
   happened.
2. Get approval for that stated set.
3. Execute, then report the outcome of every operation, including the ones that
   were skipped.

The plan renders as a compact table in the conversation, one row per operation,
because approval has to happen where the user already is. A plan large enough to
flood the transcript — a multi-repo bump, a forty-file catalog change — is written
to a file in the temporary directory instead, following `/handoff`'s convention,
and the path is printed.

There is no envelope, no version string, and no material hash. The hash guarded
against an agent altering the plan between approval and execution: a real threat,
but narrow, and not worth a digest implementation plus the shared package needed
to keep two skills computing it identically.

What goes is the machinery, not the content. The retired protocol required nine
fields per operation; the first draft of this decision kept four and dropped
`preconditions`, `checks`, and `recovery` without arguing for it. That was an
error, and `recovery` was the costly one: nothing else in the gate says how to
undo an operation that already happened, so a decommission or a bulk transition
could be approved with no stated way back. Preconditions and recovery are
restored. `checks` is genuinely absorbed: verifying an operation landed is part of
reporting its outcome, which step 3 already requires.

The gate ships as the `mutation-gate` reference skill, cited by every skill
that writes. It cannot live in `AGENTS.md`, which does not travel with the pack,
and it cannot be copied into each writing skill, which is the prompt duplication
[ADR-0006](0006-duplication-by-layer.md) forbids.

Read-only inspection needs no gate. A request to fetch, triage, or analyse is
intent to read, and approves no write.

The read/write seam stays where it is. `rhdh-forge` constructs payloads and never
executes them; a caller that needs a write receives a command, not an effect. That
separation is what makes the gate enforceable — the module that knows how to build
the command is structurally unable to run it.

## Consequences

- Roughly two thirds of the artifact material is deleted, along with the store,
  its contract registry, and two test modules.
- Cross-session handoff becomes a user action rather than a pack feature.
- Consumers no longer validate contract versions, because there are none.
- The gate is enforced by review and by the reference skill's prose rather than by
  a schema. Accepted: the previous schema did not prevent three of eight copies
  from being wrong.

---
name: mutation-gate
description: >-
  Supplies the approval rule another RHDH skill applies when it is already about
  to change something outside the session: how to state each operation, what
  approval binds to, what to report afterwards, and how to keep credentials out
  of a plan preview. Cited by name from the skill doing the work. Not an entry
  point — it performs no forge, Jira, or repository action itself, and a request
  to open, comment, transition, push, or post belongs to the skill that owns
  that target.
compatibility: "Python 3.9+ for the credential scanner. No other tools required."
---

# RHDH write gate

An external write is anything the user cannot undo by closing the session: a
pushed commit, an opened pull request, a Jira transition, a posted message, a
file changed in someone else's repository.

Reading is not a write. A request to fetch, triage, analyse, or report is intent
to read, and it approves nothing.

## The gate

**1. State the operations.** List every operation you are about to perform, in
the order you will perform them. For each one give:

| Field | What it carries |
|---|---|
| Target | The exact thing being changed: `owner/repo#412`, `RHIDP-1234`, a branch name, a channel |
| Command | The exact command or request, as it will run. Not a paraphrase |
| Preview | The body, label, field value, or diff that will land |
| Precondition | What must already be true. Check it immediately before executing, and stop the batch if it is not |
| On failure | What happens to the operations after this one if it fails |
| Recovery | How to undo or contain this operation once it has happened |

Render this as a table in the conversation. Approval happens where the user
already is, so the plan goes to them rather than to a file.

**Recovery is not optional, and it is not the same as failure handling.** Failure
handling says what happens to the operations that have not run yet. Recovery says
what to do about the one that already did. Write it before asking for approval: an
operation you cannot say how to undo is one the user is approving blind. Where
there is genuinely no undo — a posted message, a triggered pipeline, a published
package — say that, in those words. "Cannot be undone; the message stays" is a
complete and useful recovery entry. Silence is not.

When a plan is too large to read in the transcript — a multi-repository bump, a
catalog change touching dozens of files — write it to a file in the operating
system temporary directory instead, following `/handoff`'s convention, and print
the absolute path. Do not write it into the user's checkout, where it can reach a
commit.

**2. Get approval for that stated set.** The user approves what they were shown.
Earlier intent to publish never authorizes an operation whose exact target and
payload have not been shown. If the plan changes after approval — a different
target, an extra operation, an edited body — it is a new plan and needs new
approval.

**3. Execute, then report every operation.** Report each one as completed,
failed, or skipped, in the order it was planned. An operation that never ran
because an earlier one failed is reported as skipped, not omitted. A failed
write is reported, never quietly retried into a different shape.

## Credentials never reach a preview

A preview shows a command as it will run, so it can carry a token that was
pasted, interpolated from the environment, or returned by a tool. Scan before
showing:

```bash
uv run scripts/scan_credentials.py <plan.json> --json
uv run scripts/scan_credentials.py --text "<a single command or body>"
```

It exits non-zero and names the offending path when it finds a credential-shaped
field or value — an authorization header, a PEM private key, a `ghp_`, `glpat-`,
`xox`, `sk-`, or `AKIA` token, or a field named like a secret at any depth. It
reports the field, never the secret.

A credential in a plan is a bug in how the command was built, not something to
redact and continue past. Fix the construction so the secret is supplied by the
authenticated tool at run time.

## Who executes

The skill that owns the target executes it. A caller that needs a Jira write
invokes `/rhdh-jira-update`; one that needs a forge write builds the command and
runs it itself. `/rhdh-forge` constructs forge payloads and never executes them —
that separation is what makes this gate enforceable, because the module that
knows how to build the command cannot run it.

## Completion

Complete when every operation the user approved has an outcome, the outcomes are
in the planned order, and each one names its target. An operation missing from
the report, or reported without the target it changed, means the gate did not
close.

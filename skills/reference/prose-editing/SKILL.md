---
name: prose-editing
description: >-
  Edits or audits prose that the caller supplies as text or a file, preserves
  its claims and voice, removes machine-writing patterns, and verifies the
  result with the bundled linter. Use for explicit requests such as "rewrite
  this draft", "edit this existing PR body", "make this sound human", or
  "audit this prose without changing it". It does not review code, decide what
  a pull request or Jira issue should say, or compose from a blank sheet.
compatibility: "Python 3.9+; the bundled linter is stdlib-only"
---

# Prose editing

Edit an existing draft without changing what it claims. The caller supplies
the prose and, when it knows, the register. Return only the prose when another
skill invokes this one.

## Choose the operation

Explicit edit intent wins. A request to rewrite, tighten, or humanize remains
an edit even when it also asks for findings or a score.

Use `audit` only when the caller explicitly asks for no changes, an audit, or
findings without a rewrite. Text written by somebody else is not automatically
read-only. Protect quoted third-party passages, but offer or make a requested
rewrite of the surrounding draft.

## Choose the primary register

A caller-provided register wins. Otherwise, use the document's primary purpose:

| Register | Primary purpose | Loaded references |
|---|---|---|
| `strict` | procedure, runbook, safety text, operator-facing error | [mechanical](references/mechanical.md) and all of [compression](references/compression.md) |
| `flavored` | README, technical docs, PR or MR body, Jira prose, code comment | [mechanical](references/mechanical.md) and the shared part of [compression](references/compression.md) |
| `voiced` | announcement, community message, blog post, personal prose | [mechanical](references/mechanical.md) and [voice](references/voice.md) |
| `audit` | explicit no-change inspection | all three references; recommendations follow the document's primary purpose |

Purpose outranks a byline. A technical README with an author's name remains
`flavored`. When the purpose is genuinely ambiguous and choosing wrong would
materially change the rewrite, ask one focused question. Otherwise use
`voiced`, which makes the least structural change.

Use one numeric primary score. Do not invent a register map. In a mixed
document, keep its primary register and manually apply `strict` rules to
procedural and safety sections. This local override does not produce a second
score.

If the user supplies a sample of their own writing, read it before the draft.
Its stable sentence rhythm, vocabulary, punctuation, transitions, and quirks
govern `voiced` edits. A sample can justify em dashes, curly quotes, repeated
openings, or other deliberate habits that are weak evidence by themselves.

## Prepare a safe working copy

Never write beside this installed skill. Create a unique directory with the
system temporary-directory API. Keep these paths inside it:

- `source.md`: an unchanged snapshot used for the meaning check.
- `rewrite.md`: the only bytes scored before and after; edit this file.
- `before.json`: the baseline report for that exact normalized `rewrite.md`
  path.
- `voice.md`: an unchanged snapshot of a supplied writing sample, when present.

For pasted text, write the supplied bytes to `source.md`, then copy it to
`rewrite.md`. For a user file, copy the file to both paths and do not touch the
original until the rewrite passes every guard. Use process argument arrays
where the host supports them. If a shell is unavoidable, quote every path,
including the trusted skill directory and all temporary paths. Never paste a
user-controlled path into an unquoted command.

When the user supplies a writing sample, copy its exact bytes to `voice.md` and
pass `--voice-sample "<unique-temp-dir>/voice.md"` on both linter runs. Omit the
option on both runs when there is no sample. A different or changed sample makes
the baseline incompatible.

Resolve `scripts/lint.py` relative to this `SKILL.md`. The equivalent shell
shape without a writing sample is:

```bash
python "<skill-dir>/scripts/lint.py" --json --register <register> \
  "<unique-temp-dir>/rewrite.md" > "<unique-temp-dir>/before.json"
```

When a sample exists, insert
`--voice-sample "<unique-temp-dir>/voice.md"` after the register argument.

Use the host's UTF-8 file APIs or redirection in the temporary directory. Do
not use a fixed `before.json`. Delete the unique directory after delivery.

## Edit loop

Skip to [Audit](#audit) for `audit`. For an edit:

1. Load the references named by the register. Read every rule that applies.
2. Score `rewrite.md` and save the complete JSON as `before.json`.
3. Read all `violations`, `samples`, `markers`, and manual checks. A zero score
   does not clear a marker or a rule that needs judgment.
4. Build a private source inventory. Record every proposition, condition,
   exception, scope qualifier, modal force, name, number, version, date, quote,
   citation, identifier, and safety consequence.
5. Rewrite `rewrite.md`. Change the smallest useful span, except when several
   patterns cluster in one paragraph; then rewrite that paragraph around its
   concrete point.
6. Score the same normalized `rewrite.md` path against `before.json`:

   ```bash
   python "<skill-dir>/scripts/lint.py" --json --register <register> \
     --baseline "<unique-temp-dir>/before.json" \
     "<unique-temp-dir>/rewrite.md"
   ```

   When the baseline used a writing sample, insert the same
   `--voice-sample "<unique-temp-dir>/voice.md"` argument after the register.

   A baseline metadata or path mismatch is a failed verification, not a score.
   Correct the invocation and rerun it. Never reuse a report from another
   register, quote policy, file, or linter score version.
7. Make at most one more rewrite-and-score pass.
8. Compare `source.md` with `rewrite.md` in both directions. Every source
   proposition and qualifier must survive, and every output proposition must
   come from the source or an explicit user instruction. Preserve `must`,
   `should`, `may`, `can`, uncertainty, negation, and exceptions unless the
   source itself licenses the change.
9. Run the manual checklist and an adversarial final read. Ask: "What still
   sounds generated?", "What fact or limit disappeared?", and "What did this
   rewrite add?" Repair any defect those questions expose.
10. Only now copy the final prose to the requested destination. For a user
    file, replace its prose while preserving protected spans. For pasted text,
    return the rewrite.

If Python cannot run, perform the same reference, inventory, and adversarial
checks by eye. Say **not linted** and report no estimated number.

## Audit

Do not rewrite or create an output document.

1. Load all three references and score the supplied working copy once with
   `--register audit`.
2. Infer the primary register from document purpose. Classify each hit as
   governing, out of register, or a false positive.
3. Check every marker and every manual rule, including claim preservation,
   voice-sample conflicts, repeated names/openings, article use, paragraph
   focus, headings that restate themselves, and hollow paragraphs.
4. Return the single score, the source claim/condition/scope inventory, and a
   compact findings table: rule, source span, classification, and suggested
   edit. Make no change.

## Protected spans and Markdown

Never change fenced or inline code, commands, identifiers, part numbers,
units, error strings used for search, YAML frontmatter, data, or link targets.
Link text is prose. Preserve quoted third-party language when context identifies
it as a quotation, title, example under discussion, or externally owned text.

Blockquotes, callouts, and table cells are not inherently quotations. Lint and
edit their first-party prose. Use `--quote-safe` only when the caller explicitly
identifies the running prose as examples or third-party quotation that must be
excluded. It suppresses findings only in those protected regions. The option
must not hide ordinary first-party prose elsewhere in the document.

## Read the report

Consume the full JSON object. Never decide from the exit code alone.

| Key | Meaning |
|---|---|
| `violations` and `samples` | high-confidence counts that contribute to the score, with examples |
| `markers` | possible issues that require contextual judgment and do not contribute to the score |
| `by_layer` | the reference layer that owns each scored category |
| `manual_checks` | rules the linter cannot certify |
| `file_identity`, `voice_sample_identity` | canonical inputs that make baseline comparison safe |
| `delta` | compatible baseline `before`, `after`, and `improved` values |
| `total_per100w` | one primary density score, not a quality verdict |
| `fail_over`, `over_fail_over` | optional caller-supplied finite, nonnegative CI threshold and its result; absent without `--fail-over N` |

Singleton transitions, curly quotes, em dashes, short emphatic sentences, and
deliberate repetition are markers, not proof of machine writing. Score them
only when they form the repeated or clustered pattern documented by the
reference. A supplied voice sample outranks those style defaults in `voiced`.

## Delivery

| Caller | Return |
|---|---|
| another skill editing final outbound prose | final prose only; keep register and score metadata in the transcript |
| person who pasted prose | final rewrite, register, score delta, and unresolved findings |
| person who supplied a file | edit the file, then report register, score delta, and unresolved findings |
| explicit `audit` | findings and one score; no rewrite |

Another skill invokes this pass exactly once, after it has composed all
free-form prose and before it shows, gates, or posts that prose. A transport
layer does not invoke it. Do not apply it automatically to structured payloads,
commands, checksums, generated reports, ADRs, AGENTS files, skills, PRDs, or
other local documents with an owning authoring skill. An explicit user request
can still edit any prose document.

## Completion

Work is complete only when:

- the operation and primary register match the caller's intent;
- the before and after reports came from the same canonical `rewrite.md`, voice
  sample, score version, register, and quote policy, or the response says
  **not linted**;
- every scored violation, marker, and applicable manual rule is fixed, rejected
  with a concrete false-positive reason, classified out of register in an
  audit, or reported as unresolved;
- the two-way inventory proves that no source claim, scope limit, condition, or
  modal force was lost and no unsupported claim was added;
- protected bytes are unchanged;
- an adversarial final read found no remaining unreported defect;
- delivery follows the table above; and
- the unique temporary directory is removed.

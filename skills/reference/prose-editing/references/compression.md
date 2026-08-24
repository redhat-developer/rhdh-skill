# Compression layer

Loaded in `strict` and `flavored`. Not loaded in `voiced`, where fixed sentence
caps would remove the voice that register exists to protect.

This is Simplified Technical English discipline: short sentences, plain words,
named actors, one name per thing. It shapes how a sentence is built. The
machine tells in `mechanical.md` are a separate problem and apply on top of
everything here.

**This file has two parts.** Everything from here down to the end of
[Structure](#structure) applies in `strict` and in `flavored`. Everything under
[`strict` only](#strict-only) applies in `strict` alone. In `flavored`, read to
the end of Structure and stop there.

## Sentences

### `long_sentence`

An instruction has at most 20 words. A descriptive sentence has at most 25.
Classify by function, not by punctuation: an imperative step or a sentence
that tells the reader what to do is an instruction. Split at the natural joint,
usually a conjunction or a relative pronoun.

> When the plugin export overlay is regenerated after an upstream release, the
> workflow opens a pull request against the overlays repository so that the
> plugin catalog can pick up the new version on the next build.

> The workflow regenerates the plugin export overlay after an upstream release.
> It then opens a pull request against the overlays repository. The plugin
> catalog picks up the new version on the next build.

Split by adding a period, never by deleting a qualifier. A condition, version,
or scope word that was in the draft stays even when the sentence remains over
its limit. Keep the long sentence and report the reason.

### `semicolon`

Replace it with a period. The two halves were already two sentences.

### `contraction`

Expand it. `it is`, `does not`, `cannot`, `will not`.

### `long_paragraph`

Over six sentences. Split at the point where the topic changes. When no such
point exists, the paragraph is probably saying one thing six times, and the
edit is to cut rather than to split.

### Connectors

Compression produces staccato when it is applied without care. Short sentences
are the goal; disconnected ones are not. Join related steps with a plain
connector: `then`, `but`, `so`, `thus`, `as a result`, `after that`.

> Push the tag. The Konflux pipeline starts. A Snapshot appears. The release
> plan runs. The bundle lands in the catalog.

> Push the tag. The Konflux pipeline then starts and produces a Snapshot. When
> the release plan runs, the bundle lands in the catalog.

The voice layer scores this rhythm as `staccato_drama`, where it reads as
manufactured drama rather than as over-compression. That layer does not load in
`strict` or in `flavored`, so nothing scores the rhythm here. Fix it anyway.

## Verbs

### `passive_voice`

Name the actor and put it in front.

> The dynamic-plugins ConfigMap is mounted by the operator.

> The operator mounts the dynamic-plugins ConfigMap.

Two cases stay as they are. Where the participle describes a state rather than
reporting an action, nothing is being done to anything and there is no actor to
restore: `the field is required`, `the route is disabled`, `the plugin is
installed`. And a passive whose actor the draft never named stays passive.

### `complex_tense`

Use the infinitive, the imperative, the simple present, the simple past, or the
simple future. Drop the perfect and the progressive from the spine of the
sentence.

> The overlay has been regenerated and the catalog is now rebuilding.

> The workflow regenerated the overlay. The catalog rebuild is running.

### `ing_main_verb`

A progressive form where a simple tense says the same thing.

> The operator is watching the ConfigMap for changes.

> The operator watches the ConfigMap for changes.

### `nominalization`

An action hidden inside a noun, propped up by an empty verb.

> Perform a validation of the `app-config.yaml` file before the deployment of
> the chart.

> Validate `app-config.yaml` before you deploy the chart.

### `phrasal_verb`

| Do not write | Write |
|---|---|
| spin up | start |
| spin down, tear down | stop, remove |
| kick off | start |
| roll out | release |
| reach out | contact |
| dive into | read |
| drill down | inspect |
| circle back | return |
| ramp up | increase |
| stand up | deploy |

## Words

### `verbose_word`

The long form of a word that has a short one. Words that are wrong in every
register live in `mechanical.md` under `ai_vocabulary`, so they are not
repeated here.

| Do not write | Write |
|---|---|
| begin, commence, initiate | start |
| prior to | before |
| subsequent to | after |
| obtain, acquire | get |
| provide | give, or the concrete verb |
| perform, conduct | do, or the action verb |
| in order to | to |
| additionally, furthermore, moreover | start a new sentence, or delete |
| regarding, concerning | about |
| demonstrate | show |
| facilitate | name the action |
| ensure | make sure, or state the requirement outright |
| aforementioned | this |
| whilst, amongst | while, among |
| numerous, myriad, plethora | the count the source gives, or `many` |

### One name per thing

Pick one word for each concept and reuse it for the whole document. Do not
rotate `check`, `verify`, `validate`, and `confirm` for the same action. Do not
call the same object the operator, the controller, and the reconciler in three
consecutive paragraphs.

Technical nouns the source already uses stay: `PipelineRun`, `Snapshot`,
`overlay`, `dynamic plugin`, `ConfigMap`. An abbreviation gets spelled out the
first time it appears, and is the only form used from then on.

This rule is not lintable. Read for it.

### One meaning per word

Use a word with the same meaning throughout the document. Do not use `fall` for
both physical movement and a decrease, or `follow` for both sequence and
obedience. Keep established technical meanings and replace only the ambiguous
use. This rule requires judgment.

### American spelling

Use American spelling in compressed technical prose: `color`, `behavior`,
`catalog`, and `license` as the noun. Do not alter product names, quotations,
identifiers, or a repository's explicit house style.

## Structure

### Keep the articles

Do not drop `a`, `an`, or `the` to make a sentence shorter. Telegraphic prose
is not compressed prose.

> Remove secret from namespace and restart deployment.

> Remove the secret from the namespace, then restart the deployment.

General statements about an abstract idea take no article, and that is correct
English rather than a dropped word. `Dynamic plugins load at startup.` stays as
it is.

### A list item may stay a label

Some list items name a thing rather than assert something about it: steps in a
sequence, entries in a changelog, cells in a table. Those are labels, and a
label is allowed to be a fragment. Padding one out into a full sentence so that
it can carry an article makes it longer and no clearer.

> - Frontend receives the session JWT
> - Backend validates the token against Keycloak
> - Catalog returns the entity

Rewriting those three into full sentences adds words and no meaning. Leave
them. The `inline_header_list` tell in `mechanical.md` is a different thing: a
label plus a sentence that restates the label. A bare label is fine.

### Condition before command

Put the condition first and separate it from the command with a comma.

> Read the task log if the PipelineRun fails.

> If the PipelineRun fails, read the task log.

Give each sentence a single instruction. Two actions share one sentence only
when the reader has to perform them together.

## `strict` only

**Everything below applies in `strict` and in no other register.** In
`flavored`, the file ended at the section above.

### `strict_banned_word`

Ambiguous words carry real risk in a procedure. A reader who guesses wrong runs
the wrong command.

| Do not write | Write |
|---|---|
| however | but, or start a new sentence |
| since | because for a reason, after for a time |
| should | must, or the bare command: `Stop the pod.` |
| shall | must, or the bare command |
| using | with, or `use` as the verb |
| follow, follows, followed | do, or `do the steps in` |
| may | can for ability, might for possibility |
| press | push, for a physical control |

The match on `may` is case-sensitive, so the month is not flagged.

> You should follow the runbook using the listed steps.

> Do the steps in the runbook.

### Safety labels

Three labels, three meanings, and they are not interchangeable.

| Label | Means | Rule |
|---|---|---|
| `WARNING` | risk of injury to a person | rare in software prose. Keep it for text that touches hardware or a physical operation. |
| `CAUTION` | risk of damage to equipment, data, or a running system | carries most of the traffic in a runbook |
| `NOTE` | information only | never an instruction. A `NOTE` that tells the reader to do something is a step in disguise. |

Put the label immediately before the step it protects, not in a block at the
top of the procedure. State the condition or the command first, then the
consequence.

> **CAUTION:** The next command deletes the PostgreSQL PVC. The catalog
> database cannot be recovered after it runs.
>
> 4. Run `oc delete pvc data-rhdh-postgresql-0`.

Safety text and error strings take no hedge. Name the condition and the action.
Write `If the reconcile fails, check the operator log.` rather than `you might
want to consider checking the logs`.

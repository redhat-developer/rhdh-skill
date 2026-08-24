# Mechanical layer

Loaded in every register. These are patterns to inspect, not proof that a
machine wrote the text. Some are strong enough to score from one occurrence;
others become a tell only when they repeat or cluster. Apply the documented
false-positive test before changing them.

## Punctuation and decoration

| Category | The tell | The edit |
|---|---|---|
| `em_dash` | repeated `—`, `–`, or spaced ` -- ` used for a sales-like rhythm | use the writer's sample; otherwise use a period, comma, colon, or parentheses. One dash is a marker, not a tell. |
| `curly_quote` | curly quotation marks clustered with other machine patterns when the target style uses straight quotes | follow the writer's sample or target format. One curly quotation is a marker, not a tell. Never change code or shell strings. |
| `emoji` | a rocket, a check mark, or a warning sign decorating a heading or a bullet | delete it. The heading already carries the meaning. |
| `title_case_heading` | `## Installing Dynamic Plugins On OpenShift` | sentence case: `## Installing dynamic plugins on OpenShift`. Proper nouns keep their capitals: OpenShift, Backstage, Red Hat Developer Hub, Konflux. |

A heading that is a literal identifier stays exactly as written. `## app-config.yaml`
is a filename, not a title.

### `boldface_overuse`

Bold applied repeatedly to ordinary nouns in running prose is decoration, not
structure. Remove it. Keep bold on a defined term at first use, a definition
label, or the one phrase a warning must emphasize. One bold term is a marker;
several decorative spans form the tell.

### `inline_header_list`

A bulleted list where each item opens with a bolded generic label, a colon,
then a sentence restating the label. The label carries no information and the
sentence carries almost none.

> - **Performance:** Performance has been improved in this release.
> - **Security:** Security has been strengthened for plugin loading.
> - **Usability:** The user experience of the header is now better.

Fix it by moving the fact into the item, not by deleting the list.

> - The backend starts in half the time it took in 1.9.
> - The backend verifies a dynamic plugin's integrity hash before it loads it.
> - The global-header plugin reads its layout from `app-config.yaml`.

A real term followed by its definition is a definition list, and it is fine.
`**RHIDP**: the Jira project for Developer Hub engineering work` is not this
tell.

## Chatbot residue and hedging

### `chatbot_residue`

Conversation with the assistant, pasted into the document as if it were
content. Delete the whole sentence and keep what surrounded it.

> Here is an overview of the bulk-import plugin. I hope this helps! Let me know
> if you would like the API reference as well.

> The bulk-import plugin adds repositories from a GitHub organization to the
> software catalog.

Praise that exists only to agree with the reader is the same residue. Remove
`great question`, `you are absolutely right`, `that is an excellent point`, and
similar approval before an answer. Keep praise when evaluating somebody's work
is the document's actual purpose.

### `modal_hedge`

A sentence that announces the importance of the next clause instead of stating
it. Delete the announcement and keep the clause.

> It is important to note that the operator does not restart the Deployment on
> every reconcile.

> The operator does not restart the Deployment on every reconcile.

The same edit applies to `it should be noted`, `it is worth noting`, `please
note that`, `as mentioned above`, and `as previously discussed`.

### `qualifier_pile`

Keep uncertainty and scope that the source supports, but do not stack repairs
such as `could potentially possibly`, `might arguably`, `to be fair`, and `in
some cases it may`. Choose the one qualifier that states the actual confidence
or scope. Never strengthen `may` to `will` merely to shorten a sentence.

### `filler_phrase`

| Do not write | Write |
|---|---|
| due to the fact that | because |
| at this point in time | now |
| in the event that | if |
| has the ability to | can |
| a number of | the count from the source, or `some` |
| for the purpose of | to |

### `vague_attribution`

A claim credited to an authority that is never named.

> Industry reports show that platform teams prefer a single developer portal.

Name the source when the draft has one, and cut the sentence when it does not.

### `notability_padding`

A list of famous publications, experts, or follower counts used only to prove
that a subject matters. Keep a citation when the draft says what the source
reported. Otherwise keep only the useful context and do not invent it.

> Her work has received independent coverage from leading national media
> outlets, and she has an active social media presence.

> The New York Times reported her position on the 2025 policy change.

### `knowledge_gap`

A knowledge-cutoff disclaimer followed by a plausible guess is not a fact.
Watch for `up to my last update`, `based on available information`, `not
publicly available`, `likely`, `it is believed`, and claims that missing public
detail proves somebody is private. State only what the supplied sources show,
or remove the passage. Never turn absence of evidence into biography.

### Unsupported defenses and fake alternatives

`unsupported_objection` answers an objection nobody raised: `this is not
really about`, `I am not arguing that`, `to be clear`, `some might say`, or a
similar defense with no named source or developed response. Remove the defense
and state its surviving claim directly. Keep legal limits, safety disclaimers,
FAQ answers, named objections, and corrections.

`fake_alternative` introduces an option no reader would choose, rejects it in a
clause, and never uses it again: `a tempting approach would be`, `you might
think`, `it would be easy to just`. Remove drafting residue. Keep real design
alternatives that inform a decision or argument.

## Inflation

### `ai_vocabulary`

Words that are wrong in every register. A word that is merely long is a
compression problem rather than a machine tell, so it is not listed here.

| Do not write | Write |
|---|---|
| leverage, utilize | use |
| delve into | read, examine |
| crucial, pivotal, vital | say what breaks without it, or cut |
| seamless, effortless | cut |
| robust, powerful, cutting-edge | cut, or keep a measure the source already gives |
| showcase | show, list |
| underscore, highlight (as a verb) | say the point directly |
| landscape, tapestry, ecosystem (as abstract nouns) | name the actual set of things |
| testament to | cut |
| align with | match, follow |
| intricate, nuanced | cut, or say what the complication is |
| actually, key, valuable, enduring, fostering, garner | use the concrete claim, or cut |
| quietly | keep only when it literally describes sound or secrecy |
| gate, gated, gating | keep established technical use; replace figurative use |

> The marketplace plugin leverages a robust catalog to showcase the plugin
> landscape.

> The marketplace plugin reads the catalog and lists the available plugins.

### `promotional`

Advertisement register in a document nobody is buying.

| Do not write | Write |
|---|---|
| boasts a, features a | has |
| vibrant, thriving, rich | cut |
| nestled in, at the heart of | the actual location, or cut |
| renowned, industry-leading, best-in-class | cut |
| breathtaking, stunning | cut |
| commitment to, dedication to | the thing that was actually done |

> Red Hat Developer Hub boasts a vibrant plugin ecosystem and a deep commitment
> to developer productivity.

> Red Hat Developer Hub supports dynamic plugins.

### `authority_trope`

A ceremonial run-up that promises a deeper truth and then delivers an ordinary
point. Watch for `the real question is`, `at its core`, `what really matters`,
`fundamentally`, `the deeper issue`.

> At its core, what really matters about dynamic plugins is load order.

> Dynamic plugins depend on load order.

### `aphorism`

An ordinary claim reshaped into a portable saying. Watch for `X is the Y of Z`,
`the currency of`, `the architecture of`, `X becomes a trap`.

> Configuration is the tax you pay for flexibility.

> Every option in `app-config.yaml` is one more thing to keep working.

### `generic_conclusion`

A closing paragraph made of good feeling and no content. The usual shapes are a
bright future, an invitation to build something, and a thank-you to a community
that was never described. A `## Conclusion` heading over one of them counts too.

> The future of the platform is bright, and we cannot wait to see what you
> build with it. Exciting things are ahead.

> In conclusion, the possibilities with dynamic plugins are endless.

The second one is the reason this sits in the mechanical layer: a README ends
that way as readily as an announcement does.

Delete the paragraph and stop wherever the draft last said something specific:
the release date, the upgrade path, the docs link, the tracker that takes
feedback. When the draft states real plans, use those. Rewriting one send-off
into a better send-off leaves the same defect in place.

### `formulaic_section`

A stock `Challenges`, `Legacy`, or `Future outlook` section often repeats
vague constraints and optimism. Keep concrete facts such as named shortages,
deadlines, and planned actions. Remove the section when it adds none.

### `significance_inflation`

A sentence whose only job is to say that the topic matters. It usually claims a
turning point, a broader trend, or an ongoing commitment.

> The 1.10 release marks a pivotal moment in the evolution of the platform and
> underscores our ongoing commitment to the developer community.

> Red Hat Developer Hub 1.10 is generally available today.

Watch for `marks a turning point`, `represents a shift`, `reflects a broader`,
`sets the stage for`, `is a testament to`, `plays a key role in`, `leaves an
indelible mark`.

The test is subtraction. Delete the sentence and read the paragraph again. When
nothing factual is missing, the sentence was inflation. When the draft has a
real reason the release matters, such as a deprecation deadline or a supported
upgrade path, state that reason instead of the feeling.

| Do not write | Write |
|---|---|
| a pivotal moment in the evolution of | what changed |
| reflects a broader shift toward | the change itself, when the draft names one |
| underscores our commitment to | what was shipped |
| sets the stage for | what happens next, with its date, when the draft has one |

### `previous_version_frame`

Documentation and comments describe the current behavior. Do not anchor them
to the diff with `was added`, `now`, `new`, `previously`, or a discarded
implementation unless the document is a changelog, release note, migration
guide, or other intentionally version-scoped text. State the current behavior.

## Sentence shapes

### `copula_avoidance`

An elaborate verb standing in for `is` or `has`.

> The dynamic-plugins ConfigMap serves as the source of truth for enabled
> plugins.

> The dynamic-plugins ConfigMap lists the enabled plugins.

`serves as`, `stands as`, `represents`, `marks`, and `boasts` all collapse to
`is` or `has`, or to a verb that names the real job.

### `negative_parallelism`

Three shapes, one habit: defining a thing by what it is not.

> It is not just a plugin registry, it is a marketplace.

> The marketplace plugin lists plugins and installs them.

> Not only does the operator create the Deployment, it also creates the Route.

> The operator creates the Deployment and the Route.

The third shape is a negation fragment tacked onto a sentence in place of a
real clause.

> The overlay reads the version from the plugin's `package.json`, no manual
> bumps.

> The overlay reads the version from the plugin's `package.json`, so nobody
> edits it by hand.

### `ing_analysis`

A trailing participial phrase bolted onto a finished sentence to add depth it
does not have. Split it into its own sentence when it carries a fact, and cut
it when it does not.

> The operator now watches the ConfigMap, ensuring that the backend restarts
> whenever the configuration changes and reflecting a tighter reconcile loop.

> The operator watches the ConfigMap. The backend restarts when the
> configuration changes.

Watch for a comma followed by `highlighting`, `underscoring`, `ensuring`,
`reflecting`, `contributing to`, `showcasing`, `enabling`, `allowing`.

### `false_range`

A `from X to Y` frame whose endpoints do not sit on a scale.

> The plugin catalog covers everything from authentication to observability,
> from CI status to cost insights.

> The plugin catalog includes authentication, observability, CI status, and
> cost plugins.

### `signposting`

Announcing the next paragraph instead of writing it. Watch for `let us dive
in`, `here is what you need to know`, `now let us look at`, `in this section we
will`.

> Let us look at how the operator mounts the ConfigMap. Here is what you need
> to know.

> The operator mounts the app-config ConfigMap into the backend container.

A heading already does this job, which is why the sentence under it is
redundant.

Casual announcements such as `heads up`, `quick note`, `before I forget`, and
`one thing that bit me` have the same defect when they only announce the next
sentence. Keep them when they carry real voice or context rather than serving
as an empty signpost.

### `rhetorical_opener`

A staged pause before an ordinary answer. Watch for a standalone `Honestly?`,
`Look,`, `Here is the thing`, `The thing is`, `Let us be honest`.

> Is the 1.10 upgrade safe? Honestly? It depends on which dynamic plugins you
> enabled.

> Whether the 1.10 upgrade is safe depends on which dynamic plugins you
> enabled.

The word inside a sentence is ordinary English. The tell is the theatrical
one-word opener.

### Active subjects and stable names

Use active voice when it makes the actor and action clearer. Restore a missing
subject in fragments such as `No configuration file needed`. Keep a passive
when the actor is unknown or irrelevant and keep participles that describe a
state, such as `the field is required`. In `strict`, a known actor must be
active. In other registers this is a contextual marker.

Use one clear name for one subject. Do not cycle through synonyms to avoid a
useful repetition. Also inspect several consecutive sentences that begin with
the same subject. Merge or vary them only when the repetition is accidental;
deliberate anaphora and a supplied voice sample win.

### `predicate_hyphenation`

Keep a compound modifier hyphenated before its noun: `a high-quality report`.
Do not automatically carry that hyphen into predicate position: `the report is
high quality`. Product terms and established technical compounds keep their
spelling.

### Heading restatement and hollow paragraphs

A heading followed by a sentence that merely repeats it has not begun the
section. Remove the repeated sentence. A paragraph that adds no proposition,
condition, name, number, or command beyond the preceding paragraph is hollow;
delete it or merge its one useful clause.

## Markers

Reported in `markers`, never added to the score. Account for them with context;
do not let one drive a rewrite on its own.

### `noun_train`

Four or more nouns stacked with nothing between them. Keep a multi-word noun to
three words at most. Unpack the rest with `of`, `that`, or a hyphen.

> the dynamic plugin registry cache invalidation handler

> the handler that invalidates the dynamic-plugin registry cache

A product name is one noun no matter how many words it holds. Red Hat Developer
Hub is not a noun train.

### `rule_of_three`

Three abstract nouns in a row, arranged for rhythm rather than for content.

> The 1.10 release brings speed, stability, and simplicity.

> The 1.10 release cuts backend startup time and adds RBAC for dynamic plugins.

A list with three real members is a fact, not a tell. Three supported OpenShift
versions, three Jira projects, and three failing tasks in a PipelineRun all
stay as they are.

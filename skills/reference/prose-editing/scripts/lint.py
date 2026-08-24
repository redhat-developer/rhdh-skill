#!/usr/bin/env python3
"""Score prose for AI tells and Simplified Technical English discipline.

Three layers. Mechanical checks run in every register, compression checks run
in the two rewriting registers, voice checks run only where prose is allowed a
voice. See the register table in --help. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCORE_VERSION = 11

REGISTERS = ("strict", "flavored", "voiced", "audit")
DEFAULT_REGISTER = "flavored"

INSTRUCTION_MAX_WORDS = 20
DESCRIPTIVE_MAX_WORDS = 25
LONG_PARAGRAPH_SENTENCES = 6
# The documented example stacks fragments of four to seven words, so a cap of
# five saw three of its five fragments and never fired. The run is the tell,
# not the length, so the cap is loose and STACCATO_RUN does the deciding.
STACCATO_MAX_WORDS = 7
STACCATO_RUN = 3
BOLD_PER_PARAGRAPH = 1
NOUN_TRAIN_MIN = 4
SAMPLE_LIMIT = 6

MECHANICAL = (
    "em_dash",
    "transition_stack",
    "chatbot_residue",
    "copula_avoidance",
    "negative_parallelism",
    "emoji",
    "curly_quote",
    "title_case_heading",
    "inline_header_list",
    "boldface_overuse",
    "ai_vocabulary",
    "promotional",
    "authority_trope",
    "aphorism",
    "signposting",
    "rhetorical_opener",
    "ing_analysis",
    "false_range",
    "vague_attribution",
    "modal_hedge",
    "filler_phrase",
    # A send-off made of good feeling and a sentence claiming the topic matters
    # are tells in every register. A README closing on "in conclusion, the
    # possibilities are endless" is the same defect as a blog post doing it.
    "generic_conclusion",
    "significance_inflation",
)
COMPRESSION = (
    "long_sentence",
    "semicolon",
    "contraction",
    "passive_voice",
    "complex_tense",
    "ing_main_verb",
    "nominalization",
    "phrasal_verb",
    "verbose_word",
    "long_paragraph",
    "strict_banned_word",
)
# Only the two tells that a register can legitimately want. Short steps are
# correct in a runbook and a bold defined term is correct in a README, so
# neither is scored outside prose that is allowed a voice.
VOICE = ("staccato_drama",)
MARKERS = (
    "singleton_em_dash",
    "singleton_curly_quote",
    "singleton_transition",
    "singleton_bold",
    "american_spelling",
    "condition_before_command",
    "copula_candidate",
    "qualifier_phrase",
    "noun_train",
    "rule_of_three",
    "notability_padding",
    "knowledge_gap",
    "unsupported_objection",
    "fake_alternative",
    "formulaic_section",
    "previous_version_frame",
    "repeated_opening",
    "predicate_hyphenation",
    "heading_restatement",
    "missing_subject",
    "watched_vocabulary",
    "casual_signposting",
)
MANUAL_CHECKS = (
    "claim_preservation",
    "voice_fidelity",
    "terminology_consistency",
    "word_meaning_consistency",
    "active_subject_context",
    "one_instruction_per_sentence",
    "article_use",
    "abbreviation_definition",
    "paragraph_focus",
    "safety_labels",
    "heading_restatement",
    "hollow_paragraph",
    "quotation_ownership",
    "objection_context",
    "alternative_relevance",
    "american_spelling",
    "condition_before_command",
)

LAYERS = {"mechanical": MECHANICAL, "compression": COMPRESSION, "voice": VOICE}
REGISTER_LAYERS = {
    "strict": ("mechanical", "compression"),
    "flavored": ("mechanical", "compression"),
    "voiced": ("mechanical", "voice"),
    # audit reports every rewriting layer and applies none of it.
    "audit": ("mechanical", "compression", "voice"),
}
STRICT_ONLY = ("strict_banned_word",)
# ---------------------------------------------------------------------------
# Phrase lists. Data only. Every list is matched in one pass and the longest
# match over a span wins, so a longer phrase in one list may contain a shorter
# phrase in another: `marks a pivotal moment` scores inflation, not inflation
# plus vocabulary. Two lists must still never hold the same phrase, because
# then no rule decides which one owns it.
# ---------------------------------------------------------------------------

AI_VOCABULARY = (
    "actionable insights",
    "aforementioned",
    "align with",
    "aligns with",
    "amongst",
    "bolster",
    "bolsters",
    "bolstered",
    "bolstering",
    "comprehensive",
    "comprehensively",
    "cornerstone",
    "crucial",
    "deep dive",
    "deep dives",
    "deep-dive",
    "delve",
    "delves",
    "delved",
    "delving",
    "enduring",
    "enhance",
    "enhances",
    "enhanced",
    "ever-evolving",
    "foster",
    "fosters",
    "fostered",
    "garner",
    "garners",
    "garnered",
    # "harness" alone is a test harness or a dev harness in any engineering
    # repository, so only the transitive marketing shape scores.
    "harness the",
    "harnesses the",
    "harnessing",
    "henceforth",
    "highlight",
    "highlights",
    "highlighted",
    "holistic",
    "interplay",
    "intricate",
    "intricacies",
    "landscape",
    "leverage",
    "leverages",
    "leveraged",
    "leveraging",
    "multifaceted",
    "myriad",
    "navigate the complexities",
    "navigating the complexities",
    "nuanced",
    "paradigm shift",
    "pivotal",
    "plethora",
    "realm",
    "robust",
    "seamless",
    "seamlessly",
    "showcase",
    "showcases",
    "showcased",
    "streamline",
    "streamlines",
    "streamlined",
    "streamlining",
    "synergies",
    "synergy",
    "tapestry",
    "testament",
    "therein",
    "transformative",
    "underscore",
    "underscores",
    "underscored",
    "unprecedented",
    "utilization",
    "utilize",
    "utilizes",
    "utilized",
    "utilizing",
    "whilst",
)
PROMOTIONAL = (
    "battle-tested",
    "best-in-class",
    "blazing",
    "bleeding-edge",
    "boasts",
    "breathtaking",
    "commitment to",
    "cutting-edge",
    "delightful",
    "effortless",
    "effortlessly",
    "elegant",
    "elevate",
    "elevates",
    "empower",
    "empowers",
    "enterprise-grade",
    "exemplifies",
    "fast-paced",
    "first-class",
    "future-proof",
    "game changer",
    "game-changer",
    "game-changing",
    "groundbreaking",
    "in the heart of",
    "industry-leading",
    "lightning-fast",
    "must-visit",
    "natural beauty",
    "nestled",
    "next-generation",
    "powerful",
    "profound",
    "renowned",
    "revolutionary",
    "robust and scalable",
    "rock-solid",
    "state-of-the-art",
    "stunning",
    "supercharge",
    "to the next level",
    "turnkey",
    "unleash",
    "unlock",
    "unmatched",
    "unparalleled",
    "vibrant",
    "world-class",
)
AUTHORITY_TROPE = (
    "at its core",
    "fundamentally",
    "in reality",
    "make no mistake",
    "the bottom line is",
    "the deeper issue",
    "the heart of the matter",
    "the real question is",
    "what really matters",
)
APHORISM = (
    "becomes a trap",
    "is not a tool but",
    "is not a tool, but",
    "the currency of",
    "the language of",
    "the price you pay",
    "the tax you pay",
)
SIGNPOSTING = (
    "here is what you need to know",
    "here's what you need to know",
    "in this article",
    "in this section we",
    "let us dive in",
    "let us get started",
    "let's break this down",
    "let's get started",
    # "let's dive into" is deliberately absent: phrasal_verb already owns
    # "dive into", and one span must not score in two categories.
    "let's dive in",
    "let's explore",
    "let's take a look",
    "now let's look at",
    "we'll explore",
    "without further ado",
)
CHATBOT_RESIDUE = (
    "certainly!",
    "excellent point",
    "great question",
    "here is a",
    "here is an",
    "here's a",
    "here's an",
    "i hope this helps",
    "let me know if",
    "of course!",
    "should i continue",
    "want me to",
    "would you like",
    "you're absolutely right",
)
COPULA_AVOIDANCE = (
    "features a",
    "features an",
    "offers a",
    "offers an",
    "serve as",
    "serves as",
    "serving as",
    "stand as",
    "standing as",
    "stands as",
)
VAGUE_ATTRIBUTION = (
    "analysts say",
    "critics argue",
    "experts argue",
    "experts believe",
    "experts say",
    "industry reports",
    "it has been suggested",
    "it is believed",
    "it is widely",
    "many believe",
    "observers have",
    "research suggests",
    "some argue",
    "some critics",
    "some say",
    "sources say",
    "studies show",
    "widely considered",
    "widely regarded",
)
MODAL_HEDGE = (
    "as mentioned",
    "as noted above",
    "as previously discussed",
    "could potentially",
    "it can be argued",
    "it could be argued",
    "it is important to note",
    "it is worth noting",
    "it should be noted",
    "it's important to note",
    "it's worth noting",
    "might potentially",
    "please note that",
)
FILLER_PHRASE = (
    "a number of",
    "at the end of the day",
    "at this point in time",
    "find themselves",
    "finds themselves",
    "first and foremost",
    "for all intents and purposes",
    "for the purpose of",
    "found themselves",
    "has the ability to",
    "have the ability to",
    "in terms of",
    "in today's fast-paced",
    "in today's world",
    "it goes without saying",
    "last but not least",
    "needless to say",
    "one of the most",
    "when it comes to",
)
ING_ANALYSIS = (
    "cementing",
    "contributing",
    "cultivating",
    "demonstrating",
    "emphasizing",
    "embodying",
    "encompassing",
    "ensuring",
    "fostering",
    "highlighting",
    "illustrating",
    "reflecting",
    "showcasing",
    "signaling",
    "solidifying",
    "symbolizing",
    "underscoring",
)

VERBOSE_WORD = (
    "a variety of",
    "acquire",
    "acquires",
    "ascertain",
    "attempt to",
    "begin",
    "begins",
    "commence",
    "commences",
    "demonstrate",
    "demonstrates",
    "due to the fact that",
    "endeavor",
    "ensure",
    "ensures",
    "ensured",
    "facilitate",
    "facilitates",
    "in order to",
    "in the event that",
    "initiate",
    "initiates",
    "numerous",
    "obtain",
    "obtains",
    "originate",
    "prior to",
    "provide",
    "provides",
    "provided",
    "subsequent to",
    "terminate",
    "with regard to",
)
STRICT_BANNED = (
    "however",
    "since",
    "should",
    "shall",
    "using",
    "follow",
    "follows",
    "followed",
)
PHRASAL_VERB = (
    "circle back",
    "dive into",
    "dives into",
    "diving into",
    "drill down",
    "kick off",
    "kicks off",
    "ramp up",
    "reach out",
    "reaching out",
    "roll out",
    "rolls out",
    "spin down",
    "spin up",
    "spun up",
    "tear down",
)

GENERIC_CONCLUSION = (
    "a step in the right direction",
    "as we look ahead",
    "can't wait to see",
    "cannot wait to see",
    "continues to evolve",
    # covers "exciting times ahead" too
    "exciting times",
    "in conclusion",
    "in summary",
    "one thing is clear",
    "only time will tell",
    "stay tuned",
    "the journey ahead",
    "the possibilities are endless",
    "the road ahead",
    "to sum up",
    "to wrap up",
    "watch this space",
)
SIGNIFICANCE_INFLATION = (
    "a pivotal moment",
    "at a crossroads",
    "cements its place",
    "deeply rooted",
    "in the annals of",
    "indelible mark",
    "key turning point",
    "lasting impact",
    "marks a shift",
    "marks a turning point",
    "plays a key role",
    "plays a vital role",
    "plays an important role",
    "reflects a broader",
    "reflects broader",
    "represents a shift",
    "set the stage for",
    "sets the stage for",
    "setting the stage for",
    "solidifies its place",
)

PHRASE_LISTS = {
    "ai_vocabulary": AI_VOCABULARY,
    "promotional": PROMOTIONAL,
    "authority_trope": AUTHORITY_TROPE,
    "aphorism": APHORISM,
    "signposting": SIGNPOSTING,
    "chatbot_residue": CHATBOT_RESIDUE,
    "copula_avoidance": COPULA_AVOIDANCE,
    "vague_attribution": VAGUE_ATTRIBUTION,
    "modal_hedge": MODAL_HEDGE,
    "filler_phrase": FILLER_PHRASE,
    "verbose_word": VERBOSE_WORD,
    "strict_banned_word": STRICT_BANNED,
    "phrasal_verb": PHRASAL_VERB,
    "generic_conclusion": GENERIC_CONCLUSION,
    "significance_inflation": SIGNIFICANCE_INFLATION,
}

# Title case capitalizes the function words that a name never does, so a
# capitalized minor word is the one piece of evidence that does not need a
# lexicon of every product on earth. Compared lowercase.
MINOR_WORDS = (
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "nor",
    "of",
    "off",
    "on",
    "or",
    "out",
    "over",
    "per",
    "than",
    "that",
    "the",
    "to",
    "up",
    "via",
    "vs",
    "with",
)
# A "from X to Y" governed by one of these is a real transformation or a real
# scale, not the AI habit of pairing two things that share no axis.
RANGE_LOOKBACK = 4
# Characters of context read behind a candidate range. Four words never sit
# further back than this, and a fixed window keeps the check linear.
CLAUSE_WINDOW = 200
# A range endpoint is a noun phrase. One of these inside it means the regex ran
# past the end of the phrase and caught a clause.
RANGE_STOP_WORDS = (
    "are",
    "be",
    "been",
    "did",
    "do",
    "does",
    "had",
    "has",
    "have",
    "if",
    "is",
    "not",
    "rather",
    "than",
    "was",
    "were",
    "when",
    "which",
    "while",
)
RANGE_VERBS = (
    "back",
    "backed",
    "bump",
    "bumped",
    "change",
    "changed",
    "changes",
    "clone",
    "cloned",
    "convert",
    "converted",
    "converts",
    "copied",
    "copies",
    "copy",
    "deploy",
    "deployed",
    "deploys",
    "download",
    "downloaded",
    "downgrade",
    "downgraded",
    "export",
    "exported",
    "extract",
    "extracted",
    "fetch",
    "fetched",
    "fetches",
    "go",
    "goes",
    "going",
    "grew",
    "grow",
    "grows",
    "import",
    "imported",
    "increase",
    "increased",
    "inherit",
    "inherits",
    "jump",
    "jumped",
    "migrate",
    "migrated",
    "migrates",
    "migrating",
    "move",
    "moved",
    "moves",
    "moving",
    "port",
    "ported",
    "promote",
    "promoted",
    "publish",
    "published",
    "pull",
    "pulled",
    "push",
    "pushed",
    "range",
    "ranged",
    "ranges",
    "ranging",
    "read",
    "reads",
    "rebase",
    "rebased",
    "rename",
    "renamed",
    "run",
    "runs",
    "scale",
    "scaled",
    "scales",
    "send",
    "sent",
    "step",
    "stepped",
    "switch",
    "switched",
    "switches",
    "sync",
    "synced",
    "transition",
    "transitioned",
    "translate",
    "translated",
    "update",
    "updated",
    "upgrade",
    "upgraded",
    "upgrades",
    "upgrading",
    "upload",
    "uploaded",
    "vary",
    "varies",
    "went",
    "write",
    "writes",
)
FUNC_WORDS = frozenset(
    """a an the this that these those of for to in on at by with from as and or but if
when then than not no is are was were be been being am do does did has have had will would can could
may might must should shall it its their your our his her they we you i""".split()
)

TRANSITIONS = ("additionally", "consequently", "furthermore", "however", "moreover")

# An imperative has no grammatical subject, so the first word is the public
# signal available to a deterministic checker. Keep this list to common
# technical-writing commands. Ambiguous verbs such as "change" still need the
# same 20-word cap when they open a sentence because that is the imperative
# reading in procedures.
INSTRUCTION_VERBS = frozenset(
    """add apply attach build change check choose click close compare configure
connect copy create delete disable download edit enable enter examine export
extract fetch follow get give import install keep load make move open paste
press provide publish pull push read remove rename replace restart restore run
save select send set start stop supply switch test type uninstall update upgrade
upload use validate verify wait write""".split()
)
CONDITION_OPENERS = frozenset("after before if once unless until when whenever while".split())

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

BE = r"(?:am|is|are|was|were|be|been|being)"
PP_IRREG = (
    r"(?:done|made|sent|read|built|kept|held|set|put|run|written|shown|"
    r"given|taken|found|got|gotten|seen|known|thrown|drawn)"
)
# Predicate adjectives. `The field is required` describes a state, not an
# action somebody performed, so it is not the passive the compression layer is
# looking for. The `X is <stative> by Y` shape still scores through
# STATIVE_BY_RE, which is where a real agent shows up.
STATIVE = (
    r"(?:closed|opened?|damaged|completed?|installed|connected|required|"
    r"expected|configured|enabled|disabled|deprecated|supported|allowed|"
    r"needed|defined|undefined|named|set|limited|related|unrelated|"
    r"documented|detailed|dedicated|unchanged)"
)
# Words that end in `ed` without being a participle, so `is indeed` and
# `is agreed` do not both read as passive voice.
NOT_PARTICIPLE = frozenset(
    """indeed need speed seed feed deed breed greed weed embed exceed proceed
succeed hundred sacred wicked naked red bed shed""".split()
)
# `is missing` is a state, not a progressive. These adjectives end in `ing` and
# take a copula the way `is empty` does.
ING_STATE = frozenset(
    """missing existing remaining pending outstanding ongoing willing unwilling
interesting exciting promising surprising confusing misleading encouraging
challenging demanding binding corresponding conflicting matching upcoming
incoming outgoing""".split()
)
# Nouns naming an action somebody performs. A positive list is the only safe
# shape here: `\\w+(tion|ment|ance|ence) of` also matches `an instance of`, `the
# distance of` and `the sentence of`, which name no action at all. A miss costs
# a tell; a stop list of every non-action noun costs a false positive on every
# noun nobody thought of.
NOMINALIZATION_NOUNS = (
    "allocation",
    "approval",
    "cancellation",
    "classification",
    "completion",
    "configuration",
    "confirmation",
    "conversion",
    "creation",
    "deletion",
    "deployment",
    "detection",
    "distribution",
    "enforcement",
    "evaluation",
    "execution",
    "expansion",
    "generation",
    "identification",
    "implementation",
    "initialization",
    "inspection",
    "installation",
    "integration",
    "introduction",
    "invocation",
    "management",
    "migration",
    "modification",
    "normalization",
    "notification",
    "observation",
    "operation",
    "optimization",
    "orchestration",
    "preparation",
    "presentation",
    "prevention",
    "promotion",
    "propagation",
    "publication",
    "reconciliation",
    "reduction",
    "registration",
    "removal",
    "replacement",
    "resolution",
    "restoration",
    "retention",
    "retrieval",
    "selection",
    "separation",
    "simulation",
    "submission",
    "synchronization",
    "transformation",
    "transmission",
    "transition",
    "translation",
    "validation",
    "verification",
)
# A clause opening with one of these is a conditional, and the negation that
# follows it is the condition's consequence rather than an antithesis.
SUBORDINATORS = frozenset(
    """if when unless while because once after before whenever where whereas
although though since until as""".split()
)

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
BACKTICK_FENCE_CANDIDATE_RE = re.compile(r"^[ \t]*`{3,}")
TABLE_ROW_RE = re.compile(r"^\s{0,3}\|")
BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>")
LINK_DEF_RE = re.compile(r"^\s{0,3}\[[^\]\n]+\]:\s*\S+")
TABLE_DELIMITER_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
IDENTIFIER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+|"
    r"[a-z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*)(?![A-Za-z0-9])"
)
IMAGE_RE = re.compile(r"!\[[^\]\n]*\]\([^)\n]*\)")
LINK_RE = re.compile(r"\[([^\]\n]*)\]\([^)\n]*\)")
REF_LINK_RE = re.compile(r"\[([^\]\n]*)\]\[[^\]\n]*\]")
AUTOLINK_RE = re.compile(r"<https?://[^>\s]+>|\bhttps?://\S+")
INLINE_QUOTATION_RE = re.compile(r'(?:"[^"\n]+"|“[^”\n]+”)')

HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.M)
LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s")
INLINE_HEADER_LIST_RE = re.compile(
    r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+\*\*(?P<label>[^*\n]+?)(?::\*\*|\*\*[ \t]*:)"
    r"[ \t]*(?P<value>.*)$",
    re.M,
)
BOLD_RE = re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__")

# An em dash, an en dash used as punctuation, or a spaced double hyphen
# standing in for one. An en dash between two word characters is a range —
# `3–9`, `5.1–5.6`, `L1–L4b` — and the en dash is the correct character there,
# so only a free-standing one scores.
EM_DASH_RE = re.compile("[—―]|(?<!\\w)–(?!\\w)|(?<=\\s)--(?=\\s)")
CURLY_QUOTE_RE = re.compile("[‘’‚‛“”„‟]")
TRANSITION_RE = re.compile(r"(?<![a-z0-9-])(?:" + "|".join(TRANSITIONS) + r")(?![a-z0-9-])", re.I)
PRESS_CONTROL_RE = re.compile(
    r"\bpress\s+(?:(?:the|a|an|this|that)\s+)?(?:[\w-]+\s+){0,2}(?:button|key|control|switch)\b",
    re.I,
)
NON_AMERICAN_SPELLING_RE = re.compile(
    r"\b(?:colours?|coloured|colouring|behaviours?|catalogues?|licence)\b", re.I
)
COPULA_CANDIDATE_RE = re.compile(
    r"\b(?:represents?|marks?)\s+"
    r"(?!(?:(?:a|an|the)\s+)?(?:pivotal moment|shift|(?:key\s+)?turning point)\b)"
    r"(?:a|an|the|[A-Za-z][\w’'-]*)\b",
    re.I,
)
QUALIFIER_PHRASE_RE = re.compile(
    r"\b(?:to be fair|it['’]s also possible|might arguably|in some cases it may|"
    r"this is an inference)\b",
    re.I,
)
# Pictographic ranges only. Arrows, dashes, quotes and ellipses are not emoji,
# and neither are the check and cross marks that carry the data in a support
# matrix: U+2713-U+2718 and the arrow block at U+2B00 are left out on purpose.
EMOJI_RE = re.compile(
    "["
    "⌚⌛⏩-⏳⏸-⏺Ⓜ"
    "▪▫▶◀◻-◾"
    "☀-⛿✀-✒✙-➓⤴⤵⬛⬜⭐⭕"
    "〰〽㊗㊙"
    "\U0001f004\U0001f0cf\U0001f170-\U0001f19a\U0001f1e6-\U0001f1ff"
    "\U0001f201-\U0001f251\U0001f300-\U0001f5ff\U0001f600-\U0001f64f"
    "\U0001f680-\U0001f6ff\U0001f7e0-\U0001f7eb\U0001f900-\U0001f9ff"
    "\U0001fa70-\U0001faff"
    "]"
)

# Every multi-clause pattern is bounded to one paragraph: (?!\n\s*\n) stops the
# match at a blank line so a tell cannot be assembled out of two paragraphs.
PARA = r"(?:(?!\n\s*\n).)"
NOT_JUST_RE = re.compile(
    r"\b(?:it|this|that)(?:'s|’s| is)\s+not\s+(?:just|merely|only|simply)\b"
    + PARA
    + r"{0,300}?\b(?:it|this|that)(?:'s|’s| is)\b",
    re.I | re.S,
)
# The second half of a "not only" is usually "but"; the documented example
# lands it with a bare "it also", which is the same construction.
NOT_ONLY_RE = re.compile(
    r"\bnot only\b" + PARA + r"{0,300}?\b(?:but|(?:it|they|this|that|we)\s+also)\b",
    re.I | re.S,
)
# The antithesis fragment: a finished clause, a comma, then a negated noun
# phrase of two or three words closing the sentence. One word after `no` is a
# list fact (`, no lockfile`), and a second `no` in the same sentence makes it
# an enumeration rather than an antithesis.
TAILING_NEGATION_RE = re.compile(
    r",\s+no\s+(?!longer|more|less|fewer|one|matter|doubt|such)"
    r"(?:[\w'’-]+\s+){1,2}[\w'’-]+\s*(?=[.!?]|$)",
)
BARE_NO_RE = re.compile(r"(?<![\w'’-])no(?![\w'’-])", re.I)
FIRST_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")

RHETORICAL_PUNCTUATED_RE = re.compile(
    r"^(?:honestly|look|frankly|obviously|real talk)\s*[,?!.]", re.I
)
RHETORICAL_OPENER_RE = re.compile(
    r"^(?:here(?:'s|’s) the thing|the thing is|let(?:'s|’s) be honest|truth be told)\b",
    re.I,
)
ING_ANALYSIS_RE = re.compile(r",\s*(?:" + "|".join(ING_ANALYSIS) + r")\b", re.I)
# The shape, not one wording: "the future looks bright" and "the future of the
# platform is bright" are the same send-off.
FUTURE_BRIGHT_RE = re.compile(
    r"\bthe future\s+(?:of\s+(?:[\w'’-]+\s+){0,4})?(?:is|looks|remains|seems)\s+bright\b",
    re.I,
)
COMMITMENT_RE = re.compile(
    r"\bunderscor(?:e|es|ed|ing)\s+(?:our|its|their|the)\s+"
    r"(?:[\w'’-]+\s+){0,2}(?:commitment|dedication)\b",
    re.I,
)
FALSE_RANGE_RE = re.compile(
    r"\bfrom\s+((?:[\w'’-]+\s+){0,7}[\w'’-]+)\s+to\s+"
    r"((?:[\w'’-]+\s+){0,7}[\w'’-]+)",
    re.I,
)
GENERIC_HEADING_RE = re.compile(
    r"^\s{0,3}#{1,6}\s*(?:conclusion|final thoughts|closing thoughts|"
    r"in closing|wrapping up|the road ahead)\s*$",
    re.I | re.M,
)
NOTABILITY_PADDING_RE = re.compile(
    r"\b(?:independent coverage|(?:local|regional|national) media outlets?|"
    r"leading expert|active social media presence)\b",
    re.I,
)
KNOWLEDGE_GAP_RE = re.compile(
    r"\b(?:up to my last (?:training )?update|based on available information|"
    r"not publicly available|maintains? a low profile|keeps? (?:their|his|her) "
    r"personal details private|likely\b|it is believed that)\b",
    re.I,
)
UNSUPPORTED_OBJECTION_RE = re.compile(
    r"\b(?:this (?:isn't|is not) (?:mainly |really )?about|i(?:'m| am) not "
    r"(?:saying|arguing|trying to)|to be clear|don't get me wrong|"
    r"this is not to say|some might say)\b",
    re.I,
)
FAKE_ALTERNATIVE_RE = re.compile(
    r"\b(?:a tempting (?:option|approach) would be|one might be tempted to|"
    r"an obvious approach would be|you might think|it would be easy to just|"
    r"some would suggest)\b",
    re.I,
)
FORMULAIC_SECTION_RE = re.compile(
    r"^\s{0,3}#{1,6}\s*(?:challenges(?: and legacy)?|future outlook|legacy)\s*$",
    re.I | re.M,
)
PREVIOUS_VERSION_RE = re.compile(
    r"\b(?:was added|newly added|previous(?:ly| implementation| approach)|"
    r"former implementation|now (?:uses|supports|returns|reads|writes))\b",
    re.I,
)
PREDICATE_HYPHEN_RE = re.compile(
    rf"\b{BE}\s+[a-z]+-[a-z]+(?:-[a-z]+)*\b",
    re.I,
)
MISSING_SUBJECT_RE = re.compile(
    r"^(?:no|not)\s+[^.!?]{0,80}\b(?:needed|required|available|configured)\b",
    re.I,
)
WATCHED_VOCABULARY_RE = re.compile(
    r"(?<![a-z0-9-])(?:actually|key|valuable|quietly|gate|gated|gating)(?![a-z0-9-])",
    re.I,
)
CASUAL_SIGNPOSTING_RE = re.compile(
    r"\b(?:heads up|quick note|before i forget|one thing that bit me)\b",
    re.I,
)

# `'s` is a possessive far more often than it is a contraction, so the general
# branches cover the endings that only ever contract and the `'s` case is an
# explicit set. Without this, `the skill's own reference` scored a contraction.
CONTRACTION_RE = re.compile(
    r"\b\w+['’](?:t|re|ve|ll|d|m)\b"
    r"|\b(?:it|that|what|let|here|there|he|she|who)['’]s\b",
    re.I,
)
PASSIVE_RE = re.compile(rf"\b{BE}\s+(\w+ed|{PP_IRREG})\b", re.I)
STATIVE_RE = re.compile(STATIVE, re.I)
STATIVE_BY_RE = re.compile(rf"\b{BE}\s+{STATIVE}\s+by\b", re.I)
COMPLEX_TENSE_RE = re.compile(
    rf"\b(?:(?:may|might|could|would|should|must|will|shall|can)\s+)?"
    rf"(?:have|has|had)\s+(?:been\s+)?(?:\w+ed|{PP_IRREG})\b",
    re.I,
)
ING_MAIN_VERB_RE = re.compile(rf"\b{BE}\s+(\w+ing)\b", re.I)
NOMINALIZATION_VERB_RE = re.compile(
    r"\b(?:perform(?:s|ed)?|conduct(?:s|ed)?|carry out|carries out|"
    r"make use of|makes use of)\b",
    re.I,
)
NOMINALIZATION_NOUN_RE = re.compile(r"\b(?:" + "|".join(NOMINALIZATION_NOUNS) + r")s?\s+of\b", re.I)
MAY_RE = re.compile(r"(?<![A-Za-z])may(?![a-z])")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-/]*")
TRAIN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")
RULE_OF_THREE_RE = re.compile(
    r"\b([\w'’-]+(?:\s+[\w'’-]+){0,2}),\s+([\w'’-]+(?:\s+[\w'’-]+){0,2})"
    r",?\s+(?:and|or)\s+([\w'’-]+(?:\s+[\w'’-]+){0,2})\b",
    re.I,
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?:])\s+(?=[A-Z0-9\"'\-])")
# Staccato counts whole sentences only. A colon does not end one, and a
# fragment left behind by a stripped code span is not a punchline.
STACCATO_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
STACCATO_SHAPE_RE = re.compile(r"^[A-Z0-9][^\n]*[.!?]$")
HEADING_PREFIX_RE = re.compile(r"^\s*#{1,6}\s*")
LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")

# Categories that own a shape as well as a word list. They join the same
# single pass, so the longest match still wins across all of them.
PHRASE_PATTERNS = {
    "generic_conclusion": (FUTURE_BRIGHT_RE, GENERIC_HEADING_RE),
    "significance_inflation": (COMMITMENT_RE,),
    "ing_analysis": (ING_ANALYSIS_RE,),
}
# A phrase boundary rejects a trailing hyphen as well as a trailing letter, so
# the STE ban on `follow` does not fire on `Follow-up`.
PHRASE_RES = {
    name: tuple(
        (
            phrase,
            re.compile(r"(?<![a-z0-9-])" + re.escape(phrase.replace("’", "'")) + r"(?![a-z0-9-])"),
        )
        for phrase in phrases
    )
    for name, phrases in PHRASE_LISTS.items()
}


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------


FRONTMATTER_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*\s*:")


def _frontmatter_end(lines: list[str]) -> int:
    """Where the leading frontmatter block ends, or 0 when there is none.

    A leading `---` is only frontmatter when what follows it looks like YAML. A
    document may legally open on a thematic break, and treating that break as
    frontmatter deletes everything down to the next one.
    """
    if not lines or lines[0].strip() not in ("---", "+++"):
        return 0
    marker = lines[0].strip()
    opening = next((line.strip() for line in lines[1:] if line.strip()), "")
    if opening == marker or not FRONTMATTER_KEY_RE.match(opening):
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() == marker:
            return index + 1
    return 0


def _fenced_lines(lines: list[str]) -> set[int]:
    """Line numbers inside a complete fence pair.

    An unterminated fence is a typo, not a code block. Blanking everything
    after it would silently delete the rest of the document from the score.
    """
    inside: set[int] = set()
    index = 0
    while index < len(lines):
        marker = _fence_marker(lines[index])
        if marker is None:
            index += 1
            continue
        for close in range(index + 1, len(lines)):
            candidate = re.fullmatch(r" {0,3}(`{3,}|~{3,})[ \t]*", lines[close])
            if (
                candidate
                and candidate.group(1)[0] == marker[0]
                and len(candidate.group(1)) >= len(marker)
            ):
                inside.update(range(index, close + 1))
                index = close + 1
                break
        else:
            index += 1
    return inside


def _fence_marker(line: str) -> str | None:
    """Return a valid CommonMark fence marker from an opening line."""
    opened = FENCE_RE.match(line)
    if not opened:
        return None
    marker = opened.group(1)
    info = line[opened.end() :]
    if marker[0] == "`" and "`" in info:
        return None
    return marker


def _invalid_backtick_fence(line: str) -> bool:
    return bool(BACKTICK_FENCE_CANDIDATE_RE.match(line) and _fence_marker(line) is None)


def _strip_inline_code(text: str) -> str:
    """Blank code spans whose closing backtick run matches the opener."""
    out: list[str] = []
    cursor = 0
    while cursor < len(text):
        opened = None
        for candidate in re.finditer(r"`+", text[cursor:]):
            start = cursor + candidate.start()
            slash_count = 0
            before = start - 1
            while before >= 0 and text[before] == "\\":
                slash_count += 1
                before -= 1
            if slash_count % 2 == 0:
                opened = candidate
                break
        if opened is None:
            out.append(text[cursor:])
            break
        start = cursor + opened.start()
        marker = opened.group(0)
        out.append(text[cursor:start])
        # Backslashes do not escape a closing code-span delimiter. Only the
        # opening delimiter follows Markdown's odd/even backslash rule.
        close_re = re.compile(r"(?<!`)" + re.escape(marker) + r"(?!`)")
        closed = close_re.search(text, start + len(marker))
        if closed is None:
            out.append(text[start : start + len(marker)])
            cursor = start + len(marker)
            continue
        out.append(" ")
        cursor = closed.end()
    return "".join(out)


def _table_prose(line: str) -> str:
    if TABLE_DELIMITER_RE.match(line):
        return ""
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return ". ".join(cell for cell in cells if cell)


def _has_unescaped_pipe(line: str) -> bool:
    backslashes = 0
    for character in line:
        if character == "|" and backslashes % 2 == 0:
            return True
        backslashes = backslashes + 1 if character == "\\" else 0
    return False


def _gfm_table_lines(lines: list[str]) -> set[int]:
    """Find pipe-table rows from their required delimiter row in one pass."""
    found: set[int] = set()
    index = 1
    while index < len(lines):
        if not (
            TABLE_DELIMITER_RE.fullmatch(lines[index]) and _has_unescaped_pipe(lines[index - 1])
        ):
            index += 1
            continue
        found.update((index - 1, index))
        index += 1
        while index < len(lines) and lines[index].strip() and _has_unescaped_pipe(lines[index]):
            found.add(index)
            index += 1
    return found


def strip_quoted(text: str, quote_safe: bool = False) -> str:
    """Remove every zone that is not the author's own prose.

    Fenced code, inline code, YAML frontmatter, identifiers and link targets are
    not prose. Blockquotes, callouts and table cells can be first-party prose,
    so the default mode keeps their words. Quote-safe mode blanks blockquotes
    because it is the caller's explicit signal that quoted material is not the
    author's voice.
    """
    lines = text.split("\n")
    frontmatter_end = _frontmatter_end(lines)
    fenced = _fenced_lines(lines)
    gfm_table_lines = _gfm_table_lines(lines)
    kept: list[str] = []
    for index, line in enumerate(lines):
        if index < frontmatter_end or index in fenced:
            kept.append("")
            continue
        if LINK_DEF_RE.match(line):
            kept.append("")
            continue
        if index in gfm_table_lines or TABLE_ROW_RE.match(line):
            # A row is one prose unit. The extra newline prevents adjacent
            # rows from becoming one artificial typography cluster.
            kept.append(_table_prose(line) + "\n")
            continue
        if BLOCKQUOTE_RE.match(line):
            if quote_safe:
                kept.append("")
                continue
            unquoted = re.sub(r"^\s{0,3}>\s?", "", line)
            kept.append("" if re.fullmatch(r"\[![A-Za-z]+\]", unquoted.strip()) else unquoted)
            continue
        if _invalid_backtick_fence(line):
            kept.append(line.replace("`", " "))
            continue
        kept.append(line)
    body = "\n".join(kept)
    body = _strip_inline_code(body)
    if quote_safe:
        body = INLINE_QUOTATION_RE.sub(" ", body)
    body = IDENTIFIER_RE.sub(" ", body)
    body = IMAGE_RE.sub(" ", body)
    body = LINK_RE.sub(r"\1", body)
    body = REF_LINK_RE.sub(r"\1", body)
    return AUTOLINK_RE.sub(" ", body)


def _starts_a_unit(line: str) -> bool:
    """A line that opens its own unit and never continues the line above it."""
    return bool(
        HEADING_PREFIX_RE.match(line)
        or LIST_ITEM_RE.match(line)
        or TABLE_ROW_RE.match(line)
        or BLOCKQUOTE_RE.match(line)
        or _fence_marker(line) is not None
    )


def logical_lines(text: str) -> list[str]:
    """Rejoin hard-wrapped prose so a sentence is one string again.

    Markdown wrapped at eighty columns splits most sentences across lines. Read
    line by line, a wrapped paragraph reports as many short sentences: the long
    ones vanish and a two-sentence paragraph counts as seven. Continuation
    lines therefore join the line above, and a blank line, a heading, a list
    item, a table row or a fence starts a new unit. A list item is a unit of
    its own, so it never merges with the paragraph before it.
    """
    out: list[str] = []
    buffer: list[str] = []
    for raw in text.split("\n"):
        stripped = raw.strip()
        if not stripped:
            if buffer:
                out.append(" ".join(buffer))
                buffer = []
            continue
        if _starts_a_unit(stripped):
            if buffer:
                out.append(" ".join(buffer))
            # A stray fence marker left by an unterminated block is punctuation,
            # not the opening of a sentence.
            buffer = [] if _fence_marker(stripped) is not None else [stripped]
            continue
        buffer.append(stripped)
    if buffer:
        out.append(" ".join(buffer))
    return out


def sentences(text: str) -> list[str]:
    out: list[str] = []
    for line in logical_lines(text):
        stripped = HEADING_PREFIX_RE.sub("", line)
        stripped = LIST_PREFIX_RE.sub("", stripped)
        if not WORD_RE.search(stripped):
            continue
        for part in SENTENCE_SPLIT_RE.split(stripped):
            part = part.strip()
            if part:
                out.append(part)
    return out


def paragraphs(text: str) -> list[str]:
    return [block for block in re.split(r"\n\s*\n", text) if block.strip()]


def prose_lines(block: str) -> list[str]:
    """Lines that are running prose: no headings, list items or table leftovers."""
    out: list[str] = []
    for line in block.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "|", ">")):
            continue
        if LIST_ITEM_RE.match(stripped):
            continue
        out.append(stripped)
    return out


def word_count(sentence: str) -> int:
    return len(WORD_RE.findall(sentence))


def is_instruction(sentence: str) -> bool:
    """Return whether a sentence has the deterministic imperative shape."""
    words = WORD_RE.findall(sentence)
    lowered = [word.lower() for word in words]
    if not lowered:
        return False

    def command_at(sequence: list[str], index: int) -> bool:
        while index < len(sequence) and (
            sequence[index].endswith("ly") or sequence[index] in {"always", "never"}
        ):
            index += 1
        return index < len(sequence) and sequence[index] in INSTRUCTION_VERBS

    if command_at(lowered, 0):
        return True
    # A declarative requirement remains an instruction when an adverb or a
    # passive construction separates `must` from the functional verb.
    if "must" in lowered:
        return True
    if lowered[0] not in CONDITION_OPENERS:
        return False
    if "," in sentence:
        command = [word.lower() for word in WORD_RE.findall(sentence.split(",", 1)[1])]
        return command_at(command, 0)
    condition_predicates = {
        "change",
        "changes",
        "complete",
        "completed",
        "completes",
        "differ",
        "differs",
        "exist",
        "exists",
        "fail",
        "failed",
        "fails",
        "finish",
        "finished",
        "finishes",
        "match",
        "matches",
        "occur",
        "occurs",
        "pass",
        "passed",
        "passes",
        "return",
        "returns",
        "start",
        "starts",
        "stop",
        "stops",
        "succeed",
        "succeeded",
        "succeeds",
    }
    condition_states = {
        "available",
        "complete",
        "empty",
        "invalid",
        "missing",
        "present",
        "ready",
        "successful",
        "unavailable",
        "valid",
    }
    for index, word in enumerate(lowered[1:], start=1):
        if word in condition_predicates and command_at(lowered, index + 1):
            return True
        if word in {"do", "does", "did", "has", "have", "had"}:
            predicate = index + 1
            if predicate < len(lowered) and lowered[predicate] == "not":
                predicate += 1
            if (
                predicate < len(lowered)
                and lowered[predicate] in condition_predicates
                and command_at(lowered, predicate + 1)
            ):
                return True
        if word in {"am", "is", "are", "was", "were", "be", "been"}:
            state = index + 1
            while state < len(lowered) and (
                lowered[state] in {"not", "no", "longer"} or lowered[state].endswith("ly")
            ):
                state += 1
            if (
                state < len(lowered)
                and lowered[state] in condition_states
                and command_at(lowered, state + 1)
            ):
                return True
    return False


def _normalize(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'")


def _folded(text: str) -> str:
    """Lowercase without moving any offset, so a span means the same in both."""
    lowered = _normalize(text).lower()
    if len(lowered) == len(text):
        return lowered
    return "".join(
        character.lower() if len(character.lower()) == 1 else character
        for character in _normalize(text)
    )


def _provided_is_a_verb(text: str, start: int, end: int) -> bool:
    """`Provided the token is valid` is a conjunction, not a verbose verb."""
    before = text[:start].rstrip(" \t")
    if not before or before[-1] in ".!?;:\n":
        return False
    return not text[end:].lstrip(" \t").lower().startswith("that ")


PHRASE_FILTERS = {"provided": _provided_is_a_verb}


def phrase_hits(text: str) -> dict[str, list[str]]:
    """Score every phrase list and phrase shape in one pass, longest match first.

    A span belongs to one category. Matching each list on its own let
    `utilization of` score vocabulary and nominalization, and
    `marks a pivotal moment` score inflation and vocabulary, so the same words
    counted twice. Sorting the candidates by position and keeping the longest
    non-overlapping match gives every span exactly one owner.
    """
    lowered = _folded(text)
    candidates: list[tuple[int, int, str, str]] = []
    for name, compiled in PHRASE_RES.items():
        for phrase, pattern in compiled:
            allowed = PHRASE_FILTERS.get(phrase)
            for match in pattern.finditer(lowered):
                if allowed and not allowed(lowered, match.start(), match.end()):
                    continue
                candidates.append((match.start(), match.end(), name, phrase))
    for name, patterns in PHRASE_PATTERNS.items():
        for pattern in patterns:
            for match in pattern.finditer(text):
                sample = " ".join(match.group(0).split())
                candidates.append((match.start(), match.end(), name, sample))

    hits: dict[str, list[str]] = {name: [] for name in PHRASE_RES}
    for name in PHRASE_PATTERNS:
        hits.setdefault(name, [])
    last_end = -1
    for start, end, name, sample in sorted(candidates, key=lambda item: (item[0], -item[1])):
        if start < last_end:
            continue
        last_end = end
        hits[name].append(sample)
    return hits


def _hits(pattern: "re.Pattern[str]", text: str) -> tuple[int, list[str]]:
    found = [match.group(0).strip() for match in pattern.finditer(text)]
    return len(found), found


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------


def title_case_headings(text: str) -> tuple[int, list[str]]:
    """Count headings written in Title Case, on the one piece of hard evidence.

    A heading of capitalized words is either Title Case or a name, and no list
    of proper nouns can tell them apart: `Amazon Elastic Kubernetes Service` and
    `Red Hat Advanced Cluster Security` are products, and the product namespace
    has no end. Title Case has one habit a name never has, which is
    capitalizing the function words, so a capitalized `And`, `On` or `Of` is
    the evidence and nothing else is. This trades recall for precision on
    purpose: heading case is a house style, not an AI tell, and a markdown
    linter is the better place to enforce it.
    """
    hits: list[str] = []
    for match in HEADING_RE.finditer(text):
        heading = re.sub(r"[*_`]", "", match.group(1)).strip()
        words = TRAIN_WORD_RE.findall(heading)
        if len(words) < 3:
            continue
        rest = words[1:]
        if any(word[0].islower() and word.lower() not in MINOR_WORDS for word in rest):
            continue
        if not any(word[0].isupper() and word.lower() in MINOR_WORDS for word in rest):
            continue
        loud = [
            word
            for word in rest
            if word[0].isupper() and not word.isupper() and word.lower() not in MINOR_WORDS
        ]
        if len(loud) >= 2:
            hits.append(heading)
    return len(hits), hits


def inline_header_lists(text: str) -> tuple[int, list[str]]:
    """Count bolded list labels followed by a sentence that restates the label.

    A bolded label carrying a datum is a definition list and is good structure:
    ``- **Milestone:** 2026-03-01``. A bolded label carrying a sentence that says
    the label again is the padding tell: ``- **Performance:** Performance has
    been enhanced.`` The difference is the value, so the value decides.
    """
    hits: list[str] = []
    for match in INLINE_HEADER_LIST_RE.finditer(text):
        label = re.sub(r"[*_`]", "", match.group("label")).strip()
        value = re.sub(r"[*_`]", "", match.group("value")).strip()
        words = TRAIN_WORD_RE.findall(value)
        if len(words) < 4 or not value.endswith((".", "!", "?")):
            continue
        lowered = value.lower()
        echo = [word for word in TRAIN_WORD_RE.findall(label) if len(word) >= 4]
        if echo and any(word.lower() in lowered for word in echo):
            hits.append(f"{label}: {value}"[:80])
    return len(hits), hits


def tailing_negations(text: str) -> list[str]:
    """The negation fragment tacked onto a finished clause.

    `The overlay reads the version from `package.json`, no manual bumps.` is
    the tell. A conditional (`If validation fails, no installation operation
    runs.`), a one-word list fact (`, no lockfile`), a run of them (`no
    imports, no host layout probing`) and any list item are not: they state
    what is there, or absent, rather than defining a thing by what it is not.
    """
    hits: list[str] = []
    for line in logical_lines(text):
        if _starts_a_unit(line):
            continue
        for sentence in SENTENCE_SPLIT_RE.split(line):
            opener = FIRST_WORD_RE.match(sentence.strip())
            if opener and opener.group(0).lower() in SUBORDINATORS:
                continue
            if len(BARE_NO_RE.findall(sentence)) != 1:
                continue
            match = TAILING_NEGATION_RE.search(sentence)
            if match:
                hits.append(" ".join(match.group(0).split()))
    return hits


def negative_parallelisms(text: str) -> tuple[int, list[str]]:
    hits: list[str] = []
    for pattern in (NOT_JUST_RE, NOT_ONLY_RE):
        hits.extend(" ".join(match.group(0).split()) for match in pattern.finditer(text))
    hits.extend(tailing_negations(text))
    return len(hits), hits


def em_dashes(text: str) -> tuple[int, list[str]]:
    hits = [
        match.group(0)
        for match in EM_DASH_RE.finditer(text)
        if match.group(0) != "--" or _double_hyphen_is_a_dash(text, match.end())
    ]
    return len(hits), hits


def _double_hyphen_is_a_dash(text: str, end: int) -> bool:
    """A spaced `--` is a dash unless it is the POSIX end-of-options marker.

    `npm test -- --watch` and `git log -- src/` both put a flag or a path after
    it. A dash standing in for punctuation is followed by a word.
    """
    rest = text[end:].split()
    if not rest:
        return False
    word = rest[0]
    return not word.startswith("-") and not any(character in word for character in "/\\=")


def rhetorical_openers(found: list[str]) -> tuple[int, list[str]]:
    hits = [
        sentence
        for sentence in found
        if RHETORICAL_PUNCTUATED_RE.match(sentence) or RHETORICAL_OPENER_RE.match(sentence)
    ]
    return len(hits), hits


def false_ranges(text: str) -> tuple[int, list[str]]:
    hits: list[str] = []
    for match in FALSE_RANGE_RE.finditer(text):
        left, right = match.group(1).strip(), match.group(2).strip()
        if any(character.isdigit() for character in left + right):
            continue
        if len(left.split()) < 2 or len(right.split()) < 2:
            continue
        sides = {word.lower() for word in (left + " " + right).split()}
        if sides & set(RANGE_STOP_WORDS):
            continue
        # Only the few words before the match decide, so read a fixed window
        # instead of re-splitting the whole document per candidate. On a large
        # file the old prefix split turned this check quadratic.
        window = text[max(0, match.start() - CLAUSE_WINDOW) : match.start()]
        clause = re.split(r"[.!?;:]", window)[-1].split()
        lead = [re.sub(r"[^A-Za-z]", "", word).lower() for word in clause[-RANGE_LOOKBACK:]]
        if any(word in RANGE_VERBS for word in lead):
            continue
        hits.append(f"from {left} to {right}")
    return len(hits), hits


def passive_voices(text: str) -> tuple[int, list[str]]:
    """Passive voice, minus the spans another category already owns.

    `has been deployed` is one verb phrase. It scored `complex_tense` for the
    perfect and `passive_voice` for the participle, so a single edit had to
    remove two violations. The compound tense keeps it.
    """
    claimed = [(match.start(), match.end()) for match in COMPLEX_TENSE_RE.finditer(text)]

    def unclaimed(matches: list["re.Match[str]"]) -> list["re.Match[str]"]:
        kept: list["re.Match[str]"] = []
        claimed_index = 0
        for match in matches:
            while claimed_index < len(claimed) and claimed[claimed_index][1] <= match.start():
                claimed_index += 1
            overlaps = (
                claimed_index < len(claimed)
                and claimed[claimed_index][0] < match.end()
                and claimed[claimed_index][1] > match.start()
            )
            if not overlaps:
                kept.append(match)
        return kept

    candidates = [
        match
        for match in PASSIVE_RE.finditer(text)
        if match.group(1).lower() not in NOT_PARTICIPLE and not STATIVE_RE.fullmatch(match.group(1))
    ]
    hits = [match.group(0) for match in unclaimed(candidates)]
    hits.extend(match.group(0) for match in unclaimed(list(STATIVE_BY_RE.finditer(text))))
    return len(hits), hits


def ing_main_verbs(text: str) -> tuple[int, list[str]]:
    hits = [
        match.group(0)
        for match in ING_MAIN_VERB_RE.finditer(text)
        if match.group(1).lower() not in ING_STATE
    ]
    return len(hits), hits


def curly_quotes(text: str) -> tuple[int, list[str]]:
    """Curly quotes, minus the apostrophes a contraction already scored.

    One `’` in `doesn’t` is one defect, not a curly quote plus a contraction.
    A possessive apostrophe is no longer a contraction, so it still scores here.
    """
    claimed: set[int] = set()
    for match in CONTRACTION_RE.finditer(text):
        claimed.update(range(match.start(), match.end()))
    hits = [
        match.group(0) for match in CURLY_QUOTE_RE.finditer(text) if match.start() not in claimed
    ]
    return len(hits), hits


def clustered_tell(
    current: tuple[int, list[str]],
    sample: tuple[int, list[str]] | None,
    target_words: int,
    sample_words: int,
    singleton_allowance: int = 1,
) -> tuple[int, list[str]]:
    """Count style evidence only above a singleton or a supplied voice rate."""
    count, hits = current
    allowance = singleton_allowance
    if sample is not None:
        allowance = max(
            singleton_allowance,
            math.ceil(sample[0] * target_words / max(sample_words, 1)),
        )
    excess = max(0, count - allowance)
    return excess, hits[allowance : allowance + excess]


def local_clustered_tell(
    body: str,
    detector: Callable[[str], tuple[int, list[str]]],
    voice_body: str | None,
    singleton_allowance: int = 1,
) -> tuple[tuple[int, list[str]], tuple[int, list[str]]]:
    """Separate local clusters from isolated style markers.

    A repeated tell is evidence only within one paragraph. Two isolated uses in
    distant paragraphs remain two markers instead of becoming one violation.
    A supplied voice sample governs the allowed rate in each target paragraph.
    """
    sample = detector(voice_body) if voice_body is not None else None
    sample_words = sum(word_count(sentence) for sentence in sentences(voice_body or "")) or 1
    target_words = sum(word_count(sentence) for sentence in sentences(body)) or 1
    violation_hits: list[str] = []
    isolated_hits: list[str] = []
    sample_allowance_used = 0
    for block in logical_lines(body):
        current = detector(block)
        block_words = sum(word_count(sentence) for sentence in sentences(block)) or 1
        violation = clustered_tell(
            current,
            sample,
            block_words,
            sample_words,
            singleton_allowance,
        )
        violation_hits.extend(violation[1])
        if violation[0]:
            sample_allowance_used += current[0] - violation[0]
        else:
            isolated_hits.extend(current[1])
    marker_allowance = 0
    if sample is not None and sample[0] > 0:
        total_allowance = math.ceil(sample[0] * target_words / sample_words)
        marker_allowance = max(0, total_allowance - sample_allowance_used)
    marker_hits = isolated_hits[marker_allowance:]
    return (len(violation_hits), violation_hits), (len(marker_hits), marker_hits)


def staccato_runs(blocks: list[str]) -> tuple[int, list[str]]:
    hits: list[str] = []
    for block in blocks:
        text = " ".join(prose_lines(block))
        run: list[str] = []
        for sentence in STACCATO_SPLIT_RE.split(text) + [""]:
            sentence = sentence.strip()
            short = 2 <= word_count(sentence) <= STACCATO_MAX_WORDS
            if sentence and short and STACCATO_SHAPE_RE.match(sentence):
                run.append(sentence)
                continue
            if len(run) >= STACCATO_RUN:
                hits.append(" ".join(run))
            run = []
    return len(hits), hits


def boldface_clusters(
    blocks: list[str],
) -> tuple[tuple[int, list[str]], tuple[int, list[str]]]:
    violation_hits: list[str] = []
    marker_hits: list[str] = []
    for block in blocks:
        if HEADING_PREFIX_RE.match(block):
            continue
        spans = BOLD_RE.findall(LIST_PREFIX_RE.sub("", block))
        if len(spans) > BOLD_PER_PARAGRAPH:
            violation_hits.extend(spans[BOLD_PER_PARAGRAPH:])
        elif spans:
            marker_hits.extend(spans)
    return (len(violation_hits), violation_hits), (len(marker_hits), marker_hits)


def long_paragraphs(blocks: list[str]) -> tuple[int, list[str]]:
    hits: list[str] = []
    for block in blocks:
        found = sentences("\n".join(prose_lines(block)))
        if len(found) > LONG_PARAGRAPH_SENTENCES:
            hits.append(found[0])
    return len(hits), hits


def noun_trains(text: str) -> tuple[int, list[str]]:
    hits: list[str] = []
    for sentence in sentences(text):
        run: list[str] = []
        for word in TRAIN_WORD_RE.findall(sentence)[1:] + [""]:
            if word and word.lower() not in FUNC_WORDS and not word[0].isupper():
                run.append(word)
                continue
            if len(run) >= NOUN_TRAIN_MIN:
                hits.append(" ".join(run))
            run = []
    return len(hits), hits


def rule_of_three(text: str) -> tuple[int, list[str]]:
    hits = [" ".join(match.group(0).split()) for match in RULE_OF_THREE_RE.finditer(text)]
    return len(hits), hits


def repeated_openings(found: list[str]) -> tuple[int, list[str]]:
    hits: list[str] = []
    run: list[str] = []
    opening = ""
    for sentence in found + [""]:
        match = FIRST_WORD_RE.match(sentence.strip())
        current = match.group(0).lower() if match else ""
        if current and current == opening:
            run.append(sentence)
            continue
        if len(run) >= 3:
            hits.append(" ".join(run))
        run = [sentence] if current else []
        opening = current
    return len(hits), hits


def heading_restatements(text: str) -> tuple[int, list[str]]:
    """Mark close lexical repeats between a heading and its first sentence."""
    hits: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        if not heading:
            continue
        heading_words = {word.lower() for word in WORD_RE.findall(heading.group(1))}
        for candidate_index in range(index + 1, len(lines)):
            candidate = lines[candidate_index].strip()
            if not candidate:
                continue
            if _starts_a_unit(candidate):
                break
            sentence_words = {word.lower() for word in WORD_RE.findall(candidate)}
            if heading_words and heading_words <= sentence_words and len(sentence_words) <= 8:
                hits.append(candidate)
            break
    return len(hits), hits


def marker_scores(
    body: str,
    phrase_body: str,
    found: list[str],
    register: str,
    singleton_markers: dict[str, tuple[int, list[str]]],
) -> dict[str, tuple[int, list[str]]]:
    phrase_markers = {
        "notability_padding": _hits(NOTABILITY_PADDING_RE, phrase_body),
        "knowledge_gap": _hits(KNOWLEDGE_GAP_RE, phrase_body),
        "unsupported_objection": _hits(UNSUPPORTED_OBJECTION_RE, phrase_body),
        "fake_alternative": _hits(FAKE_ALTERNATIVE_RE, phrase_body),
        "watched_vocabulary": _hits(WATCHED_VOCABULARY_RE, phrase_body),
        "casual_signposting": _hits(CASUAL_SIGNPOSTING_RE, phrase_body),
    }
    missing = [sentence for sentence in found if MISSING_SUBJECT_RE.match(sentence)]
    misplaced_conditions = []
    for sentence in found:
        words = WORD_RE.findall(sentence)
        if (
            words
            and words[0].lower() in INSTRUCTION_VERBS - {"check"}
            and re.search(r"\b(?:if|when|unless|until)\b", sentence, re.I)
        ):
            misplaced_conditions.append(sentence)

    return {
        **singleton_markers,
        "american_spelling": (
            (0, []) if register == "voiced" else _hits(NON_AMERICAN_SPELLING_RE, phrase_body)
        ),
        "condition_before_command": (
            (0, []) if register == "voiced" else (len(misplaced_conditions), misplaced_conditions)
        ),
        "copula_candidate": _hits(COPULA_CANDIDATE_RE, phrase_body),
        "qualifier_phrase": _hits(QUALIFIER_PHRASE_RE, phrase_body),
        "noun_train": noun_trains(body),
        "rule_of_three": rule_of_three(body),
        **phrase_markers,
        "formulaic_section": _hits(FORMULAIC_SECTION_RE, body),
        "previous_version_frame": _hits(PREVIOUS_VERSION_RE, body),
        "repeated_opening": repeated_openings(found),
        "predicate_hyphenation": _hits(PREDICATE_HYPHEN_RE, body),
        "heading_restatement": heading_restatements(body),
        "missing_subject": (len(missing), missing),
    }


def _phrase(phrases: dict[str, list[str]], name: str) -> tuple[int, list[str]]:
    hits = phrases[name]
    return len(hits), hits


def _mechanical_scores(
    body: str,
    found: list[str],
    phrases: dict[str, list[str]],
    voice_body: str | None,
) -> tuple[
    dict[str, tuple[int, list[str]]],
    dict[str, tuple[int, list[str]]],
]:
    em_dash = local_clustered_tell(body, em_dashes, voice_body)
    transition = local_clustered_tell(
        body,
        lambda text: _hits(TRANSITION_RE, text),
        voice_body,
    )
    curly_quote = local_clustered_tell(body, curly_quotes, voice_body, 2)
    bold = boldface_clusters(logical_lines(body))
    scores = {
        "em_dash": em_dash[0],
        "transition_stack": transition[0],
        "chatbot_residue": _phrase(phrases, "chatbot_residue"),
        "copula_avoidance": _phrase(phrases, "copula_avoidance"),
        "negative_parallelism": negative_parallelisms(body),
        "emoji": _hits(EMOJI_RE, body),
        "curly_quote": curly_quote[0],
        "title_case_heading": title_case_headings(body),
        "inline_header_list": inline_header_lists(body),
        "boldface_overuse": bold[0],
        "ai_vocabulary": _phrase(phrases, "ai_vocabulary"),
        "promotional": _phrase(phrases, "promotional"),
        "authority_trope": _phrase(phrases, "authority_trope"),
        "aphorism": _phrase(phrases, "aphorism"),
        "signposting": _phrase(phrases, "signposting"),
        "rhetorical_opener": rhetorical_openers(found),
        "ing_analysis": _phrase(phrases, "ing_analysis"),
        "false_range": false_ranges(body),
        "vague_attribution": _phrase(phrases, "vague_attribution"),
        "modal_hedge": _phrase(phrases, "modal_hedge"),
        "filler_phrase": _phrase(phrases, "filler_phrase"),
        "generic_conclusion": _phrase(phrases, "generic_conclusion"),
        "significance_inflation": _phrase(phrases, "significance_inflation"),
    }
    singleton_markers = {
        "singleton_em_dash": em_dash[1],
        "singleton_curly_quote": curly_quote[1],
        "singleton_transition": transition[1],
        "singleton_bold": bold[1],
    }
    return scores, singleton_markers


def _compression_scores(
    body: str, found: list[str], blocks: list[str], phrases: dict[str, list[str]]
) -> dict[str, tuple[int, list[str]]]:
    longs = [
        sentence
        for sentence in found
        if word_count(sentence)
        > (INSTRUCTION_MAX_WORDS if is_instruction(sentence) else DESCRIPTIVE_MAX_WORDS)
    ]
    strict_count, strict_hits = _phrase(phrases, "strict_banned_word")
    press_count, press_hits = _hits(PRESS_CONTROL_RE, body)
    strict_count += press_count
    strict_hits.extend(press_hits)
    may_count, may_hits = _hits(MAY_RE, body)
    nominal_count, nominal_hits = _hits(NOMINALIZATION_VERB_RE, body)
    noun_count, noun_hits = _hits(NOMINALIZATION_NOUN_RE, body)
    return {
        "long_sentence": (len(longs), longs),
        "semicolon": (body.count(";"), [";"] * body.count(";")),
        "contraction": _hits(CONTRACTION_RE, body),
        "passive_voice": passive_voices(body),
        "complex_tense": _hits(COMPLEX_TENSE_RE, body),
        "ing_main_verb": ing_main_verbs(body),
        "nominalization": (nominal_count + noun_count, nominal_hits + noun_hits),
        "phrasal_verb": _phrase(phrases, "phrasal_verb"),
        "verbose_word": _phrase(phrases, "verbose_word"),
        "long_paragraph": long_paragraphs(blocks),
        "strict_banned_word": (strict_count + may_count, strict_hits + may_hits),
    }


def _voice_scores(blocks: list[str]) -> dict[str, tuple[int, list[str]]]:
    return {
        "staccato_drama": staccato_runs(blocks),
    }


def _sample(hits: list[str]) -> list[str]:
    cleaned = [" ".join(hit.split()) for hit in hits if hit.strip()]
    return list(dict.fromkeys(cleaned))[:SAMPLE_LIMIT]


def lint(
    text: str,
    register: str = DEFAULT_REGISTER,
    quote_safe: bool = False,
    voice_sample: str | None = None,
) -> dict[str, Any]:
    if register not in REGISTERS:
        raise ValueError(f"unknown register: {register!r}")
    body = strip_quoted(text, quote_safe=quote_safe)
    phrase_body = body
    found = sentences(body)
    blocks = paragraphs(body)
    words = sum(word_count(sentence) for sentence in found) or 1

    phrases = phrase_hits(phrase_body)
    scored: dict[str, tuple[int, list[str]]] = {}
    voice_body = (
        strip_quoted(voice_sample, quote_safe=quote_safe)
        if voice_sample is not None and register == "voiced"
        else None
    )
    mechanical_scores, singleton_markers = _mechanical_scores(body, found, phrases, voice_body)
    scored.update(mechanical_scores)
    scored.update(_compression_scores(body, found, blocks, phrases))
    scored.update(_voice_scores(blocks))

    violations: dict[str, int] = {}
    by_layer = {"mechanical": 0, "compression": 0, "voice": 0}
    samples: dict[str, list[str]] = {}
    for layer in ("mechanical", "compression", "voice"):
        if layer not in REGISTER_LAYERS[register]:
            continue
        for name in LAYERS[layer]:
            # audit reports the strict word set too. It cannot know whether the
            # document is a procedure, and an audit that hides the one word set
            # procedures exist to enforce is worse than a review that overreports:
            # nothing here is applied, and the reader filters by document type.
            if name in STRICT_ONLY and register not in ("strict", "audit"):
                continue
            count, hits = scored[name]
            violations[name] = count
            by_layer[layer] += count
            if hits:
                samples[name] = _sample(hits)

    marker_results = marker_scores(body, phrase_body, found, register, singleton_markers)
    markers: dict[str, int] = {}
    for name in MARKERS:
        count, hits = marker_results[name]
        markers[name] = count
        if hits:
            samples[name] = _sample(hits)

    total = sum(violations.values())
    per100 = round(total * 100.0 / words, 2)
    return {
        "score_version": SCORE_VERSION,
        "register": register,
        "quote_safe": quote_safe,
        "voice_sample": voice_sample is not None and register == "voiced",
        "voice_sample_identity": (
            hashlib.sha256(voice_sample.encode("utf-8")).hexdigest()
            if voice_sample is not None and register == "voiced"
            else None
        ),
        "words": words,
        "sentences": len(found),
        "violations": violations,
        "by_layer": by_layer,
        "total": total,
        "total_per100w": per100,
        "longest_sentence_words": max((word_count(s) for s in found), default=0),
        "markers": markers,
        "manual_checks": list(MANUAL_CHECKS),
        "samples": samples,
        "delta": None,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _finite_non_negative(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError("must be a finite non-negative number")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lint.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Score prose for AI tells and Simplified Technical English discipline.\n"
            "Registers: strict for procedures and error messages, flavored for "
            "docs and PR bodies, voiced for bylined prose, and audit to report "
            "without rewriting. Thresholds exist only when --fail-over is set."
        ),
        epilog=(
            "usage example: python3 lint.py --json --register strict RUNBOOK.md\n"
            "exit codes: 0 clean, 1 over --fail-over, 2 a path or baseline could "
            "not be read (every other path is still scored and reported)."
        ),
    )
    parser.add_argument("paths", nargs="*", help="Files to lint. Reads stdin when omitted.")
    parser.add_argument(
        "--register",
        choices=REGISTERS,
        default=None,
        help=f"Which layers to score. Default {DEFAULT_REGISTER}.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Deprecated alias for --register strict.",
    )
    parser.add_argument(
        "--quote-safe",
        action="store_true",
        help="Suppress word-list categories so a glossary does not score the words it names.",
    )
    parser.add_argument(
        "--voice-sample",
        metavar="FILE",
        help="Match typography and transition rates from this sample in the voiced register.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the full JSON report.")
    parser.add_argument(
        "--fail-over",
        type=_finite_non_negative,
        metavar="N",
        help="Exit 1 when the worst total_per100w is greater than N.",
    )
    parser.add_argument(
        "--baseline",
        metavar="FILE",
        help="A JSON report from an earlier run. Adds a delta object to the output.",
    )
    return parser


def _resolve_register(args: argparse.Namespace) -> str:
    if args.register:
        return args.register
    if args.strict:
        return "strict"
    return DEFAULT_REGISTER


class BaselineError(ValueError):
    """A readable baseline that cannot be compared to this run."""

    def __init__(self, kind: str, detail: str):
        super().__init__(detail)
        self.kind = kind


def _file_identity(name: str) -> str:
    return os.path.normcase(str(Path(name).resolve(strict=False)))


def _baseline_scores(
    path: str, register: str, quote_safe: bool, voice_sample_identity: str | None
) -> tuple[dict[str, float], float | None]:
    """Load compatible baseline scores keyed by normalized path identity."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    reports = data if isinstance(data, list) else [data]
    if not reports or any(not isinstance(report, dict) for report in reports):
        raise BaselineError("incompatible", "expected one report or a list of reports")
    by_file: dict[str, float] = {}
    anonymous_scores: list[float] = []
    for report in reports:
        required = {
            "score_version",
            "register",
            "quote_safe",
            "voice_sample_identity",
            "total_per100w",
        }
        missing = sorted(required - report.keys())
        if missing:
            raise BaselineError("incompatible", f"missing {', '.join(missing)}")
        if report["score_version"] != SCORE_VERSION:
            raise BaselineError(
                "incompatible",
                f"score_version {report['score_version']!r} != {SCORE_VERSION}",
            )
        if report["register"] != register:
            raise BaselineError("incompatible", f"register {report['register']!r} != {register!r}")
        if report["quote_safe"] is not quote_safe:
            raise BaselineError(
                "incompatible",
                f"quote_safe {report['quote_safe']!r} != {quote_safe!r}",
            )
        if report["voice_sample_identity"] != voice_sample_identity:
            raise BaselineError("incompatible", "voice sample content or policy differs")
        try:
            score = float(report["total_per100w"])
        except (TypeError, ValueError) as error:
            raise BaselineError("incompatible", "total_per100w is not numeric") from error
        if not math.isfinite(score) or score < 0:
            raise BaselineError(
                "incompatible",
                "total_per100w must be finite and non-negative",
            )
        name = report.get("file")
        if name:
            identity = report.get("file_identity")
            if not isinstance(identity, str) or not Path(identity).is_absolute():
                raise BaselineError("incompatible", "missing canonical file_identity")
            identity = os.path.normcase(os.path.normpath(identity))
            if identity in by_file:
                raise BaselineError("ambiguous", f"duplicate file identity {identity!r}")
            by_file[identity] = score
        else:
            anonymous_scores.append(score)
    if len(anonymous_scores) > 1 or (anonymous_scores and by_file):
        raise BaselineError("ambiguous", "anonymous report cannot be mixed or repeated")
    return by_file, anonymous_scores[0] if anonymous_scores else None


def _attach_deltas(
    reports: list[dict[str, Any]],
    by_file: dict[str, float],
    anonymous: float | None,
) -> None:
    named = [report for report in reports if report.get("file") is not None]
    if named:
        identities = [report.get("file_identity") for report in named]
        if any(not isinstance(identity, str) for identity in identities):
            raise BaselineError("incompatible", "current report lacks file_identity")
        identities = [os.path.normcase(os.path.normpath(identity)) for identity in identities]
        if len(identities) != len(set(identities)):
            raise BaselineError("ambiguous", "current run repeats a file identity")
        if anonymous is not None or set(identities) != set(by_file):
            raise BaselineError("mismatch", "current and baseline file identities differ")
        for report, identity in zip(named, identities):
            before = by_file[identity]
            after = report["total_per100w"]
            report["delta"] = {"before": before, "after": after, "improved": after < before}
        return
    if len(reports) != 1 or anonymous is None or by_file:
        raise BaselineError("mismatch", "stdin requires one anonymous baseline report")
    after = reports[0]["total_per100w"]
    reports[0]["delta"] = {
        "before": anonymous,
        "after": after,
        "improved": after < anonymous,
    }


def _read_stdin() -> str:
    if hasattr(sys.stdin, "reconfigure"):
        # Without this the platform default decodes the pipe, so an em dash
        # piped in scores zero while the same bytes in a file score two.
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    return sys.stdin.read()


def _read_file(path: Path) -> str:
    """Read one file the way stdin is read: UTF-8, replacing what will not decode.

    A file that is not UTF-8 is still prose worth scoring, so a stray byte
    becomes a replacement character instead of a traceback. A file carrying NUL
    is not prose at all, and scoring a PNG as English helps nobody.
    """
    data = path.read_bytes()
    if b"\x00" in data:
        raise ValueError("binary file")
    return data.decode("utf-8", errors="replace")


def _failure(path: str, error: Exception) -> dict[str, Any]:
    return {"file": path, "error": f"{type(error).__name__}: {error}"}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    register = _resolve_register(args)
    if hasattr(sys.stdout, "reconfigure"):
        # Without this a sample carrying an em dash cannot be printed on a
        # console whose default encoding is not UTF-8, and the whole run dies
        # on the write rather than on anything about the prose.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    reports: list[dict[str, Any]] = []
    failed = False
    voice_sample: str | None = None
    if args.voice_sample:
        try:
            voice_sample = _read_file(Path(args.voice_sample))
        except (OSError, ValueError, UnicodeDecodeError) as error:
            print(f"voice sample unreadable: {type(error).__name__}: {error}", file=sys.stderr)
            failed = True
    if args.paths:
        for raw_path in args.paths:
            path = Path(raw_path)
            try:
                text = _read_file(path)
            except (OSError, ValueError, UnicodeDecodeError) as error:
                # One unreadable path must not discard the reports already
                # computed for the paths that were fine.
                reports.append(_failure(str(path), error))
                failed = True
                continue
            report = lint(
                text,
                register=register,
                quote_safe=args.quote_safe,
                voice_sample=voice_sample,
            )
            if args.voice_sample and register == "voiced":
                report["voice_sample"] = str(args.voice_sample)
            report["file"] = str(path)
            report["file_identity"] = _file_identity(str(path))
            reports.append(report)
    else:
        report = lint(
            _read_stdin(),
            register=register,
            quote_safe=args.quote_safe,
            voice_sample=voice_sample,
        )
        if args.voice_sample and register == "voiced":
            report["voice_sample"] = str(args.voice_sample)
        reports.append(report)

    scored = [report for report in reports if "total_per100w" in report]
    if args.fail_over is not None:
        for report in scored:
            report["fail_over"] = args.fail_over
            report["over_fail_over"] = report["total_per100w"] > args.fail_over
    if args.baseline:
        try:
            by_file, anonymous = _baseline_scores(
                args.baseline,
                register,
                args.quote_safe,
                scored[0]["voice_sample_identity"] if scored else None,
            )
        # JSONDecodeError is a ValueError, which also covers a baseline report
        # whose total_per100w is not a number.
        except BaselineError as error:
            print(f"baseline {error.kind}: {error}", file=sys.stderr)
            failed = True
        except (OSError, UnicodeDecodeError, ValueError) as error:
            print(f"baseline unreadable: {type(error).__name__}: {error}", file=sys.stderr)
            failed = True
        else:
            try:
                _attach_deltas(scored, by_file, anonymous)
            except BaselineError as error:
                print(f"baseline {error.kind}: {error}", file=sys.stderr)
                failed = True

    if args.json:
        payload: Any = reports[0] if len(reports) == 1 else reports
        json.dump(payload, sys.stdout, indent=2, allow_nan=False)
        print()
    else:
        for report in reports:
            label = Path(report["file"]).name if "file" in report else "-"
            if "error" in report:
                print(f"{label:32} error={report['error']}")
                continue
            state = ""
            if "over_fail_over" in report:
                state = " over" if report["over_fail_over"] else " ok"
            print(
                f"{label:32} register={report['register']:8} "
                f"words={report['words']:5d} total={report['total']:4d} "
                f"per100w={report['total_per100w']:7.2f}{state}"
            )

    if failed:
        return 2
    if any(report.get("over_fail_over", False) for report in scored):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

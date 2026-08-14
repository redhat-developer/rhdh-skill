# Superseded: orchestrator-plus-sub-skills architecture

**Status:** Superseded by [ADR-0005](0005-one-skill-per-trigger-phrase.md).

The project is structured as an orchestrator skill (`rhdh`) that presents an
intake menu and routes to specialized sub-skills (`overlay`, `rhdh-local`,
`create-plugin`) rather than a single monolithic skill. The `create-plugin`
skill itself uses a sub-command router for its four concerns (backend,
frontend, export, wiring). Most Agent Skills are single-purpose — this one is a
router. The orchestrator handles orientation (environment detection, doctor
checks, config) and delegates domain-specific work to sub-skills that can be
developed and tested independently. This adds complexity (intake menus, routing
tables, cross-skill references) but enables progressive disclosure: agents load
only the sub-skill relevant to the current task instead of the entire corpus.

The original architecture used a model-invoked `rhdh` orchestrator to run
orientation and setup, present an intake menu, and open sibling skill files.
Specialized skills such as `overlay`, `rhdh-local`, and `create-plugin` held the
domain workflows.

That design established useful progressive disclosure, but the orchestrator's
broad description competed with every specialized skill and duplicated their
routing knowledge. Cross-skill file paths also made editorial folder layout part
of the composition interface.

The replacing decision keeps specialization while separating the concerns:

- human `/ask-rhdh` is the catalog;
- human `/setup-rhdh-skills` owns setup and compatibility state;
- model `/rhdh-context` owns shared read-only context;
- model skills are invoked by name and exchange versioned artifacts.

This file remains as historical context for the original tradeoff.

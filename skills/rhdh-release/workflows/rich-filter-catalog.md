# Workflow: Inspect or Query the Rich Filter Catalog

Expose every query-bearing entry in the configured Rich Filter export.

<prerequisites>

Run `python scripts/release.py --json check` and require the Rich Filter contract check to pass.

</prerequisites>

<process>

First list the catalog:

```bash
python scripts/release.py --json rich-filter inventory
```

Then query an entry by kind. Smart-filter clauses require their group name;
`--version` adds release scope and `--count` executes the composed JQL.

```bash
python scripts/release.py --json rich-filter query static demo --version {{RELEASE_VERSION}} --count
python scripts/release.py --json rich-filter query smart AI --group "Scrum Team" --version {{RELEASE_VERSION}} --count
python scripts/release.py --json rich-filter query queue "RNs Proposed" --version {{RELEASE_VERSION}} --count
python scripts/release.py --json rich-filter query time-series "Last week" --version {{RELEASE_VERSION}} --count
python scripts/release.py --json rich-filter query ratio-numerator "1.10 Plan to Commit" --count
python scripts/release.py --json rich-filter query ratio-denominator "1.10 Plan to Commit" --count
```

Inventory output also lists dynamic fields and view columns as presentation
metadata. Time-series JQL and both custom-ratio JQL sides are executable.

</process>

<success_criteria>

- [ ] The requested catalog entry is identified unambiguously
- [ ] Composed JQL and a Jira search link are returned
- [ ] A live count is included when requested

</success_criteria>

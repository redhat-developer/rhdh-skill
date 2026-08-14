# Patterns for Skills That Wrap APIs

Lessons learned from building skills that wrap CLIs, REST APIs, and GraphQL APIs. Read this when the skill interacts with external services or APIs.

For general reference architecture patterns (transitive loading, error placement, decision tables, agent-only audience), see `spec-guide.md` → Reference Architecture. For the gate contract every capability check follows, see `architecture-patterns.md` → Setup and capability gates.

## Credential handling

Skills that authenticate against external services must handle credentials carefully.

**Rules:**

1. **Use an authenticated adapter backed by the owning tool's native credential store or a host
   connector.** Only that adapter retrieves a transient credential, authenticates the request, and
   redacts errors. Its public inputs and outputs remain credential-free.
2. **Never materialize credentials in model-visible inputs.** Do not use `read`, `cat`, shell
   substitution, command arguments, request previews, logs, receipts, or artifacts for secrets.
3. **Separate setup from use.** A human-invoked setup skill owns installation, login, repair, and
   browser consent. A model-invoked consumer performs only a non-secret capability check.
4. **Add a capability gate.** Adapter readiness is a gate like any other; follow the gate contract
   in `architecture-patterns.md` → Setup and capability gates. Check readiness without inspecting
   credential material.
5. **Keep setup single-sourced.** Consumer references explain the required capability, not how to
   install a tool or create credentials.
6. **Test the boundary.** Tests assert capability detection, safe failure, and secret exclusion;
   they do not inspect a real credential store or test prose that mentions setup.

Example capability gate in SKILL.md:

```markdown
Before attempting authenticated API calls:
1. Run the local capability check without inspecting credential contents.
2. Use a ready authenticated adapter backed by a native CLI or host connector.
3. If the required adapter is unavailable, stop this branch and name the exact setup
   entry point and route that supplies it.
4. Do not reproduce installation, login, or credential-repair steps in this model skill.
```

## API schema discovery

When a skill wraps an API, the agent should be able to discover available endpoints, fields, and types dynamically — not rely solely on hardcoded documentation.

### REST APIs (OpenAPI)

If the API publishes an OpenAPI spec:

1. Document the download URL (without version pins that go stale)
2. Show how to query it programmatically (Python `json.load` + dict traversal)
3. Do not load the spec into context — it's typically 1-10MB
4. Also document live discovery endpoints (e.g., `/rest/api/3/field` for Jira)

### GraphQL APIs

GraphQL APIs are self-describing via introspection. There is no spec file to download.

1. Document `__type(name: "TypeName")` queries for targeted discovery
2. Document full `__schema` dump for offline analysis (save to file, query programmatically)
3. Note that introspection output is large — do not load into context

### Schema discovery comparison table

Include a table comparing how to discover the schema for each API the skill covers:

```markdown
| | REST API | GraphQL |
|--|---------|---------|
| **Spec format** | OpenAPI JSON (downloadable file) | No spec file — introspection queries |
| **Download** | `curl -o spec.json 'https://...'` | `__schema` query against the live endpoint |
| **Live field registry** | `GET /rest/api/3/field` | `__type(name: "...")` introspection |
```

## Validate examples against the live API

Do not write API examples from memory or documentation alone. Run them against the real endpoint and verify the output before including them in the skill.

**Why:** API schemas drift from documentation. Field names, payload formats, and required headers discovered through docs may not match the live API. A skill with broken examples is worse than no skill — the agent will retry the broken pattern repeatedly.

**Process:**

1. Draft the example from docs or training knowledge
2. Run it against the real endpoint
3. If it fails, use schema discovery (OpenAPI spec, GraphQL introspection) to find the correct field names and formats
4. Include only verified examples in the skill

This is especially important for GraphQL APIs where field names are typed and case-sensitive — `displayName` vs `name`, `parent` vs `parentIssue`, `sprint` vs `selectedSprintsConnection` can all differ from what you'd guess.

## Multi-API preference order

When a skill wraps multiple APIs (e.g., CLI + GraphQL + REST), define the preference order once in SKILL.md. Branch files point at it instead of each explaining when to use which API.

**Pattern:**

```markdown
### Adapter preference order

1. Use the authenticated native CLI when it supports the operation, including pagination or batch
   modes.
2. Use an authenticated host connector for API-only fields or relationship-heavy queries.
3. If neither capability is ready, stop the branch and name the exact setup entry point and
   route; do not construct a parallel raw HTTP authentication path.
```

Each branch names the capability it requires and defers authentication to that adapter. Branches do
not repeat setup or transport details.

**Prefer a real batch interface.** Process-spawn overhead alone does not justify bypassing the
native credential boundary. Use CLI pagination or batching when available; use a host API adapter
when the data shape genuinely requires another interface.

## Instance-specific values

Any value that is specific to a deployment (instance URL, tenant ID, cloud ID, org name) must include a programmatic discovery method.

Do not hardcode the value and move on. Show how the authenticated adapter obtains it without
exposing credentials:

```markdown
### Discovering your cloudId

The `cloudId` below is for `example.atlassian.net`. Discover another instance through the native
CLI or authenticated host connector's tenant-info capability. Keep request headers and credentials
inside the adapter and return only the cloud ID.
```

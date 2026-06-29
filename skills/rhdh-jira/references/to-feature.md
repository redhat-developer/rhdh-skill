# Create Feature

Create a RHDHPLAN Feature from conversation context. Grills the user on scope, customer value, and acceptance criteria before creating. Optionally chains into Epic decomposition.

## Workflow

### Step 1 — Draft from Context

Load `assets/templates/feature.txt` for structure and `assets/examples/feature-example.txt` for tone calibration.

Before asking questions, review what the conversation already established. Draft as many template sections as possible from existing context:

- Feature Overview, Goals, AC, Out of Scope, Customer Considerations, Documentation, Upstream engagement

Present the draft: "Based on our conversation, here's what I have so far. Review and tell me what's missing or wrong."

### Step 2 — Fill Gaps

For any template sections the agent couldn't fill from context, ask targeted questions (one at a time):

1. **Feature Overview** — what is this? Elevator pitch.
2. **Goals** — what does the user get? Which persona benefits?
3. **Requirements / Acceptance Criteria** — what must be true for this to be complete? Include non-functional requirements.
4. **Out of Scope** — what is explicitly NOT included?
5. **Customer Considerations** — any customer-specific context?
6. **Documentation Considerations** — what docs need creating/updating?
7. **Upstream engagement** — does this need Backstage community alignment?

Skip questions the draft already answered well.

### Step 3 — Challenge

Follow the challenging behavior in `references/grill.md` on the completed draft.

### Step 4 — Infer Fields

Infer all Jira fields from the conversation per the Field Inference section in `references/grill.md`. Present recommendations for confirmation.

Key fields for Features: Priority, Team, Size (T-shirt), Assignee (Feature Owner), Components, and Labels.

**Components:** Infer likely components from the feature description. Validate them against the project's component list per `references/feature-exploration.md` → Component Validation. Confirm with the user.

**Labels — ask about each during the grill:**

| Label | Question |
|-------|----------|
| `demo` | Does this feature need a customer-facing demo? |
| `rhdh-testday` | Should this feature be tested during release test day? |
| `rhdh-X.Y-candidate` | Which release does this target? |
| `stretch` | Is this a stretch goal? |

**Documentation:** If the feature involves documentation, set the `Documentation` component. After creation, prompt: "Create a Doc EPIC from this Feature? (Feature → More → Create Doc EPIC from RHDHPlan)"

**Cross-team dependencies:** Ask if other scrum teams are affected. If yes, note them — they become Epics in Step 9.

### Step 5 — Review

Render the filled template and inferred fields as a temporary markdown file for user review:

```bash
# Save to temp file
cat > /tmp/feature-review.md << 'EOF'
## Feature: {summary}

### Description
{filled template content}

### Fields
- **Priority**: {value} — {rationale}
- **Team**: {value}
- **Size**: {value} — {rationale}
- **Assignee**: {value}
- **Labels**: {values}
EOF
```

Present to the user: "Review the Feature before creating. Edit the file or tell me what to change. [approve / edit / cancel]"

- **approve** — proceed to duplicate check and creation
- **edit** — user modifies the file or provides changes verbally, agent updates
- **cancel** — abort creation

### Step 6 — Duplicate Check and Feature Request Link

Before creating, run the pre-creation check from `references/duplicates.md` using the proposed summary. Search RHDHPLAN Features specifically (`issuetype = Feature`).

Also search for accepted Feature Requests that this Feature may originate from:

```bash
jql: "project = RHDHPLAN AND issuetype = 'Feature Request' AND status = Accepted AND summary ~ \"KEYWORD1 KEYWORD2\""
```

If a matching Feature Request is found: "Found accepted Feature Request {KEY}: {summary}. Link this Feature to it?" If yes, add a `Related` issue link after creation.

If a likely duplicate Feature is found, present it and ask: "This may already exist as {KEY}: {summary}. Use the existing issue instead?"

### Step 7 — Create Feature

Fill the template with grill results. Save to a temp file. Then convert to ADF using the helper script (see Gotcha #6). `acli create` accepts ADF via `--description-file`:

```bash
FEATURE_ADF=$(mktemp)  # on Windows: use %TEMP% or Python tempfile
python scripts/jira-wiki-to-adf.py feature-filled.txt "$FEATURE_ADF"
```

Create the issue — note `--priority` and `--yes` do not exist on `create` (see Gotcha #18):

```bash
acli jira workitem create --project RHDHPLAN --type Feature \
  --summary "Feature summary" \
  --description-file "$FEATURE_ADF" \
  --assignee "ACCOUNT_ID" \
  --label "rhdh-2.1-candidate"
```

Then set priority, Team, and Size together in one REST call:

```bash
curl -s -X PUT -u "$AUTH" -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "priority": {"name": "Major"},
      "customfield_10795": {"value": "M"}
    }
  }' \
  "https://redhat.atlassian.net/rest/api/3/issue/RHDHPLAN-XXX"
```

Set Team via REST — follow API preference order in SKILL.md.

### Step 8 — Comments

Follow the comment suggestion behavior from `references/grill.md` — proactively suggest decision trail, elaboration, and abandoned paths as comments.

Add each approved comment via:

```bash
acli jira workitem comment --key RHDHPLAN-XXX --comment "comment text" --yes
```

### Step 9 — Chain Decomposition

After the Feature is created:

> "Break this Feature into Epics? The RHDH process typically creates Epics per team (Eng, QE, Doc). [y/N]"

If yes:

1. Ask: "Which teams are involved?" Default suggestion: Eng + Doc (QE is often covered within the Eng epic).
2. For each team, invoke the `to-epic` workflow with context carried down from this Feature:
   - The Feature's scope, AC, and customer considerations are established — don't re-grill on these
   - The Epic grill narrows to: delivery scope for *this team*, dependencies, team-specific AC
3. Each Epic is automatically linked to the parent Feature via `customfield_10018` (cross-project parent link — see Gotcha #16 and to-epic.md Step 8)

## Error Handling

| Error | Action |
|-------|--------|
| RHDHPLAN project inaccessible | Stop. User lacks project access. |
| `acli create` fails | Fall back to REST API. See SKILL.md Error Handling. |
| Duplicate check finds match | Present match. If user confirms duplicate, open existing issue instead. |
| Team field update fails via acli | Fall back to REST. See `references/rest-api-fallback.md`. |

## Caveats

1. **Feature Owner responsibility.** Creating a Feature implies ownership. Ensure the assignee understands the Feature Owner responsibilities (single point of contact, coordinates cross-team dependencies, ensures sizing and labels).
2. **Candidate label convention.** The label format is `rhdh-X.Y-candidate` (e.g., `rhdh-2.1-candidate`). Ask which release this targets during the grill. **Do not remove candidate labels without PM approval.**
3. **Description stays structured.** Only template sections go in the description. Decision trail, elaboration, and abandoned approaches go in comments.
4. **Rescoping.** If the feature is too large for a single release, suggest splitting. Document what's deferred and why as a comment. Adjust the candidate label if the target release changes. See `references/feature-exploration.md` → Rescoping.
5. **Feature Exploration checklist.** After creation, the Feature should pass the full checklist in `references/feature-exploration.md` before moving to Backlog.

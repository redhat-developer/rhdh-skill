# Create Epic

Create an RHIDP Epic from conversation context. Grills the user on delivery scope, dependencies, and acceptance criteria. Optionally chains into Story/Task decomposition.

## Workflow

### Step 1 — Determine Context

Two entry modes:

- **Chained from Feature**: Context carries down. The Feature's scope, AC, and customer considerations are established. The grill narrows to delivery scope for this team.
- **Standalone**: Full grill. No parent Feature context.

If chained, the parent Feature key is known. If standalone, ask: "Is this Epic part of an existing Feature? [Feature key / no]"

### Step 1.5 — Sibling Awareness

When creating an Epic under a parent Feature, check for existing sibling Epics before drafting:

1. Query existing siblings: `parent = FEATURE-KEY AND issuetype = Epic AND status != Closed`
2. Present the sibling list with summaries:
   > "This Feature already has these Epics:"
   > - RHIDP-100: Entity-Provider SDK (M)
   > - RHIDP-101: OCI Skill Registry (S)
   >
   > "Which of these does the new Epic relate to? Does it overlap with any?"
3. Carry sibling context into the grill — the grill's "Challenge epic independence" and "Challenge sibling overlap" behaviors use this list.
4. If the proposed Epic overlaps with an existing sibling, recommend adding scope as ACs on the sibling instead of creating a new Epic.

Skip this step for standalone Epics (no parent Feature).

### Step 2 — Draft from Context

Load `assets/templates/epic.txt` for structure and `assets/examples/epic-example.txt` for tone calibration.

Synthesize: Draft as many template sections as possible from the conversation (and parent Feature if chained):

- EPIC Goal, Background/Feature Origin, Why important, User Scenarios, Dependencies, AC

If chained from a Feature, pre-fill: Goal (scoped to this team's delivery), Background (link to parent Feature), Dependencies (other Epics in the Feature).

Present the draft: "Here's what I have for this Epic. Review and tell me what's missing."

### Step 3 — Fill Gaps

For unfilled sections, ask targeted questions. Adapt based on entry mode:

**Chained (narrowed):**

1. **EPIC Goal** — what does *this team's* delivery achieve within the parent Feature?
2. **Dependencies** — internal (other Epics) and external (upstream, other teams)
3. **Acceptance Criteria** — team-specific. Which checklist items apply? (DEV, QE, DOC)

**Standalone (full):**

1. **EPIC Goal** — what are we trying to solve?
2. **Background/Feature Origin** — where did this come from?
3. **Why is this important?**
4. **User Scenarios** — who benefits and how?
5. **Dependencies** — internal and external
6. **Acceptance Criteria** — full checklist

Skip questions the draft already answered.

### Step 4 — Challenge

Follow the challenging behavior in `references/grill.md`.

### Step 5 — Infer Fields

Infer all Jira fields per `references/grill.md` Field Inference. If chained, inherit Priority and Team from parent Feature. Key fields: Team, Priority, Size (T-shirt), Component, Assignee (Epic Owner).

**Components:** Infer from the epic description and validate against the project's component list per `references/fields.md` → Component Validation. If the epic involves documentation, set the `Documentation` component.

**Dependencies:** Link or note key dependencies on other issues, teams, or upstream work.

### Step 6 — Review

Render the filled template and inferred fields as a temporary markdown file for user review:

```bash
cat > /tmp/epic-review.md << 'EOF'
## Epic: {summary}

### Description
{filled template content}

### Fields
- **Priority**: {value}
- **Team**: {value}
- **Size**: {value}
- **Component**: {value}
- **Assignee**: {value}
EOF
```

Present to the user: "Review the Epic before creating. [approve / edit / cancel]"

### Step 7 — Duplicate Check

Run the pre-creation check from `references/duplicates.md`. Search RHIDP Epics (`issuetype = Epic`).

### Step 8 — Create Epic

Fill the template. Then convert to ADF using the helper script (see Gotcha #6). `acli create` accepts ADF via `--description-file`:

```bash
EPIC_ADF=$(mktemp)  # on Windows: use %TEMP% or Python tempfile
python scripts/jira-wiki-to-adf.py epic-filled.txt "$EPIC_ADF"
```

Create the issue — note `--priority`, `--component`, and `--yes` do not exist on `create` (see Gotcha #18):

```bash
acli jira workitem create --project RHIDP --type Epic \
  --summary "Epic summary" \
  --description-file "$EPIC_ADF" \
  --assignee "ACCOUNT_ID"
```

Then set priority, components, size, and parent Feature link together in one REST call. Cross-project parent links accept either `customfield_10018` or `parent.key` — do not use `issuelinks` (see Gotcha #16):

```bash
curl -s -X PUT -u "$AUTH" -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "priority": {"name": "Major"},
      "components": [{"name": "Catalog"}],
      "customfield_10795": {"value": "M"},
      "customfield_10018": "RHDHPLAN-XXX"
    }
  }' \
  "https://redhat.atlassian.net/rest/api/3/issue/RHIDP-XXX"
```

Set Team via REST — follow API preference order in SKILL.md.

### Step 9 — Comments

Follow the comment suggestion behavior from `references/grill.md` — proactively suggest decision trail, elaboration, and abandoned paths as comments.

Add via `acli jira workitem comment --key RHIDP-XXX --comment "text" --yes`.

### Step 10 — Chain Decomposition

After the Epic is created:

> "Break this Epic into Stories/Tasks? [y/N]"

If yes:

1. Discuss the breakdown: what are the deliverable slices?
2. For each slice, invoke the `to-issue` workflow with context carried down:
   - The Epic's goal, AC, and dependencies are established
   - The issue grill narrows to: implementation specifics, story points, approach
3. Each Story/Task is automatically linked to the parent Epic via `parent` field
4. Type inference runs per slice (Story if user-facing, Task if internal)

#### Batch Review (Feature → Epics)

When decomposing a Feature into multiple Epics (chained creation), run a batch review before finalizing any of them:

1. **Propose all Epics first**: Collect the full set of proposed Epics as a summary table before creating any:

   | # | Epic Summary | Size | Key Dependencies | Overlaps with |
   |---|-------------|------|------------------|---------------|
   | 1 | Entity-Provider SDK | M | upstream catalog API | — |
   | 2 | OCI Skill Registry | S | #1 (SDK) | — |
   | 3 | Annotation Scheme | XS | #1 (SDK) | #1 (same package) |

2. **Cross-epic overlap check**: "Do any two of these Epics share implementation — would they naturally ship in the same PR or package?" Flag pairs that overlap.

3. **Count challenge**: If >5 Epics are proposed under a single Feature, flag: "That's a lot of Epics. Are any of these implementation details that should be ACs on a broader Epic?"

4. **Consolidation check**: If multiple XS/S Epics target the same technical domain, suggest merging: "Epics #1 and #3 both target the SDK package — could #3 be ACs on #1?"

5. **User decides**: Allow the user to merge, drop, or proceed before creation begins. Only create Epics after the batch is approved.

## Error Handling

| Error | Action |
|-------|--------|
| RHIDP project inaccessible | Stop. User lacks project access. |
| Parent Feature key invalid | Warn. Create Epic without parent link. |
| `acli create` fails | Fall back to REST API. |
| Parent link update fails | Report failure. Epic is created — user can link manually. |

## Caveats

1. **Epic Owner responsibility.** The assignee is the Epic Owner — single point of contact for delivery, works with the Feature Owner to align execution. The Epic Owner is responsible for sizing the Epic.
2. **Component is required at New status.** Don't skip this during the grill. Validate against `references/fields.md` → Component Validation.
3. **Multi-team Features create multiple Epics.** When chained from a Feature, each team gets its own Epic. The Feature Owner coordinates across them.
4. **Size via sizing guide.** Use T-shirt sizing per `references/sizing.md`. If the parent Feature has multiple L or XL Epics, flag for the Feature Owner — the Feature scope may need reassessment.

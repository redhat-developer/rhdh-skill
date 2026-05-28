# RHDH Support Workflow

How support cases flow between RHDHSUPP, RHDHBUGS, and RHDHPLAN.

## Key Concepts

- **RHDHSUPP** — Internal project for engineering-support conversations. Not public.
- **RHDHBUGS** — Public project for product defects. **Never include customer information.**
- **RHDHPLAN** — Public project for feature requests.
- The engineering support liaison owns the relationship with the support team. Route questions about the support process to them.

## Anti-Pattern: Don't Comment on External Support Tickets

Engineering discussions happen in **RHDHSUPP issues only**. Do not comment directly on external customer support cases. Instead:

1. Create an internal RHDHSUPP issue
2. Link it to the external support case
3. Keep all engineering discussion in the RHDHSUPP issue

This keeps customer-facing communication controlled through the support team.

## Full Workflow

### Step 1 — Customer Creates Request

Customer submits a request on the Customer Portal. Support ensures it has the correct:

- Product and version
- Severity (1–4, where 1 is highest: 1-hour SLA)
- Description, trace logs, entitlement

### Step 2 — Support Investigates

A support representative is assigned. They:

- Review documentation and KCS articles
- Attempt to reproduce and diagnose

### Step 3 — Engineering Engaged (if needed)

If support needs engineering help, they open an **RHDHSUPP Bug** to track the discussion.

- Each RHDHSUPP Bug should be linked to the support ticket
- Priority, Component, and issue template must be set

### Step 4 — Investigation

Engineering responds following SLA. Investigation continues until an agreed solution is reached.

During investigation, if defects are found that are **unrelated** to the customer case, the engineer should still create RHDHBUGS Bugs to capture them for future work.

### Step 5 — Resolution

Resolutions include:

- Solution or workaround provided
- Termination of investigation (not supported, no further work possible, technical limitations)
- Identification of a product defect → go to Step 6
- Identification of a feature request → go to Step 7

### Step 6 — Product Defect (RHDHSUPP → RHDHBUGS)

When a product defect is identified:

1. Create `Bug` in **RHDHBUGS** with:
   - Priority, Component (use `Documentation` for doc defects)
   - Bug template filled out (reproduction steps, expected behavior)
   - **No customer information** — RHDHBUGS is a public project
   - Link to Customer Case via SFDC Cases Links
2. Comment on the RHDHSUPP issue with the RHDHBUGS link — this tells the customer when the fix is expected

```bash
# Convert wiki markup to ADF (required — plain wiki text is not rendered by Jira)
BUG_ADF=$(mktemp)  # on Windows: use %TEMP% or Python tempfile
python scripts/jira-wiki-to-adf.py bug_description.txt "$BUG_ADF"

# Create the bug (note: --yes does not exist on create, see Gotcha #18)
acli jira workitem create --project RHDHBUGS --type Bug \
  --summary "Login fails when SSO token expires during session" \
  --description-file "$BUG_ADF" \
  --label "rhdh-customer" \
  --assignee "@me"

# Link it to the support issue
acli jira workitem link create --out RHDHSUPP-456 --in RHDHBUGS-789 --type "Related" --yes

# Comment on support issue with the link
acli jira workitem comment create --key RHDHSUPP-456 \
  --body "Defect captured in RHDHBUGS-789. Fix targeted for next y-stream release."
```

### Step 7 — Feature Request (RHDHSUPP → RHDHPLAN)

When a support case reveals a missing capability:

1. Create `Feature Request` in **RHDHPLAN** with:
   - Priority, Component
   - Feature Request template filled out
   - Link to Customer Case via SFDC Cases Links
2. Encourage customer to follow up with their account team to prioritize with Product Management

```bash
# Convert wiki markup to ADF (required — plain wiki text is not rendered by Jira)
FEATURE_ADF=$(mktemp)  # on Windows: use %TEMP% or Python tempfile
python scripts/jira-wiki-to-adf.py feature_request.txt "$FEATURE_ADF"

# Create the feature request (note: --yes does not exist on create, see Gotcha #18)
acli jira workitem create --project RHDHPLAN --type "Feature Request" \
  --summary "Support OIDC token refresh in admin console" \
  --description-file "$FEATURE_ADF"

acli jira workitem link create --out RHDHSUPP-456 --in RHDHPLAN-123 --type "Related" --yes
```

### Step 8 — Close RHDHSUPP Issue

Close the RHDHSUPP Bug when:

- Investigation is resolved, OR
- No response from customer within SLA

On close, set **Story Points** to capture the effort spent on the investigation. See the sizing guide for RHDHSUPP-specific point scale.

## Bug Fix Prioritization

| Scenario | Target Release | Priority |
|----------|---------------|----------|
| Default | Next y-stream (e.g., 1.11.0) | As determined by triage |
| Critical to customer | Current z-stream (e.g., 1.10.4) | Set to **Blocker** + target fix version |
| Customer request, not urgent | Future y-stream | As determined by triage |

For z-stream targeting, discuss with the engineer to prioritize. If committed, set Priority to Blocker and the target fix version.

## Communication Channels

| Channel | Purpose |
|---------|---------|
| `#rhdh-support` | Engineering and Developer Hub support team communication |
| `#rhdh-support-cases` | Notification channel for new RHDHSUPP bugs from support team |

New support case notifications are managed through Hydra (the internal notification routing tool). Contact the engineering support liaison if notification configuration changes are needed.

## Ticket SLA

SLA depends on case severity:

| Severity | Response Time | Notes |
|----------|--------------|-------|
| Sev 1 | 1 hour | 24x7 support. Handed over between GEO teams. |
| Sev 2 | 2 hours | 24x7 support. |
| Sev 3 | 4 business hours | Business hours only. |
| Sev 4 | 1 business day | Business hours only. |

SLA may be negotiated (Negotiated Entitlement Process) or adjusted when a workaround is found.

## Special Case Types

| Type | Handling |
|------|---------|
| **Strategic customer** | Extra attention — opportunity to expand Red Hat relationship |
| **TAM customer** | Technical Account Manager assists with implementation |
| **Consulting/Partner** | Cases opened during project implementation |
| **CSE customer** | Customer Success Executive helps communication (non-technical) |

## Reference Resources

The following internal resources exist for deeper reference (access required):

- **RHDH Support Plan** — overall support strategy and staffing
- **RHDHSUPP CEE Process** — detailed CEE-side workflow
- **RHDH Support Dashboard / RHDH Supp Kanban Board** — operational views in Jira
- **RHDH CVE Management** — CVE fix tracking and justifications
- **RHDH Troubleshooting Guide** — common troubleshooting steps for support cases
- **Lifecycle Policies** — RHDH, RHPIB, and Red Hat Plug-Ins lifecycle policies (determines support scope per version)
- **Severity Definition & 24x7 Qualifications** — detailed severity criteria and eligibility

These are internal documents. Do not embed their URLs in agent output or share externally.

## Jira Projects Used in Support

| Project | Purpose | Public? |
|---------|---------|---------|
| RHDHSUPP | Internal conversations between support and engineering | No |
| RHDHBUGS | Product defects — bugs and doc defects | Yes |
| RHDHPLAN | Feature requests from customers | Yes |

**Security rule:** Never copy customer-identifying information from RHDHSUPP into RHDHBUGS or RHDHPLAN. Those projects are public.

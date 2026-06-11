# fullsend

Routing skill for the fullsend agent platform. Groom Jira tickets for
agent-readiness, then bridge them to GitHub Issues for fullsend processing.

## Commands

| Command | Description |
|---------|-------------|
| `groom <KEY>` | Score and improve a Jira ticket against a 6-dimension agent-readiness rubric |
| `bridge <KEY>` | Create a GitHub Issue from a groomed ticket, linking both sides |

## Attribution

The grooming workflow and agent-readiness rubric are derived from
[platform-frontend-ai-dev](https://github.com/redhat-developer/platform-frontend-ai-dev),
the autonomous dev bot built by the ConsoleDot Platform Experience team.

Key inspirations:

- **`prompts/groom.md`** — conversational grooming prompt that walks users
  through what the bot needs to pick up a ticket. Our 6-dimension scoring
  rubric formalizes the same checks Rehor performs implicitly.
- **`needs-investigation` workflow** — Rehor treats investigation tickets as
  fundamentally different from implementation tickets (report findings, don't
  code). Our groom workflow adopts this distinction.
- **`project-repos.json`** — Rehor's repo-to-persona mapping. Our
  `references/repo-mapping.md` follows the same pattern but uses the existing
  `rhdh-jira` component catalog as the source of truth.
- **Primary label routing** — Rehor uses team-specific labels (`hcc-ai-framework`,
  `hcc-ai-ui`) for triage routing. Our bridge uses the `fullsend` label for the
  same purpose.

The key architectural difference: Rehor is a monolith (groom + execute + triage
in one agent), while fullsend separates preparation (this skill) from execution
(the fullsend agent on GitHub).

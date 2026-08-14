---
name: rhdh-release-announce
description: >-
  Drafts the Slack message for an RHDH Feature Freeze or Code Freeze — either the
  milestone announcement sent on the day or the status update sent ahead of it —
  filling team counts, blocker bugs, CVEs, release notes, feature demos, and Test
  Day figures from Jira RHIDP and RHDHPLAN. Use for "announce feature freeze",
  "draft the code freeze message for 1.10", "send the freeze update for 1.11", or
  "write the freeze post for the release channel".
compatibility: "Python 3.9+ and uv; acli with a Jira session; gog for team data; an RHIDP Operational Rich Filter export; the external /humanizer skill."
---

# RHDH freeze announcements

Produce a Slack message a human posts under their own name. The counts come from
the CLI; the voice must not sound machine-written.

## Hard prerequisite: /humanizer

`/humanizer` is required before any draft is shown to the user, on every route.

If `/humanizer` is not installed, stop. Say the draft cannot be presented, name
`/setup-rhdh-skills install` as the way to add it, and do not show the raw
message in the meantime — not as a preview, not in a code block, not "just so you
can see the numbers". Reporting the counts as plain data is fine; presenting
anything shaped like the post is not.

Never post to Slack. This skill hands the user a message to copy; the user
decides whether, when, and where it goes out.

## Route

Load `workflows/freeze-announcement.md`. It maps the four announcements to their
CLI tokens and carries the milestone-versus-update distinction, which is the
thing people get wrong.

## Boundary with the neighbouring skills

- The date a freeze falls on is `/rhdh-release-schedule`.
- The underlying counts, on their own and without a message around them, are
  `/rhdh-release-status`.
- The team roster and Slack handles are `/rhdh-release-teams`.
- Rich Filter configuration lives in `/rhdh-release-status`. When the CLI reports
  a template unavailable, run `uv run scripts/release.py --json check`, follow its
  `next_steps`, and retry. Never substitute a hand-written query for a Rich Filter
  scope.

## Completion

Complete when the message is the humanized draft, wrapped in a triple-backtick
block ready to paste, with every placeholder filled and every count carrying a
URL-encoded Jira search link. State which of the four announcements was drafted
and whether it is the milestone or the update, so the sender knows what day it
belongs to. A figure the CLI could not produce is named as missing in the note
beside the draft rather than left as a placeholder or filled with a plausible
number. Say explicitly that nothing was posted.

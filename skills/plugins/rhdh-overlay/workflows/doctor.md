# Workflow: Validate Overlay Environment

Run read-only checks before an overlay workflow:

1. `git rev-parse --show-toplevel` succeeds.
2. `git remote -v` identifies
   `redhat-developer/rhdh-plugin-export-overlays` or a fork with that upstream.
3. `gh auth status` succeeds.
4. The checkout contains `workspaces/`, `catalog-entities/`, and
   `.github/workflows/`.
5. Python 3 is available for `scripts/analyze-pr.py` and
   `scripts/triage-prs.py`.

If no checkout is available, ask for its path or clone URL. If authentication
is absent, return the missing capability without reading credential files.
Environment validation is complete when the repository, forge identity, and
required paths are reported with pass/fail evidence.

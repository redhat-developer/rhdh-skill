# Assess RHDH repositories in batch

Load this reference when the user wants to assess multiple RHDH repositories.

1. Ask for the directory containing the checkouts.
2. Find git worktrees no deeper than two directories below it.
3. Compare each origin remote with `/rhdh-context`; ignore unrelated
   repositories.
4. Verify `uvx`, then run agentready for every matched repository with one fresh
   OS temporary output directory per repository. Parse each
   `assessment-latest.json`.
5. Present repository, score, certification, and failing-count columns in one
   table.
6. Ask which repository, if any, to improve. Return to the single-repository
   route and run a fresh assessment before remediation.

Batch assessment is complete when every matched RHDH repository appears once in
the summary and unrelated repositories were excluded.

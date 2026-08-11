# Reference: Findings & Recommendations Structure (Shared)

Shared Phase 7 for all PR review workflows. The calling workflow defines repo-specific best-practice bullets and rollback commands before referencing this file.

<findings_structure>

## Findings & Recommendations

Synthesize the verification results and provide a complete review assessment.

### 7.1 Verification summary

Summarize what was tested and the results:

| Category | Test performed | Result | Evidence |
|---|---|---|---|
| *[category]* | *[what was tested]* | Pass/Fail | *[key observation]* |

### 7.2 Best practice assessment

Review the PR's approach against the repo's development best practices. Reference `../../rhdh/references/rhdh-repos.md` for conventions. Use the repo-specific best-practice bullets defined by the calling workflow.

### 7.3 Security review

Evaluate the changes from a security perspective:

- Are secrets handled safely (no plaintext logging, proper Secret resources)?
- Do RBAC changes follow least-privilege principle?
- Are container image references pinned appropriately?
- Are new network exposures (ports, routes, service accounts) intentional and documented?
- Do dependency updates introduce known CVEs?
- Are user-supplied inputs validated before use in resource names or labels?

Add any repo-specific security concerns defined by the calling workflow.

### 7.4 Improvement suggestions

Based on the findings, suggest concrete improvements if any:

- Code or template changes needed (reference specific files and lines from the diff)
- Missing test coverage for the changed code paths
- Documentation gaps
- Configuration or operational concerns

### 7.5 Rollback instructions

Present the rollback commands recorded in Phase 4. Include verification that the rollback succeeded.

</findings_structure>

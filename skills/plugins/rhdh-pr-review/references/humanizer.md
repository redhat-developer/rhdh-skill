# Humanizer Gate

`/humanizer` is required for every review draft, including analysis-only.
Cluster-only routes that produce no review prose do not need it.

Before drafting, check whether the named skill is available through the host's
skill inventory. Do not scan installation directories and do not implement a
local substitute.

If unavailable, stop the draft branch, say that `humanizer` is missing, and name
`/setup-rhdh-skills install` as the human's next step. Do not draft review prose
without it.

After the top-level summary and inline bodies exist, invoke `/humanizer` on all
of them. Preserve technical meaning, severity, file paths, line numbers,
suggestion fences, and review event. Present only the humanized draft to the
user.

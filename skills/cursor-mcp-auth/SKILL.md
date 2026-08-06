---
name: cursor-mcp-auth
description: >-
  Ensures Cursor Atlassian MCP (plugin-atlassian-atlassian → mcp.atlassian.com) is
  authenticated for redhat.atlassian.net via OAuth. Use for "authenticate Jira",
  "Atlassian MCP", "jira auth failed", "mcp_auth Atlassian", "cursor MCP auth",
  or when another skill needs working Jira access through Cursor MCP.
---

# Cursor MCP auth (Atlassian / Jira)

Reusable auth gate for skills that query `https://redhat.atlassian.net` via Cursor MCP.

Access is Cursor’s Atlassian MCP plugin → Atlassian’s hosted Rovo MCP endpoint (OAuth).

## How access works

| Piece | Value |
|-------|--------|
| Plugin | Cursor `atlassian` → MCP server `plugin-atlassian-atlassian` |
| Endpoint | `https://mcp.atlassian.com/v1/mcp/authv2` (HTTP MCP; not a local process) |
| Site | `https://redhat.atlassian.net` |
| cloudId | `2b9e35e3-6bd3-4cec-b838-f4249ee02432` (or pass site URL as `cloudId`) |
| Auth | OAuth 2.1 browser login (Atlassian account) |
| Call path | agent → Cursor MCP client → `mcp.atlassian.com` (OAuth) → Jira Cloud API |

`~/.cursor/mcp.json` may be empty; the server comes from the installed plugin. OAuth is stored by Cursor (global storage / OS keyring) — never paste secrets into chat.

## Process (agent)

1. Discover tools: `GetMcpTools` for server `plugin-atlassian-atlassian` (or `atlassianUserInfo` / `getJiraIssue`).
2. If `serverStatus` is **`needsAuth`** (or calls fail with auth errors):
   - Call MCP tool `mcp_auth` on `plugin-atlassian-atlassian` with `{}`.
   - User completes browser OAuth when Cursor prompts (or connect via MCP settings).
   - Re-inspect the server; do **not** loop `mcp_auth` if consent failed.
3. Smoke: call `atlassianUserInfo` (no args). Success → report `ok:mcp` and stop.
4. Optional stronger smoke: `getJiraIssue` with `cloudId` = site URL or UUID and a known key (e.g. `RHIDP-1`) — only if the user can see that issue.
5. If the plugin is missing: instruct install/enable of the **Atlassian** Cursor plugin, then retry from step 1.

## Success criteria

- [ ] `plugin-atlassian-atlassian` is usable (`ready`, not `needsAuth` / `error`)
- [ ] `atlassianUserInfo` succeeds
- [ ] Agent never prints or requests OAuth secrets

## References

- [references/mcp-auth.md](references/mcp-auth.md)

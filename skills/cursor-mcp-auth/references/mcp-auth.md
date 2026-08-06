# Atlassian MCP auth (Cursor)

## Path

1. Enable the Cursor **Atlassian** plugin (`plugin-atlassian-atlassian`).
2. When status is `needsAuth`, run MCP `mcp_auth` (empty args) and finish browser OAuth.
3. Smoke with `atlassianUserInfo`.

Site for RHDH work: `https://redhat.atlassian.net`  
cloudId: `2b9e35e3-6bd3-4cec-b838-f4249ee02432` (UUID or site URL both work as `cloudId` on tools).

## Where credentials live

Not in plaintext `mcp.json`. Cursor stores OAuth under its global storage / OS keyring (e.g. GNOME libsecret). Agents call MCP tools; Cursor attaches tokens. Re-auth via MCP UI / `mcp_auth`. Never paste secrets into chat.

## Useful MCP tools

| Tool | Use |
|------|-----|
| `atlassianUserInfo` | Auth smoke |
| `getJiraIssue` | Issue fields (status, resolution, duedate, summary, `customfield_10859` for CVSS) |
| `searchJiraIssuesUsingJql` | Find issues by CVE summary, etc. |
| `mcp_auth` | Only when server `needsAuth` or auth errors |

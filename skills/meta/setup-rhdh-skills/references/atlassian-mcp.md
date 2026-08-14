# Authenticate Atlassian MCP in Cursor

Cursor's Atlassian plugin exposes `plugin-atlassian-atlassian`, backed by
`https://mcp.atlassian.com/v1/mcp/authv2`. Cursor stores OAuth in its global storage or OS keyring;
an empty `~/.cursor/mcp.json` is normal.

1. Discover tools for `plugin-atlassian-atlassian`.
2. When status is `needsAuth`, call its `mcp_auth` tool with `{}` exactly once and let the user
   complete browser OAuth. Re-inspect status after consent instead of looping authentication.
3. Smoke test with `atlassianUserInfo`.
4. If the server is missing, have the user install or enable Cursor's Atlassian plugin, then retry.
5. Optionally verify RHDH Jira visibility with `getJiraIssue` and a user-supplied issue key.

The RHDH Jira site is `https://redhat.atlassian.net`; its cloud ID is
`2b9e35e3-6bd3-4cec-b838-f4249ee02432`. Completion requires a ready server and successful user-info
call. Report statuses only; OAuth material never enters conversation.

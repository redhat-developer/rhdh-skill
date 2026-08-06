# Jira Input Parsing & REST API Patterns

Shared reference for resolving Jira issue keys from user input and performing Jira REST API operations. Used by `raise-pr` (Step 1.5, Step 11) and `bug-fix` (Step 1).

## Parsing Jira References

Accept any of these formats and normalize to a key + URL pair:

| Input format | Example | Extraction |
|-------------|---------|------------|
| Bare key | `RHDHBUGS-1934` | Match directly |
| Browse URL | `https://redhat.atlassian.net/browse/RHDHBUGS-1934` | Extract after `/browse/` |
| URL without scheme | `redhat.atlassian.net/browse/RHIDP-15252` | Extract after `/browse/` |
| URL with query params | `https://redhat.atlassian.net/browse/RHIDP-15252?focusedId=123` | Extract key between `/browse/` and `?` |

### Extraction rules

1. If the input contains `atlassian.net/browse/`, extract the path segment immediately after `/browse/` (strip any query string or fragment).
2. Otherwise, scan the full input string for a match against the pattern `(RHIDP|RHDHBUGS|RHDHPLAN|RHDHSUPP)-\d+`.
3. If neither matches, the input is invalid — ask the user to provide a valid key or URL.

### Normalization

Once the key is extracted:

```
jira_key  = "RHDHBUGS-1934"
jira_url  = "https://redhat.atlassian.net/browse/RHDHBUGS-1934"
```

Always construct `jira_url` from the key — do not store the user's raw URL (it may have query params or fragments).

## Authentication

All REST API calls use the `.jira-token` file. Locate it next to the `acli` binary:

```bash
ACLI_PATH="$(readlink -f "$(which acli)" 2>/dev/null || which acli)"
TOKEN_FILE="$(dirname "$ACLI_PATH")/.jira-token"
AUTH="$(cat "$TOKEN_FILE")"
```

The file contains `email:api_token` in a single line. **Never read the token into the conversation context** — only use it in shell commands via variable substitution.

If `acli` is not on PATH or `.jira-token` does not exist, warn the user: "Jira REST API auth not configured. Run `rhdh-jira setup` or see rhdh-jira skill for setup instructions." Continue without Jira operations.

## REST API Patterns

Base URL: `https://redhat.atlassian.net`

### Fetch issue summary

```bash
curl -s -u "$AUTH" \
  "https://redhat.atlassian.net/rest/api/3/issue/$JIRA_KEY?fields=summary,status" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d['fields']['summary'])"
```

### Add Web Link (remote link)

```bash
curl -s -X POST \
  -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"object\": {\"url\": \"$PR_URL\", \"title\": \"$PR_TITLE\"}}" \
  "https://redhat.atlassian.net/rest/api/3/issue/$JIRA_KEY/remotelink"
```

Returns `201 Created` on success with `{"id": ..., "self": "..."}`.

### Add comment

Prefer `acli` when available:

```bash
acli jira workitem comment add --key "$JIRA_KEY" --comment "PR submitted: $PR_URL" --yes
```

REST API fallback (requires ADF format):

```bash
curl -s -X POST \
  -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "body": {
      "type": "doc",
      "version": 1,
      "content": [{"type": "paragraph", "content": [{"type": "text", "text": "PR submitted: '"$PR_URL"'"}]}]
    }
  }' \
  "https://redhat.atlassian.net/rest/api/3/issue/$JIRA_KEY/comment"
```

### Query available transitions

```bash
curl -s -u "$AUTH" \
  "https://redhat.atlassian.net/rest/api/3/issue/$JIRA_KEY/transitions" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for t in data.get('transitions', []):
    print(f\"{t['id']:>5}  {t['to']['name']}\")
"
```

### Execute transition

```bash
curl -s -X POST \
  -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"transition\": {\"id\": \"$TRANSITION_ID\"}}" \
  "https://redhat.atlassian.net/rest/api/3/issue/$JIRA_KEY/transitions"
```

Returns `204 No Content` on success.

## Error Handling

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| 200/201/204 | Success | Continue |
| 400 | Bad request | Check payload format. For transitions, the requested transition may not be valid from the current status. |
| 401 | Unauthorized | `.jira-token` is missing, malformed, or expired. Warn user. |
| 403 | Forbidden | User lacks permission on this issue. Warn user. |
| 404 | Not found | Issue key is wrong or issue does not exist. Warn user. |
| 429 | Rate limited | Wait 5 seconds, retry once. |

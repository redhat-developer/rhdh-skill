# Configure Jira access

RHDH Jira workflows prefer `acli` for ordinary and bulk reads and supported writes. An authenticated
host Atlassian adapter covers relationship-heavy GraphQL reads and REST-only gaps. The site is
`https://redhat.atlassian.net`.

1. Confirm `acli` is on `PATH`.
2. Have the user create an Atlassian API token in their browser. Pass it directly to `acli`'s
   interactive login; do not print it or read it into conversation.
3. Authenticate the CLI:

   ```bash
   acli jira auth login --site redhat.atlassian.net --email <email> --token
   ```

4. Smoke test with `acli jira project list --recent 1` because `acli auth status` can report a
   false negative for API-token authentication.
5. Keep Jira credentials in the owning CLI's native credential store. Do not create a parallel
   plaintext credential file. If a required REST or GraphQL operation is unavailable through the
   authenticated CLI, configure the host connector through `/setup-rhdh-skills atlassian-mcp` or
   report the capability as unavailable instead of copying credentials into another store.

The Red Hat Jira cloud ID is `2b9e35e3-6bd3-4cec-b838-f4249ee02432`. Discover another site's ID
from `https://<site>/_edge/tenant_info` rather than copying this value.

Report capability statuses only. The report must not contain emails, credential locations, tokens,
authorization headers, or cookies.

# Configure the private-data checkout

The internal repository contains Jira Rich Filter exports used for release coordination.

1. Clone it into a user-selected workspace:

   ```bash
   git clone git@gitlab.cee.redhat.com:rhidp/rhdh-skills-private-data.git
   ```

2. Register the resolved checkout through the `rhdh` CLI, which keeps the same key names and
   config locations it always had:

   ```bash
   rhdh config set private-data <absolute-checkout-path>
   ```

3. Verify that `jira-rich-filter/rhidp-operational-rich-filter.json` exists.
4. Report the repository path and verification result.

Repository contents may be private. Keep them out of conversation and out of anything a skill writes
unless a workflow explicitly needs a bounded derived result.

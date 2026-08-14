# Configure RHDH repositories

Use `rhdh doctor --json` to inspect repository discovery. The preserved configuration precedence is
environment override, project `.rhdh/config.json`, user `~/.config/rhdh-skills/config.json`, then
bounded workspace discovery.

For each missing repository:

1. Ask for or discover its checkout without modifying unrelated repositories.
2. Verify it is a Git repository with `git -C <path> rev-parse --show-toplevel`.
3. State every `rhdh config set <key> <path>` operation as one plan: target, exact command,
   preview, and failure behavior.
4. After the user approves that stated set, run it, report each operation's outcome, and rerun
   `rhdh doctor --json`.

Use `rhdh setup submodule list` and `rhdh setup submodule add` only when the user explicitly chooses
the submodule layout. Preserve existing `.rhdh` configuration and never rewrite worklog or todo
state during repository setup.

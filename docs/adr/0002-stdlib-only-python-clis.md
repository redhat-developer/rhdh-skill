# Zero-install portability for bundled scripts

A script shipped inside a skill runs in whatever environment the agent happens to
be in. It cannot assume a package manager has run. Every bundled script therefore
uses only its runtime's standard library — no `pip install`, no `npm install`, no
virtualenv, no lockfile. The trade-off is rougher ergonomics for the author in
exchange for a script that works the first time, everywhere.

The rule is about the *install step*, not about Python. Two runtimes qualify today.

## Python

The `rhdh` and `rhdh-local` CLIs and every bundled Python script use only the
Python 3.9+ standard library. No `click`, `rich`, `typer`, or any other package.

- **`argparse`** for argument parsing, not click/typer
- **`OutputFormatter`** for auto-detecting TTY vs piped output
- **`urllib`** only inside a narrow authenticated adapter; any bearer credential
  is retrieved from the owning native CLI, used transiently in memory for the
  request header, and excluded from public arguments, output, and logs
- **`uv`** as the dev tool runner (`uv run pytest`) — used for development and
  testing, never shipped as a runtime requirement

## Node

Bundled Node scripts use only `node:`-prefixed builtins — `node:fs`, `node:os`,
`node:path`, `node:child_process`. No `package.json`, no `node_modules`. Tests
run under the built-in runner (`node --test`), which needs no framework.

This is the same rule, not an exception to it. A Node script that would need a
dependency does not qualify and should be Python or a native CLI call instead.

## Exceptions

Scripts that must round-trip YAML while preserving comments, key ordering, and
quoting may use `ruamel.yaml`. Such scripts declare dependencies with PEP 723
inline metadata and run through `uv run --script`, which provides an ephemeral
environment without a user-facing install step.

The exception is capability-based, not category-based: it applies only when the
standard library cannot preserve the required representation. An adapter that
delegates to a native CLI is not an exception, because the native CLI is the
user's install, not ours.

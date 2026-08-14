---
name: rhdh-base-images
description: >-
  Analyzes and updates the `FROM` base images, Node headers, Go toolchain, and
  `rpms.lock.yaml` files in rhdh, rhdh-operator, and rhdh-must-gather on `main` or
  a `release-1.10` branch. Use for weekly base-image maintenance, a UBI or RHEL
  bump, an RPM lockfile refresh, "which base images are out of date", or UBI minor
  skew inside a Containerfile.
compatibility: "bash, jq, skopeo, curl, git; podman or docker for toolchain detection; gh for PR creation."
---

# RHDH base images

Use the bundled scripts instead of reconstructing their repository-specific logic.

Repository checkouts are explicit inputs the user names. This skill never
discovers another skill's paths.

## Route

| Intent | Load or run |
|---|---|
| Read-only current/latest image scan | `workflows/update-base-images.md`, then `scripts/base-images-and-rpms.sh --analyze ...` |
| Explain repository rules | `references/repos.md` |
| Preview an update | `workflows/update-base-images.md`, then `scripts/base-images-and-rpms.sh --dry-run ...` |
| Update images, lockfiles, Node headers, or Go toolchain | `workflows/update-base-images.md` |

A scan reports, per repository: every `FROM` image with its current and latest
tag, UBI minor skew within a file, Node or Go toolchain drift, the registries and
branches it read, and anything it could not read.

## Writing rules

Any checkout, branch, file edit, dependency install, commit, push, or PR is a
write. Run read-only discovery or `--dry-run` first, then follow
`/mutation-gate`: state each operation with its target repository and branch
(`rhdh:release-1.10`), the exact command, the change it will land, and what
happens to the remaining operations if it fails; get approval for that stated
set; execute; then report every operation as completed, failed, or skipped, with
the resources it changed and the risks that remain.

Installing `rpm-lockfile-prototype`, logging into registries, using `--push`, and
opening PRs are each their own operation. Default to local, no-push behavior; do
not push directly to protected branches. Verify the branch exists and the working
tree is clean before writing.

## Repository invariants

- Accepted branch selectors are `main` or `release-*`; map them to the documented
  GitLab scripts branch in `references/repos.md`.
- Keep base-image UBI minors aligned with RPM repository URLs.
- On RHDH, update Node headers when the builder image changes Node.
- On rhdh-operator `main`, align `go.mod` with the Go toolset image.
- Exclude RHDH `e2e-tests/` and `.ci/` from image scans.

Another skill invokes `/rhdh-base-images` by name and uses what it reports; it
never reaches for these script paths.

## Completion

An analysis is complete when every repository in scope is named with its current
and latest tag, UBI skew and toolchain drift are stated or stated as none, and
every registry, lockfile, or branch the scan could not read is named as unread
instead of reported as current.

An update is complete when the target branch was verified to exist against a
clean working tree before any edit, every approved operation has been reported by
target and outcome, and the push and PR state is stated explicitly — including
"not pushed" when the default local behavior was kept.

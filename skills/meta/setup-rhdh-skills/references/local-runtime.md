# Configure the local RHDH runtime

Local testing needs the `rhdh-local` repository and either Podman or Docker.

1. Confirm `rhdh-local` is configured with `rhdh doctor --json`.
2. Prefer Podman when both runtimes exist; accept Docker as the adapter when it is the configured
   project convention.
3. Verify the runtime with `podman info` or `docker info` without starting containers.
4. Run the `rhdh-local` skill's status command after capability checks pass.

Container starts, stops, volume removal, and restore operations go through the write gate. State the
compose files, profiles, volume behavior, and target checkout in the plan so one approval covers the
deterministic batch.

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["ruamel.yaml"]
# ///
"""List EKS test entries in RHDH CI config files."""

import sys

from rhdh_prow.k8s_configs import main

if __name__ == "__main__":
    main(["--pattern", "^e2e-eks-", *sys.argv[1:]])

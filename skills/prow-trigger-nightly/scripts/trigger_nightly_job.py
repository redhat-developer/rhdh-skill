#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# ///
"""Trigger RHDH nightly ProwJobs via the OpenShift CI Gangway REST API.

Supports both the rhdh and rhdh-plugin-export-overlays repositories.

Prerequisites:
  - oc CLI installed.
  - Python 3.9+.

Authentication:
  The script uses a dedicated kubeconfig (~/.config/openshift-ci/kubeconfig)
  to avoid interfering with your current cluster context.
  If not logged in or the token is expired, the script will automatically
  open a browser for SSO login via ``oc login --web``.
  See: https://docs.ci.openshift.org/how-tos/triggering-prowjobs-via-rest/

Usage examples:
  # List all available nightly jobs:
  uv run trigger_nightly_job.py --list

  # Trigger the OCP Helm nightly job on the main branch:
  uv run trigger_nightly_job.py --job periodic-ci-redhat-developer-rhdh-main-e2e-ocp-helm-nightly

  # Trigger with a custom image (e.g. RC verification):
  uv run trigger_nightly_job.py \\
    --job periodic-ci-redhat-developer-rhdh-main-e2e-ocp-helm-nightly \\
    --image-repo rhdh/rhdh-hub-rhel9 \\
    --tag 1.9-123

  # Trigger an overlay nightly job:
  uv run trigger_nightly_job.py \\
    --job periodic-ci-redhat-developer-rhdh-plugin-export-overlays-main-e2e-ocp-helm-nightly

  # Dry-run mode (print the request without executing):
  uv run trigger_nightly_job.py \\
    --job periodic-ci-redhat-developer-rhdh-main-e2e-ocp-helm-nightly \\
    --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

# --- Constants ---
GANGWAY_URL = "https://gangway-ci.apps.ci.l2s4.p1.openshiftapps.com/v1/executions"
CI_SERVER = "https://api.ci.l2s4.p1.openshiftapps.com:6443"

REPOS = [
    "redhat-developer/rhdh",
    "redhat-developer/rhdh-plugin-export-overlays",
]

OVERLAY_JOB_PREFIX = "periodic-ci-redhat-developer-rhdh-plugin-export-overlays-"


# --- Logging ---
def log_info(msg: str) -> None:
    print(f"[INFO] {msg}", file=sys.stderr)


def log_warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


# --- Job listing ---
def fetch_configured_jobs(repo: str) -> list[str]:
    """Fetch nightly job names from the Prow configured-jobs page.

    The page returns HTML with embedded JSON containing ``"name":"<job>"``
    entries. We extract job names ending in ``-nightly`` via regex.
    """
    url = f"https://prow.ci.openshift.org/configured-jobs/{repo}"
    req = urllib.request.Request(url, headers={"User-Agent": "rhdh-skill"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError) as exc:
        log_warn(f"Failed to fetch jobs from {url}: {exc}")
        return []

    # Extract job names from embedded JSON: "name":"periodic-ci-...-nightly"
    matches = re.findall(r'"name":"(periodic-ci-[^"]*-nightly)"', html)
    return sorted(set(matches))


def _short_name(job: str, repo: str) -> str:
    """Extract the human-readable test name from a full job name.

    E.g. ``periodic-ci-redhat-developer-rhdh-main-e2e-ocp-helm-nightly``
    -> ``e2e-ocp-helm-nightly``
    """
    # The prefix is: periodic-ci-{org}-{repo}-{branch}-
    # We need to strip the prefix up to and including the branch segment.
    org_repo = repo.replace("/", "-")
    prefix = f"periodic-ci-{org_repo}-"
    if not job.startswith(prefix):
        return job

    remainder = job[len(prefix) :]
    # remainder is e.g. "main-e2e-ocp-helm-nightly" or "release-1.9-e2e-ocp-helm-nightly"
    # Find the first "e2e-" segment to split branch from test name.
    match = re.search(r"(e2e-.+)$", remainder)
    if match:
        return match.group(1)
    return remainder


def _extract_branch(job: str, repo: str) -> str:
    """Extract the branch name from a full job name."""
    org_repo = repo.replace("/", "-")
    prefix = f"periodic-ci-{org_repo}-"
    if not job.startswith(prefix):
        return "?"

    remainder = job[len(prefix) :]
    match = re.search(r"(e2e-.+)$", remainder)
    if match:
        branch = remainder[: match.start()].rstrip("-")
        return branch if branch else "?"
    return "?"


def list_jobs(*, json_output: bool = False) -> None:
    """Fetch and print available nightly jobs from all repos."""
    # Collect all jobs grouped by (repo, short_name) -> set of branches
    table: dict[tuple[str, str], set[str]] = {}
    all_branches: set[str] = set()
    # Also collect full job names for JSON output.
    full_names: dict[tuple[str, str, str], str] = {}

    for repo in REPOS:
        log_info(f"Fetching jobs from {repo}...")
        jobs = fetch_configured_jobs(repo)
        for job in jobs:
            short = _short_name(job, repo)
            branch = _extract_branch(job, repo)
            key = (repo, short)
            table.setdefault(key, set()).add(branch)
            all_branches.add(branch)
            full_names[(repo, short, branch)] = job

    if not table:
        log_error("No nightly jobs found.")
        sys.exit(1)

    if json_output:
        result: list[dict] = []
        for (repo, short), branches in sorted(table.items()):
            for branch in sorted(branches):
                result.append(
                    {
                        "repo": repo,
                        "job": short,
                        "branch": branch,
                        "full_name": full_names[(repo, short, branch)],
                    }
                )
        print(json.dumps(result, indent=2))
        return

    # Sort branches: main first, then release-* in descending order
    def branch_sort_key(b: str) -> tuple[int, str]:
        if b == "main":
            return (0, "")
        return (1, b)

    sorted_branches = sorted(all_branches, key=branch_sort_key)

    # Print table
    repo_col = "Repo"
    job_col = "Job"
    max_repo = max(len(repo_col), max(len(r.split("/")[-1]) for r, _ in table))
    max_job = max(len(job_col), max(len(s) for _, s in table))
    branch_widths = {b: max(len(b), 1) for b in sorted_branches}

    header = f"| {'Repo':<{max_repo}} | {'Job':<{max_job}} |"
    for b in sorted_branches:
        header += f" {b:<{branch_widths[b]}} |"
    sep = f"|{'-' * (max_repo + 2)}|{'-' * (max_job + 2)}|"
    for b in sorted_branches:
        sep += f"{'-' * (branch_widths[b] + 2)}|"

    print(header)
    print(sep)

    for (repo, short), branches in sorted(table.items()):
        repo_short = repo.split("/")[-1]
        row = f"| {repo_short:<{max_repo}} | {short:<{max_job}} |"
        for b in sorted_branches:
            mark = "x" if b in branches else ""
            row += f" {mark:<{branch_widths[b]}} |"
        print(row)


# --- Tag listing ---
DEFAULT_IMAGE_REPO = "rhdh/rhdh-hub-rhel9"


def _fetch_quay_tags(image_repo: str, like_filter: str) -> list[dict]:
    """Fetch tags from the Quay API with a ``like:`` substring filter."""
    encoded_repo = urllib.request.quote(image_repo, safe="")
    encoded_filter = urllib.request.quote(like_filter, safe="")
    url = (
        f"https://quay.io/api/v1/repository/{encoded_repo}/tag/"
        f"?limit=100&onlyActiveTags=true&filter_tag_name=like:{encoded_filter}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "rhdh-skill"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as exc:
        log_warn(f"Failed to fetch tags (filter={like_filter!r}): {exc}")
        return []
    return data.get("tags", [])


def _fetch_version_tags(image_repo: str, tag_filter: str = "") -> list[str]:
    """Fetch version tags from quay.io for the given image repo.

    If *tag_filter* is provided (e.g. ``1.10``), a single Quay request with
    ``filter_tag_name=like:<tag_filter>`` is issued — fast and precise.

    Without a filter, two requests are made for the ``1.`` and ``2.`` major
    version prefixes and the results are merged, covering current and upcoming
    RHDH releases.

    In both cases the results are filtered locally by a strict version regex
    (``MAJOR.MINOR`` or ``MAJOR.MINOR-BUILD``) to discard digest artifacts
    that happen to match the substring filter.
    """
    version_re = re.compile(r"^[0-9]+\.[0-9]+(-[0-9]+)?$")

    if tag_filter:
        prefixes = [tag_filter]
    else:
        prefixes = ["1.", "2."]

    seen: set[str] = set()
    tags: list[str] = []
    for prefix in prefixes:
        for t in _fetch_quay_tags(image_repo, prefix):
            name = t.get("name", "")
            if name not in seen and version_re.match(name):
                seen.add(name)
                tags.append(name)

    tags.sort(key=lambda t: [int(x) for x in re.split(r"[-.]", t)])
    return tags


def list_tags(
    image_repo: str, limit: int = 20, *, tag_filter: str = "", json_output: bool = False
) -> None:
    """Fetch and print available image tags from quay.io."""
    tags = _fetch_version_tags(image_repo, tag_filter=tag_filter)

    if not tags:
        log_error(f"No matching tags found for {image_repo}")
        sys.exit(1)

    # JSON always returns all tags; human output shows the latest N.
    if json_output:
        print(json.dumps({"image_repo": image_repo, "tags": tags}, indent=2))
        return

    display_tags = tags[-limit:]
    log_info(f"Available tags for {image_repo} (latest {len(display_tags)}):")
    for i, tag in enumerate(display_tags, 1):
        print(f"  {i}. {tag}")


# --- Authentication ---
def ensure_auth(kubeconfig: str, dry_run: bool) -> str:
    """Ensure authentication to the OpenShift CI cluster. Returns the token."""
    if dry_run:
        return "<TOKEN>"

    if not shutil.which("oc"):
        log_error(
            "'oc' CLI not found. Install it from https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/"
        )
        sys.exit(1)

    oc_base = ["oc", "--kubeconfig", kubeconfig]

    # Check current server
    result = subprocess.run(
        [*oc_base, "whoami", "--show-server"],
        capture_output=True,
        text=True,
    )
    current_server = result.stdout.strip() if result.returncode == 0 else ""
    needs_login = False

    if current_server != CI_SERVER:
        if current_server:
            log_warn(f"Currently logged in to {current_server}, need {CI_SERVER}")
        needs_login = True
    else:
        # Check if token is valid
        result = subprocess.run(
            [*oc_base, "whoami", "-t"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log_warn("Token expired.")
            needs_login = True

    if needs_login:
        log_info("Logging in to OpenShift CI cluster...")
        result = subprocess.run(
            [*oc_base, "login", "--web", CI_SERVER],
        )
        if result.returncode != 0:
            log_error("Login failed.")
            sys.exit(1)

    # Get token
    result = subprocess.run(
        [*oc_base, "whoami", "-t"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log_error("Failed to get authentication token after login.")
        sys.exit(1)

    return result.stdout.strip()


# --- Payload ---
def build_payload(args: argparse.Namespace) -> dict:
    """Build the Gangway API request payload."""
    envs: dict[str, str] = {}

    is_overlay = args.job.startswith(OVERLAY_JOB_PREFIX)

    if is_overlay:
        # Overlay jobs support fork overrides, catalog index, and playwright version.
        # Image overrides, chart version, and alerts are not supported.
        unsupported: list[str] = []
        if args.image_repo:
            unsupported.append("--image-repo")
        if args.image_registry:
            unsupported.append("--image-registry")
        if args.tag:
            unsupported.append("--tag")
        if args.chart_version:
            unsupported.append("--chart-version")
        if args.send_alerts:
            unsupported.append("--send-alerts")
        if unsupported:
            log_error(
                f"Overlay jobs do not support: {', '.join(unsupported)}. "
                "These flags only work with rhdh repo jobs."
            )
            sys.exit(1)

        if args.org:
            envs["MULTISTAGE_PARAM_OVERRIDE_GITHUB_ORG_NAME"] = args.org
        if args.repo:
            envs["MULTISTAGE_PARAM_OVERRIDE_GITHUB_REPOSITORY_NAME"] = args.repo
        if args.branch:
            envs["MULTISTAGE_PARAM_OVERRIDE_RELEASE_BRANCH_NAME"] = args.branch
        if args.catalog_index_image:
            envs["MULTISTAGE_PARAM_OVERRIDE_CATALOG_INDEX_IMAGE"] = args.catalog_index_image
        if args.playwright_version:
            envs["MULTISTAGE_PARAM_OVERRIDE_PLAYWRIGHT_VERSION"] = args.playwright_version
    else:
        # RHDH repo jobs do not support playwright version.
        if args.playwright_version:
            log_error("--playwright-version is only supported for overlay jobs.")
            sys.exit(1)

        # RHDH repo jobs support full overrides.
        if args.image_repo:
            envs["MULTISTAGE_PARAM_OVERRIDE_IMAGE_REPO"] = args.image_repo
        if args.image_registry:
            envs["MULTISTAGE_PARAM_OVERRIDE_IMAGE_REGISTRY"] = args.image_registry
        if args.tag:
            envs["MULTISTAGE_PARAM_OVERRIDE_TAG_NAME"] = args.tag
        if args.org:
            envs["MULTISTAGE_PARAM_OVERRIDE_GITHUB_ORG_NAME"] = args.org
        if args.repo:
            envs["MULTISTAGE_PARAM_OVERRIDE_GITHUB_REPOSITORY_NAME"] = args.repo
        if args.branch:
            envs["MULTISTAGE_PARAM_OVERRIDE_RELEASE_BRANCH_NAME"] = args.branch
        if args.catalog_index_image:
            envs["MULTISTAGE_PARAM_OVERRIDE_CATALOG_INDEX_IMAGE"] = args.catalog_index_image
        if args.chart_version:
            envs["MULTISTAGE_PARAM_OVERRIDE_CHART_VERSION"] = args.chart_version

        skip_alert = "false" if args.send_alerts else "true"
        envs["MULTISTAGE_PARAM_OVERRIDE_SKIP_SEND_ALERT"] = skip_alert

    payload: dict = {
        "job_name": args.job,
        "job_execution_type": "1",
    }
    if envs:
        payload["pod_spec_options"] = {"envs": envs}

    return payload


# --- Trigger ---
def trigger_job(token: str, payload: dict) -> dict:
    """Send the trigger request to the Gangway API. Returns the response body."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GANGWAY_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "rhdh-skill",
        },
        method="POST",
    )

    log_info("Triggering job...")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        log_error(f"API returned HTTP {exc.code}")
        try:
            err = json.loads(body_text)
            print(json.dumps(err, indent=2), file=sys.stderr)
        except json.JSONDecodeError:
            print(body_text, file=sys.stderr)
        log_error(
            "The job name may be invalid. Verify at:\n"
            "  https://prow.ci.openshift.org/configured-jobs/redhat-developer/rhdh\n"
            "  https://prow.ci.openshift.org/configured-jobs/redhat-developer/rhdh-plugin-export-overlays"
        )
        sys.exit(1)
    except (urllib.error.URLError, OSError) as exc:
        log_error(f"Request failed: {exc}")
        sys.exit(1)

    log_info("Response:")
    print(json.dumps(body, indent=2), file=sys.stderr)
    return body


def poll_job_status(token: str, job_id: str) -> None:
    """Poll the Gangway API for the job URL."""
    print("", file=sys.stderr)
    log_info(f"Job ID: {job_id}")
    log_info("Waiting for Prow URL...")

    job_url = ""
    for _ in range(5):
        print(".", end="", flush=True, file=sys.stderr)
        url = f"{GANGWAY_URL}/{job_id}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "rhdh-skill",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                job_url = data.get("job_url", "")
                if job_url:
                    break
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            pass
        time.sleep(2)

    print("", file=sys.stderr)
    if job_url:
        log_info(f"Job URL: {job_url}")
    else:
        log_warn("Job URL not yet available.")

    log_info("Re-check status:")
    log_info(
        f'  curl -s -H "Authorization: Bearer $(oc whoami -t)" {GANGWAY_URL}/{job_id} | python3 -m json.tool'
    )


# --- CLI ---
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trigger RHDH nightly ProwJobs via the OpenShift CI Gangway REST API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Job name patterns:
  RHDH:     periodic-ci-redhat-developer-rhdh-{BRANCH}-e2e-{PLATFORM}-{METHOD}-nightly
  Overlays: periodic-ci-redhat-developer-rhdh-plugin-export-overlays-{BRANCH}-e2e-{PLATFORM}-{METHOD}-nightly

Examples:
  %(prog)s --list
  %(prog)s --job periodic-ci-redhat-developer-rhdh-main-e2e-ocp-helm-nightly
  %(prog)s --job periodic-ci-redhat-developer-rhdh-plugin-export-overlays-main-e2e-ocp-helm-nightly
  %(prog)s --job periodic-ci-redhat-developer-rhdh-main-e2e-ocp-helm-nightly --tag 1.9-123
""",
    )

    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_jobs",
        help="List available nightly jobs from all repos.",
    )
    parser.add_argument(
        "-j",
        "--job",
        dest="job",
        help="Full ProwJob name to trigger.",
    )
    parser.add_argument(
        "-T",
        "--list-tags",
        action="store_true",
        dest="list_tags",
        help="List available image tags from quay.io. Use --image-repo to specify the repo.",
    )
    parser.add_argument(
        "--tag-filter",
        dest="tag_filter",
        default="",
        help="Filter tags by version prefix (e.g. '1.10'). Used with --list-tags.",
    )

    shared = parser.add_argument_group("Shared overrides (both rhdh and overlay jobs)")
    shared.add_argument(
        "-o",
        "--org",
        dest="org",
        default="",
        help="Override the GitHub org (default: redhat-developer).",
    )
    shared.add_argument(
        "-r",
        "--repo",
        dest="repo",
        default="",
        help="Override the GitHub repo name (default: rhdh).",
    )
    shared.add_argument(
        "-b",
        "--branch",
        dest="branch",
        default="",
        help="Override the branch name.",
    )
    shared.add_argument(
        "--catalog-index-image",
        dest="catalog_index_image",
        default="",
        help="Override the catalog index image (e.g. quay.io/rhdh/plugin-catalog-index:1.9-60).",
    )

    rhdh_only = parser.add_argument_group("RHDH-only overrides (not supported for overlay jobs)")
    rhdh_only.add_argument(
        "-I",
        "--image-registry",
        dest="image_registry",
        default="",
        help="Override the image registry (default: quay.io).",
    )
    rhdh_only.add_argument(
        "-q",
        "--image-repo",
        dest="image_repo",
        default="",
        help="Override the image repository (e.g. rhdh/rhdh-hub-rhel9). Requires --tag.",
    )
    rhdh_only.add_argument(
        "-t",
        "--tag",
        dest="tag",
        default="",
        help="Override the image tag (e.g. 1.9-123).",
    )
    rhdh_only.add_argument(
        "--chart-version",
        dest="chart_version",
        default="",
        help="Override the Helm chart version (e.g. 1.9-227-CI).",
    )
    rhdh_only.add_argument(
        "-S",
        "--send-alerts",
        action="store_true",
        help="Send Slack alerts (default: alerts are skipped).",
    )

    overlay_only = parser.add_argument_group("Overlay-only overrides (not supported for rhdh jobs)")
    overlay_only.add_argument(
        "--playwright-version",
        dest="playwright_version",
        default="",
        help="Override the Playwright version (overlay jobs only).",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print the request payload without executing.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output structured JSON instead of human-readable text (for --list and --list-tags).",
    )

    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    """Validate parsed arguments."""
    if not args.list_jobs and not args.list_tags and not args.job:
        log_error("Either --list, --list-tags, or --job is required.")
        sys.exit(1)

    if args.tag_filter and not args.list_tags:
        log_warn("--tag-filter is only used with --list-tags, ignoring.")

    if args.job:
        if not args.job.startswith("periodic-ci-"):
            log_error(f"Job name must start with 'periodic-ci-', got: {args.job}")
            sys.exit(1)

        if args.image_repo and not args.tag:
            log_error("--image-repo requires --tag to be set.")
            sys.exit(1)


def print_summary(args: argparse.Namespace, payload: dict) -> None:
    """Print a summary of the job to be triggered."""
    log_info(f"Job:     {args.job}")
    log_info("Payload:")
    print(json.dumps(payload, indent=2), file=sys.stderr)
    print("", file=sys.stderr)


def print_dry_run(payload: dict) -> None:
    """Print the equivalent curl command without executing."""
    payload_str = json.dumps(payload)
    print("[DRY RUN] Would execute:")
    print("curl -s -X POST \\")
    print('  -H "Authorization: Bearer $(oc whoami -t)" \\')
    print('  -H "Content-Type: application/json" \\')
    print(f"  -d '{payload_str}' \\")
    print(f"  {GANGWAY_URL}")


def main(argv: list[str] | None = None) -> None:
    # Use a dedicated kubeconfig to avoid interfering with current cluster context.
    config_home = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")
    )
    kubeconfig = os.path.join(config_home, "openshift-ci", "kubeconfig")
    os.makedirs(os.path.dirname(kubeconfig), exist_ok=True)

    args = parse_args(argv)
    validate_args(args)

    if args.list_jobs:
        list_jobs(json_output=args.json_output)
        return

    if args.list_tags:
        list_tags(
            args.image_repo or DEFAULT_IMAGE_REPO,
            tag_filter=args.tag_filter,
            json_output=args.json_output,
        )
        return

    payload = build_payload(args)
    token = ensure_auth(kubeconfig, args.dry_run)

    print_summary(args, payload)

    if args.dry_run:
        print_dry_run(payload)
        return

    response = trigger_job(token, payload)

    job_id = response.get("id", "")
    if job_id:
        poll_job_status(token, job_id)


if __name__ == "__main__":
    main()

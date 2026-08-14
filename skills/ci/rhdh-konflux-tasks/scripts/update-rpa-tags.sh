#!/usr/bin/env bash
#
# Bump RHDH ReleasePlanAdmission tag versions in konflux-release-data.
# See the local rhdh-release workflow: workflows/konflux-rpa-update.md
#
# SPDX-License-Identifier: EPL-2.0

set -euo pipefail

NEW_VERSION=""
REPO_DIR=""
RPA_DIR=""

readonly PUSH_REMOTE="origin"
readonly GITLAB_PROJECT="releng/konflux-release-data"
readonly RPA_REL_DIR="config/stone-prod-p02.hjvn.p1/product/ReleasePlanAdmission/rhdh"

DRY_RUN=0
VALIDATE=0
BASE_BRANCH="main"

usage() {
    cat <<'EOF'
Update RHDH ReleasePlanAdmission tags for a stream release in konflux-release-data.

Usage:
  update-rpa-tags.sh VERSION [OPTIONS]

Arguments:
  VERSION                 Target RHDH version (e.g. 1.9.7, 1.10.3)

Options:
  --repo-dir PATH         konflux-release-data checkout (default: $PWD)
  --base-branch BRANCH    Target branch for merge request (default: main)
  --dry-run               Preview tag changes without writing, committing, pushing, or opening an MR
  --validate              Run `tox -e test` after editing (requires tox in repo)
  -h, --help              Show this help

Examples:
  cd /path/to/konflux-release-data && update-rpa-tags.sh 1.9.7
  update-rpa-tags.sh 1.9.7 --repo-dir /path/to/konflux-release-data
  update-rpa-tags.sh 1.10.3 --dry-run
EOF
}

die() {
    echo "[ERROR] $*" >&2
    exit 1
}

log() {
    echo "[INFO] $*" >&2
}

warn() {
    echo "[WARN] $*" >&2
}

validate_version() {
    local version="$1"
    [[ "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
        || die "Invalid version '${version}'. Expected MAJOR.MINOR.PATCH (e.g. 1.9.7)"
}

version_stream() {
    local version="$1"
    echo "${version%.*}"
}

version_stream_dashed() {
    local stream
    stream=$(version_stream "$1")
    echo "${stream//./-}"
}

is_rpa_directory() {
    local dir="$1"
    local matches=()

    [[ -d "${dir}" ]] || return 1
    shopt -s nullglob
    matches=("${dir}"/rhdh-*.yaml "${dir}"/rhdh-plugin-catalog-*.yaml)
    shopt -u nullglob
    ((${#matches[@]} > 0))
}

resolve_paths() {
    local input="${REPO_DIR:-${KONFLUX_RELEASE_DATA_REPO:-${PWD}}}"
    local git_root

    [[ -d "${input}" ]] || die "Directory not found: ${input}"
    input=$(cd "${input}" && pwd)

    if is_rpa_directory "${input}"; then
        RPA_DIR="${input}"
        git_root=$(git -C "${input}" rev-parse --show-toplevel 2>/dev/null) \
            || die "RPA directory is not inside a git repository: ${input}"
        REPO_DIR="${git_root}"
        log "Using RPA directory: ${RPA_DIR}"
        return
    fi

    if [[ -d "${input}/${RPA_REL_DIR}" ]] && is_rpa_directory "${input}/${RPA_REL_DIR}"; then
        git_root=$(git -C "${input}" rev-parse --show-toplevel 2>/dev/null) \
            || die "Directory is not inside a git repository: ${input}"
        REPO_DIR="${git_root}"
        RPA_DIR="${input}/${RPA_REL_DIR}"
        log "Using repository: ${REPO_DIR}"
        log "Using RPA directory: ${RPA_DIR}"
        return
    fi

    die "Could not find RPA YAML files at ${input}/${RPA_REL_DIR}. Pass --repo-dir to the konflux-release-data root."
}

collect_target_files() {
    local rpa_dir="$1"
    local stream_dashed="$2"
    local file

    shopt -s nullglob
    for file in \
        "${rpa_dir}/rhdh-${stream_dashed}-prod.yaml" \
        "${rpa_dir}/rhdh-${stream_dashed}-stage.yaml" \
        "${rpa_dir}/rhdh-plugin-catalog-${stream_dashed}-prod.yaml" \
        "${rpa_dir}/rhdh-plugin-catalog-${stream_dashed}-stage.yaml"
    do
        [[ -f "${file}" ]] || die "Expected RPA file not found: ${file}"
        printf '%s\n' "${file}"
    done
    shopt -u nullglob
}

collect_stale_versions() {
    local stream="$1"
    shift
    local files=("$@")
    local file
    local matches=()

    for file in "${files[@]}"; do
        while IFS= read -r match; do
            [[ -n "${match}" ]] && matches+=("${match}")
        done < <(grep -oE "\"${stream//./\\.}\\.[0-9]+\"" "${file}" \
            | tr -d '"' \
            | sort -u)
    done

    if ((${#matches[@]} == 0)); then
        die "Could not detect current patch version in target RPAs for stream ${stream}"
    fi

    printf '%s\n' "${matches[@]}" | sort -uV | while IFS= read -r candidate; do
        if [[ "${candidate}" != "${NEW_VERSION}" ]]; then
            printf '%s\n' "${candidate}"
        fi
    done
}

detect_from_version() {
    local versions
    mapfile -t versions < <(collect_stale_versions "$@")

    if ((${#versions[@]} == 0)); then
        die "All tag versions already appear to be ${NEW_VERSION}. Nothing to update."
    fi

    if ((${#versions[@]} > 1)); then
        warn "Multiple stale patch versions found: ${versions[*]}. Replacing all with ${NEW_VERSION}."
    fi

    printf '%s\n' "${versions[@]}"
}

count_replacements() {
    local from_version="$1"
    local file="$2"

    if grep -q "${from_version}" "${file}" 2>/dev/null; then
        grep -o "${from_version}" "${file}" | wc -l | tr -d ' '
    else
        echo 0
    fi
}

apply_replacements() {
    local from_version="$1"
    local file="$2"
    local count

    count=$(count_replacements "${from_version}" "${file}")
    if [[ "${count}" == "0" ]]; then
        return 0
    fi

    log "Updating ${count} tag reference(s) in $(basename "${file}") (${from_version} -> ${NEW_VERSION})"
    if [[ ${DRY_RUN} -eq 1 ]]; then
        return 0
    fi

    sed -i "s/${from_version}/${NEW_VERSION}/g" "${file}"
}

open_url_in_browser() {
    local url="$1"

    if command -v brave-browser >/dev/null 2>&1; then
        log "Opening merge request in Brave"
        brave-browser "${url}" >/dev/null 2>&1 &
    elif command -v google-chrome >/dev/null 2>&1; then
        log "Opening merge request in Chrome"
        google-chrome "${url}" >/dev/null 2>&1 &
    elif command -v firefox >/dev/null 2>&1; then
        log "Opening merge request in Firefox"
        firefox "${url}" >/dev/null 2>&1 &
    elif command -v xdg-open >/dev/null 2>&1; then
        log "Opening merge request via xdg-open"
        xdg-open "${url}" >/dev/null 2>&1 &
    else
        warn "No supported browser found. Open manually: ${url}"
    fi
}

ensure_clean_enough() {
    local repo_dir="$1"

    if [[ ${DRY_RUN} -eq 1 ]]; then
        return 0
    fi

    if ! git -C "${repo_dir}" diff --quiet || ! git -C "${repo_dir}" diff --cached --quiet; then
        die "Repository has uncommitted changes. Commit or stash before running."
    fi
}

ensure_push_remote_is_upstream() {
    local repo_dir="$1"
    local url

    url=$(git -C "${repo_dir}" remote get-url "${PUSH_REMOTE}")
    if [[ "${url}" == *"rhdh-bot/"* ]] || [[ "${url}" == *"rhdh-bot:"* ]]; then
        die "origin remote points to fork (${url}). Expected releng/konflux-release-data."
    fi
    if [[ "${url}" != *"releng/konflux-release-data"* ]]; then
        warn "origin remote is not releng/konflux-release-data: ${url}"
    fi
}

verify_branch_on_remote() {
    local repo_dir="$1"
    local branch="$2"
    local local_sha
    local remote_sha

    local_sha=$(git -C "${repo_dir}" rev-parse "${branch}")
    remote_sha=$(git -C "${repo_dir}" ls-remote "${PUSH_REMOTE}" "refs/heads/${branch}" | awk '{print $1}')

    [[ -n "${remote_sha}" ]] || die "Branch ${branch} was not found on ${PUSH_REMOTE} after push"
    [[ "${local_sha}" == "${remote_sha}" ]] \
        || die "Branch ${branch} on ${PUSH_REMOTE} (${remote_sha}) does not match local commit (${local_sha})"
}

verify_merge_request_has_changes() {
    local project="$1"
    local branch="$2"
    local changes_count

    changes_count=$(glab api "projects/${project//\//%2F}/merge_requests" \
        --method GET \
        -f source_branch="${branch}" \
        -f state=opened \
        -f per_page=1 2>/dev/null \
        | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data[0].get("changes_count") if data else "")' 2>/dev/null || true)

    if [[ -z "${changes_count}" || "${changes_count}" == "0" || "${changes_count}" == "None" ]]; then
        die "Merge request for ${branch} has no changes. Ensure the branch was pushed to origin (${project}), not a fork."
    fi

    log "Merge request includes ${changes_count} changed file(s)"
}

create_merge_request() {
    local repo_dir="$1"
    local branch="$2"
    local stream_dashed="$3"
    local title
    local description
    local mr_url

    command -v glab >/dev/null 2>&1 || die "glab is required to create a merge request"

    ensure_push_remote_is_upstream "${repo_dir}"

    title="chore: update rhdh-${stream_dashed}-*.yaml RPAs for upcoming release ${NEW_VERSION}"
    description="Generated-by: cursor

#### What:

chore: update rhdh-${stream_dashed}-*.yaml RPAs for upcoming release ${NEW_VERSION}

Bump ReleasePlanAdmission tags to ${NEW_VERSION} for the ${stream_dashed} stream."

    if ((${#FROM_VERSIONS[@]} == 1)); then
        description="${description}
Replaced ${FROM_VERSIONS[0]} tag references."
    else
        description="${description}
Replaced stale patch tag references: ${FROM_VERSIONS[*]}."
    fi

    description="${description}

#### Why:

Prepare konflux-release-data for the upcoming RHDH ${NEW_VERSION} release.

#### Tickets:"

    log "Pushing branch ${branch} to ${PUSH_REMOTE} (${GITLAB_PROJECT})"
    pushd "${repo_dir}" >/dev/null
    git push -u "${PUSH_REMOTE}" "${branch}"
    verify_branch_on_remote "${repo_dir}" "${branch}"

    log "Creating merge request in ${GITLAB_PROJECT} (${branch} -> ${BASE_BRANCH})"
    mr_url=$(glab api --method POST "projects/${GITLAB_PROJECT//\//%2F}/merge_requests" \
        -f source_branch="${branch}" \
        -f target_branch="${BASE_BRANCH}" \
        -f title="${title}" \
        -f description="${description}" \
        -f remove_source_branch=true 2>/dev/null \
        | python3 -c 'import json,sys; m=json.load(sys.stdin); print(m["web_url"])') || {
        popd >/dev/null
        die "glab api merge_requests create failed (check glab auth: glab auth login -h gitlab.cee.redhat.com)"
    }

    verify_merge_request_has_changes "${GITLAB_PROJECT}" "${branch}"
    popd >/dev/null

    [[ -n "${mr_url}" ]] || die "Merge request created but URL was empty"
    log "Merge request: ${mr_url}"
    open_url_in_browser "${mr_url}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h | --help)
            usage
            exit 0
            ;;
        --repo-dir)
            REPO_DIR=$2
            shift 2
            ;;
        --base-branch)
            BASE_BRANCH=$2
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --validate)
            VALIDATE=1
            shift
            ;;
        -*)
            die "Unknown option: $1"
            ;;
        *)
            if [[ -z "${NEW_VERSION}" ]]; then
                NEW_VERSION=$1
            else
                die "Unexpected argument: $1"
            fi
            shift
            ;;
    esac
done

[[ -n "${NEW_VERSION}" ]] || {
    usage
    exit 1
}

validate_version "${NEW_VERSION}"

REPO_DIR=""
RPA_DIR=""
resolve_paths

STREAM=$(version_stream "${NEW_VERSION}")
STREAM_DASHED=$(version_stream_dashed "${NEW_VERSION}")

mapfile -t TARGET_FILES < <(collect_target_files "${RPA_DIR}" "${STREAM_DASHED}")

mapfile -t FROM_VERSIONS < <(detect_from_version "${STREAM}" "${TARGET_FILES[@]}")

if ((${#FROM_VERSIONS[@]} == 0)); then
    die "No source versions to replace"
fi

for FROM_VERSION in "${FROM_VERSIONS[@]}"; do
    if [[ "${FROM_VERSION}" == "${NEW_VERSION}" ]]; then
        die "Source and target versions are the same (${NEW_VERSION})"
    fi
done

log "Repository: ${REPO_DIR}"
log "Stream: ${STREAM} (${STREAM_DASHED})"
if ((${#FROM_VERSIONS[@]} == 1)); then
    log "Updating tags: ${FROM_VERSIONS[0]} -> ${NEW_VERSION}"
else
    log "Updating tags: ${FROM_VERSIONS[*]} -> ${NEW_VERSION}"
fi
log "Target files:"
for file in "${TARGET_FILES[@]}"; do
    log "  - $(basename "${file}")"
done

TOTAL=0
for FROM_VERSION in "${FROM_VERSIONS[@]}"; do
    for file in "${TARGET_FILES[@]}"; do
        count=$(count_replacements "${FROM_VERSION}" "${file}")
        TOTAL=$((TOTAL + count))
    done
done

if [[ "${TOTAL}" == "0" ]]; then
    warn "No stale tag versions found in target RPAs; nothing changed"
    exit 0
fi

if [[ ${DRY_RUN} -eq 1 ]]; then
    for FROM_VERSION in "${FROM_VERSIONS[@]}"; do
        for file in "${TARGET_FILES[@]}"; do
            count=$(count_replacements "${FROM_VERSION}" "${file}")
            if [[ "${count}" != "0" ]]; then
                log "Would update ${count} tag reference(s) in $(basename "${file}") (${FROM_VERSION} -> ${NEW_VERSION})"
            fi
        done
    done
    log "Dry run complete (${TOTAL} replacement(s) would be made)"
    exit 0
fi

ensure_clean_enough "${REPO_DIR}"

BRANCH="chore/rhdh-update-rpa-${NEW_VERSION}"
COMMIT_SUBJECT="chore: update rhdh-${STREAM_DASHED}-*.yaml RPAs for upcoming release ${NEW_VERSION}"

log "Creating branch ${BRANCH} from ${BASE_BRANCH}"
git -C "${REPO_DIR}" fetch origin "${BASE_BRANCH}"
git -C "${REPO_DIR}" checkout "${BASE_BRANCH}"
git -C "${REPO_DIR}" pull --ff-only origin "${BASE_BRANCH}"
git -C "${REPO_DIR}" checkout -B "${BRANCH}"

for FROM_VERSION in "${FROM_VERSIONS[@]}"; do
    for file in "${TARGET_FILES[@]}"; do
        apply_replacements "${FROM_VERSION}" "${file}"
    done
done

REL_PATHS=()
for file in "${TARGET_FILES[@]}"; do
    REL_PATHS+=("${file#"${REPO_DIR}"/}")
done

git -C "${REPO_DIR}" add "${REL_PATHS[@]}"
git -C "${REPO_DIR}" commit -s -m "${COMMIT_SUBJECT}"

if [[ ${VALIDATE} -eq 1 ]]; then
    log "Running tox -e test"
    (cd "${REPO_DIR}" && tox -e test)
fi

create_merge_request "${REPO_DIR}" "${BRANCH}" "${STREAM_DASHED}"

log "Done"

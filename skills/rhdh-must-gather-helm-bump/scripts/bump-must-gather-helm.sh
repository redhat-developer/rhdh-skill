#!/usr/bin/env bash
#
# Bump Helm in rhdh-must-gather upstream and mirror into rhidp/rhdh distgit + Tekton.
# See skills/rhdh-must-gather-helm-bump/SKILL.md
#
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

DISTGIT_REL="distgit/containers/rhdh-must-gather"

PREFETCH_CGW='[{"type": "rpm", "path": "distgit/containers/rhdh-must-gather"},{"type": "pip", "path": "distgit/containers/rhdh-must-gather", "allow_binary": "false"},{"type": "generic", "path": "distgit/containers/rhdh-must-gather"},{"type": "cargo", "path": "distgit/containers/rhdh-must-gather/vendor/websocat"}]'

PREFETCH_VENDOR='[{"type": "rpm", "path": "distgit/containers/rhdh-must-gather"},{"type": "pip", "path": "distgit/containers/rhdh-must-gather", "allow_binary": "false"},{"type": "gomod", "path": "distgit/containers/rhdh-must-gather/vendor/helm"},{"type": "cargo", "path": "distgit/containers/rhdh-must-gather/vendor/websocat"}]'

SYNC_REL_PATHS=(
    Makefile
    artifacts.lock.yaml
    Containerfile
    .rhdh/docker/Containerfile
    hack/check-helm-binary-available.sh
    hack/install-helm-binary.sh
    hack/install-helm-local.sh
    hack/update-helm-lockfile.sh
    hack/update-vendor.sh
)

TO_VERSION=""
UPSTREAM_DIR=""
DOWNSTREAM_DIR=""
CHECK_ONLY=0
SKIP_UPSTREAM=0
SKIP_DOWNSTREAM=0
DRY_RUN=0
ALLOW_DIRTY=0

usage() {
    cat <<'EOF'
Bump Helm in rhdh-must-gather and mirror into rhidp/rhdh distgit + .tekton prefetch.

Usage:
  bump-must-gather-helm.sh --to VERSION [OPTIONS]

Required:
  --to VERSION              Target Helm version (4.3.0 or v4.3.0)

Repo selection (provide upstream+downstream or --parent-dir):
  --upstream PATH           rhdh-must-gather checkout
  --downstream PATH         rhidp/rhdh midstream checkout
  --parent-dir PATH         Auto-discover 1-must-gather + 4-rhdh (and aliases)

Workflow:
  --check                   Probe CGW only; print planned path
  --skip-upstream           Sync downstream + Tekton only
  --skip-downstream         Bump upstream only
  --dry-run                 Print actions without writing
  --allow-dirty             Proceed with uncommitted changes

Examples:
  bump-must-gather-helm.sh --to 4.3.0 --parent-dir ~/RHDH
  bump-must-gather-helm.sh --to v4.3.0 --upstream ~/RHDH/1-must-gather --downstream ~/RHDH/4-rhdh
  bump-must-gather-helm.sh --to 4.3.0 --check --parent-dir ~/RHDH
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

run_cmd() {
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[DRY-RUN] $*" >&2
    else
        "$@"
    fi
}

normalize_version() {
    local v="$1"
    v="${v#v}"
    if [[ ! "${v}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]]; then
        die "Invalid Helm version '${v}'. Expected semver like 4.3.0"
    fi
    printf '%s' "${v}"
}

discover_repo() {
    local parent="$1"
    shift
    local name candidate
    for name in "$@"; do
        candidate="${parent%/}/${name}"
        if [[ -d "${candidate}" ]]; then
            printf '%s' "${candidate}"
            return 0
        fi
    done
    return 1
}

validate_upstream() {
    local dir="$1"
    [[ -f "${dir}/Makefile" ]] || die "Not a must-gather repo (missing Makefile): ${dir}"
    [[ -f "${dir}/hack/update-helm-lockfile.sh" ]] || die "Missing hack/update-helm-lockfile.sh in ${dir}"
    [[ -d "${dir}/collection-scripts" ]] || die "Missing collection-scripts/ in ${dir}"
}

validate_downstream() {
    local dir="$1"
    [[ -d "${dir}/${DISTGIT_REL}" ]] || die "Missing ${DISTGIT_REL} in ${dir}"
    [[ -f "${dir}/.tekton/rhdh-must-gather-2-pull.yaml" ]] || die "Missing .tekton/rhdh-must-gather-2-pull.yaml in ${dir}"
}

assert_clean_tree() {
    local dir="$1"
    local label="$2"
    if [[ "${ALLOW_DIRTY}" -eq 1 ]]; then
        return 0
    fi
    if ! git -C "${dir}" diff --quiet 2>/dev/null || ! git -C "${dir}" diff --cached --quiet 2>/dev/null; then
        die "${label} has uncommitted changes (${dir}). Commit/stash or pass --allow-dirty"
    fi
}

cgw_available() {
    local upstream="$1"
    local version="$2"
    "${upstream}/hack/check-helm-binary-available.sh" "${version}"
}

read_makefile_helm_version() {
    local makefile="$1"
    grep '^HELM_VERSION := ' "${makefile}" | sed 's/^HELM_VERSION := *//'
}

bump_upstream_cgw() {
    local upstream="$1"
    local version="$2"
    log "Upstream: refreshing CGW lockfile for helm v${version}..."
    run_cmd bash -c "cd '${upstream}' && ./hack/update-helm-lockfile.sh 'v${version}'"
}

bump_upstream_vendor() {
    local upstream="$1"
    local version="$2"
    log "Upstream: vendoring helm v${version} source..."
    run_cmd bash -c "cd '${upstream}' && ./hack/update-vendor.sh helm 'v${version}'"
}

sync_to_distgit() {
    local upstream="$1"
    local downstream="$2"
    local mode="$3"
    local dest="${downstream}/${DISTGIT_REL}"

    log "Syncing helm-related files to ${dest}..."
    local rel
    for rel in "${SYNC_REL_PATHS[@]}"; do
        local src="${upstream}/${rel}"
        if [[ ! -e "${src}" ]]; then
            warn "Skipping missing upstream path: ${rel}"
            continue
        fi
        local dst="${dest}/${rel}"
        local dst_parent
        dst_parent=$(dirname "${dst}")
        if [[ "${DRY_RUN}" -eq 1 ]]; then
            echo "[DRY-RUN] cp -pPR '${src}' -> '${dst}'" >&2
        else
            mkdir -p "${dst_parent}"
            cp -pPR "${src}" "${dst}"
        fi
    done

    if [[ "${mode}" == "vendor" ]]; then
        if [[ "${DRY_RUN}" -eq 1 ]]; then
            echo "[DRY-RUN] rsync -a --delete '${upstream}/vendor/helm/' -> '${dest}/vendor/helm/'" >&2
        else
            mkdir -p "${dest}/vendor"
            rsync -a --delete "${upstream}/vendor/helm/" "${dest}/vendor/helm/"
        fi
    elif [[ -d "${dest}/vendor/helm" ]]; then
        warn "distgit still has vendor/helm/ but CGW path is active — remove vendor/helm manually if switching from vendored build"
    fi
}

replace_prefetch_in_file() {
    local file="$1"
    local prefetch="$2"
    local tmp
    tmp=$(mktemp)
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[DRY-RUN] update prefetch in ${file}" >&2
        rm -f "${tmp}"
        return 0
    fi
    awk -v prefetch="${prefetch}" '
        $0 ~ /^[[:space:]]*- name: prefetch-input$/ {
            print
            if ((getline line) > 0 && line ~ /^[[:space:]]*value:/) {
                match(line, /^[[:space:]]*/)
                indent = substr(line, 1, RLENGTH)
                print indent "value: '\''" prefetch "'\''"
            } else {
                print line
            }
            next
        }
        $0 ~ /^[[:space:]]*prefetch_input:/ {
            match($0, /^[[:space:]]*/)
            indent = substr($0, 1, RLENGTH)
            print indent "prefetch_input: '\''" prefetch "'\''"
            next
        }
        { print }
    ' "${file}" > "${tmp}"
    mv "${tmp}" "${file}"
}

update_tekton_prefetch() {
    local downstream="$1"
    local mode="$2"
    local prefetch="${PREFETCH_CGW}"
    if [[ "${mode}" == "vendor" ]]; then
        prefetch="${PREFETCH_VENDOR}"
    fi

    log "Downstream: setting Tekton prefetch to ${mode} mode..."
    replace_prefetch_in_file "${downstream}/.tekton/rhdh-must-gather-2-pull.yaml" "${prefetch}"
    replace_prefetch_in_file "${downstream}/.tekton/rhdh-must-gather-2-push.yaml" "${prefetch}"
    replace_prefetch_in_file "${downstream}/.tekton-templates/components.yaml" "${prefetch}"
}

print_vendor_reminders() {
    cat >&2 <<'EOF'
[WARN] Vendored helm path selected. Manual steps still required:
  1. In upstream Containerfile and .rhdh/docker/Containerfile:
     - Comment out Stage 2a (CGW helm-builder)
     - Uncomment Stage 2b (go-toolset + vendor/helm)
  2. Re-sync distgit Containerfiles after editing upstream .rhdh/docker/Containerfile
  3. Confirm distgit/vendor/helm is present and artifacts.lock.yaml is not used for helm
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --to)
            TO_VERSION=$(normalize_version "${2:-}")
            shift 2
            ;;
        --upstream)
            UPSTREAM_DIR="${2:-}"
            shift 2
            ;;
        --downstream)
            DOWNSTREAM_DIR="${2:-}"
            shift 2
            ;;
        --parent-dir)
            parent="${2:-}"
            [[ -n "${parent}" ]] || die "--parent-dir requires a path"
            if [[ -z "${UPSTREAM_DIR}" ]]; then
                UPSTREAM_DIR=$(discover_repo "${parent}" 1-must-gather rhdh-must-gather must-gather) \
                    || die "Could not find must-gather under ${parent}"
            fi
            if [[ -z "${DOWNSTREAM_DIR}" ]]; then
                DOWNSTREAM_DIR=$(discover_repo "${parent}" 4-rhdh rhdh rhidp-rhdh) \
                    || die "Could not find rhidp/rhdh midstream under ${parent}"
            fi
            shift 2
            ;;
        --check)
            CHECK_ONLY=1
            shift
            ;;
        --skip-upstream)
            SKIP_UPSTREAM=1
            shift
            ;;
        --skip-downstream)
            SKIP_DOWNSTREAM=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --allow-dirty)
            ALLOW_DIRTY=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown option: $1 (try --help)"
            ;;
    esac
done

[[ -n "${TO_VERSION}" ]] || die "--to VERSION is required"

if [[ "${SKIP_UPSTREAM}" -eq 0 ]]; then
    [[ -n "${UPSTREAM_DIR}" ]] || die "Set --upstream or --parent-dir"
    UPSTREAM_DIR=$(cd "${UPSTREAM_DIR}" && pwd)
    validate_upstream "${UPSTREAM_DIR}"
fi

if [[ "${SKIP_DOWNSTREAM}" -eq 0 ]]; then
    [[ -n "${DOWNSTREAM_DIR}" ]] || die "Set --downstream or --parent-dir"
    DOWNSTREAM_DIR=$(cd "${DOWNSTREAM_DIR}" && pwd)
    validate_downstream "${DOWNSTREAM_DIR}"
fi

if [[ "${SKIP_UPSTREAM}" -eq 0 && "${SKIP_DOWNSTREAM}" -eq 1 ]]; then
    :
elif [[ -n "${UPSTREAM_DIR}" && -n "${DOWNSTREAM_DIR}" ]]; then
  log "Upstream:  ${UPSTREAM_DIR}"
  log "Downstream: ${DOWNSTREAM_DIR}"
fi

MODE="cgw"
if [[ "${SKIP_UPSTREAM}" -eq 0 ]]; then
    if cgw_available "${UPSTREAM_DIR}" "${TO_VERSION}"; then
        MODE="cgw"
        log "CGW mirror has helm v${TO_VERSION} linux-amd64/arm64 binaries"
    else
        MODE="vendor"
        warn "CGW mirror has no helm v${TO_VERSION} linux-amd64/arm64 — vendored source path"
    fi
else
    if [[ -f "${DOWNSTREAM_DIR}/${DISTGIT_REL}/artifacts.lock.yaml" ]] \
        && grep -q "cgw/helm/${TO_VERSION}/" "${DOWNSTREAM_DIR}/${DISTGIT_REL}/artifacts.lock.yaml" 2>/dev/null; then
        MODE="cgw"
    elif [[ -d "${DOWNSTREAM_DIR}/${DISTGIT_REL}/vendor/helm" ]]; then
        MODE="vendor"
    else
        die "Cannot infer CGW vs vendor mode with --skip-upstream; ensure distgit has artifacts.lock.yaml or vendor/helm"
    fi
    log "Inferred mode: ${MODE}"
fi

if [[ "${CHECK_ONLY}" -eq 1 ]]; then
    echo "helm_version=${TO_VERSION}"
    echo "mode=${MODE}"
    echo "upstream=${UPSTREAM_DIR:-}"
    echo "downstream=${DOWNSTREAM_DIR:-}"
    if [[ "${MODE}" == "vendor" ]]; then
        print_vendor_reminders
    fi
    exit 0
fi

if [[ "${SKIP_UPSTREAM}" -eq 0 ]]; then
    assert_clean_tree "${UPSTREAM_DIR}" "Upstream"
    current=$(read_makefile_helm_version "${UPSTREAM_DIR}/Makefile")
    if [[ "${current}" == "${TO_VERSION}" ]]; then
        log "Upstream HELM_VERSION already ${TO_VERSION}"
    else
        log "Upstream HELM_VERSION: ${current} -> ${TO_VERSION}"
    fi
    if [[ "${MODE}" == "cgw" ]]; then
        bump_upstream_cgw "${UPSTREAM_DIR}" "${TO_VERSION}"
    else
        bump_upstream_vendor "${UPSTREAM_DIR}" "${TO_VERSION}"
    fi
fi

if [[ "${SKIP_DOWNSTREAM}" -eq 0 ]]; then
    assert_clean_tree "${DOWNSTREAM_DIR}" "Downstream"
    [[ -n "${UPSTREAM_DIR}" ]] || die "--skip-upstream requires a prior upstream bump in distgit; pass --upstream for sync source"
    sync_to_distgit "${UPSTREAM_DIR}" "${DOWNSTREAM_DIR}" "${MODE}"
    update_tekton_prefetch "${DOWNSTREAM_DIR}" "${MODE}"
fi

log "Done. Review git diff in each repo before committing."
if [[ "${MODE}" == "vendor" ]]; then
    print_vendor_reminders
fi

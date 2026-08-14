#!/usr/bin/env bash
#
# Bump Helm in rhdh-must-gather upstream and mirror into rhidp/rhdh distgit + Tekton.
# See skills/rhdh-must-gather-helm-bump/SKILL.md
#
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

DISTGIT_REL="distgit/containers/rhdh-must-gather"
UPSTREAM_SHA_REL="sync/upstream_SHA_rhdh-must-gather"
RHDH_DOCKER_CF=".rhdh/docker/Containerfile"

PREFETCH_CGW='[{"type": "rpm", "path": "distgit/containers/rhdh-must-gather"},{"type": "pip", "path": "distgit/containers/rhdh-must-gather", "allow_binary": "false"},{"type": "generic", "path": "distgit/containers/rhdh-must-gather"},{"type": "cargo", "path": "distgit/containers/rhdh-must-gather/vendor/websocat"}]'

PREFETCH_VENDOR='[{"type": "rpm", "path": "distgit/containers/rhdh-must-gather"},{"type": "pip", "path": "distgit/containers/rhdh-must-gather", "allow_binary": "false"},{"type": "gomod", "path": "distgit/containers/rhdh-must-gather/vendor/helm"},{"type": "cargo", "path": "distgit/containers/rhdh-must-gather/vendor/websocat"}]'

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
  --check                   Probe CGW only; print planned path (helm_version=, mode=, ...)
  --skip-upstream           Sync downstream + Tekton + upstream SHA only
  --skip-downstream         Bump upstream only
  --dry-run                 Print actions without writing
  --allow-dirty             Proceed with uncommitted changes

Syncs Makefile, artifacts.lock.yaml, hack/, .rhdh/docker/Containerfile, and
vendor/ (omits vendor/helm on CGW). Regenerates distgit Containerfile from
.rhdh/docker/Containerfile (preserves RHDH_MUST_GATHER_VERSION / MIDSTREAM_REPO).
Flips Stage 2a/2b to match mode. Updates sync/upstream_SHA_rhdh-must-gather.

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

require_value() {
    local flag="$1"
    local value="${2:-}"
    [[ -n "${value}" ]] || die "${flag} requires a value"
    printf '%s' "${value}"
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
    [[ -f "${dir}/.tekton/rhdh-must-gather-2-push.yaml" ]] || die "Missing .tekton/rhdh-must-gather-2-push.yaml in ${dir}"
    [[ -f "${dir}/.tekton-templates/components.yaml" ]] || die "Missing .tekton-templates/components.yaml in ${dir}"
}

assert_clean_tree() {
    local dir="$1"
    local label="$2"
    if [[ "${ALLOW_DIRTY}" -eq 1 ]]; then
        return 0
    fi
    if [[ -n "$(git -C "${dir}" status --porcelain 2>/dev/null)" ]]; then
        die "${label} has uncommitted or untracked changes (${dir}). Commit/stash or pass --allow-dirty"
    fi
}

cgw_available() {
    local upstream="$1"
    local version="$2"
    "${upstream}/hack/check-helm-binary-available.sh" "${version}"
}

read_makefile_helm_version() {
    local makefile="$1"
    local line
    line=$(grep '^HELM_VERSION := ' "${makefile}" 2>/dev/null || true)
    [[ -n "${line}" ]] || die "No HELM_VERSION := line in ${makefile}"
    printf '%s' "${line#HELM_VERSION := }"
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

# Bidirectional Stage 2a/2b comment flip. Doc-only comments stay commented.
flip_helm_stages() {
    local file="$1"
    local mode="$2"
    local tmp

    [[ -f "${file}" ]] || die "Missing Containerfile for stage flip: ${file}"

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[DRY-RUN] flip Stage 2a/2b to mode=${mode} in ${file}" >&2
        return 0
    fi

    tmp=$(mktemp)
    awk -v mode="${mode}" '
        BEGIN { stage = "" }
        /^# Stage 2a:/ { stage = "2a"; print; next }
        /^# Stage 2b:/ { stage = "2b"; print; next }
        /^# Stage / { stage = ""; print; next }

        stage == "" { print; next }

        # Documentation lines inside Stage 2a/2b — never toggle
        /^# Comment this out/ || /^# Swap with/ || /^# update via/ || /^# https:\/\// {
            print
            next
        }
        /^[[:space:]]*$/ { print; next }

        {
            want_active = 0
            if (stage == "2a" && mode == "cgw") want_active = 1
            if (stage == "2b" && mode == "vendor") want_active = 1

            line = $0
            if (want_active) {
                if (line ~ /^# /) sub(/^# /, "", line)
                print line
            } else {
                if (line ~ /^# /) print line
                else print "# " line
            }
        }
    ' "${file}" > "${tmp}"
    mv "${tmp}" "${file}"
    log "Flipped Stage 2a/2b to mode=${mode} in ${file}"
}

sync_path() {
    local src="$1"
    local dst="$2"
    local dst_parent
    dst_parent=$(dirname "${dst}")
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[DRY-RUN] cp -pPR '${src}' -> '${dst}'" >&2
        return 0
    fi
    mkdir -p "${dst_parent}"
    # Replace destination file/dir atomically for directories via rsync when both dirs
    if [[ -d "${src}" ]]; then
        mkdir -p "${dst}"
        rsync -a --delete "${src}/" "${dst}/"
    else
        cp -pPR "${src}" "${dst}"
    fi
}

sync_to_distgit() {
    local upstream="$1"
    local downstream="$2"
    local mode="$3"
    local dest="${downstream}/${DISTGIT_REL}"

    log "Syncing helm-related files to ${dest}..."

    local rel
    for rel in Makefile artifacts.lock.yaml; do
        if [[ ! -e "${upstream}/${rel}" ]]; then
            warn "Skipping missing upstream path: ${rel}"
            continue
        fi
        sync_path "${upstream}/${rel}" "${dest}/${rel}"
    done

    if [[ -d "${upstream}/hack" ]]; then
        sync_path "${upstream}/hack" "${dest}/hack"
    else
        warn "Skipping missing upstream hack/"
    fi

    if [[ -f "${upstream}/${RHDH_DOCKER_CF}" ]]; then
        sync_path "${upstream}/${RHDH_DOCKER_CF}" "${dest}/${RHDH_DOCKER_CF}"
    else
        warn "Skipping missing upstream ${RHDH_DOCKER_CF}"
    fi

    # Never copy upstream root Containerfile onto distgit (hermetic derivation).
    if [[ -d "${upstream}/vendor" ]]; then
        if [[ "${DRY_RUN}" -eq 1 ]]; then
            if [[ "${mode}" == "cgw" ]]; then
                echo "[DRY-RUN] rsync vendor/ -> distgit (exclude helm/)" >&2
            else
                echo "[DRY-RUN] rsync vendor/ -> distgit (include helm/)" >&2
            fi
        else
            mkdir -p "${dest}/vendor"
            if [[ "${mode}" == "cgw" ]]; then
                rsync -a --delete --exclude helm/ "${upstream}/vendor/" "${dest}/vendor/"
                if [[ -d "${dest}/vendor/helm" ]]; then
                    log "Removing stale distgit vendor/helm/ (CGW path active)"
                    rm -rf "${dest}/vendor/helm"
                fi
            else
                rsync -a --delete "${upstream}/vendor/" "${dest}/vendor/"
            fi
        fi
    else
        warn "Skipping missing upstream vendor/"
        if [[ "${mode}" == "cgw" && -d "${dest}/vendor/helm" ]]; then
            if [[ "${DRY_RUN}" -eq 1 ]]; then
                echo "[DRY-RUN] rm -rf '${dest}/vendor/helm'" >&2
            else
                log "Removing stale distgit vendor/helm/ (CGW path active)"
                rm -rf "${dest}/vendor/helm"
            fi
        fi
    fi
}

# Mimic sync-midstream: derive distgit Containerfile from .rhdh/docker/Containerfile,
# preserving ARG RHDH_MUST_GATHER_VERSION and the Brew/Konflux metadata footer
# (ENV SUMMARY=… / LABEL …) that sync-midstream appends after ENTRYPOINT.
regenerate_distgit_containerfile() {
    local dest="$1"
    local src="${dest}/${RHDH_DOCKER_CF}"
    local out="${dest}/Containerfile"
    local existing_version="" footer="" tmp

    [[ -f "${src}" ]] || die "Missing ${src}; cannot regenerate distgit Containerfile"

    if [[ -f "${out}" ]]; then
        existing_version=$(sed -n 's/^ARG RHDH_MUST_GATHER_VERSION="\(.*\)"/\1/p' "${out}" | head -n1)
        # Footer is midstream-only branding appended after the upstream-derived body.
        footer=$(awk '/^ENV SUMMARY=/{p=1} p{print}' "${out}" || true)
    fi

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[DRY-RUN] regenerate ${out} from ${src} (preserve VERSION='${existing_version}' footer=$([ -n "${footer}" ] && echo yes || echo no))" >&2
        return 0
    fi

    tmp=$(mktemp)
    cp -pPR "${src}" "${tmp}"
    if [[ -n "${existing_version}" ]]; then
        sed -i.bak -e "s/RHDH_MUST_GATHER_VERSION=.*/RHDH_MUST_GATHER_VERSION=\"${existing_version}\"/" "${tmp}"
        rm -f "${tmp}.bak"
    fi
    if [[ -n "${footer}" ]]; then
        printf '\n%s\n' "${footer}" >> "${tmp}"
    fi
    mv "${tmp}" "${out}"
    log "Regenerated ${DISTGIT_REL}/Containerfile from ${RHDH_DOCKER_CF}"
}

update_upstream_sha() {
    local upstream="$1"
    local downstream="$2"
    local sha_file="${downstream}/${UPSTREAM_SHA_REL}"
    local sha branch remote_url line parent

    sha=$(git -C "${upstream}" rev-parse --short HEAD)
    branch=$(git -C "${upstream}" rev-parse --abbrev-ref HEAD)
    remote_url=$(git -C "${upstream}" remote get-url origin 2>/dev/null || true)
    if [[ -z "${remote_url}" ]]; then
        remote_url="https://github.com/redhat-developer/rhdh-must-gather"
    fi
    line="${sha} = ${branch} @ ${remote_url}"

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[DRY-RUN] write '${sha_file}': ${line}" >&2
        return 0
    fi

    parent=$(dirname "${sha_file}")
    mkdir -p "${parent}"
    printf '%s\n' "${line}" > "${sha_file}"
    log "Updated ${UPSTREAM_SHA_REL} -> ${sha}"
}

replace_prefetch_plr() {
    local file="$1"
    local prefetch="$2"
    local tmp
    tmp=$(mktemp)
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[DRY-RUN] update prefetch-input in ${file}" >&2
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
        { print }
    ' "${file}" > "${tmp}"
    mv "${tmp}" "${file}"
}

# Only rewrite prefetch_input under the must-gather: component block.
replace_prefetch_components() {
    local file="$1"
    local prefetch="$2"
    local tmp
    tmp=$(mktemp)
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[DRY-RUN] update must-gather.prefetch_input in ${file}" >&2
        rm -f "${tmp}"
        return 0
    fi
    awk -v prefetch="${prefetch}" '
        BEGIN { in_mg = 0 }
        /^[a-zA-Z0-9_-]+:/ {
            in_mg = ($0 ~ /^must-gather:/)
            print
            next
        }
        in_mg && /^[[:space:]]*prefetch_input:/ {
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

    log "Downstream: setting Tekton prefetch to ${mode} mode (must-gather only)..."
    replace_prefetch_plr "${downstream}/.tekton/rhdh-must-gather-2-pull.yaml" "${prefetch}"
    replace_prefetch_plr "${downstream}/.tekton/rhdh-must-gather-2-push.yaml" "${prefetch}"
    replace_prefetch_components "${downstream}/.tekton-templates/components.yaml" "${prefetch}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --to)
            TO_VERSION=$(normalize_version "$(require_value --to "${2:-}")")
            shift 2
            ;;
        --upstream)
            UPSTREAM_DIR=$(require_value --upstream "${2:-}")
            shift 2
            ;;
        --downstream)
            DOWNSTREAM_DIR=$(require_value --downstream "${2:-}")
            shift 2
            ;;
        --parent-dir)
            parent=$(require_value --parent-dir "${2:-}")
            if [[ -z "${UPSTREAM_DIR}" ]]; then
                UPSTREAM_DIR=$(discover_repo "${parent}" \
                    1-must-gather 1-rhdh-must-gather rhdh-must-gather must-gather) \
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

# --skip-upstream still needs UPSTREAM_DIR as sync source when doing downstream.
if [[ "${SKIP_UPSTREAM}" -eq 1 && "${SKIP_DOWNSTREAM}" -eq 0 ]]; then
    if [[ -z "${UPSTREAM_DIR}" ]]; then
        die "--skip-upstream still needs --upstream (or --parent-dir) as the sync source"
    fi
    UPSTREAM_DIR=$(cd "${UPSTREAM_DIR}" && pwd)
    validate_upstream "${UPSTREAM_DIR}"
fi

if [[ -n "${UPSTREAM_DIR:-}" && -n "${DOWNSTREAM_DIR:-}" ]]; then
    log "Upstream:  ${UPSTREAM_DIR}"
    log "Downstream: ${DOWNSTREAM_DIR}"
fi

MODE="cgw"
if [[ -n "${UPSTREAM_DIR:-}" ]] && [[ "${SKIP_UPSTREAM}" -eq 0 || "${CHECK_ONLY}" -eq 1 ]]; then
    if cgw_available "${UPSTREAM_DIR}" "${TO_VERSION}"; then
        MODE="cgw"
        log "CGW mirror has helm v${TO_VERSION} linux-amd64/arm64 binaries"
    else
        MODE="vendor"
        warn "CGW mirror has no helm v${TO_VERSION} linux-amd64/arm64 — vendored source path"
    fi
elif [[ "${SKIP_UPSTREAM}" -eq 1 ]]; then
    if [[ -f "${DOWNSTREAM_DIR}/${DISTGIT_REL}/artifacts.lock.yaml" ]] \
        && grep -q "cgw/helm/${TO_VERSION}/" "${DOWNSTREAM_DIR}/${DISTGIT_REL}/artifacts.lock.yaml" 2>/dev/null; then
        MODE="cgw"
    elif [[ -d "${DOWNSTREAM_DIR}/${DISTGIT_REL}/vendor/helm" ]]; then
        MODE="vendor"
    else
        # Prefer probing upstream check script when available
        if [[ -n "${UPSTREAM_DIR:-}" ]] && cgw_available "${UPSTREAM_DIR}" "${TO_VERSION}"; then
            MODE="cgw"
        else
            die "Cannot infer CGW vs vendor mode with --skip-upstream; ensure distgit has artifacts.lock.yaml or vendor/helm"
        fi
    fi
    log "Inferred mode: ${MODE}"
fi

if [[ "${CHECK_ONLY}" -eq 1 ]]; then
    echo "helm_version=${TO_VERSION}"
    echo "mode=${MODE}"
    echo "upstream=${UPSTREAM_DIR:-}"
    echo "downstream=${DOWNSTREAM_DIR:-}"
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
    flip_helm_stages "${UPSTREAM_DIR}/Containerfile" "${MODE}"
    if [[ -f "${UPSTREAM_DIR}/${RHDH_DOCKER_CF}" ]]; then
        flip_helm_stages "${UPSTREAM_DIR}/${RHDH_DOCKER_CF}" "${MODE}"
    else
        warn "No ${RHDH_DOCKER_CF} in upstream; skipped stage flip there"
    fi
fi

if [[ "${SKIP_DOWNSTREAM}" -eq 0 ]]; then
    assert_clean_tree "${DOWNSTREAM_DIR}" "Downstream"
    [[ -n "${UPSTREAM_DIR}" ]] || die "Downstream sync requires --upstream (or --parent-dir)"
    sync_to_distgit "${UPSTREAM_DIR}" "${DOWNSTREAM_DIR}" "${MODE}"
    regenerate_distgit_containerfile "${DOWNSTREAM_DIR}/${DISTGIT_REL}"
    # Ensure distgit root matches mode even if regenerate source lagged
    flip_helm_stages "${DOWNSTREAM_DIR}/${DISTGIT_REL}/Containerfile" "${MODE}"
    update_tekton_prefetch "${DOWNSTREAM_DIR}" "${MODE}"
    update_upstream_sha "${UPSTREAM_DIR}" "${DOWNSTREAM_DIR}"
fi

log "Done. Review git diff in each repo before committing."

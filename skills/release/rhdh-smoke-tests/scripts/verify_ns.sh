#!/usr/bin/env bash
#
# Verify an RHDH smoke-test namespace: pods, logs, Guest token, packages API.
#
# Requires: oc, curl, jq. A current oc session (KUBECONFIG).
#
set -euo pipefail

SCRIPT_NAME=$(basename "$0")
NS=""
RHDH_URL=""
JSON_OUT=0
MIN_PACKAGES=100

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME --namespace NS [options]

Verify pods, Guest sign-in, and the extensions packages API in an RHDH
smoke-test namespace.

Options:
  -h, --help              Show this help
  -n, --namespace NS      Namespace to check (required)
  --url URL               RHDH base URL (default: first matching Route)
  --min-packages N        Packages API length must be >= N (default: 100)
  --json                  JSON object on stdout (warnings still on stderr)

Exit codes:
  0  pods ready, Guest token present, packages count >= min
  1  verification failed
  2  usage or tooling error
EOF
}

log_err() { printf '%s\n' "$*" >&2; }

guest_token() {
  jq -r '(.backstageIdentity // {}).token // .token // empty' 2>/dev/null || true
}

packages_len() {
  jq -r 'if type == "array" then length else 0 end' 2>/dev/null || printf '0\n'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -n|--namespace)
      NS="${2:-}"
      shift 2
      ;;
    --url)
      RHDH_URL="${2:-}"
      shift 2
      ;;
    --min-packages)
      MIN_PACKAGES="${2:-}"
      shift 2
      ;;
    --json) JSON_OUT=1; shift ;;
    --)
      shift
      break
      ;;
    -*)
      log_err "Unknown option: $1"
      usage >&2
      exit 2
      ;;
    *)
      log_err "Unexpected argument: $1"
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$NS" ]]; then
  log_err "$SCRIPT_NAME: --namespace is required"
  usage >&2
  exit 2
fi

if ! command -v oc >/dev/null 2>&1; then
  log_err "$SCRIPT_NAME: oc is not on PATH"
  exit 2
fi
if ! command -v curl >/dev/null 2>&1; then
  log_err "$SCRIPT_NAME: curl is not on PATH"
  exit 2
fi
if ! command -v jq >/dev/null 2>&1; then
  log_err "$SCRIPT_NAME: jq is not on PATH"
  exit 2
fi

FAILURES=()
PACKAGES=0
DEPLOY=""

if ! oc get ns "$NS" >/dev/null 2>&1; then
  log_err "namespace not found: $NS"
  FAILURES+=("namespace-missing")
fi

BAD_REASONS=$(oc -n "$NS" get pods -o jsonpath='{range .items[*].status.containerStatuses[*]}{.state.waiting.reason}{"\n"}{.lastState.terminated.reason}{"\n"}{end}' 2>/dev/null || true)
if printf '%s\n' "$BAD_REASONS" | grep -Eq 'ImagePullBackOff|ErrImagePull|CrashLoopBackOff|OOMKilled'; then
  log_err "bad pod reason in $NS:"
  log_err "$BAD_REASONS"
  FAILURES+=("bad-pod")
fi

DEPLOY=$(oc -n "$NS" get deploy -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null | grep -E 'redhat-developer-hub|backstage' | head -1 || true)
if [[ -z "$DEPLOY" ]]; then
  log_err "no redhat-developer-hub/backstage Deployment in $NS"
  FAILURES+=("no-deploy")
else
  PLUGIN_LOG=$(oc -n "$NS" logs "deploy/${DEPLOY}" -c install-dynamic-plugins --tail=200 2>/dev/null || true)
  if [[ -n "$PLUGIN_LOG" ]]; then
    printf '%s\n' "$PLUGIN_LOG" >&2
    if printf '%s\n' "$PLUGIN_LOG" | grep -Eq '401|403'; then
      log_err "401/403 in install-dynamic-plugins logs"
      FAILURES+=("plugin-auth")
    fi
  else
    oc -n "$NS" logs "deploy/${DEPLOY}" --all-containers --tail=50 >&2 || true
  fi
  oc -n "$NS" logs "deploy/${DEPLOY}" -c backstage-backend --tail=50 >&2 || true
fi

if [[ -z "$RHDH_URL" ]]; then
  HOST=$(oc -n "$NS" get route -o jsonpath='{range .items[*]}{.spec.host}{"\n"}{end}' 2>/dev/null | grep -E 'redhat-developer-hub|backstage' | head -1 || true)
  if [[ -n "$HOST" ]]; then
    RHDH_URL="https://${HOST}"
  fi
fi

if [[ -z "$RHDH_URL" ]]; then
  log_err "no Route host and --url not set"
  FAILURES+=("no-url")
else
  REFRESH=$(curl -sS -X POST "${RHDH_URL}/api/auth/guest/refresh" || true)
  TOKEN=$(printf '%s' "$REFRESH" | guest_token || true)
  if [[ -z "$TOKEN" ]]; then
    log_err "Guest refresh returned no token (Guest may be off)"
    FAILURES+=("no-guest-token")
  else
    PACK_JSON=$(curl -sS -H "Authorization: Bearer ${TOKEN}" "${RHDH_URL}/api/extensions/packages" || true)
    PACKAGES=$(printf '%s' "$PACK_JSON" | packages_len || true)
    PACKAGES=${PACKAGES:-0}
    if [[ "$PACKAGES" -lt "$MIN_PACKAGES" ]]; then
      log_err "packages API length ${PACKAGES} < ${MIN_PACKAGES}"
      FAILURES+=("packages-low")
    fi
  fi
fi

if [[ "$JSON_OUT" -eq 1 ]]; then
  FAIL_JSON='[]'
  if [[ ${#FAILURES[@]} -gt 0 ]]; then
    FAIL_JSON=$(jq -nc '$ARGS.positional' --args -- "${FAILURES[@]}")
  fi
  jq -nc \
    --arg ns "$NS" \
    --arg url "${RHDH_URL:-}" \
    --argjson packages "${PACKAGES:-0}" \
    --argjson failures "$FAIL_JSON" \
    '{
      namespace: $ns,
      url: $url,
      packages: $packages,
      ok: ($failures | length == 0),
      failures: $failures
    }'
else
  printf 'namespace: %s\n' "$NS"
  printf 'url: %s\n' "${RHDH_URL:-}"
  printf 'deploy: %s\n' "${DEPLOY:-}"
  printf 'packages: %s\n' "$PACKAGES"
  if [[ ${#FAILURES[@]} -gt 0 ]]; then
    printf 'failures: %s\n' "${FAILURES[*]}"
  else
    printf 'ok: true\n'
  fi
fi

if [[ ${#FAILURES[@]} -gt 0 ]]; then
  exit 1
fi
exit 0

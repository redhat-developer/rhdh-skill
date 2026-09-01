#!/usr/bin/env bash
#
# Patch an RHDH OLM Subscription's channel / startingCSV and approve the
# resulting InstallPlan. CatalogSource install is a different script
# (install-rhdh-catalog-source.sh).
#
# Requires: oc, jq.
#
set -euo pipefail

SCRIPT_NAME=$(basename "$0")
SUB_NS=rhdh-operator
SUB_NAME=rhdh
CHANNEL=""
STARTING_CSV=""
DRY_RUN=0
JSON_OUT=0
WAIT_SECONDS=300

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME --channel CHANNEL [options]

Patch the RHDH operator Subscription and approve a pending InstallPlan.

Options:
  -h, --help                         Show this help
  --channel CHANNEL                  Subscription spec.channel (required)
  --starting-csv CSV                 Subscription spec.startingCSV (optional)
  --subscription-namespace NS        Namespace of the Subscription
                                     (default: rhdh-operator)
  --subscription-name NAME           Subscription name (default: rhdh)
  --wait-seconds N                   Seconds to wait for CSV (default: 300)
  --dry-run                          Print oc commands; do not run them
  --json                             JSON object on stdout

Exit codes:
  0  Subscription patched (and InstallPlan approved unless --dry-run)
  1  InstallPlan Failed or CSV not Succeeded
  2  usage or tooling error
EOF
}

log_err() { printf '%s\n' "$*" >&2; }

run_oc() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf 'oc'
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  oc "$@"
}

emit_json() {
  local dry_run_json="$1"
  local extra="$2"
  jq -nc \
    --argjson dryRun "$dry_run_json" \
    --arg ns "$SUB_NS" \
    --arg name "$SUB_NAME" \
    --arg channel "$CHANNEL" \
    --arg csv "$STARTING_CSV" \
    --argjson extra "$extra" \
    '{
      dryRun: $dryRun,
      subscriptionNamespace: $ns,
      subscriptionName: $name,
      channel: $channel,
      startingCSV: (if $csv == "" then null else $csv end)
    } + $extra'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --channel)
      CHANNEL="${2:-}"
      shift 2
      ;;
    --starting-csv)
      STARTING_CSV="${2:-}"
      shift 2
      ;;
    --subscription-namespace)
      SUB_NS="${2:-}"
      shift 2
      ;;
    --subscription-name)
      SUB_NAME="${2:-}"
      shift 2
      ;;
    --wait-seconds)
      WAIT_SECONDS="${2:-}"
      shift 2
      ;;
    --dry-run) DRY_RUN=1; shift ;;
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

if [[ -z "$CHANNEL" ]]; then
  log_err "$SCRIPT_NAME: --channel is required"
  usage >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  log_err "$SCRIPT_NAME: jq is not on PATH"
  exit 2
fi

if [[ "$DRY_RUN" -eq 0 ]] && ! command -v oc >/dev/null 2>&1; then
  log_err "$SCRIPT_NAME: oc is not on PATH"
  exit 2
fi

PATCH_JSON=$(jq -nc --arg channel "$CHANNEL" --arg csv "$STARTING_CSV" '
  {spec: ({channel: $channel} + if $csv == "" then {} else {startingCSV: $csv} end)}
')

run_oc -n "$SUB_NS" patch subscription "$SUB_NAME" --type merge -p "$PATCH_JSON"

if [[ "$DRY_RUN" -eq 1 ]]; then
  if [[ "$JSON_OUT" -eq 1 ]]; then
    emit_json true '{}'
  else
    printf 'dry-run: true\n'
    printf 'subscription: %s/%s\n' "$SUB_NS" "$SUB_NAME"
    printf 'channel: %s\n' "$CHANNEL"
    if [[ -n "$STARTING_CSV" ]]; then
      printf 'startingCSV: %s\n' "$STARTING_CSV"
    fi
  fi
  exit 0
fi

PENDING=$(oc -n "$SUB_NS" get installplan -o json 2>/dev/null | jq -r '
  (.items // [])[] | select(.spec.approved == false) | .metadata.name // empty
' || true)
while IFS= read -r ip; do
  [[ -z "$ip" ]] && continue
  oc -n "$SUB_NS" patch installplan "$ip" --type merge -p '{"spec":{"approved":true}}'
  PHASE=$(oc -n "$SUB_NS" get installplan "$ip" -o jsonpath='{.status.phase}' 2>/dev/null || true)
  if [[ "$PHASE" == "Failed" ]]; then
    log_err "InstallPlan ${ip} is Failed"
    exit 1
  fi
done <<<"$PENDING"

CSV="$STARTING_CSV"
if [[ -z "$CSV" ]]; then
  CSV=$(oc -n "$SUB_NS" get subscription "$SUB_NAME" -o jsonpath='{.status.installedCSV}' 2>/dev/null || true)
fi
if [[ -z "$CSV" ]]; then
  log_err "no startingCSV / installedCSV to wait on in ${SUB_NS}/${SUB_NAME}"
  exit 1
fi
if ! oc -n "$SUB_NS" wait "csv/${CSV}" --for=jsonpath='{.status.phase}'=Succeeded --timeout="${WAIT_SECONDS}s"; then
  log_err "CSV ${CSV} did not reach Succeeded"
  exit 1
fi

if [[ "$JSON_OUT" -eq 1 ]]; then
  emit_json false '{"ok":true}'
else
  printf 'ok: true\n'
  printf 'subscription: %s/%s\n' "$SUB_NS" "$SUB_NAME"
  printf 'channel: %s\n' "$CHANNEL"
fi
exit 0

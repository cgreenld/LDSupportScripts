#!/usr/bin/env bash
# token_cleanup.sh — List and remove unused / stale LaunchDarkly access tokens.
# Relies on lastUsed from GET /api/v2/tokens (0 = never used, >0 = Unix millis).
set -euo pipefail

API_BASE="${LD_API_BASE:-https://app.launchdarkly.com}"
DEFAULT_DAYS=90

API_KEY="${LD_API_KEY:-}"
DAYS="$DEFAULT_DAYS"
NEVER_USED=0
PERSONAL_ONLY=0
SERVICE_ONLY=0
SHOW_ALL=1
YES=0
LIMIT=100
OUTPUT_JSON=""
declare -a TOKEN_IDS=()

die() {
  echo "Error: $*" >&2
  exit 1
}

require_deps() {
  command -v jq >/dev/null 2>&1 || die "jq is required but not installed"
  command -v curl >/dev/null 2>&1 || die "curl is required but not installed"
}

usage() {
  cat <<EOF
Usage:
  $(basename "$0") list   [options]
  $(basename "$0") remove [options]

List or remove LaunchDarkly access tokens that are never used or unused for N days.
Uses lastUsed from the list tokens API (0 = never used, >0 = last-used timestamp).

Commands:
  list              Print stale tokens and write a JSON report (read-only)
  remove            Delete tokens by --id, or all matching the same filters as list

Common options:
  -k, --api-key KEY     API access token (or set LD_API_KEY). Admin recommended for showAll.
  -d, --days N          Unused longer than N days (default: ${DEFAULT_DAYS}). Ignored with --never-used.
      --never-used      Only tokens with lastUsed == 0
      --personal-only   Personal tokens only
      --service-only    Service tokens only
      --no-show-all     Do not pass showAll=true (only tokens visible to this key)
  -o, --output FILE     JSON report path (default: stale_tokens_YYYYMMDD_HHMMSS.json)
  -h, --help            Show this help

Remove-only options:
      --id ID           Token _id to delete (repeatable). If any --id is set, filters are ignored.
  -y, --yes             Skip interactive confirmation

Examples:
  $(basename "$0") list -k "\$LD_API_KEY" --days 90
  $(basename "$0") list -k "\$LD_API_KEY" --never-used --personal-only
  $(basename "$0") remove -k "\$LD_API_KEY" --id 61095542756dba551110ae21 --yes
  $(basename "$0") remove -k "\$LD_API_KEY" --days 180 --yes
EOF
}

# Relay LaunchDarkly API errors (status + code/message when present).
relay_api_error() {
  local status="$1"
  local body="$2"
  local hint=""

  case "$status" in
    401) hint="Invalid or missing API key (unauthorized)." ;;
    403) hint="Forbidden — key likely lacks Admin / token-management permission." ;;
    404) hint="Token ID not found." ;;
    429) hint="Rate limited — retry later." ;;
  esac

  local code message
  code=$(echo "$body" | jq -r '.code // empty' 2>/dev/null || true)
  message=$(echo "$body" | jq -r '.message // empty' 2>/dev/null || true)

  if [[ -n "$code" || -n "$message" ]]; then
    echo "Error: HTTP ${status} — ${code:-unknown}: ${message:-no message}" >&2
  elif [[ -n "$body" ]]; then
    echo "Error: HTTP ${status} — ${body}" >&2
  else
    echo "Error: HTTP ${status} — empty response body" >&2
  fi

  [[ -n "$hint" ]] && echo "  Hint: $hint" >&2
}

# Perform an API request. On success, prints response body to stdout and returns 0.
# On failure, relays the error on stderr and returns 1 (safe inside $(...); callers must check).
# Usage: api_request METHOD PATH [QUERY_STRING]
api_request() {
  local method="$1"
  local path="$2"
  local query="${3:-}"
  local url="${API_BASE}${path}"
  [[ -n "$query" ]] && url="${url}?${query}"

  local tmp_body http_code curl_exit
  tmp_body=$(mktemp)
  http_code=0
  curl_exit=0

  # curl -sS still prints errors to stderr; silence transport noise and handle ourselves
  http_code=$(curl -sS -o "$tmp_body" -w '%{http_code}' \
    -X "$method" \
    -H "Authorization: ${API_KEY}" \
    -H "Content-Type: application/json" \
    "$url" 2>/dev/null) || curl_exit=$?

  local body
  body=$(cat "$tmp_body")
  rm -f "$tmp_body"

  if [[ "$curl_exit" -ne 0 ]]; then
    echo "Error: curl failed talking to ${url} (exit ${curl_exit})" >&2
    return 1
  fi

  if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
    printf '%s' "$body"
    return 0
  fi

  relay_api_error "$http_code" "$body"
  return 1
}

# Same as api_request but soft-fail for per-item deletes: prints status to stdout as "STATUS|BODY"
api_request_soft() {
  local method="$1"
  local path="$2"
  local url="${API_BASE}${path}"
  local tmp_body http_code curl_exit
  tmp_body=$(mktemp)
  http_code=0
  curl_exit=0

  http_code=$(curl -sS -o "$tmp_body" -w '%{http_code}' \
    -X "$method" \
    -H "Authorization: ${API_KEY}" \
    -H "Content-Type: application/json" \
    "$url") || curl_exit=$?

  local body
  body=$(cat "$tmp_body")
  rm -f "$tmp_body"

  if [[ "$curl_exit" -ne 0 ]]; then
    echo "000|curl_exit_${curl_exit}"
    return 0
  fi
  # Encode newlines in body so caller can split on first |
  body=${body//$'\n'/ }
  echo "${http_code}|${body}"
}

parse_common_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -k|--api-key)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        API_KEY="$2"
        shift 2
        ;;
      -d|--days)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        DAYS="$2"
        shift 2
        ;;
      --never-used)
        NEVER_USED=1
        shift
        ;;
      --personal-only)
        PERSONAL_ONLY=1
        shift
        ;;
      --service-only)
        SERVICE_ONLY=1
        shift
        ;;
      --no-show-all)
        SHOW_ALL=0
        shift
        ;;
      -o|--output)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        OUTPUT_JSON="$2"
        shift 2
        ;;
      --id)
        [[ $# -ge 2 ]] || die "$1 requires a value"
        TOKEN_IDS+=("$2")
        shift 2
        ;;
      -y|--yes)
        YES=1
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

  if [[ -z "$API_KEY" ]]; then
    die "API key required via -k/--api-key or LD_API_KEY"
  fi

  if ! [[ "$DAYS" =~ ^[0-9]+$ ]] || [[ "$DAYS" -lt 0 ]]; then
    die "--days must be a non-negative integer"
  fi

  if [[ "$PERSONAL_ONLY" -eq 1 && "$SERVICE_ONLY" -eq 1 ]]; then
    die "Use only one of --personal-only or --service-only"
  fi
}

# Fetch all tokens (paginated). Prints a JSON array of Token objects to stdout.
# Uses temp files so large accounts do not hit "Argument list too long" (ARG_MAX)
# when merging pages — common on Git Bash / Windows.
fetch_all_tokens() {
  local offset=0
  local page=1
  local tmp_dir acc_file page_file next_file
  tmp_dir=$(mktemp -d)
  acc_file="$tmp_dir/all.json"
  page_file="$tmp_dir/page.json"
  next_file="$tmp_dir/next.json"
  echo '[]' > "$acc_file"

  # shellcheck disable=SC2064
  trap "rm -rf '$tmp_dir'" RETURN

  while true; do
    local query="limit=${LIMIT}&offset=${offset}"
    [[ "$SHOW_ALL" -eq 1 ]] && query="${query}&showAll=true"

    echo "Fetching tokens page ${page} (offset=${offset})..." >&2
    local response
    if ! response=$(api_request GET "/api/v2/tokens" "$query"); then
      return 1
    fi

    printf '%s' "$response" > "$page_file"

    local count
    count=$(jq '.items | length' "$page_file")
    # Merge via file args (not --argjson) to stay under OS argv limits
    jq -s '.[0] + .[1].items' "$acc_file" "$page_file" > "$next_file"
    mv "$next_file" "$acc_file"

    if [[ "$count" -lt "$LIMIT" ]]; then
      break
    fi
    offset=$((offset + LIMIT))
    page=$((page + 1))
  done

  cat "$acc_file"
}

# Filter tokens JSON array by stale rules / type. Prints filtered JSON array.
filter_tokens() {
  local tokens_json="$1"
  local cutoff_ms
  cutoff_ms=$(( $(date +%s) * 1000 - DAYS * 24 * 60 * 60 * 1000 ))

  echo "$tokens_json" | jq \
    --argjson cutoff "$cutoff_ms" \
    --argjson never "$NEVER_USED" \
    --argjson personal "$PERSONAL_ONLY" \
    --argjson service "$SERVICE_ONLY" \
    '
    map(
      select(
        (if $personal == 1 then (.serviceToken != true) else true end)
        and (if $service == 1 then (.serviceToken == true) else true end)
        and (
          if $never == 1 then
            (.lastUsed == 0 or .lastUsed == null)
          else
            (.lastUsed == 0 or .lastUsed == null or (.lastUsed > 0 and .lastUsed < $cutoff))
          end
        )
      )
    )
    '
}

# Enrich filtered tokens for display/report.
enrich_tokens() {
  local tokens_json="$1"
  echo "$tokens_json" | jq '
    map({
      _id: ._id,
      name: (.name // ""),
      description: (.description // ""),
      serviceToken: (.serviceToken // false),
      role: (.role // ""),
      memberEmail: (._member.email // ""),
      memberId: (.memberId // ""),
      creationDate: .creationDate,
      creationDateHuman: (if .creationDate then (.creationDate / 1000 | strftime("%Y-%m-%d %H:%M:%S")) else "" end),
      lastUsed: (.lastUsed // 0),
      lastUsedHuman: (
        if (.lastUsed == 0 or .lastUsed == null) then "never"
        else (.lastUsed / 1000 | strftime("%Y-%m-%d %H:%M:%S"))
        end
      ),
      daysSinceLastUse: (
        if (.lastUsed == 0 or .lastUsed == null) then null
        else (((now * 1000) - .lastUsed) / 86400000 | floor)
        end
      ),
      tokenSuffix: (.token // "")
    })
  '
}

print_table() {
  local enriched="$1"
  local count
  count=$(echo "$enriched" | jq 'length')

  if [[ "$count" -eq 0 ]]; then
    echo "No matching tokens."
    return 0
  fi

  printf "%-26s %-28s %-8s %-10s %-32s %-20s %s\n" \
    "ID" "NAME" "SERVICE" "ROLE" "MEMBER" "LAST_USED" "DAYS"
  printf "%s\n" "$(printf '=%.0s' {1..140})"

  echo "$enriched" | jq -r '
    .[] |
    [
      ._id,
      (.name | if length > 28 then .[0:25] + "..." else . end),
      (if .serviceToken then "yes" else "no" end),
      (.role // ""),
      (.memberEmail | if length > 32 then .[0:29] + "..." else . end),
      .lastUsedHuman,
      (if .daysSinceLastUse == null then "n/a" else (.daysSinceLastUse | tostring) end)
    ] | @tsv
  ' | while IFS=$'\t' read -r id name service role member last_used days; do
    printf "%-26s %-28s %-8s %-10s %-32s %-20s %s\n" \
      "$id" "$name" "$service" "$role" "$member" "$last_used" "$days"
  done

  echo
  echo "Total matching: ${count}"
}

auth_token_suffix() {
  # List responses only expose last 4 chars of each token; compare against our key's last 4.
  local key="$API_KEY"
  if [[ ${#key} -ge 4 ]]; then
    echo "${key: -4}"
  else
    echo "$key"
  fi
}

cmd_list() {
  parse_common_args "$@"

  local all filtered enriched
  if ! all=$(fetch_all_tokens); then
    exit 1
  fi
  filtered=$(filter_tokens "$all")
  enriched=$(enrich_tokens "$filtered")

  if [[ -z "$OUTPUT_JSON" ]]; then
    OUTPUT_JSON="stale_tokens_$(date +%Y%m%d_%H%M%S).json"
  fi

  echo "$enriched" | jq '.' > "$OUTPUT_JSON"

  echo
  if [[ "$NEVER_USED" -eq 1 ]]; then
    echo "Tokens never used (lastUsed == 0):"
  else
    echo "Tokens never used or unused for ${DAYS}+ days:"
  fi
  echo "----------------------------------------"
  print_table "$enriched"
  echo "Report written to: ${OUTPUT_JSON}"
}

cmd_remove() {
  parse_common_args "$@"

  local targets_json
  local self_suffix
  self_suffix=$(auth_token_suffix)

  if [[ ${#TOKEN_IDS[@]} -gt 0 ]]; then
    # Explicit IDs — build minimal objects for the delete loop
    targets_json=$(printf '%s\n' "${TOKEN_IDS[@]}" | jq -R -s '
      split("\n") | map(select(length > 0)) | map({_id: ., name: "", tokenSuffix: ""})
    ')
  else
    local all filtered enriched
    if ! all=$(fetch_all_tokens); then
      exit 1
    fi
    filtered=$(filter_tokens "$all")
    enriched=$(enrich_tokens "$filtered")
    targets_json="$enriched"

    if [[ -z "$OUTPUT_JSON" ]]; then
      OUTPUT_JSON="stale_tokens_$(date +%Y%m%d_%H%M%S).json"
    fi
    echo "$enriched" | jq '.' > "$OUTPUT_JSON"
    echo "Candidates written to: ${OUTPUT_JSON}"
  fi

  local count
  count=$(echo "$targets_json" | jq 'length')
  if [[ "$count" -eq 0 ]]; then
    echo "No tokens to remove."
    return 0
  fi

  echo
  echo "Tokens to remove (${count}):"
  echo "----------------------------------------"
  if [[ ${#TOKEN_IDS[@]} -gt 0 ]]; then
    echo "$targets_json" | jq -r '.[] | "  " + ._id'
  else
    print_table "$targets_json"
  fi

  if [[ "$YES" -ne 1 ]]; then
    echo
    read -r -p "Delete these ${count} token(s)? Type 'y' to confirm: " confirm
    [[ "$confirm" == "y" || "$confirm" == "Y" ]] || die "Aborted"
  fi

  local deleted=0 skipped=0 failed=0

  while IFS=$'\t' read -r id name suffix; do
    if [[ -n "$suffix" && "$suffix" == "$self_suffix" ]]; then
      echo "Skipping $id ($name) — matches last 4 chars of the API key in use" >&2
      skipped=$((skipped + 1))
      continue
    fi

    echo "Deleting ${id}${name:+ ($name)}..."
    local result status body
    result=$(api_request_soft DELETE "/api/v2/tokens/${id}")
    status=${result%%|*}
    body=${result#*|}

    if [[ "$status" == "204" || "$status" == "200" ]]; then
      echo "  OK (HTTP ${status})"
      deleted=$((deleted + 1))
    else
      relay_api_error "$status" "$body"
      failed=$((failed + 1))
    fi
  done < <(echo "$targets_json" | jq -r '.[] | [._id, (.name // ""), (.tokenSuffix // "")] | @tsv')

  echo
  echo "Done. deleted=${deleted} skipped=${skipped} failed=${failed}"
  [[ "$failed" -eq 0 ]] || exit 1
}

main() {
  require_deps

  if [[ $# -lt 1 ]]; then
    usage
    exit 1
  fi

  local cmd="$1"
  shift

  case "$cmd" in
    list)   cmd_list "$@" ;;
    remove) cmd_remove "$@" ;;
    -h|--help|help) usage ;;
    *)
      die "Unknown command: $cmd (expected list or remove)"
      ;;
  esac
}

main "$@"

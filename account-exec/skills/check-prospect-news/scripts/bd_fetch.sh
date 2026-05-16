#!/usr/bin/env bash
# Trigger a Bright Data discover_new job, poll until ready, write results.
#
# Usage: bd_fetch.sh <dataset_id> <discover_by> <input_json_file> <output_json_file>
#   <input_json_file>   JSON body: {"input":[{...},...]}
#   <output_json_file>  Where to write the JSON array of results
#
# Reads BRIGHTDATA_API_KEY from env (falls back to CLAUDE_PLUGIN_OPTION_BRIGHTDATA_API_KEY).
# Field list per discover_by lives in ../references/fields-<discover_by>.txt (URL-encoded).

set -euo pipefail

DATASET_ID="${1:?dataset_id required}"
DISCOVER_BY="${2:?discover_by required}"
INPUT_FILE="${3:?input_json_file required}"
OUTPUT_FILE="${4:?output_json_file required}"

API_KEY="${BRIGHTDATA_API_KEY:-${CLAUDE_PLUGIN_OPTION_BRIGHTDATA_API_KEY:-}}"
if [[ -z "$API_KEY" ]]; then
  echo "BRIGHTDATA_API_KEY not set — declare brightdata_api_key in plugin userConfig, or export it in your shell rc." >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIELDS_FILE="$SCRIPT_DIR/../references/fields-$DISCOVER_BY.txt"
if [[ ! -f "$FIELDS_FILE" ]]; then
  echo "No field list at $FIELDS_FILE" >&2
  exit 2
fi
FIELDS="$(tr -d '\r\n[:space:]' < "$FIELDS_FILE")"

mkdir -p "$(dirname "$OUTPUT_FILE")"

TRIGGER_URL="https://api.brightdata.com/datasets/v3/trigger?dataset_id=${DATASET_ID}&type=discover_new&discover_by=${DISCOVER_BY}&custom_output_fields=${FIELDS}&notify=false&include_errors=true"

echo "[$DISCOVER_BY] triggering…" >&2
RESP="$(curl -fsS -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d @"$INPUT_FILE" "$TRIGGER_URL")"
SNAPSHOT_ID="$(printf '%s' "$RESP" | jq -r '.snapshot_id // empty')"
if [[ -z "$SNAPSHOT_ID" ]]; then
  echo "[$DISCOVER_BY] no snapshot_id in trigger response: $RESP" >&2
  exit 1
fi
echo "[$DISCOVER_BY] snapshot=$SNAPSHOT_ID" >&2

STATUS=""
for _ in $(seq 1 40); do
  PROGRESS="$(curl -fsS -H "Authorization: Bearer $API_KEY" "https://api.brightdata.com/datasets/v3/progress/$SNAPSHOT_ID")"
  STATUS="$(printf '%s' "$PROGRESS" | jq -r '.status // empty')"
  echo "[$DISCOVER_BY] status=$STATUS" >&2
  case "$STATUS" in
    ready) break ;;
    failed) echo "[$DISCOVER_BY] failed: $PROGRESS" >&2; exit 1 ;;
  esac
  sleep 15
done

if [[ "$STATUS" != "ready" ]]; then
  echo "[$DISCOVER_BY] timed out after 10 minutes (snapshot $SNAPSHOT_ID)" >&2
  exit 1
fi

curl -fsS -H "Authorization: Bearer $API_KEY" "https://api.brightdata.com/datasets/v3/snapshot/$SNAPSHOT_ID?format=json" > "$OUTPUT_FILE"
echo "[$DISCOVER_BY] wrote $OUTPUT_FILE" >&2

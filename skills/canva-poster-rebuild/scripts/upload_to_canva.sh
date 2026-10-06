#!/usr/bin/env bash
# Upload a local file to a single-use Canva upload URL (from mcp__canva__create-upload-url).
# Usage: upload_to_canva.sh <file> '<upload_url>'
# Prints the JSON response, e.g. {"mediaId":"MAH..."}; use mediaId as asset_id in edit-design.
set -euo pipefail
[ $# -eq 2 ] || { echo "usage: $0 <file> <upload_url>" >&2; exit 2; }
curl -sS -X POST -H "Content-Type: application/octet-stream" --data-binary @"$1" "$2"
echo

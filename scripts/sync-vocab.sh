#!/usr/bin/env bash
# Copy contracts/vocab/*.json into each service that validates against them.
#   scripts/sync-vocab.sh          copy the files
#   scripts/sync-vocab.sh --check  fail if any service copy differs (used in CI)
#
# Why copies? Each service's Docker build only sees its own folder, so it can't read
# contracts/ at runtime. The copy is a build input, never edited by hand: edit
# contracts/vocab/ and re-run this script.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECK=false
[[ "${1:-}" == "--check" ]] && CHECK=true

# service folder -> where the copies live inside it
CONSUMERS=(
  "services/user-service/src/user_service/vocab"
)

status=0
for target in "${CONSUMERS[@]}"; do
  mkdir -p "$ROOT/$target"
  for source in "$ROOT"/contracts/vocab/*.json; do
    copy="$ROOT/$target/$(basename "$source")"
    if $CHECK; then
      if ! cmp -s "$source" "$copy"; then
        echo "vocab drift: ${copy#"$ROOT"/} differs from contracts — run scripts/sync-vocab.sh" >&2
        status=1
      fi
    else
      cp "$source" "$copy"
      echo "copied ${copy#"$ROOT"/}"
    fi
  done
done
exit $status

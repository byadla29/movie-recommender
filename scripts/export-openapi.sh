#!/usr/bin/env bash
# Regenerate contracts/openapi/<service>.v1.json from each service's code.
#   scripts/export-openapi.sh          write files
#   scripts/export-openapi.sh --check  fail if committed contracts are out of date (used in CI)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UV="${UV:-uv}"
CHECK=false
[[ "${1:-}" == "--check" ]] && CHECK=true

declare -A PACKAGES=(
  [user-service]=user_service
  [catalog-service]=catalog_service
  [recommendation-service]=reco_service
)

mkdir -p "$ROOT/contracts/openapi"
status=0
for service in "${!PACKAGES[@]}"; do
  target="$ROOT/contracts/openapi/${service}.v1.json"
  generated="$(cd "$ROOT/services/$service" && $UV run --quiet python -m "${PACKAGES[$service]}.export_openapi" | tr -d '\r')"
  if $CHECK; then
    if ! diff -q <(printf '%s\n' "$generated") "$target" >/dev/null 2>&1; then
      echo "contract drift: $target is out of date — run scripts/export-openapi.sh and commit" >&2
      status=1
    fi
  else
    printf '%s\n' "$generated" >"$target"
    echo "wrote ${target#"$ROOT"/}"
  fi
done
exit $status

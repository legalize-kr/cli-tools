#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ENV="$ROOT_DIR/../.env"

cd "$ROOT_DIR"

echo "== Unit + integration tests =="
(
    unset LEGALIZE_CLI_LIVE
    unset GITHUB_TOKEN
    unset LEGALIZE_GITHUB_TOKEN
    python -m pytest tests/unit tests/integration -q
)

echo
echo "== Live tests =="
(
    if [[ -f "$WORKSPACE_ENV" ]]; then
        set -a
        # shellcheck disable=SC1090
        source "$WORKSPACE_ENV"
        set +a
    fi
    python -m pytest tests/live -q
)

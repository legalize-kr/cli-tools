#!/usr/bin/env bash
set -euo pipefail

# Run live tests against GitHub before refreshing checked-in fixtures.
# Requires:
#   LEGALIZE_CLI_LIVE=1  (to unlock live tests)
#   GITHUB_TOKEN          (recommended — lifts 60 req/hr to 5,000)
#
# Usage:
#   cd cli-tools
#   LEGALIZE_CLI_LIVE=1 GITHUB_TOKEN=$(gh auth token) ./scripts/record-cassettes.sh

if [[ "${LEGALIZE_CLI_LIVE:-}" != "1" ]]; then
    echo "error: set LEGALIZE_CLI_LIVE=1 to run live fixture checks"
    exit 1
fi

echo "Running live fixture checks against GitHub..."
echo "Token: ${GITHUB_TOKEN:+(set)}"
echo

python -m pytest tests/live/ -m live -q "$@"

echo
echo "Done. If you refreshed fixtures, review their diffs before committing:"
echo "  git diff tests/fixtures/"

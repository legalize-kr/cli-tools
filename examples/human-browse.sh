#!/usr/bin/env bash
# Walking tour: list laws, view one, diff two dates

set -euo pipefail

echo "=== List first 5 법률 ==="
legalize laws list --category 법률 --page-size 5

echo
echo "=== View 민법 (current) ==="
legalize laws get 민법 | head -30

echo
echo "=== Diff 민법: 2015 vs 2024 (article mode) ==="
legalize laws diff 민법 민법 --date-a 2015-01-01 --date-b 2024-01-01 --mode article

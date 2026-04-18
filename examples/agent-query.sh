#!/usr/bin/env bash
# Example: LLM/agent queries 민법 제839조의2 as of 2015-06-01

set -euo pipefail

echo "=== Fetch article ==="
legalize laws article 민법 제839조의2 --date 2015-06-01 --json | jq '{
  article: .article_no,
  status: .status,
  date: .resolved_commit_date,
  preview: (.content | split("\n") | .[0:3] | join("\n"))
}'

echo
echo "=== Search precedents ==="
legalize search "재산분할" --in precedents --json | jq '.items[:3]'

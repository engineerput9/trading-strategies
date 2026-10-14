#!/usr/bin/env bash
# Clone the 'state' branch into $CRUDE_LIVE_DIR (create it on first run).
set -eu
URL="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
D="${CRUDE_LIVE_DIR:-state}"
rm -rf "$D"
if git ls-remote --exit-code --heads "$URL" state >/dev/null 2>&1; then
  git clone -q --depth 1 --branch state "$URL" "$D"
else
  mkdir -p "$D" && cd "$D" && git init -q -b state && git remote add origin "$URL"
fi

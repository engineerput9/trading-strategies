#!/usr/bin/env bash
# Commit $CRUDE_LIVE_DIR (a clone of the 'state' branch) and push. Safe to call repeatedly.
set -u
cd "${CRUDE_LIVE_DIR:-state}" || exit 0
[ -d .git ] || exit 0
rm -f ./*.tmp
git add -A
git diff --cached --quiet && exit 0
git -c user.name=github-actions -c user.email=41898282+github-actions[bot]@users.noreply.github.com commit -qm "state $(date -u +%FT%TZ)"
for i in 1 2 3; do git push -q origin HEAD:state && exit 0; sleep 3; done
echo "state push failed"

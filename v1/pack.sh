#!/bin/sh
# Code ships as a tarball + COMMIT file; no box needs git. Usage: v1/pack.sh [OUT_DIR]  (run from the repo, clean tree)
set -eu
OUT="${1:-.}"
cd "$(git rev-parse --show-toplevel)"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "refusing: working tree has uncommitted changes" >&2; exit 2; fi
COMMIT="$(git rev-parse HEAD)"
NAME="v1-code-$(echo "$COMMIT" | cut -c1-12)"
mkdir -p "$OUT"
git archive --format=tar HEAD premonition learnlab v1 creative custom_io run.py 2>/dev/null | gzip -n > "$OUT/$NAME.tar.gz" \
  || git archive --format=tar HEAD premonition learnlab v1 | gzip -n > "$OUT/$NAME.tar.gz"
echo "$COMMIT" > "$OUT/COMMIT"
( cd "$OUT" && sha256sum "$NAME.tar.gz" COMMIT > "$NAME.sha256" )
echo "$OUT/$NAME.tar.gz  commit=$COMMIT"

#!/bin/sh
# Code ships as a tarball + COMMIT file; no box needs git. Usage: v1/pack.sh [OUT_DIR]  (run from the repo, clean tree)
# (v1/rent.py `pack` builds the tarball the rental jobs actually use, from the same directory list.)
set -eu
OUT="${1:-.}"
cd "$(git rev-parse --show-toplevel)"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "refusing: working tree has uncommitted changes" >&2; exit 2; fi
COMMIT="$(git rev-parse HEAD)"
NAME="v1-code-$(echo "$COMMIT" | cut -c1-12)"
mkdir -p "$OUT"
git archive --format=tar HEAD premonition learnlab memorylab v1 custom_io creative mainbrain domain skills_curriculum \
  data/tokenizer/premonition-tok-v2.json data/tokenizer/premonition-tok-v2.manifest.json data/village/patterns/bank-v1.json \
  design/v1/data/village-SHA256SUMS.txt design/v1/V1_PARAMS.md | gzip -n > "$OUT/$NAME.tar.gz"
echo "$COMMIT" > "$OUT/COMMIT"
( cd "$OUT" && sha256sum "$NAME.tar.gz" COMMIT > "$NAME.sha256" )
echo "$OUT/$NAME.tar.gz  commit=$COMMIT"

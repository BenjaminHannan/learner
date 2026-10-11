#!/bin/bash
# usage: bash build_mix.sh PROJECT_DIR NARRATION.m4a OUT.m4a [--work DIR] [--keep]
# PROJECT_DIR is only read (a scratch copy is built for content.js and the effect extraction).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
[ $# -ge 3 ] || { echo "usage: bash build_mix.sh PROJECT_DIR NARRATION.m4a OUT.m4a" >&2; exit 2; }
exec python3 "$HERE/build_mix.py" "$@"

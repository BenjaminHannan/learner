#!/bin/sh
set -eu
export PATH="/opt/homebrew/bin:$PATH"
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_PYTHON=${PROJECT_PYTHON:-/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12}
exec "$PROJECT_PYTHON" -B "$PROJECT_ROOT/run.py" "$@"

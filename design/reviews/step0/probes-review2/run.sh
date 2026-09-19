#!/bin/sh
cd /Users/ben-hannan/Desktop/projects/beautiful-model
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
PYTHONPATH=$($PY -c "import json;print(':'.join(json.load(open('runtime.local.json'))['import_roots']))"):. exec $PY -B "$@"

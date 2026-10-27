#!/bin/sh
# Prepare an unpacked bundle for this host.  POSIX sh; no bashisms, no zsh-isms.
# Run this on a Linux box before run_remote.sh.  On the Mac it is OPTIONAL and will
# report that torch is not importable directly - that is expected, because the bundled
# runtime.local.json points at the uv wheel cache, which is exactly how the Mac finds it.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-python3}
echo "bundle root : $HERE"
echo "interpreter : $PY"
"$PY" - "$HERE" <<'EOF'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
try:
    import torch
except Exception as exc:                       # noqa: BLE001
    print('torch is NOT importable directly with this interpreter:', exc)
    print('LEAVING runtime.local.json import_roots as bundled (the Mac path).')
    print('On Linux this means the wrong interpreter: set PY=/opt/conda/bin/python.')
    raise SystemExit(0)
print('torch', torch.__version__, 'from', torch.__file__)
path = root/'runtime.local.json'
data = json.loads(path.read_text())
data['import_roots'] = []
data['shared_roots'] = []
data['python'] = sys.executable
path.write_text(json.dumps(data, indent=2) + '\n')
print('runtime.local.json import_roots cleared (torch resolves natively)')
EOF
"$PY" -B -c 'import sys; sys.path.insert(0, sys.argv[1]+"/scripts"); import fable_operator_reliability as R; print("repo root resolved to", R.find_repo())' "$HERE"
"$PY" -B "$HERE/scripts/fable_operator_reliability.py" verify \
      --repo "$HERE" --variant "${VARIANT:-grow-blind}" 2>/dev/null \
  || echo "no frozen roster yet - run_remote.sh will create one"
echo "setup ok"

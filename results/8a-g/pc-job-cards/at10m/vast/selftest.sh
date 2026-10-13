#!/usr/bin/env bash
# Offline checks of the kit (no network, no Vast): bash -n, py_compile, and the speed-guard arithmetic. Run: bash selftest.sh
set -u
H=$(cd "$(dirname "$0")" && pwd); T=$(mktemp -d); fail=0
bash -n "$H/at10m_box.sh" && echo "ok  bash -n at10m_box.sh" || fail=1
python3 -m py_compile "$H/vast.py" && echo "ok  py_compile vast.py" || fail=1
export J=$T/job AT10M_SOURCE_ONLY=1; mkdir -p $J/state
# shellcheck disable=SC1090
source "$H/at10m_box.sh" >/dev/null; write_guard
L=$T/stdout.txt
g() { want=$1; shift; python3 $J/guard.py "$@" > $T/o.txt; rc=$?; [ $rc = $want ] && echo "ok  guard rc=$rc: $(cat $T/o.txt | head -1 | cut -c1-110)" || { echo "FAIL guard rc=$rc want $want"; fail=1; }; }
echo '{"event": "train", "step": 500, "loss": 2.0, "elapsed": 400.0}' > $L
g 4 $L 1000 1700 0.5 70 1000 24000 1.5                      # no step-1000 line yet
echo '{"event": "train", "step": 1000, "loss": 1.8, "elapsed": 800.0}' >> $L
g 0 $L 1000 2500 0.5 70 1000 24000 1.5                      # 0.8 s/update: about 7 h, 3.5 USD
echo '{"event": "train", "step": 1000, "loss": 1.8, "elapsed": 8000.0}' > $L
g 3 $L 1000 9000 1.4 70 1000 24000 1.5                      # 8 s/update at 1.4 USD/h: over the cap
rm -rf $T; [ $fail = 0 ] && echo SELFTEST OK || { echo SELFTEST FAILED; exit 1; }

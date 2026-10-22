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
# ---- the overlay (train.py with --ckpt-every / --resume) embedded in the box script: decodes to the pinned sha256 and to ../overlay/train.py
gsha() { sha256sum "$1" | cut -c1-64; }
overlay_b64 | base64 -d | gzip -dc > $T/train.py
if [ "$(gsha $T/train.py)" = "$OVERLAY_TRAIN_SHA" ]; then echo "ok  embedded overlay train.py = OVERLAY_TRAIN_SHA ${OVERLAY_TRAIN_SHA:0:12}"; else echo "FAIL embedded overlay sha $(gsha $T/train.py) != $OVERLAY_TRAIN_SHA"; fail=1; fi
if [ -f "$H/../overlay/train.py" ]; then [ "$(gsha $H/../overlay/train.py)" = "$OVERLAY_TRAIN_SHA" ] && echo "ok  ../overlay/train.py is the embedded one" || { echo "FAIL ../overlay/train.py differs from the embedded copy: run python3 embed_overlay.py"; fail=1; }; fi
[ "$TRAIN0_SHA" = e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d ] && echo "ok  original train.py pin (6e72a5fae5)" || fail=1
grep -q -- "--train-extra \"--ckpt-every \$CKPT_EVERY --resume\"" "$H/at10m_box.sh" && echo "ok  job line carries --train-extra '--ckpt-every \$CKPT_EVERY --resume'" || { echo "FAIL no --train-extra in the job line"; fail=1; }

# ---- checkpoint export / import round trip (GNU split needed): the newest VALID checkpoint goes through a fake log in parts and comes back byte for byte through vast.py collectck;
#      an import from a file:// URL puts it under AT/ckpt
command -v python >/dev/null 2>&1 || python() { python3 "$@"; }
if split --help 2>&1 | grep -q -- 'numeric-suffixes'; then
  export JOB=${JOB:-8aAT10M-10M-s400} O=$J/w/$JOB PACE=0 FAIL_SLEEP=0 LOG=$T/fake.log; mkdir -p $O/AT/ckpt $J/res $J/w
  mk() { head -c $2 /dev/urandom > $O/AT/ckpt/step-$1.pt; python3 - $O/AT/ckpt $1 <<'PY'
import hashlib, json, os, sys
d, k = sys.argv[1], sys.argv[2]
pt = os.path.join(d, 'step-%s.pt' % k)
json.dump(dict(file='step-%s.pt' % k, bytes=os.path.getsize(pt), sha256=hashlib.sha256(open(pt, 'rb').read()).hexdigest(), step=int(k)), open(os.path.join(d, 'step-%s.json' % k), 'w'))
PY
  }
  mk 500 4000000; mk 1000 7000000; mk 1500 3100000; printf 'x' >> $O/AT/ckpt/step-1500.pt              # 1500 is corrupt (sha differs): the export must take 1000
  : > $LOG; ckx_export > $T/ckx.out; grep -q "CKX START step=1000 jr=$JOB/AT-ck1000 parts=3" $T/ckx.out && grep -q "CKX END step=1000" $T/ckx.out && echo "ok  ckx_export: newest valid checkpoint (step 1000, 3 parts; corrupt step 1500 skipped)" || { echo "FAIL ckx_export: $(cat $T/ckx.out)"; fail=1; }
  mkdir -p $T/ckin; python3 - "$H" "$LOG" "$T/ckin" <<'PY' && echo "ok  vast.py collectck reassembled step-1000 from the fake log" || { echo "FAIL collectck"; fail=1; }
import argparse, sys, hashlib
sys.path.insert(0, sys.argv[1])
import vast
vast.log_text = lambda i, tail=9000: open(sys.argv[2]).read()
vast.time.sleep = lambda s: None
vast.collectck(argparse.Namespace(id=1, out=sys.argv[3], max_min=1, tail=9000, want='8aAT10M-10M-s400/AT-ck1000'))
d = sys.argv[3] + '/8aAT10M-10M-s400/AT/ckpt/'
import os
assert sorted(os.listdir(d)) == ['step-1000.json', 'step-1000.pt'], os.listdir(d)
PY
  cmp $T/ckin/$JOB/AT/ckpt/step-1000.pt $O/AT/ckpt/step-1000.pt && echo "ok  step-1000.pt byte for byte" || { echo "FAIL step-1000.pt differs"; fail=1; }
  tar -czf $T/imp.tgz -C $T/ckin $JOB/AT/ckpt; rm -rf $O/AT/ckpt
  export CK_IMPORT_URL=file://$T/imp.tgz CK_IMPORT_SHA=$(gsha $T/imp.tgz) CK_IMPORT_WAIT=0
  ck_import > $T/imp.out && cmp $T/ckin/$JOB/AT/ckpt/step-1000.pt $O/AT/ckpt/step-1000.pt && grep -q "CK-IMPORT ok" $T/imp.out && echo "ok  ck_import (file:// URL, sha256 checked) -> AT/ckpt/step-1000.{pt,json}" || { echo "FAIL ck_import: $(cat $T/imp.out)"; fail=1; }
  rm -rf $O/AT/ckpt; export CK_IMPORT_SHA=0000; ( ck_import ) > $T/imp2.out 2>&1; grep -q "CIO-FAIL ck-import sha256" $T/imp2.out && echo "ok  ck_import refuses a wrong sha256" || { echo "FAIL ck_import accepted a wrong sha256: $(cat $T/imp2.out | head -3)"; fail=1; }
  unset CK_IMPORT_URL CK_IMPORT_SHA
else echo "skip checkpoint export round trip (needs GNU split -d)"; fi
rm -rf $T; [ $fail = 0 ] && echo SELFTEST OK || { echo SELFTEST FAILED; exit 1; }

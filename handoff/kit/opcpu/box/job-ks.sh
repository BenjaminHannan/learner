#!/bin/bash
# opcpu job 1: handoff/queue/ks-1-lead0-mac-r2.md, science steps unchanged (see DEVIATIONS.md for every machine change).
# Rebuilds the loop nets k64 / k16384 from the qualified qual-loop sources, then Lead 0 (eval only). Nets stay in $HOME/premonition-ks/nets.
set -o pipefail
. "$(dirname "$0")/jlib.sh"
G=$OPC_OUT/ks-1-lead0; W=$HOME/premonition-ks; A=artifacts/claude-dir-ks-20260928
SRC=${KS_SRC:-$OPC_IN/artifacts/claude-fewex-20260927}
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 KS_SRC="$SRC" KS_NETS="$W/nets"
mkdir -p "$G"
echo "start $(date -u '+%F %T') UTC"; uptime; df -h "$HOME" | tail -1
FREE=$(freegb); [ "${FREE:-0}" -ge 3 ] || { echo "ABORT: under 3 GB free"; exit 4; }
[ -f "$OPC_R/$A/SEAL-code.sha256.txt" ] || { echo "WAITING: the pinned tree has no $A/SEAL-code.sha256.txt"; exit 5; }
unpack "$W" scripts artifacts/claude-fewex-20260927 artifacts/claude-distill-20260928 $A || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
sha256sum -c $A/SEAL-code.sha256.txt > $A/seal-check.log 2>&1 || { cat $A/seal-check.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
for S in 0 1; do
  [ -f "$SRC/runs/qual-loop-s$S/source.pt" ] && [ -f "$SRC/runs/qual-loop-s$S/source.json" ] || { echo "MISSING-SOURCE: $SRC/runs/qual-loop-s$S"; exit 6; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-loop-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(sha256sum "$SRC/runs/qual-loop-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S (sealed '$want', box '$have')"; exit 6; }
  wantpt=$(awk -v f="qual-loop-s$S/source.pt" '$2==f {print $1}' artifacts/claude-distill-20260928/checkpoints-sha256.txt)
  havept=$(sha256sum "$SRC/runs/qual-loop-s$S/source.pt" | awk '{print $1}')
  [ -n "$wantpt" ] && [ "$wantpt" = "$havept" ] || { echo "SOURCE-PT-MISMATCH seed $S (sealed '$wantpt', box '$havept')"; exit 6; }
done
run2() { xargs -P "${1:-2}" -I{} sh -c 'L=$(echo "{}" | tr " -" "__"); '"$PY"' scripts/claude_dir_ks_run.py {} > '"$A"'/logs/$L.log 2>&1 || echo "FAILED {}"'; }
mkdir -p $A/logs
$PY scripts/claude_dir_ks_run.py selftest 2>&1 | tee $A/selftest.log; grep -q '"uniform_mode_equals_harness_sleep": true' $A/selftest.log || { echo "STOP: plug-in selftest failed"; exit 7; }
printf '%s\n' "prep --seed 0" "prep --seed 1" | run2 2
for S in 0 1; do [ -f $A/prep/s$S.json ] || { echo "STOP: prep s$S wrote no record"; tail -20 $A/logs/prep*s$S* 2>/dev/null; exit 8; }; done
$PY - <<'KSPY'
import json
for s in (0, 1):
    r = json.load(open(f"artifacts/claude-dir-ks-20260928/prep/s{s}.json"))
    print("seed", s, "k0 old_before", r["k0"]["old_before"], "committed", r["k0"]["committed_old_before"], "dev9", r["k0"]["dev9"], "committed", r["k0"]["committed_dev9"])
    for k, v in r["rungs"].items():
        print("  rung", k, v.get("origin"), "dev9", v.get("dev9"), "committed", v["committed_dev9"], "matches", v.get("matches_committed"))
KSPY
# report only (not in the Mac job): the rebuilt nets' sha256 next to the distill list; a different sha is expected on another machine
for S in 0 1; do for f in "$KS_NETS"/loop-s$S-pre/k*.pt; do [ -f "$f" ] || continue; n=loop-s$S-pre/$(basename "$f")
  echo "$(sha256sum "$f" | awk '{print $1}') $n listed=$(awk -v f="$n" '$2==f {print $1}' artifacts/claude-distill-20260928/checkpoints-sha256.txt)"; done; done | tee $A/nets-sha256-report.txt
# lead0 is eval only (single thread each): the box runs the four at once instead of two at a time (a machine change, same numbers)
printf '%s\n' "lead0 --seed 0 --k 64" "lead0 --seed 1 --k 64" "lead0 --seed 0 --k 16384" "lead0 --seed 1 --k 16384" | run2 4
for f in s0-k64 s1-k64 s0-k16384 s1-k16384; do [ -f $A/lead0/$f.json ] || echo "MISSING lead0 $f (see $A/logs)"; done
$PY - <<'KSPY'
import json
for s in (0, 1):
    for k in (64, 16384):
        try:
            r = json.load(open(f"artifacts/claude-dir-ks-20260928/lead0/s{s}-k{k}.json"))
        except FileNotFoundError:
            continue
        print("s%d k%d P %s A %s" % (s, k, r["P"], r["A"]))
        for g, v in r["revert"].items():
            print("  revert", g, v)
        for g, v in r["only"].items():
            print("  only", g, v)
KSPY
mkdir -p "$G/$A"; for d in prep lead0 blend frows sleeps logs; do [ -d $A/$d ] && { mkdir -p "$G/$A/$d"; cp -R $A/$d/. "$G/$A/$d/"; }; done
cp $A/selftest.json $A/seal-check.log $A/nets-sha256-report.txt "$G/$A/" 2>/dev/null
echo "end $(date -u '+%F %T') UTC"

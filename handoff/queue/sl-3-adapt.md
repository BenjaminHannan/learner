STATUS: HELD. DO NOT RUN (helper SL, 2026-09-28 from date -u). The Director releases it by deleting this line, after the checks under HELD-UNTIL below.
BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no rental, no BensPC). LOAD-LIGHT: no (2 single-thread processes; the baseline loop dev jobs took 10,149 s and 10,123 s with eight running at once). TIME CAP: 300 minutes. LABEL: sl-adapt.
DISK: 2 (about 130 MB of checkpoints per run stay local; never pushed)
HELD-UNTIL: (a) job sl-2-source has finished with V1 PASS for both seeds ($HOME/premonition-sl/sl-sources/sl-source-s{0,1}/source.{pt,json} exist; the job checks V1 again and refuses otherwise); (b) origin/main holds the SEAL; (c) the Mac is not busy with another long CPU job (uptime).
Owner job (helper SL, Claude, for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), blind panels never opened, never read or print keys or auth files, counts only, every deviation reported.
WHY: artifacts/claude-dir-sl-20260928/PASSMARKS.md Part C. The sealed equal-practice harness, unedited, runs the loop from the new source nets (plug-in claude_dir_sl_stop, which defines no Learner, so maze adaptation is the baseline's: cross-entropy only, no maze stop loss). Dev panel only; the control is the baseline loop already on main (eq-runs/loop-s{0,1}-pre). The holdout is NOT touched. You run sealed code; never edit it. If something breaks, stop and report the first traceback verbatim; do not patch.
STOP RULE: any failed check, selftest or traceback: print it, run nothing further, exit non-zero.
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-sl; A=artifacts/claude-dir-sl-20260928; REF=${SL_REF:-origin/main}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 3 ] || { echo "ABORT: under 3 GB free"; exit 4; }
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
[ "$REF" = origin/main ] || git -C "$G" fetch -q origin "${REF#origin/}" || { echo "ABORT: fetch of $REF failed"; exit 4; }
git -C "$G" cat-file -e "$REF:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: $REF has no $A/SEAL-code.sha256.txt"; exit 5; }
git -C "$G" show "$REF:artifacts/claude-fewex-20260927/EQ-DEV-GATE.json" | grep -q '"verdict": "PASS"' || { echo "WAITING: baseline ruler gate is not PASS"; exit 5; }
for S in 0 1; do [ -f "$W/sl-sources/sl-source-s$S/source.pt" ] && [ -f "$W/sl-sources/sl-source-s$S/source.json" ] || { echo "WAITING: no new source net for seed $S in $W/sl-sources (run job sl-2-source first)"; exit 5; }; done
mkdir -p "$W" && git -C "$G" archive "$REF" scripts artifacts/claude-fewex-20260927 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-code.sha256.txt > $A/seal-check-adapt.log 2>&1 || { cat $A/seal-check-adapt.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check-adapt.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
for S in 0 1; do
  $PY - <<PYEOF || { echo "STOP: V1 failed for seed $S; do not adapt from it"; exit 7; }
import json, sys
d = json.load(open("sl-sources/sl-source-s$S/source.json"))
ok = d["old"]["sums4"]["right"] >= 190 and d["old"]["grids5"]["right"] >= 190 and d["gradient_check"]["nonzero_all"] and d["arm"] == "loop" and d["seed"] == $S
print("seed $S V1", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
PYEOF
done
$PY scripts/claude_dir_sl_marks.py selftest | tee $A/SELFTEST-marks-adapt-mac.log
grep -q '"selftest": "ok"' $A/SELFTEST-marks-adapt-mac.log || { echo "STOP: marks selftest failed"; exit 7; }
mkdir -p $A/eq-runs $A/sources
for S in 0 1; do
  O=$A/eq-runs/sl-pre-s$S
  [ -f $O/adapt.json ] && { echo "seed $S: adapt.json already exists; not re-running"; continue; }
  [ -d $O ] && { echo "PARTIAL: $O exists without adapt.json (the harness has no resume); delete that folder and start again"; exit 7; }
  mkdir -p $A/sources/sl-source-s$S && cp sl-sources/sl-source-s$S/source.json $A/sources/sl-source-s$S/
  nohup perl -e 'alarm shift; exec @ARGV' 17400 $PY scripts/claude_fewex_eq_bench.py adapt --plugin claude_dir_sl_stop --arm loop --seed $S --init pre --source "$W/sl-sources/sl-source-s$S" --out $O --threads 1 > $A/eq-runs/sl-pre-s$S.log 2>&1 &
  echo "seed $S pid $! started $(date -u '+%F %T') UTC"
done
wait
FAILED=0
for S in 0 1; do echo "== seed $S"; tail -2 $A/eq-runs/sl-pre-s$S.log; ls -l $A/eq-runs/sl-pre-s$S/adapt.json || FAILED=1; done
[ "$FAILED" = 0 ] || { echo "STOP: a run has no adapt.json; report the first traceback in its log verbatim"; exit 8; }
$PY scripts/claude_dir_sl_marks.py judge --out $A/JUDGE-dev.json > $A/JUDGE-dev.log 2>&1 || { tail -20 $A/JUDGE-dev.log; echo "STOP: judge failed"; exit 9; }
cat $A/JUDGE-dev.log
shasum -a 256 $A/eq-runs/sl-pre-s?/adapt.json $A/JUDGE-dev.json > $A/SHA256-sl-dev.txt
for S in 0 1; do mkdir -p "$G/$A/eq-runs/sl-pre-s$S"; cp $A/eq-runs/sl-pre-s$S/adapt.json "$G/$A/eq-runs/sl-pre-s$S/"; done
cp $A/eq-runs/*.log "$G/$A/eq-runs/"; cp $A/JUDGE-dev.json $A/JUDGE-dev.log $A/SHA256-sl-dev.txt $A/SELFTEST-marks-adapt-mac.log $A/seal-check-adapt.log "$G/$A/"
mkdir -p "$G/$A/sources"; cp -R $A/sources/. "$G/$A/sources/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, label dev-only): wall time per run; the VERDICT line; per seed the judged-rung lines (x of 300 right, fixed-16 read, cap hits of 300, mean rounds); F_eq and F_few learned and fixed-16 per seed and the accuracy words; the load and disk seen. Do not compute any mark by hand; quote JUDGE-dev.log. Say plainly: dev panel only, holdout unopened, two seeds, and that the plug-in's selftest ran only on random-init nets. Checkpoints (k*.pt, sleep*.pt) stay in $HOME/premonition-sl on the Mac; do not push weights.
AFTER THE RUN (separate step, not you): a blind recount from the raw adapt.json files and PASSMARKS.md only.
PUSH: artifacts/claude-dir-sl-20260928/JUDGE-dev.json artifacts/claude-dir-sl-20260928/JUDGE-dev.log artifacts/claude-dir-sl-20260928/SHA256-sl-dev.txt artifacts/claude-dir-sl-20260928/SELFTEST-marks-adapt-mac.log artifacts/claude-dir-sl-20260928/seal-check-adapt.log artifacts/claude-dir-sl-20260928/eq-runs artifacts/claude-dir-sl-20260928/sources

BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no rental, no BensPC; DESIGN.md section 6 says why: the qualified source checkpoints sit on the Mac and the ruler is CPU fp32). LOAD-LIGHT: no (2 single-thread processes; the two baseline loop jobs took 169 minutes with eight running at once). TIME CAP: 300 minutes. LABEL: h12-stop-dev.
DISK: 2 (about 130 MB of checkpoints per run stay local; never pushed)
HELD-UNTIL: (a) origin/main holds artifacts/claude-dir-h12-stop-20260928 including SEAL-code.sha256.txt (the job builds only from committed files and refuses otherwise; H12's files were pushed to branch claude/h12-stop-training-4sdmvq and need merging first, or set H12_REF to that branch's remote ref); (b) the Director has read DESIGN.md and PASSMARKS.md and accepts them; (c) the two qualified loop source folders exist on the Mac (the job checks; it refuses if not); (d) the Mac is not busy with another long CPU job (uptime).
Owner job (helper H12, Claude, wrote this on 2026-09-28 21:28 UTC for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), fictional names only, blind panels and readpanel320 never opened, never read or print keys or auth files, counts only, every deviation reported.
WHY: artifacts/claude-dir-h12-stop-20260928/DESIGN.md and PASSMARKS.md (committed before any code). One change: the loop's practice stop loss (0.5 x BCE to "answer is exactly right now") is also applied during the 2,048 maze adaptation updates. Practised loop only, seeds 0 and 1, dev panel only; the control is the baseline loop already on main (eq-runs/loop-s{0,1}-pre). The holdout is NOT touched here. You run sealed code; never edit it. If something breaks, stop and report the first traceback verbatim; do not patch.
STOP RULE: any failed check, selftest or traceback: print it, run nothing further, exit non-zero.
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-h12; A=artifacts/claude-dir-h12-stop-20260928; REF=${H12_REF:-origin/main}
SRC=${H12_SRC:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927/runs}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 3 ] || { echo "ABORT: under 3 GB free"; exit 4; }
{ git -C "$G" fetch -q origin main || { sleep 30; git -C "$G" fetch -q origin main; } || { sleep 120; git -C "$G" fetch -q origin main; }; } || { echo "ABORT: fetch failed"; exit 4; }
[ "$REF" = origin/main ] || git -C "$G" fetch -q origin "${REF#origin/}" || { echo "ABORT: fetch of $REF failed"; exit 4; }
git -C "$G" cat-file -e "$REF:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: $REF has no $A/SEAL-code.sha256.txt"; exit 5; }
git -C "$G" show "$REF:artifacts/claude-fewex-20260927/EQ-DEV-GATE.json" | grep -q '"verdict": "PASS"' || { echo "WAITING: baseline ruler gate is not PASS"; exit 5; }
mkdir -p "$W" && git -C "$G" archive "$REF" scripts artifacts/claude-fewex-20260927 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-code.sha256.txt > $A/seal-check.log 2>&1 || { cat $A/seal-check.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
for S in 0 1; do
  [ -f "$SRC/qual-loop-s$S/source.pt" ] && [ -f "$SRC/qual-loop-s$S/source.json" ] || { echo "MISSING-SOURCE: $SRC/qual-loop-s$S"; exit 6; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-loop-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(shasum -a 256 "$SRC/qual-loop-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S (sealed '$want', Mac '$have')"; exit 6; }
  echo "seed $S: qualified source.json matches its sealed sha256; source.pt sha256 $(shasum -a 256 "$SRC/qual-loop-s$S/source.pt" | awk '{print $1}')"
done
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$PY scripts/claude_dir_h12_marks.py selftest > $A/SELFTEST-marks-mac.log 2>&1; cat $A/SELFTEST-marks-mac.log
grep -q '"selftest": "ok"' $A/SELFTEST-marks-mac.log || { echo "STOP: marks selftest failed"; exit 7; }
$PY scripts/claude_dir_h12_selftest.py > $A/SELFTEST-plugin-mac.log 2>&1; cat $A/SELFTEST-plugin-mac.log
grep -q '"selftest": "ok"' $A/SELFTEST-plugin-mac.log || { echo "STOP: plug-in selftest failed"; exit 7; }
mkdir -p $A/eq-runs
for S in 0 1; do
  O=$A/eq-runs/h12-pre-s$S
  [ -f $O/adapt.json ] && { echo "seed $S: adapt.json already exists; not re-running"; continue; }
  [ -d $O ] && { echo "PARTIAL: $O exists without adapt.json (the harness has no resume); delete that folder and start again"; exit 7; }
  nohup perl -e 'alarm shift; exec @ARGV' 17400 $PY scripts/claude_fewex_eq_bench.py adapt --plugin claude_dir_h12_stop --arm loop --seed $S --init pre --source "$SRC/qual-loop-s$S" --out $O --threads 1 > $A/eq-runs/h12-pre-s$S.log 2>&1 &
  echo "seed $S pid $! started $(date -u '+%F %T') UTC"
done
wait
FAILED=0
for S in 0 1; do echo "== seed $S"; tail -2 $A/eq-runs/h12-pre-s$S.log; ls -l $A/eq-runs/h12-pre-s$S/adapt.json || FAILED=1; done
[ "$FAILED" = 0 ] || { echo "STOP: a run has no adapt.json; report the first traceback in its log verbatim"; exit 8; }
$PY scripts/claude_dir_h12_marks.py judge --out $A/JUDGE-dev.json > $A/JUDGE-dev.log 2>&1 || { tail -20 $A/JUDGE-dev.log; echo "STOP: judge failed"; exit 9; }
$PY - <<'PYEOF'
import json
d = json.load(open("artifacts/claude-dir-h12-stop-20260928/JUDGE-dev.json"))
print("VERDICT", d["verdict"], "| validity", d["validity"])
for s in ("0", "1"):
    if "h12" not in d:
        break
    m = d["h12"][s]
    print("seed", s, "S1 rungs", m["s1_rungs_passing"], "of 5 (need 4)", "S2 rungs", m["s2_rungs_passing"], "of 5 (need 5)",
          "F_eq learned %.2f fixed16 %.2f | F_few learned %.2f fixed16 %.2f" % (m["F"]["F_eq"]["learned"], m["F"]["F_eq"]["fixed"], m["F"]["F_few"]["learned"], m["F"]["F_few"]["fixed"]))
    for k, r in m["rungs"].items():
        print("  k", k, "right", r["right"], "fixed16", r["fixed_right"], "cap_hits", r["cap_hits"], "mean_rounds", r["mean_rounds"], "S1", r["S1"], "S2", r["S2"])
if "accuracy" in d:
    print("accuracy words", {k: (v["word"], v["delta_learned_by_seed"], v["body_word"]) for k, v in d["accuracy"].items()})
PYEOF
shasum -a 256 $A/eq-runs/h12-pre-s?/adapt.json $A/JUDGE-dev.json > $A/SHA256-h12-dev.txt
for S in 0 1; do mkdir -p "$G/$A/eq-runs/h12-pre-s$S"; cp $A/eq-runs/h12-pre-s$S/adapt.json "$G/$A/eq-runs/h12-pre-s$S/"; done
cp $A/eq-runs/*.log "$G/$A/eq-runs/"; cp $A/JUDGE-dev.json $A/JUDGE-dev.log $A/SHA256-h12-dev.txt $A/SELFTEST-marks-mac.log $A/SELFTEST-plugin-mac.log $A/seal-check.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, label dev-only): wall time per run; the VERDICT line; per seed the judged-rung lines (x of 300 right, fixed-16 read, cap hits of 300, mean rounds); F_eq and F_few learned and fixed-16 per seed and the two accuracy words; the load and disk seen. Do not compute any mark by hand; quote JUDGE-dev.json. Say plainly: dev panel only, holdout unopened, two seeds, the plug-in's selftest ran on random-init nets. Checkpoints (k*.pt, sleep*.pt) stay in $HOME/premonition-h12 on the Mac; do not push weights.
AFTER THE RUN (separate step, not you): a blind recount from the raw adapt.json files and PASSMARKS.md only.
PUSH: artifacts/claude-dir-h12-stop-20260928/JUDGE-dev.json artifacts/claude-dir-h12-stop-20260928/JUDGE-dev.log artifacts/claude-dir-h12-stop-20260928/SHA256-h12-dev.txt artifacts/claude-dir-h12-stop-20260928/SELFTEST-marks-mac.log artifacts/claude-dir-h12-stop-20260928/SELFTEST-plugin-mac.log artifacts/claude-dir-h12-stop-20260928/seal-check.log artifacts/claude-dir-h12-stop-20260928/eq-runs

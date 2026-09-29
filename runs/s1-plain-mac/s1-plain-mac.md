BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no rental, no BensPC, no vast; same reasons as pond-a-dev: the qualified source checkpoints sit on the Mac and the ruler is CPU fp32). LOAD-LIGHT: no (2 single-thread processes; the baseline dev jobs took about 169 minutes with eight running at once). TIME CAP: 330 minutes. LABEL: s1-plain-mac.
DISK: 2 (about 130 MB of checkpoints per run stay local; never pushed)
HELD-UNTIL: (a) origin/main holds artifacts/claude-s1-d4-20260929 including SEAL-code.sha256.txt (the job builds only from committed files and refuses otherwise; if the S1 files are still only on branch claude/project-thread-urhwlq set S1_REF=origin/claude/project-thread-urhwlq); (b) the two qualified plain source folders exist on the Mac (the job checks; it refuses if not); (c) the Mac is not busy with another long CPU job (uptime). Nothing is held for Ben (standing rule 21:34 UTC 09-28); run it behind the jobs already queued.
Owner job (helper S1, Claude, thread "Turn and flip mazes", wrote this for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), fictional names only, blind panels and readpanel320 never opened, never read or print keys or auth files, counts only, every deviation reported.
WHY: artifacts/claude-s1-d4-20260929/PASSMARKS.md (committed before any code). One change: each maze of each batch is turned by a random one of the 8 rotations/reflections (D4) during the 2,048 maze adaptation updates. A hand-picked, mazes-only prior, NOT kind-blind; applied to the plain arm, seeds 0 and 1, dev panel only. Control is the un-augmented row already on main (eq-runs/plain-s{0,1}-pre). The holdout is NOT touched. You run sealed code; never edit it. If something breaks, stop and report the first traceback verbatim; do not patch.
STOP RULE: any failed check, selftest or traceback: print it, run nothing further, exit non-zero.
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-s1; A=artifacts/claude-s1-d4-20260929; REF=${S1_REF:-origin/main}
SRC=${S1_SRC:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927/runs}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 3 ] || { echo "ABORT: under 3 GB free"; exit 4; }
{ git -C "$G" fetch -q origin main || { sleep 30; git -C "$G" fetch -q origin main; } || { sleep 120; git -C "$G" fetch -q origin main; }; } || { echo "ABORT: fetch failed"; exit 4; }
[ "$REF" = origin/main ] || git -C "$G" fetch -q origin "${REF#origin/}" || { echo "ABORT: fetch of $REF failed"; exit 4; }
git -C "$G" cat-file -e "$REF:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: $REF has no $A/SEAL-code.sha256.txt"; exit 5; }
git -C "$G" show "$REF:artifacts/claude-fewex-20260927/EQ-DEV-GATE.json" | grep -q '"verdict": "PASS"' || { echo "WAITING: baseline ruler gate is not PASS"; exit 5; }
mkdir -p "$W" && git -C "$G" archive "$REF" scripts artifacts/claude-fewex-20260927 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-code.sha256.txt > $A/seal-check-plain.log 2>&1 || { cat $A/seal-check-plain.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check-plain.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
for S in 0 1; do
  [ -f "$SRC/qual-plain-s$S/source.pt" ] && [ -f "$SRC/qual-plain-s$S/source.json" ] || { echo "MISSING-SOURCE: $SRC/qual-plain-s$S"; exit 6; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-plain-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(shasum -a 256 "$SRC/qual-plain-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S (sealed '$want', Mac '$have')"; exit 6; }
  echo "seed $S: qualified source.json matches its sealed sha256; source.pt sha256 $(shasum -a 256 "$SRC/qual-plain-s$S/source.pt" | awk '{print $1}')"
done
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$PY scripts/claude_s1_d4_marks.py selftest > $A/SELFTEST-marks-mac-plain.log 2>&1; cat $A/SELFTEST-marks-mac-plain.log
grep -q '"selftest": "ok"' $A/SELFTEST-marks-mac-plain.log || { echo "STOP: marks selftest failed"; exit 7; }
$PY scripts/claude_s1_d4_selftest.py > $A/SELFTEST-plugin-mac-plain.log 2>&1; tail -2 $A/SELFTEST-plugin-mac-plain.log
grep -q '"selftest": "ok", "part_b": "ran"' $A/SELFTEST-plugin-mac-plain.log || { echo "STOP: plug-in selftest failed (part B must run on the Mac)"; exit 7; }
mkdir -p $A/eq-runs
for S in 0 1; do
  O=$A/eq-runs/s1-plain-pre-s$S
  [ -f $O/adapt.json ] && { echo "seed $S: adapt.json already exists; not re-running"; continue; }
  [ -d $O ] && { echo "PARTIAL: $O exists without adapt.json (the harness has no resume); delete that folder and start again"; exit 7; }
  nohup perl -e 'alarm shift; exec @ARGV' 17400 $PY scripts/claude_fewex_eq_bench.py adapt --plugin claude_s1_d4 --arm plain --seed $S --init pre --source "$SRC/qual-plain-s$S" --out $O --threads 1 > $A/eq-runs/s1-plain-pre-s$S.log 2>&1 &
  echo "seed $S pid $! started $(date -u '+%F %T') UTC"
done
wait
FAILED=0
for S in 0 1; do echo "== seed $S"; grep d4_views $A/eq-runs/s1-plain-pre-s$S.log | tail -2; tail -2 $A/eq-runs/s1-plain-pre-s$S.log; ls -l $A/eq-runs/s1-plain-pre-s$S/adapt.json || FAILED=1; done
[ "$FAILED" = 0 ] || { echo "STOP: a run has no adapt.json; report the first traceback in its log verbatim"; exit 8; }
# report-only 8-view vote (dev panel only, no mark reads it)
for S in 0 1; do
  nohup perl -e 'alarm shift; exec @ARGV' 7200 $PY scripts/claude_s1_d4_vote.py run --arm plain --seed $S --dir $A/eq-runs/s1-plain-pre-s$S --source "$SRC/qual-plain-s$S" > $A/eq-runs/s1-plain-vote-s$S.log 2>&1 &
done
wait
for S in 0 1; do echo "== vote seed $S"; tail -3 $A/eq-runs/s1-plain-vote-s$S.log; done
shasum -a 256 $A/eq-runs/s1-plain-pre-s?/adapt.json $A/eq-runs/s1-plain-pre-s?/vote.json > $A/SHA256-s1-plain-dev.txt 2>/dev/null
for S in 0 1; do mkdir -p "$G/$A/eq-runs/s1-plain-pre-s$S"; cp $A/eq-runs/s1-plain-pre-s$S/adapt.json "$G/$A/eq-runs/s1-plain-pre-s$S/"; cp $A/eq-runs/s1-plain-pre-s$S/vote.json "$G/$A/eq-runs/s1-plain-pre-s$S/" 2>/dev/null; done
cp $A/eq-runs/s1-plain-*.log "$G/$A/eq-runs/"; cp $A/SHA256-s1-plain-dev.txt $A/SELFTEST-marks-mac-plain.log $A/SELFTEST-plugin-mac-plain.log $A/seal-check-plain.log "$G/$A/"
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, label dev-only): wall time per run; the d4_views line per seed (views drawn, redrawn for the leak guard); per seed the dev F_eq and rung counts of 300 straight from adapt.json (do not compute any mark by hand; the Director runs `python -B scripts/claude_s1_d4_marks.py judge` after all four runs land); the vote lines. Say plainly: dev panel only, holdout unopened, two seeds, hand-picked mazes-only prior. Checkpoints (k*.pt, sleep*.pt) stay in $HOME/premonition-s1 on the Mac; do not push weights.
AFTER THE RUN (separate step, not you): a blind recount from the raw adapt.json files and PASSMARKS.md only.
PUSH: artifacts/claude-s1-d4-20260929/eq-runs artifacts/claude-s1-d4-20260929/SHA256-s1-plain-dev.txt artifacts/claude-s1-d4-20260929/SELFTEST-marks-mac-plain.log artifacts/claude-s1-d4-20260929/SELFTEST-plugin-mac-plain.log artifacts/claude-s1-d4-20260929/seal-check-plain.log

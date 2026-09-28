STATUS: HELD. DO NOT RUN until the Director releases it (helper "sleep tests sealer", 2026-09-28 22:13 UTC from date -u). Delete this line to release.
BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no rental, no BensPC). LOAD-LIGHT: no (2 single-thread processes; each sleep about 6 to 7 minutes, inferred from the distill test's 255 to 290 s plus scoring) (12 sleeps). TIME CAP: 100 minutes. LABEL: dst-t1-2-fresh.
DISK: 1 (no weights written; the start nets are read from $HOME/premonition-ks/nets, written by ks-1-lead0)
Owner job (Director helper "sleep tests sealer", Claude, wrote this on 2026-09-28 for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), fictional names only, blind panels and readpanel320 never opened, never read or print keys or auth files, counts only, every deviation reported. The ruler's holdout is never opened; dev panels only.
WHY: T1 arm FRESH (the change): fresh code-made old-kind puzzles every update, KL to the pre-maze net only, the store is not trained on. Marks: artifacts/claude-dir-t1-fresh-20260928/PASSMARKS.md. You run sealed code; never edit it. If something breaks, print the first traceback verbatim, run nothing further, exit non-zero (STOP RULE). Do not re-run a failed sleep with changed settings.
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-dst; A2=artifacts/claude-dir-t2-selfpick-20260928; A1=artifacts/claude-dir-t1-fresh-20260928; AX=artifacts/claude-dir-t1-fresh-20260928; ARM=FRESH
SRC=${KS_SRC:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 KS_SRC="$SRC" KS_NETS="${KS_NETS:-$HOME/premonition-ks/nets}"
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 2 ] || { echo "ABORT: under 2 GB free"; exit 4; }
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" cat-file -e "origin/main:$AX/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: origin/main has no $AX/SEAL-code.sha256.txt"; exit 5; }
mkdir -p "$W" && git -C "$G" archive origin/main scripts artifacts/claude-fewex-20260927 $A2 $A1 | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $AX/SEAL-code.sha256.txt > $AX/seal-check.log 2>&1 || { cat $AX/seal-check.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $AX/seal-check.log) of $(wc -l < $AX/SEAL-code.sha256.txt | tr -d ' ') files OK"
for S in 0 1; do
  [ -f "$SRC/runs/qual-loop-s$S/source.pt" ] && [ -f "$SRC/runs/qual-loop-s$S/source.json" ] || { echo "MISSING-SOURCE: $SRC/runs/qual-loop-s$S"; exit 6; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-loop-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(shasum -a 256 "$SRC/runs/qual-loop-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S (sealed '$want', Mac '$have')"; exit 6; }
  for f in k0 k64 k16384; do [ -f "$KS_NETS/loop-s$S-pre/$f.pt" ] || { echo "WAITING: run ks-1-lead0 first (no $f.pt for seed $S in $KS_NETS)"; exit 5; }; done
done
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
mkdir -p $AX/logs $AX/sleeps
python3 scripts/claude_dir_t12_marks.py selftest || { echo "STOP: marks selftest failed"; exit 7; }
if [ ! -f $A2/selftest.json ]; then
  $PY scripts/claude_dir_t12_sleep.py selftest 2>&1 | tee $AX/logs/selftest.log
  grep -q "t12 selftest ok" $AX/logs/selftest.log || { echo "STOP: torch selftest failed (first traceback above)"; exit 7; }
fi
run2() { xargs -P 2 -I{} sh -c 'L=$(echo "{}" | tr " -" "__"); '"$PY"' scripts/claude_dir_t12_sleep.py {} > '"$AX"'/logs/$L.log 2>&1 || echo "FAILED {}"'; }
for D in 0 1 2; do for S in 0 1; do for K in 64 16384; do echo "sleep --seed $S --k $K --arm $ARM --draw $D"; done; done; done | run2
echo "records for $ARM: $(ls $AX/sleeps | grep -c -- "-$ARM-d")"
for f in $AX/logs/sleep*"$ARM"*.log; do tail -1 "$f"; done
mkdir -p "$G/$AX"; for d in sleeps logs; do [ -d $AX/$d ] && { mkdir -p "$G/$AX/$d"; cp -R $AX/$d/. "$G/$AX/$d/"; }; done
cp $AX/seal-check.log "$G/$AX/seal-check-$ARM.log" 2>/dev/null
[ -f $A2/selftest.json ] && cp $A2/selftest.json "$G/$A2/" 2>/dev/null
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only, dev panels only): the number of sleep records written for FRESH (12 wanted), and for each record its old (sums4, grids5 of 200), fresh_old and maze9 (of 300) as printed in the last line of its log; any FAILED line verbatim. Do not compute a verdict; the Director runs `python3 scripts/claude_dir_t12_marks.py report t1` after all arms of the test are in, and a blind recount follows.
PUSH: artifacts/claude-dir-t1-fresh-20260928/sleeps artifacts/claude-dir-t1-fresh-20260928/logs artifacts/claude-dir-t2-selfpick-20260928/selftest.json

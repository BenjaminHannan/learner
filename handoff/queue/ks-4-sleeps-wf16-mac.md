STATUS: HELD. DO NOT RUN (helper "keep old skills", 2026-09-28): Lead 2 runs only after the blend result (ks-2) is in. The helper deletes this line when it starts.
GPU: no (Mac CPU, strict fp32, $0, no rental, no BensPC). LOAD-LIGHT: no (2 single-thread processes; each sleep about 5 min) (12 sleeps; run only after the blend result is in). TIME CAP: 90 minutes. LABEL: ks-4-sleeps-wf16.
DISK: 2 (checkpoints, about 7 MB per net, up to 9 nets per seed, stay local in $HOME/premonition-ks and are never pushed)
Owner job (Director helper "keep old skills", Claude, wrote this on 2026-09-28 for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), fictional names only, blind panels and readpanel320 never opened, never read or print keys or auth files, counts only, every deviation reported. The ruler's holdout is never opened; dev panels only.
WHY: artifacts/claude-dir-ks-20260928/PASSMARKS.md (committed before any run). You run sealed code; never edit it. If something breaks, print the first traceback verbatim, run nothing further, exit non-zero (STOP RULE).
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-ks; A=artifacts/claude-dir-ks-20260928
SRC=${KS_SRC:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927}
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 KS_SRC="$SRC" KS_NETS="$W/nets"
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 3 ] || { echo "ABORT: under 3 GB free"; exit 4; }
{ git -C "$G" fetch -q origin main || { sleep 30; git -C "$G" fetch -q origin main; } || { sleep 120; git -C "$G" fetch -q origin main; }; } || { echo "ABORT: fetch failed"; exit 4; }
git -C "$G" cat-file -e "origin/main:$A/SEAL-code.sha256.txt" 2>/dev/null || { echo "WAITING: origin/main has no $A/SEAL-code.sha256.txt"; exit 5; }
mkdir -p "$W" && git -C "$G" archive origin/main scripts artifacts/claude-fewex-20260927 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL-code.sha256.txt > $A/seal-check.log 2>&1 || { cat $A/seal-check.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check.log) of $(wc -l < $A/SEAL-code.sha256.txt | tr -d ' ') files OK"
for S in 0 1; do
  [ -f "$SRC/runs/qual-loop-s$S/source.pt" ] && [ -f "$SRC/runs/qual-loop-s$S/source.json" ] || { echo "MISSING-SOURCE: $SRC/runs/qual-loop-s$S"; exit 6; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-loop-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(shasum -a 256 "$SRC/runs/qual-loop-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH seed $S (sealed '$want', Mac '$have')"; exit 6; }
done
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
mkdir -p $A/logs
run2() { while read -r L; do while [ "$(jobs -rp | wc -l | tr -d ' ')" -ge 2 ]; do sleep 5; done; N=$(echo "$L" | tr ' -' '__'); ( $PY scripts/claude_dir_ks_run.py $L > $A/logs/$N.log 2>&1 || echo "FAILED $L" ) & done; wait; }
for S in 0 1; do [ -f "$KS_NETS/loop-s$S-pre/k64.pt" ] && [ -f "$KS_NETS/loop-s$S-pre/k16384.pt" ] || { echo "WAITING: run ks-1-lead0 first (no nets for seed $S)"; exit 5; }; done
printf '%s\n' "sleep --seed 0 --k 64 --arm WF16 --draw 0" "sleep --seed 0 --k 16384 --arm WF16 --draw 0" "sleep --seed 1 --k 64 --arm WF16 --draw 0" "sleep --seed 1 --k 16384 --arm WF16 --draw 0" "sleep --seed 0 --k 64 --arm WF16 --draw 1" "sleep --seed 0 --k 16384 --arm WF16 --draw 1" "sleep --seed 1 --k 64 --arm WF16 --draw 1" "sleep --seed 1 --k 16384 --arm WF16 --draw 1" "sleep --seed 0 --k 64 --arm WF16 --draw 2" "sleep --seed 0 --k 16384 --arm WF16 --draw 2" "sleep --seed 1 --k 64 --arm WF16 --draw 2" "sleep --seed 1 --k 16384 --arm WF16 --draw 2" | run2
ls $A/sleeps | wc -l
mkdir -p "$G/$A"; for d in prep lead0 blend frows sleeps logs; do [ -d $A/$d ] && { mkdir -p "$G/$A/$d"; cp -R $A/$d/. "$G/$A/$d/"; }; done
cp $A/selftest.json $A/seal-check.log "$G/$A/" 2>/dev/null
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): the number of sleep records written, and for each record its old (sums4, grids5 of 200) and maze9 (of 300) as printed in the last line of its log. Do not compute a verdict.
PUSH: artifacts/claude-dir-ks-20260928/sleeps artifacts/claude-dir-ks-20260928/logs

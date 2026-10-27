STATUS: HELD. DO NOT RUN (Opus manager helper "five-days sealer", 2026-09-29 03:35 UTC from date -u). Real dependencies: (1) H1's kinds results must be on origin/main: artifacts/claude-dir-h1-heldout-20260928/DEV-GATE-graph.json and DEV-GATE-rank.json (job dir-h1-heldout-r2 is running; the job below stops with WAITING until both exist, and PASSMARKS rule K1 substitutes a kind whose gate is not PASS); (2) the four qualified sources qual-{loop,plain}-s{0,1}/source.pt and source.json must be on the Mac at the path below (they are not in git); (3) the Director has committed artifacts/opus-manager-20260929/five-days/ (PASSMARKS.md, DESIGN.md, SEAL.sha256.txt, the two scripts) to origin/main. The Director releases by deleting this line.
BASH-ONLY: yes
GPU: no (Mac CPU, strict fp32, $0, no rental, no BensPC). LOAD-LIGHT: no (up to 10 single-thread processes at once; each holds about 1 GB of RAM at most). TIME CAP: 780 minutes for the whole job (estimate: loop chains about 600 min, plain about 330, ref jobs 190 to 270; 8 chains plus 2 ref jobs run at once on a 10-core Mac, the other 2 ref jobs start when a ref job ends; on 8 cores or fewer expect 1.3 to 1.5 times longer; estimates scale from the ruler's 169 min per 8-rung loop ladder and 120 min plain, not measured at full size). Resume-safe: rerunning the job skips every stage whose JSON exists. LABEL: opus-fd-1.
DISK: 3 (about 1.1 GB of local checkpoints under $HOME/premonition-fd, never pushed)
Owner job (Opus manager helper "five-days sealer", Claude, wrote this on 2026-09-29 03:35 UTC 2026-09-29 for the Director). Follow handoff/director-briefs/rules.md: additive only, no git commits or pushes by the job (the watcher pushes PUSH paths), fictional names only, blind panels and readpanel320 never opened, never read or print keys or auth files, counts only, every deviation reported. No holdout, test or blind panel is opened or built for scoring: dev panels only.
WHY: artifacts/opus-manager-20260929/five-days/PASSMARKS.md (committed before any run; DESIGN.md beside it). This is Ben's problem 5: five day/night cycles, a new held-out kind each day (maze, graph, rank, compose, odd), night replay of old kinds drawn fresh from generators versus the fixed 16-item store, a plasticity probe after every night, a plain-net row, 2 seeds, 3 sleep draws. You run sealed code; never edit it. If something breaks, print the first traceback verbatim, run nothing further, exit non-zero (STOP RULE).
```bash
set -o pipefail
G=$(pwd); W=$HOME/premonition-fd; A=artifacts/opus-manager-20260929/five-days
SRC=${FD_SRC:-/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927}
H1=artifacts/claude-dir-h1-heldout-20260928
PLAN=maze,graph,rank,compose,odd   # PASSMARKS rule K: the Director may edit this line ONLY before the first run, and only per K1/K2
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
echo "start $(date -u '+%F %T') UTC"; uptime; df -g / | tail -1; sysctl -n hw.ncpu
FREE=$(df -g / | awk 'NR==2{print $4}'); [ "${FREE:-0}" -ge 4 ] || { echo "ABORT: under 4 GB free"; exit 4; }
git -C "$G" fetch -q origin main || { echo "ABORT: fetch failed"; exit 4; }
for f in $A/SEAL.sha256.txt $H1/DEV-GATE-graph.json $H1/DEV-GATE-rank.json; do
  git -C "$G" cat-file -e "origin/main:$f" 2>/dev/null || { echo "WAITING: origin/main has no $f"; exit 5; }
done
mkdir -p "$W" && git -C "$G" archive origin/main scripts artifacts/claude-fewex-20260927 $H1 $A | tar -x -C "$W" || { echo "ABORT: archive failed"; exit 4; }
cd "$W" || exit 4
shasum -a 256 -c $A/SEAL.sha256.txt > $A/seal-check.log 2>&1 || { cat $A/seal-check.log; echo "SEAL-MISMATCH"; exit 6; }
echo "seal: $(grep -c ': OK$' $A/seal-check.log) of $(wc -l < $A/SEAL.sha256.txt | tr -d ' ') files OK"
for arm in loop plain; do for S in 0 1; do
  [ -f "$SRC/runs/qual-$arm-s$S/source.pt" ] && [ -f "$SRC/runs/qual-$arm-s$S/source.json" ] || { echo "MISSING-SOURCE: $SRC/runs/qual-$arm-s$S"; exit 6; }
  want=$(awk -v f="artifacts/claude-fewex-20260927/runs/qual-$arm-s$S/source.json" '$2==f {print $1}' artifacts/claude-fewex-20260927/SHA256-EQ-RAW.txt)
  have=$(shasum -a 256 "$SRC/runs/qual-$arm-s$S/source.json" | awk '{print $1}')
  [ -n "$want" ] && [ "$want" = "$have" ] || { echo "SOURCE-JSON-MISMATCH $arm seed $S (sealed '$want', Mac '$have')"; exit 6; }
done; done
for K in graph rank; do
  python3 -c "import json,sys; sys.exit(0 if json.load(open('$H1/DEV-GATE-$K.json')).get('verdict')=='PASS' else 1)" || { echo "K1: H1 dev gate for $K is not PASS: the Director substitutes a reserve kind (PASSMARKS rule K) and edits PLAN"; exit 7; }
done
U=$(command -v uv || echo "$HOME/.local/bin/uv")
PY="$U run --offline --no-project --python 3.12 --with torch --with numpy python -B"
mkdir -p $A/logs
$PY scripts/opus_fd_run.py selftest --threads 1 2>&1 | tee $A/selftest-mac.log | grep -v '"phase"'
grep -q '"selftest": "ok"' $A/selftest-mac.log || { echo "STOP: selftest failed"; exit 7; }
python3 -B scripts/opus_fd_marks.py selftest | tail -1
# rule K2: learnability pilot for days 4 and 5 (practised loop, both seeds, 64 examples, own pilot panel); a failure stops the job
for KD in $(echo $PLAN | tr ',' ' '); do case $KD in maze|graph|rank) ;; *) for S in 0 1; do
  $PY scripts/opus_fd_run.py pilot --kind $KD --seed $S --source-root $SRC/runs > $A/logs/pilot_${KD}_s$S.log 2>&1 &
done;; esac; done; wait
grep -h '"learned"' $A/logs/pilot_*.log
grep -h '"learned": false' $A/logs/pilot_*.log && { echo "K2: a pilot kind is not learnable at 64 examples: the Director substitutes a reserve (PASSMARKS rule K) and edits PLAN"; exit 8; }
mkdir -p $A/runs
ALL=$( { for S in 0 1; do echo "chain --arm loop --night store --seed $S"; echo "chain --arm loop --night fresh --seed $S"; done
          for S in 0 1; do echo "chain --arm plain --night store --seed $S"; echo "chain --arm plain --night fresh --seed $S"; done
          for S in 0 1; do echo "ref --arm loop --seed $S"; done; for S in 0 1; do echo "ref --arm plain --seed $S"; done; } )
echo "$ALL" | xargs -P 10 -I{} sh -c 'L=$(echo "{}" | tr " -" "__"); '"$PY"' scripts/opus_fd_run.py {} --source-root '"$SRC/runs"' --plan '"$PLAN"' --out-root '"$A/runs"' > '"$A"'/logs/$L.log 2>&1 || echo "FAILED {}"'
for d in loop-store loop-fresh plain-store plain-fresh; do for S in 0 1; do [ -f $A/runs/$d-s$S/chain-done.json ] || echo "MISSING chain $d s$S (see $A/logs)"; done; done
for a in loop plain; do for S in 0 1; do [ -f $A/runs/ref-$a-s$S/ref-day5.json ] || echo "MISSING ref $a s$S (see $A/logs)"; done; done
python3 -B scripts/opus_fd_marks.py score --runs $A/runs --out $A/SCORE.json | tail -3
mkdir -p "$G/$A"; cp -R $A/logs $A/seal-check.log $A/selftest-mac.log $A/SCORE.json "$G/$A/" 2>/dev/null
mkdir -p "$G/$A/runs"; (cd $A/runs && find . -name '*.json' -o -name '*.log' | while read f; do mkdir -p "$G/$A/runs/$(dirname $f)"; cp "$f" "$G/$A/runs/$f"; done)
echo "end $(date -u '+%F %T') UTC"
```
REPORT (final reply, counts only): seal line, selftest lines, the pilot lines, for each chain the night-5 draw scores from the last line of its log (counts of 200 / 300), the ref jobs' night-0 F_eq as computed by SCORE.json, and the line "VERDICT:" printed by opus_fd_marks.py. This job prints the verdict only as the marks' own code computes it; the independent blind recount from the raw JSON and PASSMARKS.md is a separate step, and the ruler's night-0 dev ladder (RESULTS-EQ.md dev table) is quoted next to the ref job's night-0 numbers as a reproducibility check (report only).
PUSH: artifacts/opus-manager-20260929/five-days/runs artifacts/opus-manager-20260929/five-days/logs artifacts/opus-manager-20260929/five-days/SCORE.json artifacts/opus-manager-20260929/five-days/selftest-mac.log artifacts/opus-manager-20260929/five-days/seal-check.log

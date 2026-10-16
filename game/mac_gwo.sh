#!/bin/bash
# GW-O (game world thread, addendum A29) on Ben's Mac: both seeds of the one-step lookahead loop, the round-3 check, the sealed scores, results to git.
#   bash mac_gwo.sh setup     fetch code + inputs, check the parents (sha), the venv and the imports, run the lookahead tests, time one replay
#   bash mac_gwo.sh start     launch the whole pipeline detached (survives the shell; caffeinate keeps the Mac awake)
#   bash mac_gwo.sh status    short progress report
#   bash mac_gwo.sh push      copy logs + results to branch claude/game-world-mac-results now
#   bash mac_gwo.sh pipeline  (what start runs) both loops, round-3 check, sealed scores, push; safe to rerun: finished steps are skipped, the loops resume from state.pt
# Env: REPO = a clone of BenjaminHannan/learner (found under ~ when unset); GW8 = work folder (default ~/gw8); THREADS = torch threads per loop
#      (default half the performance cores); WORKERS = replay-and-fork processes per loop (default 3); GWO_SMOKE=1 = tiny test of this script (2 rounds, 3 games, no push).
#      Works with macOS bash 3.2 and BSD tools. Marks: game/A29-GWO-MARKS.md (fixed before any code ran).
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
GW8=${GW8:-$HOME/gw8}
SMOKE=${GWO_SMOKE:-0}
BRANCH=claude/project-thread-h2ya81
INPUTS=claude/game-world-inputs
RESULTS=claude/game-world-mac-results
MARKS_CODE=7251d5eac3        # game code the Mac run is pinned to (A29 code 55fc44b4fa plus saving the round-3 checkpoint); setup refuses game code that differs
SHA_200=22f70906443a9640cee5abf440a7afe229f6d1f167cae3709cbf224bd23cde7f
SHA_201=edbd1ee4a6b8d2be983de74bbad757d12249cf6671401e0999c3645ffbbfb795
T0_200=19.69166187674003
T0_201=20.368329364318342
RUNSEED_200=396
RUNSEED_201=397
SEEDS="200 201"
VPY=${GW8_PY:-$GW8/venv/bin/python}
CODE=$GW8/code-gwo
RUNS=$GW8/gwo-runs
SCORE_DIR=$GW8/gwo-score
[ "$SMOKE" = 1 ] && { RUNS=$GW8/gwo-smoke-runs; SCORE_DIR=$GW8/gwo-smoke-score; }
ITERS=7; [ "$SMOKE" = 1 ] && ITERS=2

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
die() { log "FAILED: $*"; exit 1; }
sha() { if command -v shasum >/dev/null; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi; }
parent() { echo "$GW8/inputs/checkpoints/cio-1007/70-t1sdr-s$1/T1SDR_s$1/checkpoint.pt"; }

find_repo() {
  if [ -n "${REPO:-}" ]; then echo "$REPO"; return 0; fi
  for d in "$HOME"/learner "$HOME"/*/learner "$HOME"/*/*/learner "$HOME"/*; do
    [ -e "$d/.git" ] || continue
    if git -C "$d" remote get-url origin 2>/dev/null | grep -qi 'BenjaminHannan/learner'; then echo "$d"; return 0; fi
  done
  return 1
}

threads() {
  if [ -n "${THREADS:-}" ]; then echo "$THREADS"; return; fi
  local p
  p=$(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || sysctl -n hw.physicalcpu 2>/dev/null || nproc 2>/dev/null || echo 4)
  p=$((p / 2)); [ "$p" -lt 1 ] && p=1; echo "$p"
}

pick_python() {
  local p
  for p in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$p" >/dev/null && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      command -v "$p"; return 0
    fi
  done
  return 1
}

setup() {
  local R CODE_SHA s got want
  R=$(find_repo) || die "no clone of BenjaminHannan/learner under ~; rerun with REPO=/path/to/clone"
  log "repo $R"
  mkdir -p "$GW8/logs" "$SCORE_DIR" "$RUNS"
  git -C "$R" fetch -q origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" "+refs/heads/$INPUTS:refs/remotes/origin/$INPUTS" || die "git fetch"
  # code under test: its own detached worktree at the branch tip (the GW-P8 worktree $GW8/code is left alone)
  if [ -e "$CODE/.git" ]; then git -C "$CODE" checkout -q --detach "origin/$BRANCH" || die "checkout code"
  else git -C "$R" worktree add -q --detach "$CODE" "origin/$BRANCH" || die "worktree add"; fi
  CODE_SHA=$(git -C "$CODE" rev-parse HEAD)
  git -C "$CODE" diff --quiet "$MARKS_CODE" HEAD -- game domain custom_io ':(exclude)*.md' ':(exclude)*.sh' ':(exclude)game/results' ':(exclude)game/tests' \
    || die "game code at $CODE_SHA differs from the marks commit $MARKS_CODE (git -C $CODE diff $MARKS_CODE HEAD -- game)"
  log "code $CODE_SHA (game code = marks commit $MARKS_CODE)"
  # parents (the GW-P8 setup already put them in $GW8/inputs; extract them again only if missing)
  for s in $SEEDS; do
    [ -f "$(parent $s)" ] || { git -C "$R" archive "origin/$INPUTS" inputs | tar -x -C "$GW8" || die "inputs archive"; }
    got=$(sha "$(parent $s)"); eval "want=\$SHA_$s"
    [ "$got" = "$want" ] || die "parent s$s sha $got != $want"
  done
  log "parents sha ok"
  # venv (reused from GW-P8 when it exists)
  if [ ! -x "$VPY" ]; then
    local PY; PY=$(pick_python)
    if [ -z "$PY" ]; then
      command -v uv >/dev/null || die "need python >= 3.10 (brew install python@3.12) or uv"
      uv venv -q --python 3.12 "$GW8/venv" || die "uv venv"
    else
      "$PY" -m venv "$GW8/venv" || die "venv"
    fi
  fi
  if [ "${SKIP_PIP:-0}" != 1 ]; then
    "$VPY" -m pip install -q --upgrade pip >/dev/null 2>&1 || true
    "$VPY" -m pip install -q torch numpy crafter==1.8.3 opensimplex==0.4.5.1 || die "pip install"
  fi
  (cd "$CODE" && PYTHONPATH=. "$VPY" -c "import torch, numpy, crafter; import game.lookahead, game.imitate, game.score; \
print('python', __import__('sys').version.split()[0], 'torch', torch.__version__, 'numpy', numpy.__version__)") || die "imports"
  # the lookahead tests (exactness of the one-step labels on this machine; about a minute)
  (cd "$CODE" && PYTHONPATH=. "$VPY" -m unittest game.tests.test_lookahead) > "$GW8/logs/gwo-tests.out" 2>&1 || die "lookahead tests failed, see $GW8/logs/gwo-tests.out"
  log "lookahead tests ok"
  local t0=$(date +%s)
  (cd "$CODE" && PYTHONPATH=. "$VPY" -c "
import time
from game import lookahead, play
from game.tests.test_lookahead import oracle_game, CAP
g = oracle_game(play.practice_seed(396, 0, 3), 100)
t = time.time(); rows = lookahead.label_game(g, CAP); dt = time.time() - t
print('replay-and-fork', len(g['actions']), 'steps', round(dt, 1), 's =', round(1000 * dt / len(g['actions']), 1), 'ms a step,', len(rows), 'rows')
") 2>&1 | tee "$GW8/logs/gwo-speed.out" | tail -1
  log "SETUP OK ($(( $(date +%s) - t0 )) s for the speed check). Next: bash $CODE/game/mac_gwo.sh start"
}

start() {
  [ -x "$VPY" ] && [ -e "$CODE/.git" ] || die "run setup first"
  if pgrep -f "label-rule lookahead" >/dev/null || pgrep -f "mac_gwo.sh pipeline" >/dev/null; then
    log "already running"; status; return 0
  fi
  local CAF=""; command -v caffeinate >/dev/null && CAF="caffeinate -ims"
  mkdir -p "$GW8/logs"
  nohup perl -e 'use POSIX qw(setsid); setsid(); exec @ARGV' -- $CAF /bin/bash "$CODE/game/mac_gwo.sh" pipeline \
    >> "$GW8/logs/gwo-pipeline.out" 2>&1 < /dev/null &
  sleep 20
  log "started (detached${CAF:+, $CAF})"
  status
}

run_loops() {   # starts both loops (they resume from state.pt) and waits for them
  local TH s pids="" W
  TH=$(threads); W=${WORKERS:-3}
  for s in $SEEDS; do
    eval "T0=\$T0_$s; RS=\$RUNSEED_$s"
    local EXTRA=""; [ "$SMOKE" = 1 ] && EXTRA="--smoke"
    "$VPY" -m game.imitate run --parent "$(parent $s)" --seed $s --run-seed $RS --t0 $T0 --out "$RUNS/o$s" --iterations "$ITERS" --threads "$TH" \
      --label-rule lookahead --epochs 10 --workers "$W" $EXTRA >> "$GW8/logs/gwo-s$s.out" 2>&1 &
    pids="$pids $!"
    log "seed $s: loop started (pid $!, run seed $RS)"
  done
  for p in $pids; do wait "$p"; log "loop pid $p exit $?"; done
}

gate3() {   # A29 round-3 check; writes GATE3O.json; exit 0 = keep going, 1 = proved wrong (stop)
  "$VPY" - <<PYEOF
import json, sys
R = '$RUNS'
out = {}
for s in (200, 201):
    its = [json.load(open('%s/o%d/iter-%d.json' % (R, s, k))) for k in (2, 3)]
    sh = [i['ready']['wpick_share'] for i in its]
    sh = sum(x for x in sh if x is not None) / max(1, sum(x is not None for x in sh))
    out[s] = dict(mean_share=round(sh, 4), mean_g_pick=sum(i['g_pick'] for i in its) / 2, mean_g_stone=sum(i['g_stone'] for i in its) / 2)
out['pass'] = all(out[s]['mean_share'] >= 0.30 for s in (200, 201))
out['stop'] = all(out[s]['mean_share'] < 0.15 for s in (200, 201))
json.dump(out, open('%s/GATE3O.json' % R, 'w'), indent=1)
print(json.dumps(out))
sys.exit(1 if out['stop'] else 0)
PYEOF
}

score_iter() {  # score_iter N: sealed scores (100 maps, sample, T = 1) of checkpoint-iterN.pt of both seeds, side by side
  local N=$1 TH s pids="" W=100
  TH=$(threads); [ "$SMOKE" = 1 ] && W=2
  for s in $SEEDS; do
    [ -f "$SCORE_DIR/o$s-iter$N.json" ] && continue
    [ -f "$RUNS/o$s/checkpoint-iter$N.pt" ] || { log "seed $s: no checkpoint-iter$N.pt"; continue; }
    "$VPY" -m game.score --arm model --picker sample --temp 1.0 --ckpt "$RUNS/o$s/checkpoint-iter$N.pt" --worlds $W --threads "$TH" \
      --out "$SCORE_DIR/o$s-iter$N.json" >> "$GW8/logs/gwo-score-s$s.out" 2>&1 &
    pids="$pids $!"
  done
  for p in $pids; do wait "$p"; done
  log "sealed scores at iteration $N done"
}

pipeline() {
  local TH PUSHER
  cd "$CODE" || die "no code folder"
  export PYTHONPATH=.
  TH=$(threads)
  export OMP_NUM_THREADS=$TH MKL_NUM_THREADS=$TH VECLIB_MAXIMUM_THREADS=$TH
  log "pipeline start (GW-O): code $(git rev-parse HEAD), $TH threads per loop, smoke=$SMOKE"
  ( while true; do sleep 1200; push_results > /dev/null 2>&1; done ) &
  PUSHER=$!
  mkdir -p "$RUNS" "$SCORE_DIR"
  # rounds 1 to 3 first (the round-3 check), then the rest; run_loops resumes from state.pt
  if [ "$SMOKE" != 1 ] && [ ! -f "$RUNS/GATE3O.json" ] && ! { [ -f "$RUNS/o200/iter-3.json" ] && [ -f "$RUNS/o201/iter-3.json" ]; }; then
    ITERS=3 run_loops
  fi
  if [ "$SMOKE" != 1 ]; then
    if [ -f "$RUNS/o200/iter-3.json" ] && [ -f "$RUNS/o201/iter-3.json" ]; then
      [ -f "$RUNS/GATE3O.json" ] || gate3 > "$GW8/logs/gwo-gate3.out" 2>&1
      cat "$GW8/logs/gwo-gate3.out" 2>/dev/null | tail -1
      if "$VPY" -c "import json,sys; sys.exit(0 if json.load(open('$RUNS/GATE3O.json'))['stop'] else 1)"; then
        log "round-3 check: proved wrong on both seeds (ready-state wpick share < 15%); stopping GW-O"
        score_iter 3; kill "$PUSHER" 2>/dev/null; push_results; log "PIPELINE DONE (stopped at round 3)"; return 0
      fi
      log "round-3 check: not proved wrong; continuing to round $ITERS"
    fi
  fi
  ITERS=${ITERS} run_loops
  score_iter 3
  score_iter $ITERS
  kill "$PUSHER" 2>/dev/null
  push_results
  log "PIPELINE DONE"
}

push_results() {
  local R URL W f
  [ "$SMOKE" = 1 ] && { log "push skipped (smoke)"; return 0; }
  R=$(find_repo) || { log "push: no repo"; return 1; }
  URL=$(git -C "$R" remote get-url origin)
  W="$GW8/results-repo-gwo"
  if [ ! -d "$W/.git" ]; then
    git init -q "$W" && git -C "$W" remote add origin "$URL"
    git -C "$W" fetch -q origin "+refs/heads/$RESULTS:refs/remotes/origin/$RESULTS" 2>/dev/null && git -C "$W" reset -q "origin/$RESULTS"
  fi
  git -C "$W" config user.name >/dev/null || git -C "$W" config user.name "GW-O Mac run"
  git -C "$W" config user.email >/dev/null || git -C "$W" config user.email "noreply@example.com"
  cd "$GW8" || return 1
  # small files only; checkpoints (*.pt) and files over 20 MB stay on the Mac
  find logs "${SCORE_DIR#$GW8/}" "${RUNS#$GW8/}" -type f -size -20M ! -name '*.pt' ! -name '.*' -newer "$CODE/game/mac_gwo.sh" 2>/dev/null |
    while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp -p "$f" "$W/$f"; done
  git -C "$W" add -A
  git -C "$W" commit -q -m "GW-O Mac results $(date -u +%Y-%m-%dT%H:%M:%SZ)" || true
  git -C "$W" push -q origin "HEAD:refs/heads/$RESULTS"
  log "push exit $?"
}

status() {
  local s f
  for s in $SEEDS; do
    f="$GW8/logs/gwo-s$s.out"; [ -f "$f" ] || { echo "seed $s: not started"; continue; }
    echo "seed $s: rounds done $(ls "$RUNS/o$s" 2>/dev/null | grep -c '^iter-')/$ITERS; last: $(grep -E "^[0-9]+ " "$f" | tail -1 | cut -c1-200)"
    grep -m1 -E 'Traceback|Error|Killed' "$f" > /dev/null && { echo "seed $s ERROR:"; tail -4 "$f"; }
  done
  local n; n=$(pgrep -f "label-rule lookahead" | wc -l | tr -d ' ')
  [ "$n" -gt 0 ] && echo "running: $n loop processes" || echo "no loop process running"
  [ -f "$GW8/logs/gwo-pipeline.out" ] && tail -3 "$GW8/logs/gwo-pipeline.out"
}

case "${1:-}" in
  setup) setup ;;
  start) start ;;
  status) status ;;
  push) push_results ;;
  pipeline) pipeline ;;
  *) echo "usage: bash $0 setup|start|status|push|pipeline"; exit 2 ;;
esac

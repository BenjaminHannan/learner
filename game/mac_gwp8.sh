#!/bin/bash
# GW-P8 on Ben's Mac (game world thread, addendum A16): both 8-night seeds, then scoring, audit and analysis, results to git.
#   bash mac_gwp8.sh setup     fetch code + inputs, build the skills data (sha-checked), make the venv, check imports, time one game
#   bash mac_gwp8.sh start     launch the whole pipeline detached (survives the shell; caffeinate keeps the Mac awake)
#   bash mac_gwp8.sh status    short progress report
#   bash mac_gwp8.sh push      copy logs + results to branch claude/game-world-mac-results now
#   bash mac_gwp8.sh pipeline  (what start runs) train both seeds, score, audit, analyze, push; safe to rerun: finished steps are skipped
# Env: REPO = a clone of BenjaminHannan/learner (found under ~ when unset); GW8 = work folder (default ~/gw8);
#      THREADS = torch threads per run (default half the performance cores); GW8_SMOKE=1 = tiny run for testing this script
#      (smoke flags, 2 nights, 2-map scoring, push --dry-run); GW8_NOPUSH=1 = never push (cloud scoring of the spare runs);
#      GW8_TAG = run name (default gwp8; gwpc = GW-PC, addendum A19: adds --start distil and pins its own code commit).
#      Works with macOS bash 3.2 and BSD tools.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
GW8=${GW8:-$HOME/gw8}
SMOKE=${GW8_SMOKE:-0}
BRANCH=claude/project-thread-h2ya81
INPUTS=claude/game-world-inputs
DATA_BRANCH=claude/project-thread-y0sxwe
RESULTS=claude/game-world-mac-results
TAG=${GW8_TAG:-gwp8}
case "$TAG" in
  gwp8) MARKS_CODE=4fb211347; EXTRA="" ;;          # game code the GW-P8 marks (A15) were set on; setup refuses code that differs
  gwpc) MARKS_CODE=GWPC_CODE_PIN; EXTRA="--start distil" ;;   # GW-PC (A19): the reviewed distil code
  *) echo "unknown GW8_TAG $TAG"; exit 2 ;;
esac
SHA_200=22f70906443a9640cee5abf440a7afe229f6d1f167cae3709cbf224bd23cde7f
SHA_201=edbd1ee4a6b8d2be983de74bbad757d12249cf6671401e0999c3645ffbbfb795
TRAIN_SHA=010af67124544bda9d4f26d8bd2801427770f1bb38f8c7b79921a36c87b244f5
INDIST_SHA=f975d9fb312c02d759df991fa3bbb9ac73912d5f77cdc0e6991abd7980158b86
SEEDS="200 201"
VPY=${GW8_PY:-$GW8/venv/bin/python}
SCORE_DIR=$GW8/score
RUNS=$GW8/runs
[ "$SMOKE" = 1 ] && { RUNS=$GW8/smoke-runs; SCORE_DIR=$GW8/smoke-score; }

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
  local R CODE_SHA s got
  R=$(find_repo) || die "no clone of BenjaminHannan/learner under ~; rerun with REPO=/path/to/clone"
  log "repo $R"
  mkdir -p "$GW8/logs" "$SCORE_DIR" "$RUNS"
  git -C "$R" fetch -q origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH" "+refs/heads/$INPUTS:refs/remotes/origin/$INPUTS" \
    "+refs/heads/$DATA_BRANCH:refs/remotes/origin/$DATA_BRANCH" || die "git fetch"

  # code under test: a detached worktree at the branch tip, game code identical to the marks commit
  if [ -e "$GW8/code/.git" ]; then git -C "$GW8/code" checkout -q --detach "origin/$BRANCH" || die "checkout code"
  else git -C "$R" worktree add -q --detach "$GW8/code" "origin/$BRANCH" || die "worktree add"; fi
  CODE_SHA=$(git -C "$GW8/code" rev-parse HEAD)
  git -C "$GW8/code" diff --quiet "$MARKS_CODE" HEAD -- game domain custom_io ':(exclude)*.md' ':(exclude)*.sh' \
    || die "game code at $CODE_SHA differs from the marks commit $MARKS_CODE"
  log "code $CODE_SHA (game code = marks commit $MARKS_CODE)"

  # parents, PPO checkpoints and earlier score files (pushed from /mnt/project-files by the coordinator)
  git -C "$R" archive "origin/$INPUTS" inputs | tar -x -C "$GW8" || die "inputs archive"
  for s in $SEEDS; do
    got=$(sha "$(parent $s)"); eval "want=\$SHA_$s"
    [ "$got" = "$want" ] || die "parent s$s sha $got != $want"
  done
  cp -p "$GW8"/inputs/game-world/runs/score/*.json "$SCORE_DIR"/ || die "copy score inputs"
  log "parents sha ok; inputs in $GW8/inputs"

  # venv
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

  # skills data (domain mode's diary + old-question check): rebuilt from its generator, must match the cloud copy byte for byte
  if [ "$(sha "$GW8/sk200k/train.jsonl" 2>/dev/null)" != "$TRAIN_SHA" ]; then
    log "building sk200k (a few minutes)"
    rm -rf "$GW8/skc" "$GW8/sk200k"; mkdir -p "$GW8/skc"
    git -C "$R" archive "origin/$DATA_BRANCH" skills_curriculum | tar -x -C "$GW8/skc" || die "data generator archive"
    (cd "$GW8/skc" && "$VPY" -m skills_curriculum.build --out "$GW8/sk200k" --train 200000 --dev-per-cell 40 --seed 1) \
      > "$GW8/logs/sk200k-build.out" 2>&1 || die "data build, see $GW8/logs/sk200k-build.out"
  fi
  [ "$(sha "$GW8/sk200k/train.jsonl")" = "$TRAIN_SHA" ] || die "sk200k train.jsonl sha differs"
  [ "$(sha "$GW8/sk200k/dev/in_dist.jsonl")" = "$INDIST_SHA" ] || die "sk200k dev/in_dist.jsonl sha differs"
  log "sk200k sha ok"

  # imports + one sealed-map game as a speed check (scoring only; nothing trains on it)
  (cd "$GW8/code" && PYTHONPATH=. "$VPY" -c "import torch, numpy, crafter; import game.mode, game.score, game.audit, game.analyze; \
print('python', __import__('sys').version.split()[0], 'torch', torch.__version__, 'numpy', numpy.__version__)") || die "imports"
  local t0=$(date +%s)
  (cd "$GW8/code" && PYTHONPATH=. "$VPY" -m game.score --arm model --picker sample --temp 19.691660968372133 --ckpt "$(parent 200)" \
    --worlds 2 --threads "$(threads)" --out "$GW8/logs/speed-check.json") > "$GW8/logs/speed-check.out" 2>&1 || die "speed check, see $GW8/logs/speed-check.out"
  log "speed check: 2 games in $(( $(date +%s) - t0 )) s at $(threads) threads"
  log "SETUP OK. Next: bash $GW8/code/game/mac_gwp8.sh start"
}

start() {
  [ -x "$VPY" ] && [ -e "$GW8/code/.git" ] || die "run setup first"
  if pgrep -f "game.mode --parent $GW8" >/dev/null || pgrep -f "mac_gwp8.sh pipeline" >/dev/null; then
    log "already running"; status; return 0
  fi
  local CAF=""; command -v caffeinate >/dev/null && CAF="caffeinate -ims"
  mkdir -p "$GW8/logs"
  nohup perl -e 'use POSIX qw(setsid); setsid(); exec @ARGV' -- $CAF /bin/bash "$GW8/code/game/mac_gwp8.sh" pipeline \
    >> "$GW8/logs/pipeline.out" 2>&1 < /dev/null &
  sleep 20
  log "started (detached${CAF:+, $CAF})"
  status
}

score_seed() {
  local s=$1 RUN="$RUNS/$TAG-s$1" S="$SCORE_DIR" N="$SCORE_DIR/nights-$TAG-s$1" TH W NW T0 FINAL MOVES NR P PC k
  TH=$(threads); W=100; NW=50
  [ "$SMOKE" = 1 ] && { W=2; NW=1; }
  [ -f "$RUN/summary.json" ] || { log "seed $s: no summary.json, scoring skipped"; return 1; }
  # T0 = the parent's fitted temperature (GW-PC plays from T = 1, so its fitted T0 is in t0_fitted); TF = the final policy's T
  set -- $("$VPY" -c "import json; s=json.load(open('$RUN/summary.json')); print(repr(s.get('t0_fitted', s['temp_start'])), s['final_checkpoint'], s['game_steps'] + s['quiz_steps'], s['nights_run'], repr(s['temp_final']))")
  T0=$1; FINAL=$2; MOVES=$3; NR=$4; TF=$5
  mkdir -p "$N"
  sc() {  # sc OUT ARGS...: score unless OUT already exists
    local out=$1; shift
    [ -s "$out" ] && return 0
    "$VPY" -m game.score "$@" --threads "$TH" --out "$out" >> "$GW8/logs/score-s$s.out" 2>&1 || log "seed $s: score failed for $out"
  }
  log "seed $s: scoring (T0 $T0, final $FINAL, moves $MOVES)"
  sc "$S/before-T0-mac-s$s.json" --arm model --picker sample --temp "$T0" --ckpt "$(parent $s)" --worlds $W
  sc "$S/after-$TAG-s$s.json" --arm model --picker sample --ckpt "$FINAL" --worlds $W
  k=1
  while [ $k -lt "$NR" ]; do sc "$N/night_$k.json" --arm model --picker sample --ckpt "$RUN/night_$k/checkpoint.pt" --worlds $NW; k=$((k + 1)); done
  if [ -f "$RUN/night_0/checkpoint.pt" ]; then   # GW-PC: the distilled night-0 policy (A19b PC-0 validity), 100 maps, T from its folder
    sc "$S/night0-$TAG-s$s.json" --arm model --picker sample --ckpt "$RUN/night_0/checkpoint.pt" --worlds $W
    cp -p "$S/night0-$TAG-s$s.json" "$N/night_0.json"
    # view dependence (A19b PC-2): final policy at its T and the parent at T0, on the Mac GW-P8 night-0 quiz views
    local QV="$RUNS/gwp8-s$s/moves/quiz_night_0.jsonl.gz"
    [ -s "$S/viewdep-$TAG-s$s.json" ] || "$VPY" -m game.blind --ckpt "$FINAL" --temp "$TF" --moves "$QV" --out "$S/viewdep-$TAG-s$s.json" \
      --threads "$TH" >> "$GW8/logs/score-s$s.out" 2>&1 || log "seed $s: view dependence (final) failed"
    [ -s "$S/viewdep-parent-s$s.json" ] || "$VPY" -m game.blind --ckpt "$(parent $s)" --temp "$T0" --moves "$QV" --out "$S/viewdep-parent-s$s.json" \
      --threads "$TH" >> "$GW8/logs/score-s$s.out" 2>&1 || log "seed $s: view dependence (parent) failed"
  else
    cp -p "$S/before-T0-mac-s$s.json" "$N/night_0.json"
  fi
  cp -p "$S/after-$TAG-s$s.json" "$N/night_$NR.json"
  # PPO at the first saved step >= this run's game moves (practice + quiz), both ways (A15 Q-2 takes the stronger)
  P=$(( (MOVES + 8191) / 8192 * 8192 )); [ $P -gt 229376 ] && P=229376
  PC="$GW8/inputs/game-world/runs/ppo-s0/ppo_steps_$P.pt"
  sc "$S/ppo-sample-$P.json" --arm ppo --ppo-picker sample --ckpt "$PC" --worlds $W
  sc "$S/ppo-$P.json" --arm ppo --ppo-picker argmax --ckpt "$PC" --worlds $W
  "$VPY" -m game.audit "$RUN" > "$GW8/logs/audit-s$s.out" 2>&1; log "seed $s: audit exit $?"
  local XD=""
  for kv in gwp8=after-gwp8-s$s gwp=after-gwp-s$s gws3=after-gw3-s$s old=after-s$s ppo_argmax=ppo-$P before_T0_cloud=before-T0-s$s before_greedy=before-s$s; do
    [ "${kv#*=}" = "after-$TAG-s$s" ] && continue   # never against itself
    [ -s "$S/${kv#*=}.json" ] && XD="$XD --extra-diff ${kv%%=*}=$S/${kv#*=}.json"
  done
  "$VPY" -m game.analyze --run "$RUN" --parent "$(parent $s)" --before "$S/before-T0-mac-s$s.json" --after "$S/after-$TAG-s$s.json" \
    --random "$S/random.json" --ppo "$S/ppo-sample-$P.json" --nights-dir "$N" --dev "$GW8/sk200k/dev/in_dist.jsonl" \
    --out "$RUN/analysis" --threads "$TH" $XD > "$GW8/logs/analyze-s$s.out" 2>&1
  log "seed $s: analyze exit $?"
}

pipeline() {
  local TH s pids="" PUSHER NARGS=""
  cd "$GW8/code" || die "no code folder"
  export PYTHONPATH=.
  TH=$(threads)
  export OMP_NUM_THREADS=$TH MKL_NUM_THREADS=$TH VECLIB_MAXIMUM_THREADS=$TH
  [ "$SMOKE" = 1 ] && NARGS="--smoke --nights 2" || NARGS="--nights 8"
  log "pipeline start ($TAG): code $(git rev-parse HEAD), $TH threads per run, smoke=$SMOKE"
  ( while true; do sleep 1200; push_results > /dev/null 2>&1; done ) &
  PUSHER=$!
  mkdir -p "$RUNS"
  for s in $SEEDS; do
    if [ -f "$RUNS/$TAG-s$s/summary.json" ]; then log "seed $s: already trained"; continue; fi
    [ -d "$RUNS/$TAG-s$s" ] && mv "$RUNS/$TAG-s$s" "$RUNS/$TAG-s$s-partial-$(date +%s)"   # a broken earlier try is kept, not deleted
    "$VPY" -m game.mode --parent "$(parent $s)" --out "$RUNS/$TAG-s$s" --seed $s --threads "$TH" --data "$GW8/sk200k" \
      --keep-awake-only --keep guess --picker sample --quiz-picker sample --night pg $NARGS $EXTRA > "$GW8/logs/$TAG-s$s.out" 2>&1 &
    pids="$pids $!"
    log "seed $s: training started (pid $!)"
  done
  for p in $pids; do wait "$p"; log "training pid $p exit $?"; done
  pids=""
  for s in $SEEDS; do score_seed $s & pids="$pids $!"; done
  for p in $pids; do wait "$p"; done
  kill "$PUSHER" 2>/dev/null
  push_results
  log "PIPELINE DONE"
}

push_results() {
  local R URL W f
  [ "${GW8_NOPUSH:-0}" = 1 ] && { log "push skipped (GW8_NOPUSH=1)"; return 0; }
  R=$(find_repo) || { log "push: no repo"; return 1; }
  URL=$(git -C "$R" remote get-url origin)
  W="$GW8/results-repo"; [ "$SMOKE" = 1 ] && W="$GW8/smoke-results-repo"
  if [ ! -d "$W/.git" ]; then
    git init -q "$W" && git -C "$W" remote add origin "$URL"
    git -C "$W" fetch -q origin "+refs/heads/$RESULTS:refs/remotes/origin/$RESULTS" 2>/dev/null && git -C "$W" reset -q "origin/$RESULTS"
  fi
  git -C "$W" config user.name >/dev/null || git -C "$W" config user.name "GW-P8 Mac run"
  git -C "$W" config user.email >/dev/null || git -C "$W" config user.email "noreply@example.com"
  cd "$GW8" || return 1
  # everything small; night 0-7 checkpoints and files over 20 MB stay on the Mac and are listed in NOT-PUSHED.txt
  find logs "${SCORE_DIR#$GW8/}" "${RUNS#$GW8/}" -type f -size -20M ! -path '*/night_[0-7]/checkpoint.pt' ! -name '.*' 2>/dev/null |
    while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp -p "$f" "$W/$f"; done
  for f in "${RUNS#$GW8/}"/*/log.jsonl; do   # a finished run's log (often > 20 MB) goes up gzipped, once it can no longer change
    [ -f "$(dirname "$f")/summary.json" ] && [ ! -s "$W/$f.gz" ] && { mkdir -p "$W/$(dirname "$f")"; gzip -n -c "$f" > "$W/$f.gz"; }
  done
  find "${RUNS#$GW8/}" -type f \( -size +20M -o -path '*/night_[0-7]/checkpoint.pt' \) -exec ls -l {} \; > "$W/NOT-PUSHED.txt" 2>/dev/null
  git -C "$W" add -A
  git -C "$W" commit -q -m "GW-P8 Mac results $(date -u +%Y-%m-%dT%H:%M:%SZ)" || true
  if [ "$SMOKE" = 1 ]; then git -C "$W" push --dry-run origin "HEAD:refs/heads/$RESULTS"
  else git -C "$W" push -q origin "HEAD:refs/heads/$RESULTS"; fi
  log "push exit $?"
}

status() {
  local s f
  for s in $SEEDS; do
    f="$GW8/logs/$TAG-s$s.out"; [ -f "$f" ] || { echo "seed $s: not started"; continue; }
    echo "seed $s: nights done $(grep -c '^night ' "$f")/8; last: $(grep -E '^(temp|quiz|night|done) ' "$f" | tail -1 | cut -c1-150)"
    grep -m1 -E 'Traceback|Error|Killed' "$f" > /dev/null && { echo "seed $s ERROR:"; tail -4 "$f"; }
  done
  local n; n=$(pgrep -f "$VPY -m game\." | wc -l | tr -d ' ')
  [ "$n" -gt 0 ] && echo "running: $n game processes" || echo "no game process running"
  [ -f "$GW8/logs/pipeline.out" ] && tail -2 "$GW8/logs/pipeline.out"
}

case "${1:-}" in
  setup) setup ;;
  start) start ;;
  status) status ;;
  push) push_results ;;
  pipeline) pipeline ;;
  *) echo "usage: bash $0 setup|start|status|push|pipeline"; exit 2 ;;
esac

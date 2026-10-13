#!/bin/bash
# M2 on Ben's Mac (Dopamine thread, addendum B16): does the "progress" motivator beat even practice?
# 12 domain-mode runs = parents T1SDR s200/s201 x run seeds 300/301/302 x drives {even, progress}, exactly 8 nights each,
# then the usual analysis (sealed panel sheet.v2), then results to branch claude/dopamine-mac-results.
#   bash mac_m2.sh setup     fetch code + inputs, sha-check them, check imports
#   bash mac_m2.sh start     launch the whole pipeline detached under caffeinate (safe to rerun: finished runs are skipped)
#   bash mac_m2.sh status    one line per run
#   bash mac_m2.sh push      copy small results (no checkpoints) to branch claude/dopamine-mac-results now
#   bash mac_m2.sh pipeline  (what start runs) runs, analysis, push
# Env: REPO = a clone of BenjaminHannan/learner (default ~/Desktop/projects/beautiful-model); M2 = work folder (default ~/m2);
#      GW8 = the Game world work folder whose venv and sk200k data are reused (default ~/gw8); JOBS = runs at once (default 3);
#      THREADS = torch threads per run (default 2). Works with macOS bash 3.2.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
REPO=${REPO:-$HOME/Desktop/projects/beautiful-model}
M2=${M2:-$HOME/m2}
GW8=${GW8:-$HOME/gw8}
VPY=${M2_PY:-$GW8/venv/bin/python}
SK=${M2_SK:-$GW8/sk200k}
JOBS=${JOBS:-3}
THREADS=${THREADS:-2}
CODE_BRANCH=claude/project-thread-e6smlm
OUT_BRANCH=claude/dopamine-mac-results
SHA_P200=22f70906443a9640cee5abf440a7afe229f6d1f167cae3709cbf224bd23cde7f
SHA_P201=edbd1ee4a6b8d2be983de74bbad757d12249cf6671401e0999c3645ffbbfb795
SHA_PANEL=dda9dc62d5b568ad3cc3c57bddbc821754a3dc8693c01d0629c61347af6d572c
SHA_TRAIN=010af67124544bda9d4f26d8bd2801427770f1bb38f8c7b79921a36c87b244f5
SHA_INDIST=f975d9fb312c02d759df991fa3bbb9ac73912d5f77cdc0e6991abd7980158b86
P200=$M2/inputs/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt
P201=$M2/inputs/checkpoints/cio-1007/70-t1sdr-s201/T1SDR_s201/checkpoint.pt
PANEL=$M2/inputs/domain-mode/panel/sheet.v2.jsonl

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
die() { log "FAILED: $*"; exit 1; }
sha() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }

setup() {
  mkdir -p "$M2/code" "$M2/runs" || die "mkdir"
  git -C "$REPO" fetch -q origin "$CODE_BRANCH:refs/remotes/origin/$CODE_BRANCH" \
      "claude/game-world-inputs:refs/remotes/origin/claude/game-world-inputs" \
      "claude/dopamine-inputs:refs/remotes/origin/claude/dopamine-inputs" || die "git fetch"
  rm -rf "$M2/code" && mkdir -p "$M2/code"
  git -C "$REPO" archive "origin/$CODE_BRANCH" | tar -x -C "$M2/code" || die "archive code"
  git -C "$REPO" rev-parse "origin/$CODE_BRANCH" > "$M2/code/COMMIT"
  git -C "$REPO" archive origin/claude/game-world-inputs inputs/checkpoints | tar -x -C "$M2" || die "archive parents"
  git -C "$REPO" archive origin/claude/dopamine-inputs inputs/domain-mode/panel | tar -x -C "$M2" || die "archive panel"
  [ "$(sha "$P200")" = "$SHA_P200" ] || die "parent s200 sha"
  [ "$(sha "$P201")" = "$SHA_P201" ] || die "parent s201 sha"
  [ "$(sha "$PANEL")" = "$SHA_PANEL" ] || die "panel sha"
  [ "$(sha "$SK/train.jsonl")" = "$SHA_TRAIN" ] || die "sk200k train sha (expected the Game world copy at $SK)"
  [ "$(sha "$SK/dev/in_dist.jsonl")" = "$SHA_INDIST" ] || die "sk200k in_dist sha"
  (cd "$M2/code" && "$VPY" -c "import torch, numpy, dopamine.motivator, domain.analyze; print('imports ok', torch.__version__)") || die "imports"
  log "setup ok, code $(cat "$M2/code/COMMIT")"
}

runs() {  # one line per run: parent_seed run_seed drive
  for p in 200 201; do for s in 300 301 302; do for d in even progress; do echo "$p $s $d"; done; done; done
}

one() {  # parent_seed run_seed drive
  p=$1; s=$2; d=$3
  R="$M2/runs/sheet-p$p-s$s-$d"
  if [ "$p" = 200 ]; then P=$P200; else P=$P201; fi
  if [ ! -f "$R/summary.json" ]; then
    rm -rf "$R"
    log "start $R"
    (cd "$M2/code" && "$VPY" -m dopamine.motivator --parent "$P" --tool sheet --out "$R" --seed "$s" --data "$SK" \
        --threads "$THREADS" --drive "$d" --nights 8) > "$R.out" 2>&1 || { log "run failed $R (see $R.out)"; return 0; }
  fi
  if [ ! -f "$R/analysis/RESULT.json" ]; then
    (cd "$M2/code" && "$VPY" -m domain.analyze --run "$R" --parent "$P" --panel "$PANEL" --dev "$SK/dev/in_dist.jsonl" \
        --out "$R/analysis" --threads "$THREADS") > "$R.analyze.log" 2>&1 || log "analysis failed $R"
  fi
  log "done $R"
}

push() {
  T=$(mktemp -d) || die "mktemp"
  ( cd "$T" && git init -q && git checkout -q -b "$OUT_BRANCH" ) || die "git init"
  mkdir -p "$T/m2"
  cp "$M2/code/COMMIT" "$T/m2/" 2>/dev/null
  for R in "$M2"/runs/sheet-p*; do
    [ -d "$R" ] || continue
    n=$(basename "$R"); mkdir -p "$T/m2/$n"
    cp "$R/summary.json" "$R/log.jsonl" "$T/m2/$n/" 2>/dev/null
    cp "$R/analysis/RESULT.json" "$R/analysis/RESULT.md" "$T/m2/$n/" 2>/dev/null
    cp "$R.out" "$R.analyze.log" "$T/m2/$n/" 2>/dev/null
  done
  [ -f "$M2/pipeline.log" ] && cp "$M2/pipeline.log" "$T/m2/"
  url=$(git -C "$REPO" remote get-url origin)
  ( cd "$T" && git add -A && git commit -q -m "M2 results from Ben's Mac ($(date -u +%Y-%m-%dT%H:%MZ))" \
      && git push -q -f "$url" "HEAD:refs/heads/$OUT_BRANCH" ) || die "push"
  log "pushed to $OUT_BRANCH"
  rm -rf "$T"
}

pipeline() {
  export -f one log sha; export M2 VPY SK THREADS P200 P201 PANEL
  runs | xargs -P "$JOBS" -L 1 bash -c 'one $0 $1 $2'
  push
  log "pipeline finished"
}

status() {
  for R in "$M2"/runs/sheet-p*; do
    [ -d "$R" ] || continue
    n=$(grep -c '"event": "night"' "$R/log.jsonl" 2>/dev/null); n=${n:-0}
    a=$([ -f "$R/analysis/RESULT.json" ] && echo analysed || echo -)
    echo "$(basename "$R") nights=$n $a"
  done
}

case "${1:-}" in
  setup) setup ;;
  start) nohup caffeinate -i -s bash "$0" pipeline > "$M2/pipeline.log" 2>&1 & log "started (pid $!), log $M2/pipeline.log" ;;
  pipeline) pipeline ;;
  status) status ;;
  push) push ;;
  *) echo "usage: bash mac_m2.sh setup|start|status|push"; exit 2 ;;
esac

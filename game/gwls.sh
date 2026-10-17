#!/bin/bash
# DRAFT pending coordinator review (GW-LS). Launcher for GW-LS (game/WALL-SOLVE-RESULT.md section 3): self-imitation started from the GW-L 64k
# checkpoints, seeds 200 / 201 (run seeds 398 / 399), 8 rounds, practice days 4..35, T = 1 every round, label rule segments, rare_below 100,
# epochs 3. Both seeds in parallel, 2 threads each. Resumable: rerun this script and each seed continues from its state.pt / saved play chunks.
# Authorized by Ben's goal instruction (Oct 17, via the coordinator); started 14:49 UTC Oct 17. Do NOT score sealed worlds from here (game/gwls_final.py does that, once, at round 8).
#
#   bash game/gwls.sh            (from the repo root)
SCR=/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad
PY=$SCR/venv/bin/python
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH="$PWD"
for pair in "200 398" "201 399"; do
  set -- $pair
  seed=$1; rs=$2
  out=$SCR/gwls/s$seed
  if pgrep -f "game.imitate run .*--out $out( |$)" > /dev/null; then echo "seed $seed already running, not starting a second writer"; continue; fi
  mkdir -p "$out"
  setsid nohup "$PY" -m game.imitate run --parent "$SCR/glprobe/s$seed/n64000/checkpoint.pt" --seed "$seed" --run-seed "$rs" --t0 1.0 \
    --out "$out" --iterations 8 --threads 2 --keep-rare-below 100 --day-offset 4 >> "$out/run.log" 2>&1 &
  echo "started seed $seed (run seed $rs): log $out/run.log"
done

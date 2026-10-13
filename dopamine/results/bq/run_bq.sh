#!/bin/bash
# BQ (Dopamine B20): scarce-practice bed yardstick, INFORMED vs EVEN, 256/night, 8 nights, run seed 310. Args: parent seeds.
set -uo pipefail
C=/tmp/claude-0/bq/code; R0=/tmp/claude-0/bq/runs; PY=/tmp/claude-0/v/bin/python
SK=/tmp/claude-0/-home-user-learner/8eafffd1-ff0b-5a51-aea7-c92c3c068a6c/scratchpad/sk200k
PANEL=/mnt/project-files/domain-mode/panel/sheet.v2.jsonl
KINDS="SUM,MAX,MIN,PRODUCT,cell arithmetic,division,ABS"
one() { p=$1; d=$2; R=$R0/sheet-p$p-s310-$d
  P=/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s$p/T1SDR_s$p/checkpoint.pt
  if [ ! -f $R/summary.json ]; then rm -rf $R; echo "[$(date -u +%FT%TZ)] start $R"
    if [ $d = informed ]; then X=(--drive informed --informed-kinds "$KINDS"); else X=(--drive even); fi
    (cd $C && $PY -m dopamine.motivator --parent $P --tool sheet --out $R --seed 310 --data $SK --threads 1 "${X[@]}" --day-problems 256 --nights 8) > $R.out 2>&1 || { echo "run failed $R"; return; }
  fi
  if [ ! -f $R/analysis/RESULT.json ]; then
    (cd $C && $PY -m domain.analyze --run $R --parent $P --panel $PANEL --dev $SK/dev/in_dist.jsonl --out $R/analysis --threads 1) > $R.analyze.log 2>&1 || echo "analysis failed $R"
  fi
  echo "[$(date -u +%FT%TZ)] done $R"
}
for p in "$@"; do one $p informed & one $p even & wait; done
echo "[$(date -u +%FT%TZ)] BQ DONE $*"

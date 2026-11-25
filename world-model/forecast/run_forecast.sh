#!/bin/zsh
L=/tmp/premonition_m3_mps.lock
if [ -f $L ] && ps -p $(cut -d' ' -f1 $L) >/dev/null 2>&1; then echo LOCK_BUSY; exit 3; fi
echo "$$ $(date +%s)" > $L
~/learner-ops/m3-torch/.venv/bin/python forecast.py --device mps --out run_forecast; echo "exit=$?"
rm -f $L

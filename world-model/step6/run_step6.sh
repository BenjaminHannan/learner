#!/bin/zsh
# STEP 6 scored run (PROBLEM-7 world model). Takes the M3 MPS lock only if missing or its pid is dead; releases on exit.
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm-harness || exit 9
L=/tmp/premonition_m3_mps.lock
if [ -f $L ]; then p=$(cut -d' ' -f1 $L); if ps -p $p >/dev/null 2>&1; then echo "LOCK HELD by $p"; exit 8; fi; fi
avail=$(df -g / | awk 'NR==2{print $4}'); if [ "$avail" -lt 10 ]; then echo "DISK BELOW FLOOR ${avail}G"; exit 7; fi
echo "$$ $(date +%s)" > $L; trap 'rm -f $L' EXIT
shasum -a 256 forecast4.py imagine_head6.py
~/learner-ops/m3-torch/.venv/bin/python forecast4.py --device mps --init run_recon_ridge/model.pt --out run_forecast4 > run_forecast4.log 2>&1
echo "EXIT=$?" >> run_forecast4.log; echo "EXIT=$(tail -1 run_forecast4.log)"

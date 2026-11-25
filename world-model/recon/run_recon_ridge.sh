#!/bin/zsh
L=/tmp/premonition_m3_mps.lock
if [ -f $L ] && ps -p $(cut -d' ' -f1 $L) >/dev/null 2>&1; then echo LOCK_BUSY; exit 3; fi
echo "$$ $(date +%s)" > $L
P=~/learner-ops/m3-torch/.venv/bin/python
$P recon.py --device mps --fixed-scale --ridge --out run_recon_ridge; echo "exit_board=$?"
$P recon.py --device mps --bypass --fixed-scale --ridge --out run_recon_ridge_bypass; echo "exit_bypass=$?"
rm -f $L

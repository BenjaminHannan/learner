#!/bin/zsh
# usage: withlock.sh LOG cmd...   waits for the M3 MPS lock (pid-alive check), holds it while cmd runs, then releases
L=/tmp/premonition_m3_mps.lock; LOG=$1; shift
while [ -f $L ] && ps -p $(cut -d' ' -f1 $L) >/dev/null 2>&1; do sleep 20; done
echo "$$ $(date +%s)" > $L; echo "lock taken $(date)"
"$@" 2>&1 | grep -v Warning | tee $LOG
rm -f $L; echo "lock released $(date)"

# Checkpoints off a Vast box through its log, in pieces (sourced by a queue job with GLOB set, e.g.
# GLOB="$J/w/2[0-4]-*/*/checkpoint.pt"). The Vast log API returns at most 20000 lines per read and splits lines at 500
# chars, so a 12 MB checkpoint never fits in one read: each one is tar.gz'd, split into 3 MB parts, and one part is
# printed every PACE seconds (default 100) as RBEGIN|ckN|part-sha|size|job/run|k|n, R|ckN|<480 base64 chars>, REND|ckN,
# after a CKFULL|job/run|tgz-sha|n line. vast.py collectck reads the log every 40 s and reassembles. RESULTS="job ..."
# re-prints those jobs' result tarballs first, in the normal 4-field format.
PACE=${PACE:-100}
LOG=${LOG:-/proc/1/fd/1}
N=0
# first re-print the small result tarballs of the jobs named in RESULTS (their first print is buried under the export)
for r in ${RESULTS:-}; do
  T=$J/res/re-$r.tgz; tar -czf $T --exclude='*.pt' --exclude='stdout.txt' -C $J/w $r 2>/dev/null
  ( flock 9; echo "RBEGIN|$r|$(sha256sum $T | cut -c1-64)|$(stat -c %s $T)"; base64 -w 480 $T | sed "s/^/R|$r|/"; echo "REND|$r" ) 9>$J/print.lock >> $LOG
  sleep 30
done
for c in $GLOB; do
  run=$(basename $(dirname $c)); job=$(basename $(dirname $(dirname $c)))
  T=$J/res/ck-$job-$run.tgz; tar -czf $T -C $J/w $job/$run/checkpoint.pt
  full=$(sha256sum $T | cut -c1-64)
  rm -f $J/res/ck-$job-$run.part.*
  split -b 3000000 -d -a 3 $T $J/res/ck-$job-$run.part.
  n=$(ls $J/res/ck-$job-$run.part.* | wc -l)
  echo "CKFULL|$job/$run|$full|$n" >> $LOG
  for p in $(ls $J/res/ck-$job-$run.part.* | sort); do
    k=$((10#${p##*.})); N=$((N + 1)); h=$(sha256sum $p | cut -c1-64)
    ( flock 9; echo "RBEGIN|ck$N|$h|$(stat -c %s $p)|$job/$run|$k|$n"; base64 -w 480 $p | sed "s/^/R|ck$N|/"; echo "REND|ck$N" ) 9>$J/print.lock >> $LOG
    echo "part ck$N $job/$run $k/$n"
    sleep $PACE
  done
done
echo "CKDONE|$N" >> $LOG

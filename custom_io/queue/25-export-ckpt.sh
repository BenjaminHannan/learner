# MEM 0
# PAR 1
# Keep the screen models: print every finished screen run's checkpoint.pt (tar.gz, base64, 12000-char lines) into the
# container log in the RBEGIN/R|/REND format, so vast.py collect can save them before the box is destroyed. No training.
for c in $J/w/2[0-2]-screen-*/*/checkpoint.pt; do
  run=$(basename $(dirname $c)); job=$(basename $(dirname $(dirname $c))); n=ckpt-$job-$run
  T=$J/res/$n.tgz; tar -czf $T -C $J/w $job/$run/checkpoint.pt
  h=$(sha256sum $T | cut -c1-64)
  ( flock 9; echo "RBEGIN|$n|$h|$(stat -c %s $T)"; base64 -w 12000 $T | sed "s/^/R|$n|/"; echo "REND|$n" ) 9>$J/print.lock > /proc/1/fd/1
  echo "exported $n $h"
done

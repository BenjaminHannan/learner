# MEM 100
# PAR 1
# Read-only look at box A's data step (it was still building at 30 min while box B's took about 12): log tails, files, processes, disk, network.
{ date -u; tail -30 $J/w/50-gx-s400/get_data.log; echo ---; ls -la $J/g8a8 $J/g8a8/data8a $J/g8a8/data8a/* 2>&1 | head -60; echo ---; du -sh $J/g8a8 $J/dp $J/od 2>&1
  echo ---; ps aux --sort=-%cpu | head -12; echo ---; df -h /job | tail -1; free -g | head -2; } > $J/w/$JOB/diag.txt 2>&1

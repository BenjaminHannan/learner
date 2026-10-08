#!/bin/bash
cd /home/user/learner
export PYTHONPATH=/home/user/learner
for p in s100 s101; do
  (python3 -m creative.harm_look --skills-data ~/work/data_big --out ~/c7d/harm/$p --threads 2 --model $p:B2=$HOME/fs/B2_$p.pt --model $p:N=$HOME/c7d/$p/Nprime.pt --model $p:W1=$HOME/c7d/s3/$p/W1.pt --model $p:P=$HOME/c7d/s3p/$p/P.pt --model "$p:Zp=$HOME/c7d/s3p/$p/Z.pt" > ~/c7d/harm-$p.log 2>&1; echo "HARM $p $?" >> ~/c7d/harm.txt) &
done
wait

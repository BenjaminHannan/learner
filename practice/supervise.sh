#!/bin/zsh
# Practice-1M supervisor: re-runs (= resumes) one mac_run arm until it exits 0, at most 15 times. Usage: supervise.sh P|C
arm=$1
port=$([ "$arm" = P ] && echo 8089 || echo 8090)
extra=$([ "$arm" = C ] && echo "--skip-bench" || echo "")
out=~/learner-ops/practice1m/run$arm
cd ~/learner-ops/practice1m-repo || exit 1
for i in $(seq 15); do
  echo "$(date -u +%FT%TZ) supervise $arm attempt $i" >> $out.supervise.log
  ~/learner-ops/.venv/bin/python -m practice.mac_run --out $out --arms $arm --port $port ${=extra} --practice-n 60 --sib-n 0 --test-tries 2 \
    --nights 2 --eval-nights 2 --concurrency 4 --model ~/learner-ops/models/K2-Horizon-3.7B-4bit >> ~/learner-ops/practice1m/run$arm.nohup.log 2>&1
  rc=$?
  echo "$(date -u +%FT%TZ) supervise $arm exit $rc" >> $out.supervise.log
  [ $rc -eq 0 ] && break
  pkill -f "mlx_server.py --model .*K2-Horizon-3.7B-4bit --host 127.0.0.1 --port $port"
  sleep 60
done

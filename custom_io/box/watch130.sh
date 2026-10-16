# watch130.sh NAME PID : the scratch screen's 130-minute rule, run beside one `run NAME ...` inside a queue job. Every 60 s it
# reads the run's last train event; from step 1000 on it projects training time to STEPS (default 24000) as elapsed/step*STEPS.
# Past LIM_MIN (default 130) it kills the run, writes STOPPED.json in the run folder and an "event" line in the job log.
# A stopped run is never restarted.
n=$1; p=$2; S=${STEPS:-24000}; LIM=${LIM_MIN:-130}; o=$J/w/$JOB/$n
while kill -0 $p 2>/dev/null; do
  sleep 60
  l=$(grep '"event": "train"' $o/stdout.txt 2>/dev/null | tail -1)
  [ -n "$l" ] || continue
  v=$(python -c "import json,sys; d=json.loads(sys.argv[1]); s,e=d['step'],d['elapsed']; p=e/s*$S/60; print(s, e, round(p,1), int(s>=1000 and p>$LIM))" "$l")
  set -- $v
  if [ "$4" = 1 ]; then
    echo "{\"stopped\": true, \"rule\": \"projected training past $LIM min\", \"step\": $1, \"elapsed_s\": $2, \"projected_min\": $3}" > $o/STOPPED.json
    echo "{\"event\": \"watch130_stop\", \"run\": \"$JOB/$n\", \"step\": $1, \"elapsed_s\": $2, \"projected_min\": $3}"
    pkill -f -- "--out $o " ; sleep 10; pkill -9 -f -- "--out $o "
    break
  fi
done

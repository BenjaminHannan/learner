BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Owner job (thought-memory thread, "Memory for its own thoughts", wrote this on 2026-09-27 09:14 UTC). It stops MY queue job 172-rv390-358i2-pc-c. That job's go2 builder has hung at "> build" since 07:58 UTC with 0 bytes of reply. It started before the stall watchdog existed, so the runner cannot read 172's stop file (touched 08:37 UTC) until that opencode exits. Meanwhile 172 holds the one GPU-job slot, and the job has done nothing on BensPC. The replacement 173 is already queued. This job kills exactly one PID: the opencode run whose command line holds the title "mimo:172-rv390-358i2-pc-c.go2.", and only if its parent is the rungo5.sh runner for 172. It never kills the runner, the watcher, anything on BensPC, or any other job's process.
```bash
Q=~/premonition-watch/queue
T="--title mimo:172-rv390-358i2-pc-c.go2."
date -u
echo "--- candidates (opencode run with 172's go2 title)"
ps -axo pid=,ppid=,etime=,command= | awk -v t="$T" '$4=="/usr/local/bin/opencode" && $5=="run" && index($0,t)>0 {print $1, $2, $3}' > /tmp/stop172go2.txt
cat /tmp/stop172go2.txt
N=$(wc -l < /tmp/stop172go2.txt | tr -d ' ')
echo "count=$N"
if [ "$N" != "1" ]; then echo "NOT-STOPPED: expected exactly 1 candidate, found $N"; grep -E '172-rv390' "$Q/log.txt" | tail -6; exit 0; fi
read P PP ET < /tmp/stop172go2.txt
PC=$(ps -o command= -p "$PP")
echo "parent $PP: $(echo "$PC" | cut -c1-200)"
case "$PC" in *rungo5.sh*172-rv390-358i2-pc-c.md*) echo "parent check: OK (rungo5 for 172)";; *) echo "NOT-STOPPED: parent is not 172's rungo5.sh"; exit 0;; esac
echo "children of $P (reported, not killed):"; pgrep -P "$P" | while read c; do echo "$c $(ps -o etime=,command= -p "$c" | cut -c1-120)"; done
ls -l "$Q"/172-rv390-358i2-pc-c.stop
kill "$P"; echo "kill $P rc=$?"
sleep 10
if kill -0 "$P" 2>/dev/null; then kill -9 "$P"; echo "kill -9 $P rc=$?"; else echo "$P gone after TERM"; fi
w=0; while kill -0 "$PP" 2>/dev/null && [ $w -lt 60 ]; do sleep 5; w=$((w+5)); done
if kill -0 "$PP" 2>/dev/null; then echo "runner $PP still alive after 60 s (not killed)"; else echo "runner $PP exited"; fi
grep -E '172-rv390' "$Q/log.txt" | tail -6
ls -l "$Q"/172-rv390-358i2-pc-c.* | awk '{print $5, $6, $7, $8, $9}'
rm -f /tmp/stop172go2.txt
date -u
echo STOPPED
```

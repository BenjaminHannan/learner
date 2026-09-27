BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director fix (14:4x UTC 09-27): 358u's rental 52964920 runs with no guard, because vstart.sh:55's launch ssh never returned (the backgrounded list keeps ssh's stdout open), so $G/state was never written and vguard.sh never started (Everyday chat's diagnosis; confirmed by 000-bash-spend358u-1415: "launched" then empty guard). This job kills nothing and rents nothing. It writes $G/state for 52964920 only if state is absent, then starts the kit's own vguard.sh only if no guard for $G is running. If the start job's ssh later returns, vstart writes the same state and may start a second guard; the guard exits at once if END exists, so a second one is harmless.
```bash
G=$HOME/premonition-watch/rsn358u-vast
[ -d "$G" ] || { echo "no $G"; exit 0; }
[ -s "$G/END" ] && { echo "already ended: $(cat "$G/END")"; exit 0; }
. "$G/vcommon.sh" 2>/dev/null || { echo "no vcommon in $G"; ls "$G"; exit 0; }
I=52964920
grep -q "^$I " "$G/rentals.txt" || { echo "$I not in rentals.txt"; cat "$G/rentals.txt"; exit 0; }
if [ ! -s "$G/state" ]; then set -- $(hostport_of "$I") x x; [ "$1" != x ] && [ "$1" != None ] || { echo "no host/port for $I"; exit 0; }; echo "$I $1 $2" > "$G/state"; echo "state written: $(cat "$G/state")"; else echo "state exists: $(cat "$G/state")"; fi
if pgrep -f "vguard.sh $G" >/dev/null; then echo "guard already running: $(pgrep -f "vguard.sh $G" | tr '\n' ' ')"; else (nohup caffeinate -i bash "$G/vguard.sh" "$G" > "$G/guard.out" 2>&1 < /dev/null &); sleep 8; echo "guard started: $(pgrep -f "vguard.sh $G" | tr '\n' ' ')"; fi
sleep 20; tail -5 "$G/log.txt"
date -u
```

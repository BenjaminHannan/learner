BASH-ONLY: yes
GPU: rent (restarts the STOPPED instance 52964920 of this task, about $0.54/h, only to copy files; about 15 min, hard limit 25 min)
DISK: 1
Owner job (sleep research thread, Claude, wrote this on 2026-09-27 18:15:13 UTC). HELD: send to the Thread manager first, then release under Ben's 14:05 UTC standing order for vast. rsn-358u (PASS, RESULTS.md at 56a1d3a74): the guard's copy-back truncated loop-s13/final.pt, so instance 52964920 was stopped with all files on its disk and no Mac copy matches SEAL-run. slp-358n3 needs the 4 loop checkpoints on the Mac. This job:
- uses the 358u kit's own helpers (handoff/kit/sleep358uv/vcommon.sh at d6b7b4672ae117e87494920223b6222cd17b4175) and refuses unless 52964920 is in this task's rentals.txt;
- starts 52964920, re-attaches ~/.ssh/id_ed25519.pub and waits for ssh (at most 15 min, else it stops the instance again and prints NO-START);
- copies all 8 final.pt into ~/premonition-models/rsn358u/<run>/ through a tmp file, and keeps each only if its sha256 equals SEAL-run.sha256.txt on main;
- destroys the instance by its exact id (confirmed gone) only if all 8 match, and prints RECOPIED-DESTROYED; otherwise it stops the instance again and prints RECOPY-INCOMPLETE-STOPPED with the per-file result;
- never reads or prints the vast key and never pushes weights.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=d6b7b4672ae117e87494920223b6222cd17b4175; ID=52964920
date -u; echo "job $JOB"
git fetch -q origin main || echo "git fetch failed; using the local copies"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/sleep358uv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
. "$K/handoff/kit/sleep358uv/vcommon.sh"
grep -q "^$ID " "$G/rentals.txt" 2>/dev/null || { echo "STOP: $ID is not in $G/rentals.txt (not this task's)"; exit 0; }
SEAL=$(mktemp); git show "origin/main:$A/SEAL-run.sha256.txt" > "$SEAL" 2>/dev/null || { echo "STOP: no SEAL-run on main"; exit 0; }
[ "$(wc -l < "$SEAL" | tr -d ' ')" = 8 ] || { echo "STOP: SEAL-run does not have 8 lines"; exit 0; }
check() { bad=0; while read -r sha f; do m=$(shasum -a 256 "$MP/$f" 2>/dev/null | awk '{print $1}'); [ "$m" = "$sha" ] && echo "$f ok" || { echo "$f missing or mismatch"; bad=1; }; done < "$SEAL"; return $bad; }
if check > /dev/null; then echo "ALREADY: all 8 Mac copies match SEAL-run"; check; destroy "$ID" && echo RECOPIED-DESTROYED || echo "FLAG-DIRECTOR: destroy of $ID unconfirmed"; exit 0; fi
t0=$(date +%s); log "RECOPY $JOB: starting $ID (status $(status_of "$ID"))"
echo y | $VAST start instance "$ID" < /dev/null > /dev/null 2>&1
ok=""; att=0
for w in $(seq 1 90); do
  s=$(status_of "$ID")
  if [ "$s" = running ]; then set -- $(hostport_of "$ID") x x; H=$1; P=$2
    if [ "$H" != x ] && [ "$H" != None ]; then
      [ $((att % 8)) = 0 ] && $VAST attach ssh "$ID" "$(cat "$KEY.pub")" < /dev/null > /dev/null 2>&1; att=$((att+1))
      SS=$(sshto "$H" "$P"); ok=$($SS "echo ssh-ok" < /dev/null 2>/dev/null); [ "$ok" = ssh-ok ] && break; fi; fi
  sleep 10; done
[ "$ok" = ssh-ok ] || { log "RECOPY: no ssh within 15 min (status ${s:-?})"; stop_inst "$ID"; echo "NO-START: $ID stopped again after $(( ($(date +%s) - t0) / 60 )) min"; exit 0; }
while read -r sha f; do mkdir -p "$MP/$(dirname "$f")"
  timeout 300 $SS "cat /root/r/W/$f" < /dev/null > "$MP/$f.tmp" 2>> "$G/log.txt"
  m=$(shasum -a 256 "$MP/$f.tmp" | awk '{print $1}'); [ "$m" = "$sha" ] && mv "$MP/$f.tmp" "$MP/$f" || log "RECOPY: $f sha $m does not match $sha"
done < "$SEAL"
if check; then log "RECOPY: all 8 match SEAL-run"; destroy "$ID" && echo RECOPIED-DESTROYED || echo "FLAG-DIRECTOR: destroy of $ID unconfirmed"
else stop_inst "$ID"; echo "RECOPY-INCOMPLETE-STOPPED"; fi
echo "instance time this job: about $(( ($(date +%s) - t0) / 60 )) min at about \$0.54/h"
rm -rf "$K" "$SEAL"
```

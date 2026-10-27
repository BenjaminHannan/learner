#!/bin/bash
# rd-378g vast kit: send R (the rd-378 writer, merged) from the Mac to the rental for G5 (Trustworthy notes thread, 2026-09-27).
# Started detached on the Mac by vstart.sh right after drive.sh launches; runs from $G (its own copy). BensPC keeps R too, but
# BensPC is the machine this rental replaces, so R goes from the Mac's copy (rd-378u's fallback route). It checks R's sha256 on
# the Mac first, sends the folder with tar over ssh (up to 3 tries), and writes W/R-OK on the rental only when the rental's
# sha256 of model.safetensors matches; otherwise W/R-FAIL with the reason (drive.sh then skips g5R: ADDENDUM-K's 57% fallback).
# It never prints or pushes weights, and it only writes into this task's own rental.
set -u
export COPYFILE_DISABLE=1
G=$1
. "$G/vcommon.sh"
read -r ID H P TC < "$G/state"
SS=$(sshto "$H" "$P")
rl() { echo "$(now) rsend: $*" >> "$G/log.txt"; }
rfail() { rl "R-FAIL $*"; $SS "echo '$*' > /root/r/W/R-FAIL" < /dev/null; exit 0; }
[ -f "$MR/model.safetensors" ] || rfail "no R on the Mac ($MR)"
m=$(shasum -a 256 "$MR/model.safetensors" | awk '{print $1}')
[ "$m" = "$R_SHA" ] || rfail "the Mac copy of R has sha256 $m, not $R_SHA"
rl "Mac copy of R ok ($(du -sm "$MR" | cut -f1) MB); sending"
for t in 1 2 3; do
  t0=$(date +%s)
  tar -cf - -C "$(dirname "$MR")" "$(basename "$MR")" | $SS "mkdir -p /root/r/R && tar -x -C /root/r/R" 2>> "$G/log.txt"
  r=$($SS "sha256sum /root/r/R/$(basename "$MR")/model.safetensors" < /dev/null 2>/dev/null | cut -c1-64)
  if [ "$r" = "$R_SHA" ]; then
    $SS "echo $R_SHA > /root/r/W/R-OK" < /dev/null && { rl "R-OK try $t, $(( $(date +%s) - t0 )) s; rental sha256 matches"; exit 0; }
  fi
  rl "try $t: rental sha256 '${r:-none}' after $(( $(date +%s) - t0 )) s"; sleep 30
done
rfail "R did not arrive intact after 3 tries"

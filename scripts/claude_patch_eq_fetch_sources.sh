#!/bin/bash
# Fetch the four practised source nets (not on main) over https from the branch that holds them, then check sha256.
# Prints FETCH-FAILED with the reason if the branch cannot be reached (e.g. no https credentials; the ssh remote is not used).
cd "$(dirname "$0")/.." || exit 1
A=artifacts/claude-patch-eq-20260928
BR=claude/h13-patch-takeover-x4ph8v
URL=https://github.com/BenjaminHannan/learner.git
need=0
for r in patch-s0 patch-s1 loop_ep-s0 loop_ep-s1; do [ -f $A/runs/$r/source.pt ] || need=1; done
if [ $need = 1 ]; then
  GIT_TERMINAL_PROMPT=0 git fetch -q "$URL" "$BR" 2> /tmp/h13-fetch.err || {
    echo "FETCH-FAILED: could not fetch $BR over https from $URL. Reason: $(tail -1 /tmp/h13-fetch.err)"
    echo "Fix: give this Mac https access to the repo (gh auth / credential helper), or copy runs/*/source.pt in by hand (sha256 in checkpoints-sha256.txt)."; exit 1; }
  for r in patch-s0 patch-s1 loop_ep-s0 loop_ep-s1; do
    [ -f $A/runs/$r/source.pt ] || git show FETCH_HEAD:$A/runs/$r/source.pt > $A/runs/$r/source.pt || { echo "FETCH-FAILED: $r/source.pt not on $BR"; rm -f $A/runs/$r/source.pt; exit 1; }
  done
fi
( cd $A && sha256sum -c checkpoints-sha256.txt 2>/dev/null || shasum -a 256 -c checkpoints-sha256.txt ) || { echo "SOURCE-NETS-MISMATCH"; exit 1; }
echo "source nets ok: 4 of 4 sha256 match"

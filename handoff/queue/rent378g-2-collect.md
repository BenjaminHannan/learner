BASH-ONLY: yes
GPU: no (Mac only; it never touches the rental)
DISK: 1
Owner job (Trustworthy notes thread, Claude, wrote this on 2026-09-27 14:31:04 UTC). HELD: release after rent378g-1-start has printed STARTED. rd-378g vast collect 1 of up to 2, per artifacts/claude-rd378g-20260926/ADDENDUM-N.md and ADDENDUM-N2.md. It runs handoff/kit/rd378gv/vcollect.sh from the pinned commit 54cfbbfcb2def18f121297dd833869e6e07f9e1f. It restarts the Mac guard if the guard died before ending, then waits up to 70 min for it to end. The guard itself copies back and destroys or stops the rental. It then puts the run's files into artifacts/claude-rd378g-20260926/vast/ for the PUSH, beside benspc/ and never over it: steps, logs, checks, torch and host lines, notes_confirm.json, ranked_turns.jsonl (positions only), notes_confirm_whenoff.json, train/, g5/notes_G.jsonl and notes_R.jsonl, SEAL-run, the manifest, the rental list, the guard's log and COLLECT.txt with the card line. LoCoMo-derived files go to ~/rd378g-private/vast and G's adapter to ~/premonition-models/rd378g-vast-adapter (Mac only, never pushed). If the guard has not ended, it prints NOT-YET and changes nothing. If the instance was stopped instead of destroyed, it prints FLAG-DIRECTOR.
```bash
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
JOB=$(basename "$0" .bo.sh); PIN=54cfbbfcb2def18f121297dd833869e6e07f9e1f
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d)
git archive "$PIN" handoff/kit/rd378gv | tar -x -C "$K" || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
bash "$K/handoff/kit/rd378gv/vcollect.sh" "$K" "$PIN" "$JOB"; rc=$?
rm -rf "$K"
exit $rc
```
PUSH: artifacts/claude-rd378g-20260926/vast

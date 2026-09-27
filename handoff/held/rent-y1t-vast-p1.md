BASH-ONLY: yes
GPU: rent (one vast 1-GPU card with the best TFLOPS per $/h that fits, >= 16 GB, at most $1.00/h, label claude-memory-y1t; this file's script rents, watches, copies back and destroys; no LLM builder)
DISK: 1
HELD (Answering-from-memory thread, 14:37 UTC 09-27): only the Director releases it, under Ben's 12:49 UTC allowance for jobs that were waiting for BensPC (ledger 12:50 UTC) and his 14:05 UTC standing order (such jobs go to vast, at most $4 per job, best TFLOPS per $/h), or Ben's own yes on a plan. Cap $1.50 for the whole task, every create included (the passes stop, copy back and destroy at the cap); estimate $0.30 to $0.70 (a guess: about 40 to 70 minutes on one RTX 5090). Exactly one y1t route runs: while this is out, 180-y1t-benspc-bo-p1..p4 stay held.
Owner job (Answering-from-memory thread, Claude, wrote this on 2026-09-27 at 14:37 UTC). y1t on vast without an LLM builder, while BensPC is unreachable (Ben 12:45 UTC "Just use vast for now"): artifacts/claude-y1t-20260926/ADDENDUM-9-vast.md (sealed in SEAL-y1t-add9.sha256.txt). Same data, sealed scripts, TEST-ONLY panel, steps and DEV marks as ADDENDUM-6; the chain stops its own step (by the exact PID it started) when its log is unchanged for 20 minutes or a time or money cap passes.
Pass 1 of 3 ("first"): the only pass that rents. It rents one instance (at most 3 create calls in all, each right after re-checking that this file is still in handoff/queue/ on origin/main), makes ~/tree from the pinned commit, sets up torch 2.11.0 and transformers 5.17.0, downloads MiniCPM5-1B at commit 87179e5c, checks the three seals, the items sha256 and the four selftests, starts remote/chain.sh once, and watches until 55 minutes into the pass. If the chain is done by then it copies everything back, checks each file's sha256 against the rental, copies the adapter to ~/y1t-adapter on the Mac, destroys the instance, confirms vast no longer lists it and writes artifacts/claude-y1t-20260926/run/RESULTS-vast.md. If not, it leaves the instance running and writes a NEXT-PASS-NEEDED note (with the time the cap would be reached): then rent-y1t-vast-p2 goes into the queue at once, because the instance bills every hour until a pass destroys it.
It runs handoff/kit/y1tvast/pass.sh from the pinned commit f20caff1ae27edbd970ac61ce98e27b8f80fda79 (tested against a fake vast CLI and a fake rental). The vastai CLI reads its own key file; the script never reads or prints the key, never touches an instance this task did not create, never edits sealed code, never opens the TEST-ONLY panel or the H1 rows, and never pushes weights. The Director files the spending ledger line from the LEDGER-SUGGESTION line in the reply.
```bash
set -u
JOB=$(basename "$0" .bo.sh); PIN=f20caff1ae27edbd970ac61ce98e27b8f80fda79; MODE=first
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d "${TMPDIR:-/tmp}/y1tkit.XXXXXX")
git archive "$PIN" handoff/kit/y1tvast | tar -x -C "$K"
[ -f "$K/handoff/kit/y1tvast/pass.sh" ] || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
# exec: the pass replaces this shell, so the watcher's 75-minute alarm reaches it; pass.sh removes $K when it exits
exec bash "$K/handoff/kit/y1tvast/pass.sh" "$K" "$PIN" "$JOB" "$MODE" "$(dirname "$0")/$JOB.md"
```
PUSH: artifacts/claude-y1t-20260926/run artifacts/claude-y1tH1-20260926/run

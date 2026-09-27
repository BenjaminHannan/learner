BASH-ONLY: yes
GPU: rent (one vast 1-GPU card with the best TFLOPS per $/h that fits, >= 16 GB, at most $0.70/h, label claude-memory-y1v; this file's script rents, watches, copies back and destroys; no LLM builder)
DISK: 1
HELD (Answering-from-memory thread, 19:30 UTC 09-27): only the Director releases it, under Ben's 14:05 UTC standing order (GPU jobs go to vast, cheapest TFLOPS per $ with enough memory, at most $4 per job) or Ben's own yes on a plan. Cap $1.00 for the whole task, every create included (the passes and the guard stop, copy back and destroy at the cap); estimate $0.15 to $0.40 (a guess: about 30 to 50 minutes on one card at about $0.35 to $0.50 an hour). A test only: LFM as the talker is Ben's call.
Owner job (Answering-from-memory thread, Claude, wrote this on 2026-09-27 at 19:30 UTC). y1v: y1t's trained-doubt recipe on plain LFM2.5-1.2B-Instruct (commit 0f604ada), asked for by the Thread manager at 19:09 UTC: artifacts/claude-y1v-20260927/PLAN.md (sealed in SEAL.sha256.txt). Same items as y1t (GLM-written chats, code-graded; nothing Claude-written); LFM drafts its own answers, trains on its own right answers plus "I don't know." (y1t's trainer, with the LoRA on LFM's attention q/k/v/out_proj via scripts/claude_y1v_train.py), then the sealed DEV check runs on the merged LFM and on plain LFM. Four steps: drafts, train, eval, eval_plain. Between passes a Mac-side guard (handoff/kit/y1vvast/guard.sh) copies back and destroys, else stops, at the $1.00 cap, at the time cap scaled to the card, or when the chain is done. The chain stops its own step (by the exact PID it started) when its log is unchanged for 20 minutes or a time or money cap passes.
Pass 3 of 3 ("last"): RENTS NOTHING. It goes into the queue only after rent-y1v-vast-p2 has exited with a NEXT-PASS-NEEDED note, and then at once. It watches until 45 minutes into the pass; if the chain is still running then, it asks the chain to stop its step (by the PID chain.sh started), copies back what exists, checks it, destroys the instance and writes RESULTS-vast.md as LAST-PASS-STOP. If the copy check fails, it STOPS the instance instead of destroying it (GPU billing ends, its disk keeps the files) and prints FLAG-DIRECTOR. Any other way it ends with the instance not confirmed destroyed or stopped prints ACTION NEEDED (FLAG-DIRECTOR) with the instance id.
It runs handoff/kit/y1vvast/pass.sh from the pinned commit 37d05c9f9eb585b5f4bc127b40d2029d4e327bdf (y1t's kit, tested against a fake vast CLI and a fake rental). The vastai CLI reads its own key file; the script never reads or prints the key, never touches an instance this task did not create, never edits sealed code, and never pushes weights. The adapter copy on the Mac is ~/y1v-lfm-adapter/adapter398r.pt (set below; RESULTS-vast.md labels it with the kit default name ~/y1v-adapter, but its sha256 is read from the real copy). This task is not the older held y1v judge (artifacts/claude-y1v-20260926, rent-0y1v and benspc-y1v); its folder is artifacts/claude-y1v-20260927. The Director files the spending ledger line from the LEDGER-SUGGESTION line in the reply.
```bash
set -u
# the adapter goes to ~/y1v-lfm-adapter on the Mac, not the kit default ~/y1v-adapter, which the older held y1v judge job (09-26) also uses
export MAY1T="$HOME/y1v-lfm-adapter"
JOB=$(basename "$0" .bo.sh); PIN=37d05c9f9eb585b5f4bc127b40d2029d4e327bdf; MODE=last
date -u; echo "job $JOB"
git fetch -q origin main builder-outbox || echo "git fetch failed; trying the local copy of $PIN"
K=$(mktemp -d "${TMPDIR:-/tmp}/y1vkit.XXXXXX")
git archive "$PIN" handoff/kit/y1vvast | tar -x -C "$K"
[ -f "$K/handoff/kit/y1vvast/pass.sh" ] || { echo "STOP: kit $PIN not found"; rm -rf "$K"; exit 0; }
# exec: the pass replaces this shell, so the watcher's 75-minute alarm reaches it; pass.sh removes $K when it exits
exec bash "$K/handoff/kit/y1vvast/pass.sh" "$K" "$PIN" "$JOB" "$MODE" "$(dirname "$0")/$JOB.md"
```
PUSH: artifacts/claude-y1v-20260927/run

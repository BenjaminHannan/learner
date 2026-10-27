# mu-405 V405b: the talker did not use the facts it was given -> Q1 and Q2 INCONCLUSIVE (written 2026-09-26 21:54:37 UTC by date -u)

## Verdict (sealed marks, PASSMARKS.md "Validity")
- V405b needs stored-fact asks answered right K >= N + 10 (of 60). Counted by code: N 0, K 3, W 4 of 60. 3 < 10, so both Q1
  (K vs N) and Q2 (W vs K) are INCONCLUSIVE, as the marks say: the talker did not use the facts it was given.
- Blind recount (a fresh agent with its own script, read-only): N 0, K 3, W 4 asks right; K any of the 3 values 3, W 5;
  300 session-2 rows, 60 chats and 60 asks per arm; 0 empty replies, 0 <think> leftovers. Matches the run logs'
  ask_right exactly. sha256: talk_N 1ed656f1..., talk_K 1d5be808..., talk_W 3a6a7340..., facts 4ff1c668....
- Runs: run2/ (ADDENDUM-2), exits N 20:00:54, K 20:42:09, W 21:22:17 UTC, all exit 0. Arm H (report only) still running.

## What the replies look like (post-hoc, suggested, not a registered finding)
- A regex for "I don't have / don't recall / no information / not sure / as an AI" matches the ask reply in N 24, K 27,
  W 33 of 60. Six ask turns read by the thread: each asks plainly for the right fact ("do you remember my parrot's
  name?"); K and W answer "I don't have any information about ..." or drift back to an earlier topic.
- The same failure was already on record: y1d gave the plain 1B the exact answer lines in the system message and it
  answered 3 of 56 (greedy 0 of 56, "I don't have information about ...") (scripts/claude_y1f_layout.py:4-8). y1f's L1
  layout puts the 'User said' block in the USER message (claude_y1f_layout.py:59-63); bm-398d did the same with
  LoCoMo's lines and got 137 of 297.

## Why it matters beyond this thread
- 0.2d's talker puts the W input in the SYSTEM message, exactly as this W arm did (scripts/claude_e2e02d.py:224-228,
  system_text; its header calls it "y1f's L1 form, mu-405's W arm"). On these 60 DEV chats that placement gave 4 of 60
  stored facts back. Suggested: 0.2d's memory path does not reach the user as built. Month-end owns that decision.

## Next (this thread)
- Claims judging of mu-405 is not run: both questions are INCONCLUSIVE, and the talker barely used the facts, so the
  made-up-claims question was not tested. The run files stay for reuse.
- Obvious fix first: move the 'User said' block from the system message to the latest user message (y1f's L1
  placement), one change, on the same panel, free CPU here: mu-405b, sealed before its run.

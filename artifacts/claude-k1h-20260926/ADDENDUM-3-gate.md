# k1h ADDENDUM 3: the first-10 gate on k1h-glm2, and a capped, logged route for any resume (Creative answers in chat thread, written 2026-09-26 21:04 UTC)

Written while k1h-glm2 runs, before any k1h chat, training row or check exists and before I have read any GLM answer's
text. It changes no prompt, parsing, filter, gate, recipe, arm, panel, mark or scope. Registered FAILs stay FAILs.

## The first-10 gate (the Thread manager, 20:33 UTC)
Why: lis-320's pilot 3 had 30 of 32 opencode calls fail (27 exit 1 with only "> build · glm-5.3-flash" on stderr, 3
timeouts at 300 s; the Director's 000-glm-exitcodes corrected the split). k1h-glm2 had already been launched
(20:22:25 UTC, the watcher's status file), so the gate ran as a separate job, 000-k1h-gate10 (queued in 5ade175e7).
Rule: stop k1h-glm2 by exact PID if 8 or more of the first 10 rows of its answers.jsonl have an empty answer.
Result (artifacts/claude-k1h-20260926/glm-gate/REPORT.md on builder-outbox, 20:38 UTC): **GATE-PASS. 0 of the first
10 rows empty**; 131 rows written by then, 0 empty; nothing was stopped. From the copied rows (seconds only): median 11.5 s
a call, shortest 4.6 s, longest 64.5 s.
What this does and does not show: an empty row means a call failed all 3 of helper v1.1's tries, which log no per-try
exit code (scripts/claude_glm_opencode_v11.py:123-140), so the gate counts failed calls, not failed tries. It shows
that the answer prompts (the SYSTEM333D instructions and a chat, plain text back) work on this route. It does not show
anything about the chat-writing prompts (one long instruction asking for 20 chats as JSON), which k1h-glm2's step 5
sends next.
Deviation in my gate task: its header said "no opencode call" and its step 6 asked for `opencode session list` (a count;
no GLM call). The job ran the count and reported the contradiction. My wording error.
Correction to a relayed count: 000-glm-exitcodes reported "k1h-glm2 chats phase: 14 calls, 14 text, 0 failed". Those
14 lines are the first launch's (k1h-glm, helper v1; artifacts/claude-k1h-20260926/glm-v1/chats-log.txt), and that log
cannot tell a success from a failure: run_chats prints "chats call c done" for both (scripts/claude_k1h_glm.py:84-94).
So how the first launch's chat-writing calls ended is unknown.

## Step 5 runs as launched
k1h-glm2's step 5 (36 chat-writing calls on helper v1.1, 2 at once, 600 s a try, no time limit inside run_chats) began
when its step 4 ended (about 20:50 UTC, estimated from the log's 120 rows at 13 minutes). I had written a stop job for
this point (000-stop-k1h-glm2, held; bee1d19c9). My attempt to queue it at 21:02 UTC was refused by this session's
permission check, so the job was not stopped by this thread. The job's own time cap is 8 hours in total.

## Any resume job uses wrapper v1.2 (sealed here)
scripts/claude_k1h_glm_v12.py: v1.1's route unchanged (same sealed claude_k1h_glm.py, helper v1.1, at most 2 calls at
once, 600 s a try), plus:
- --cap-minutes N, which the chats mode refuses to run without: after N minutes no new opencode try starts (a try
  already running may add up to 600 s). The Thread manager, 20:37 UTC: a 9-hour worst case with no cap is not
  acceptable for a $0 Mac job that other jobs queue behind.
- One stderr line per opencode try: start time, seconds, exit code, a label (ok, empty, exit-build, timeout,
  exit-other, capped) and the prompt's length in characters. No prompt or reply text.
Tests: selftest 3/3 (labels, no text in the log, session commands pass through unlogged, a capped try never reaches
opencode, argument handling), and a run against a fake opencode binary (1 ok try; 3 exit-build tries for one failing
call; 3 capped tries that never ran it).
A resume job is written only if k1h-glm2 ends without the new chats and their answers. Its caps are fixed then, before it
runs, and recorded in the next addendum.

## What does not change
The model, both prompts, the parsing, the 36 chat calls and their areas, the code filters, gates 1 to 3
(DATA-GATE-k1h.md), the size floor, the training recipe, the arms, the panel, the marks and the scope
(ADDENDUM-1-scope.md, ADDENDUM-2-route.md).

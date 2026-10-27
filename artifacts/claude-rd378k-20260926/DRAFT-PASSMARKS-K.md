# rd-378k addendum K, DRAFT (2026-09-27 03:50:37 UTC; NOT sealed): the grader moves from GLM to GPT-6 Luna

DRAFT for the Thread manager's review. It becomes PASSMARKS-K.md, with SEAL-ADD-K, once the Director's Luna text-call
helper exists. The {LUNA_*} fields are filled in at that point. It is written before any Luna call, and before any
output of 004-rd378k-gate3low has landed (0 files on builder-outbox 7091687815). PASSMARKS.md and addenda B-J stay as
sealed; this file adds to them.

## Why
Ben, 03:47:41 UTC 09-27: "just have luna rewrite all the training data. It's so so cheap". This came after he chose
"Allow Luna" (goals page, cd475e141 and 5ed7dcad9). GLM is out until its weekly reset (addendum J). Claude-written or
Claude-judged training data stays banned.

## The one change: the route
claude_rd378k_teacher3 runs unchanged: the same prompt words, verdict words, windows of at most 7 graded turns,
tolerant parser and two passes. The only change is that each call goes through the Director's Luna text-call helper
({LUNA_HELPER}, sha256 {LUNA_SHA}, model id {LUNA_MODEL}). A new launcher, scripts/claude_luna_run.py, binds that
helper's call in place of claude_glm_opencode, so claude_rd378k_teacher3oc.py also runs unchanged.

## Step 1: format pilot (training dialogs only, never the gate's 38)
- Luna grades the 4 rd-378g practice dialogs whose sha256(id) % 12 == 0 in glm/notes_w1.jsonl (sha256 87a51358...):
  3 chat, 1 overheard, 32 graded turns. These are training dialogs with no judge verdicts, so no gate item is touched.
- Output goes to pilot-luna/. Its grades are never used or read. Only its JSON line of counts and its wall time are
  read.
- Pass: "unparsed" is 0 (all 4 usable) and "failed_calls" is at most 2.
- Otherwise: stop, the Thread manager gets the counts, and the gate does not run. Labeller v3 is the last version (the
  Thread manager's 18:32 rule), so only a fault in the route or helper may be fixed. The prompt and parser may not.

## Step 2: gate3luna, on the same 38 dialogs (judge_train_in, sha256(id) % 3 == 1: 23 chat, 15 overheard)
- Same rows and bars as addenda E and F:
  - agreement >= 85% and kappa >= 0.5;
  - untrue notes: teacher "ok" on <= 15% of judge-unsupported notes;
  - coverage: usable dialogs chat >= 21 of 23 and overheard >= 14 of 15.
- Report only: pass A's agree line, failed calls, missed_unknown_turns, wall time.
- Route losses (addendum H) are failed tries whose raw answer is empty, or matches (case-insensitive) "usage limit",
  "rate limit" or "quota". A script counts these; it prints the count only, never raw text.
- Proved wrong (Luna does not grade like the blind judges): agreement below 85% or the untrue row above 15%, with no
  route loss.

## After
- PASS: every training grade for rd-378g and rd-378k comes from teacher3 through this Luna route.
- A row fails and a route loss is present: there is no verdict. The route is fixed, then the same 38 run again under
  a new addendum.
- A row fails and no route loss is present: this is a registered FAIL of the Luna route, and no Luna grade trains
  anything. After GLM's weekly reset a GLM-low gate (gate3low2) may run on the same 38 dialogs. It would be a second
  route tried on the same dialogs: the Thread manager reviews it first, and it is reported as the second try.
- gate3low (addendum J) is dropped. Whether or not it lands, its labels and agreement lines are never read.

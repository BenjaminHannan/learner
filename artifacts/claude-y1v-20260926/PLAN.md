# y1v: a trained judge. Can a copy of the 1B learn to tell its own right answers from wrong ones? (Answering-from-memory thread, rules fixed 18:15 UTC 2026-09-26, before y1t's verdict and before y1t's drafts exist)

Owner: the "Answering from memory" thread (row Y1; 0.2c's Y1 FAIL stays a FAIL). This is y1t's FAIL fallback: it runs
only if y1t (trained doubt, artifacts/claude-y1t-20260926/PLAN.md) is NO-GO. If y1t is GO, this plan is not run.
One change to y1g's V config: the yes/no check is done by a LoRA-trained copy of the plain MiniCPM5-1B instead of the
plain 1B itself. Selection on DEV (readable); rules fixed here before any GPU run.

## Why
- y1g (VERIFY-y1g.md, efa4d8923): the plain 1B judging its own answers (V) kept 38.5% of its right answers and 18.8%
  of its wrong ones. It said "no" to 15 of 26 right, 23 of 28 wrong and 7 of 8 answered never-told asks. A signal,
  but it leans to "no" and separates weakly.
- y1t trains the answerer itself. If that fails (it changes the answers, or it refuses too much), the other learned
  route is to leave the answers alone and train only the check. The answers stay the plain 1B's own, so the judge can
  only keep or drop them: at most the plain 1B's 26 right answers can survive, and none can be made worse.
- Source of the practice: y1t's own run already makes and grades the drafts (drafts.jsonl). y1v adds no new model
  text: code chose every fact, GLM 5.3 Flash wrote every word of the chats, code graded every draft (Ben 16:39, "Use
  GLM").

## Brain first
People judge "do I really know this?" with a monitoring step that is partly separate from recall itself
(feeling-of-knowing, source monitoring); frontal damage can leave recall working while that judgement fails. The
monitor is tuned by feedback on past recalls. Here the judge is that monitor, tuned on the 1B's graded past answers.
The mapping is a guess about the brain.

## What runs (one rental job; code sealed; scripts/claude_y1v_judge.py)
1. Judge rows (CPU): y1t's drafts.jsonl joined to y1t's items_train.jsonl. Every distinct draft (greedy + 4 samples)
   that y1f's checks let through becomes a row in y1g's V prompt (the same text V uses on DEV), target "Yes." if
   y1t's grade() calls it right (an old corrected value and any answer to a never-told twin are wrong), else "No.".
   Classes cut to equal size (seeded, at most 2000 each); repeated to about 1500 rows if smaller (at most 3 copies).
   15% of dialogs held out as judge practice-dev (seed 4033, at most 300 rows).
2. Training: scripts/claude_bm398r_train.py unchanged (rank 16 LoRA on q/k/v/o, 1 epoch, AdamW 2e-4, batch 8, loss on
   the answer tokens, seed 3992), merged copy saved.
3. DEV check: y1g's run() unchanged (seed 4024) with a routed model: V's yes/no prompt goes to the judge, everything
   else to the plain 1B, so A0, A1, C3 and C4 are the plain 1B's own. The same y1g script on the plain 1B alone, on
   the same machine, is the reference (report only; y1g's own run gave V 10 / 5 / 9).

## Decision rules (fixed before the run)
- GO if the judged config V on DEV has answerable right >= 22 of 56 AND answerable wrong-candidates <= 8 AND
  never-told "don't know" >= 8 of 10 (y1t's bars; decide() in the script). The plain 1B's A1 gives 26 / 24 / 2, so the
  judge must keep at least 22 of its right answers while dropping most wrong ones.
- Report: kept shares (y1g's signal(): right kept vs wrong kept, of the asks A1 answers) against the plain V on the
  same machine; judge practice-dev before and after (bm-398r's dev_check); judge row counts by kind.
- GO: rp1's R becomes "plain 1B A1 + y1v judge"; rp1 PASSMARKS are then sealed and run on bank E.
- NO-GO: report; the next step is decided after, and bank E stays unused.

## Proved wrong
"A trained judge carries over from practice chats to other chats" is wrong if the judge's practice-dev right rises by
at least 20 points (bm-398r's dev_check, dev_before vs dev_after_lora) while on DEV the judged V's gap (share of A1's
right answers kept minus share of A1's wrong answers kept) is less than 0.10 above the plain V's gap on the same
machine: the judge learned GLM chats, not its own reliability.

## Predictions (thread, before the run)
GO: 0.2. V keeps >= 22 of the right answers: 0.35. Never-told "don't know" >= 8 of 10: 0.6. Proved wrong: 0.3.

## Limits
DEV has 56 answerable and 10 never-told asks. The practice questions are all one kind (asking back one stored fact);
DEV has two-hop, reversal, yes/no and edit asks too. The judge sees only answers the plain 1B gave on practice chats.
The judge is a second copy of the 1B; in the joined build it would be the same base with the adapter switched on only
for the check (bm-398i's switch).

## Plain summary for Ben
If teaching the small model to say "I don't know" by itself (y1t) fails, this is the backup. The model keeps
answering the way it does now, and a second, trained copy of it checks each answer: "is this really in the chat?".
The checker practises on thousands of the model's own old answers to GLM-written chats, each marked right or wrong by
code. It passes if, on our own development chats, the checked answers keep at least 22 of 56 right, at most 8 wrong,
and it says "I don't know" to at least 8 of the 10 things it was never told.

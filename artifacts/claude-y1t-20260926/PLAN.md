# y1t: trained doubt. Can the 1B learn when to say "I don't know" from its own graded drafts? (Answering-from-memory thread, rules fixed 17:15 UTC 2026-09-26, before the practice chats exist)

Owner: the "Answering from memory" thread (row Y1; 0.2c's Y1 FAIL stays a FAIL). One change to the plain MiniCPM5-1B:
a LoRA trained on its own graded drafts from GLM-written practice chats. Selection on DEV (readable); rules fixed here
before any GPU run. If it passes, the recall path with this adapter goes to rp1 on bank E (TEST-ONLY) against plain
same-size models, with marks sealed before that run.

## Why
- y1f: in the LoCoMo reading layout (L1) the plain 1B reads 25 to 26 of 56 DEV answers from every earlier line, but
  it answered 8 or 9 of 10 never-told asks and gave 24 to 27 wrong answers.
- y1g (VERIFY-y1g.md, efa4d8923): its own tries carry a doubt signal (4-of-5 agreement kept 38% of its right answers
  and 6% of its wrong ones), but a hand-written agreement rule kept only 10 of 56 right: NO-GO. y1g's PLAN names this
  fallback.
- Risk, shown by Benchmarks (bm-398r, 84c414325): a reader adapter trained on made-up chats with code-written answers
  rose +72 on its own practice dev and added nothing on LoCoMo (110 vs 111); it learned the answer's form. Here the
  targets are the 1B's own drafts, so the form stays its own; the new thing it can learn is when to say "I don't
  know". Each practice question comes as a pair: the same GLM-written question with the fact in the chat, and with
  the turns stating it removed. Only the chat differs, so a surface cue in the question cannot tell the two apart.

## Brain first
People learn when to trust a recollection from feedback: children's confidence becomes calibrated by being corrected.
Telling "did I really hear this, or does it only feel familiar?" (reality / source monitoring) is learned the same
way. The paired questions give the model that feedback on its own recall. The mapping is a guess about the brain.

## What runs (one rental job; code sealed)
1. Chats: this thread's run of Reading facts' lis-320 seed, GLM and check scripts, unchanged (Reading facts agreed,
   17:12 UTC): seed 4027, 2400 dialogs, no --ask-back, DEV names and the hashed test-panel list (bank E included,
   6459efad0) avoided (handoff/held/y1t-glm-mac.md). Code chose every fact; GLM 5.3 Flash wrote every word; lis-320's
   check kept or dropped each turn. None of these dialogs is in DEV or bank E.
2. Items (scripts/claude_y1t_data.py items, CPU): per kept "ask" turn whose fact is current among the kept turns
   before it, an answerable item (gold = the latest ASSERT/CORRECT value from the seed's code frames whose value is
   typed in that kept user turn) and its never-told twin (every kept earlier turn with a fact on that owner and
   relation removed). 15% of dialogs held out as practice-dev (seed 4027).
3. Drafts (claude_y1t_data.py drafts, GPU): the plain 1B answers every training item in y1f's L1 layout, greedy plus
   4 samples (T 0.7 / top-p 0.9). Code grades each (336 score_ask + y1f's checks; an old corrected value is wrong).
   Target: the right greedy draft, else the first right sample, else "I don't know."; never-told twins "I don't know.".
   "I don't know" rows capped at the number of answer rows (seeded). At most 3000 items. If fewer than 1500 rows,
   each is repeated so about 1500 pass through training (at most 3 copies; the trainer does 1 pass).
4. Training: scripts/claude_bm398r_train.py unchanged (rank 16 LoRA on q/k/v/o, 1 epoch, AdamW 2e-4, batch 8, loss on
   the answer tokens, seed 3992), merged copy saved.
5. DEV check: scripts/claude_y1g_doubt.py unchanged, on the merged model (seed 4024). The trained config is A1 (one
   greedy answer through y1f's checks); C3, C4, V on top are report only. The same script on the plain 1B on the same
   machine is the reference (report only; y1g's own run gave A1 26 / 24 / 2).

## Decision rules (fixed before the run)
- GO if the merged model's A1 on DEV has answerable right >= 22 of 56 AND answerable wrong-candidates <= 8 AND
  never-told "don't know" >= 8 of 10. Plain 1B's A1 for reference: 26 / 24 / 2 (y1g). The right-answer bar is
  tighter than y1g PLAN's 18 (Thread manager, 17:07 UTC: refusing too much is its own problem): at most 4 right
  answers may be traded for the drop in wrong ones.
- Report: how many of the plain 1B's right DEV asks stay right (the two y1g rows files of this run, same asks); per
  ask type; practice-dev before and after (bm-398r's dev_check); draft counts (own greedy, own sample, "I don't know"
  targets; corrected asks).
- GO: rp1's R becomes "recall path + y1t adapter, A1"; rp1 PASSMARKS are then sealed and run.
- NO-GO: report; the next step is decided after, and bank E stays unused.

## Proved wrong
"Trained doubt transfers from practice chats to other chats" is wrong if the practice-dev never-told "don't know"
rises by at least 30 points (bm-398r's dev_check, before vs after) while DEV never-told "don't know" (A1) rises by
fewer than 3 of 10 over the plain 1B on the same machine: the model learned GLM chats, not doubt.

## Predictions (thread, before the run)
GO: 0.25. DEV never-told "don't know" >= 8 of 10: 0.6. DEV right >= 22: 0.4. Proved wrong: 0.2.

## Limits
DEV has 56 answerable and 10 never-told asks. The practice questions are all one kind (asking back one stored fact);
DEV has two-hop, reversal, yes/no and edit asks too. The adapter is meant to be on only while answering a memory
question (bm-398r showed an always-on reader adapter breaks GSM8K); the switch is bm-398i's.

## Plain summary for Ben
The small model answers questions about your chats but never admits when you didn't tell it something. Here it
practises on chats written by GLM: each question comes twice, once with the answer in the chat and once with it
taken out. Code marks its own answers right or wrong, and it trains on its own right answers plus "I don't know"
where it was wrong or the answer wasn't there. It passes if, on our own development chats (not the GLM ones), it
keeps at least 22 of 56 right, gives at most 8 wrong, and says "I don't know" to at least 8 of the 10 things it was
never told.

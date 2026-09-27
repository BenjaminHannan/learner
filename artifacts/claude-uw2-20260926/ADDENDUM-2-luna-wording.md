# uw-2 ADDENDUM-2: the training chats are worded by Luna, and a pilot gate runs first (written 2026-09-27 10:15 UTC, before any seed-324 row exists)

No mark, bar, target, prompt, mix, minimum, trainer, DEV stop rule or test panel changes.

## Why
- PASSMARKS-uw2.md ("Training cards") names lis-320's GLM-worded seed-324 chats as the source ("The wording comes from
  GLM 5.3 Flash").
- lis-320 switched its seed-324 full run to GPT-6 Luna (lis-320 ADDENDUM-9 to 12). GLM chunk 1 pushed nothing, so
  Luna is the only writer (lis-320 ADDENDUM-11, full-oc/RUN-NOTE-chunk1.md).
- Ben, 03:47 UTC 09-27 (design/v3/30-modes/ben-goals-2026-09-26.md, "Training data: Luna allowed"): Luna may write
  training text. A sealed experiment that switches to Luna needs a written addendum and a small quality pilot gate
  first, before any run. This file is that addendum.
- Seeds, labels, targets and checks still come from code. Nothing trained on is written or judged by Claude.

## What changes
1. Source: lis-320's Luna-worded kept seed-324 chats, taken only after its DATA.md exists and pinned by the sha256
   DATA.md records for kept.jsonl.
   - If DATA.md lists a second writer, its rows are used only if they pass the same checks. Card counts are then
     reported per writer.
2. Raw check: the sealed scripts/claude_lis320_rawcheck.py asserts the GLM model id, so it cannot pass Luna rows.
   uw-2 runs lis-320's own sealed Luna check instead:
   - scripts/claude_lis320_rawcheck2.py --models gpt-6-luna on the joined raw rows, joined as lis-320 ADDENDUM-11
     does (scripts/claude_lis320_resume_clean.py).
   - A failure means no training, and the counts go to the Thread manager.
3. Pilot gate (Ben's "small quality pilot gate first"). It runs before any seed-324 row is used.
   - Cards: scripts/claude_uw2_data.py build (unchanged, sealed in ADDENDUM-1) on lis-320 pilot 8. Pilot 8 is seed
     328, 60 Luna chats, artifacts/claude-lis320-20260926/pilot8e/ on origin/builder-outbox, PASS on every lis-320
     mark (PILOT-REVIEW.md, "Pilot 8").
   - Gate: the sealed uw-2 data gate, run unchanged on those cards.
     - gateprep draws 60 cards with seed 4053: 30 corrections (15 correct_ref) and 30 look-alike NONE cards.
     - Two fresh blind judges answer with JUDGE-gate-uw2.md (sealed with this file). A fresh third judge answers the
       split packets only. gatecmp compares the answers.
   - PASS if at least 54 of 60 agree with the code label, the same bar as the full gate.
   - Pilot cards are never trained on (PASSMARKS: never the pilots).
   - If the pilot gate fails:
     - no seed-324 card is trained on;
     - the counts by label kind go to the Thread manager;
     - any fix is made by code in a new addendum, never from the judges' answers.
   - If it passes, the full gate still runs on the real training cards, exactly as PASSMARKS and ADDENDUM-1 say, with
     new fresh judges.
4. The same JUDGE-gate-uw2.md is used for the full gate. Until now the gate's question was fixed only in PASSMARKS and
   ADDENDUM-1 item 2. That is still the question; the file only puts it in one place.
5. The Mac line in "Machine and cost" reads "none beyond lis-320's own Luna run". uw-2 makes no Luna or GLM calls of
   its own.

## Format check done before this file (counts only)
Code only; no judge and no mark. claude_uw2_data.py build on pilot8e gave these counts:
- 404 cards; 290 of them in the mix.
- 58 correction cards:
  - 19 correct_ref, all 19 earlier-owner by the uw-2 panel's code definition;
  - 28 name their owner;
  - 11 are the user's own.
- 232 NONE cards.
- Skipped: 10 turns not kept, 1 correction whose old fact is not a note, 0 value-not-span drops.

The full run is 6000 chats against the pilot's 60. At the pilot's rate that is roughly 5,800 corrections, about 1,900
of them correct_ref. This is an estimate from the pilot; the minimum is 300 and 80.

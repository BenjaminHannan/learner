# rd-378g DRAFT addendum K, second draft (2026-09-27 10:06 UTC): train G on the notes as written, and add mark G5 (are G's notes true?)

DRAFT for the Thread manager's review; it replaces DRAFT-ADDENDUM-K.md (f78f4ecb7), which stays as written. Not sealed:
nothing here runs until it is sealed as ADDENDUM-K.md. Written before any Luna-written dialog for rd-378g has been read,
before notes_w1_tagged.jsonl exists, before any row is built and before any G note exists. PASSMARKS.md and addenda A-J
stay as sealed; this file would add to them.

## Why
- rd-378k's label gate through Luna is a registered FAIL, proved wrong (VERIFY-gate3luna.md, 38ad6d0a3):
  - agreement 489 of 624, 78.4%, against a bar of 85%;
  - untrue 9 of 296, 3.0%;
  - 0 route losses.
- By PASSMARKS-K no Luna grade trains anything, so ADDENDUM-I's grade step (rd378g-label3luna) does not run.
- The only other sealed grader route is GLM-low (gate3low2) after the opencode Go weekly limit resets. The reset time is
  not known to this thread, and that gate is a reviewed second try on the same 38 dialogs. As sealed, G cannot be trained
  until then, and never if gate3low2 also fails.
- What the grade filter was protecting against (the Thread manager's review, 10:03 UTC): untrue notes in training.
  - The 624 notes in the gate sample were written by the rd-378 writer (R, Claude-trained), not by GLM or Luna. They are
    rd-371b's judge set.
  - The blind judges called 296 of them unsupported (47%). On rd-371b's sealed test key, R's greedy notes were 145 of 277
    unsupported (52%).
  - R itself was trained only on turns an Opus judge passed.
  - How many GLM and Luna training notes are untrue has not been measured, because no grader has passed.
  - Keep-all trains on all of them, so a G that passes G1-G4 could still write untrue notes. G1-G4 measure search help
    (any@10) and parsing, not truth. Hence G5.

## The one change: no grade filter
- As sealed (PASSMARKS "The one change"), a turn trains G only if a grader called every note on it "ok" and found
  nothing missed.
- Here every turn trains G exactly as its writer (GLM or Luna) wrote it, including turns where the writer chose to write
  no note.
- The rows come from the sealed builder scripts/claude_rd378_data.py, unchanged. It reads a keep-all file written by the
  new scripts/claude_rd378g_keepall.py.
  - The keep-all file is not a grade: no model and no rule looks at any note.
  - Dry run on the 90 GLM dialogs (counts only): 897 turns, 767 notes, 284 turns with no note; kept 850 train and 47 dev
    turns, 0 dropped.
- The notes are still checked in code when written (check_batch's structure and note-form checks) and by the tag step's
  error-text scan (ADDENDUM-I).
- Unchanged:
  - the writers: 90 GLM dialogs plus the Luna batches (ADDENDUM-I);
  - the 120-dialog floor;
  - the trainer and its settings: MiniCPM5-1B + LoRA, epochs 2, lr 2e-4, rank 32, batch 16, max-len 512, seed 300,
    repeat 3, --merge;
  - the LoCoMo 5-9 test through store v4, marks G1-G4, the proved-wrong line, and R = 585 of 772.

## New registered mark G5: G's notes are no less true than R's
- Dialogs: the 43 dialogs of rd-371b's judge set with sha256(id) % 3 == 2 (14 chat, 29 overheard).
  - No grader gate has used them.
  - They are not LoCoMo, so the notes can be pushed and judged in the cloud.
  - Neither G nor R trained on them.
- Writing: on BensPC, G and R (the rd-378 writer, merged sha256 dbcc8db5...8510) each write greedy notes over those
  dialogs with the notes removed (scripts/claude_rd378_write.py, the same command as step 6's dev check).
- Judging:
  - `scripts/claude_rd378g_g5.py make --seed 37805` puts both writers' notes into one shuffled list of 86 items with
    opaque ids. The id map is a separate file the judges never read.
  - Two fresh blind judges each grade every note with the rd-378 judge brief (artifacts/claude-rd378-20260925/data/
    JUDGE_NOTES.md). They are new cloud agents that have seen none of this work, have no file access beyond items.jsonl
    and the brief, and never learn which writer wrote which note.
  - Their verdicts only measure. They never train, tune or filter anything.
- Key and count: `claude_rd378g_g5.py score`, rd-371b's key rule. A note is ok where both say ok and unsupported where
  both say unsupported; the rest are excluded and reported. Share = key unsupported / (key ok + key unsupported), per
  writer.
- Bar: G's share is at most R's share + 5 points.
- Proved wrong for G5: G's share is at least R's share + 15 points.
- Fallback, fixed now: if R's weights cannot be found on BensPC or the Mac, R's share is taken as 52% (rd-371b's key:
  same brief, two blind judges, R's greedy notes on fresh dialogs, 145 of 277). The bar is then G's share <= 57%.
- Prediction, written now: R about 50% and G about 50%, so G5 PASS. Confidence is low: G learns from notes that nobody
  graded, but one strong writer (Luna) wrote most of them.
- Report only: the excluded counts, the per-kind shares, notes per turn per writer, and unparsed turns per writer.

## Steps (after the Luna write lands and ADDENDUM-I's step 3 tag passes its floor)
1. glm3U/notes_w1.jsonl = copy of glm2N/notes_w1_tagged.jsonl.
2. Run `claude_rd378g_keepall.py make --notes glm3U/notes_w1.jsonl --out glm3U/judge_w1.jsonl`, then
   `claude_rd378_data.py --notes glm3U --out glm3U/rows` (repeat 3).
3. SEAL-B (PASSMARKS "Seal") covers glm3U/notes_w1.jsonl, judge_w1.jsonl and rows/ before training.
4. BensPC: train G, run the dev check, score LoCoMo 5-9 (the held rd378g-pc job, re-pointed at glm3U/rows). Then G and
   R write the G5 notes, and the notes are pushed (no LoCoMo text in them).
5. Cloud: g5 make, the two blind judges, g5 score. Then RESULTS.md and a blind recount.

## What each result means (fixed now)
- PASS = G1-G5. G is a Claude-free note writer that helps search and whose notes are no less true than R's, trained with
  no grader. It is offered to Month-end for 0.2d's notes slot (ADDENDUM-20 there) and disclosed as "trained on ungraded
  GLM and Luna notes; about half of R's and G's notes are untrue on fresh dialogs".
- Until G5 passes, no G note goes to Month-end as trustworthy. Notes stay search pointers to the raw lines (store v4
  answers from raw lines only).
- G1-G4 pass and G5 fails: registered FAIL. Suggested reading: training without a grader costs truth. After the GLM
  reset, gate3low2 runs as PASSMARKS-K says. If it passes, the graded G (as originally sealed) is trained and scored as
  the second try, and reported as such.
- G1, G2, G3 or G4 fails: registered FAIL, with the same next step.
- Proved wrong: G any@10 <= A any@10 + 1 point (unchanged), or the G5 line above.
- rd-378k (the cut-only step) needs a grader for its own rows, so it still waits for a grader that passes.

## Disclosed
- G2 compares R (a filtered, Claude-trained writer) with an unfiltered GLM+Luna writer. Two things differ, the writers and
  the filter, which is why G2 was always "as good a search aid", not a one-change comparison. G5 compares the same pair.
- G5's judges are Claude agents. That is allowed for a test (they measure, never train). The same kind of judges made
  every earlier key, including rd-371b's.
- Luna's gate result suggests Luna is stricter than the blind judges (121 of 135 misses were judge-ok notes it turned
  down). That result is not used here in any way.

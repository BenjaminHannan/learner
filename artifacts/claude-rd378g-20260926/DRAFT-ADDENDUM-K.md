# rd-378g DRAFT addendum K (2026-09-27 10:01 UTC): train G on the notes as written, with no grade filter

DRAFT for the Thread manager's review. It is not sealed, and nothing here runs until it is sealed as ADDENDUM-K.md. It
is written before any Luna-written dialog for rd-378g has been read, before notes_w1_tagged.jsonl exists, and before any
row is built. PASSMARKS.md and addenda A-J stay as sealed; this file would add to them.

## Why
- rd-378k's label gate through Luna is a registered FAIL, proved wrong (VERIFY-gate3luna.md, 38ad6d0a3). The numbers:
  - agreement 489 of 624, 78.4%, against a bar of 85%;
  - untrue 9 of 296, 3.0%;
  - 0 route losses.
- By PASSMARKS-K, no Luna grade trains anything, so ADDENDUM-I's grade step (rd378g-label3luna) does not run.
- The only other sealed grader route is GLM-low (gate3low2), after the opencode Go weekly limit resets. The reset time
  is not known to this thread. That gate would be a reviewed second try on the same 38 dialogs.
- So as sealed, G cannot be trained until then. And if gate3low2 also fails, G cannot be trained at all.

## The one change: no grade filter
- As sealed (PASSMARKS "The one change"), a turn trains G only if a grader called every note on it "ok" and found
  nothing missed.
- Here every turn trains G exactly as its writer (GLM or Luna) wrote it, including turns where the writer chose to write
  no note.
- The rows come from the sealed builder scripts/claude_rd378_data.py, unchanged. It reads a keep-all file written by the
  new scripts/claude_rd378g_keepall.py.
  - The keep-all file is NOT a grade: no model and no rule looks at any note.
  - It lists every turn the builder reads with verdicts "ok" for each note and missed 0.
  - Dry run on the 90 GLM dialogs (counts only): 897 turns, 767 notes, 284 turns with no note; builder kept 850 train
    turns, 47 dev turns, 0 dropped.
- The notes are still checked in code when written: check_batch's structure and note-form checks, and the tag step's
  error-text scan (ADDENDUM-I).
- Unchanged: the writers (90 GLM dialogs plus the Luna batches, ADDENDUM-I), the 120-dialog floor, the trainer and its
  settings (MiniCPM5-1B + LoRA, epochs 2, lr 2e-4, rank 32, batch 16, max-len 512, seed 300, repeat 3, --merge), the
  test (LoCoMo 5-9 through store v4) and marks G1-G4, the proved-wrong line, and R.

## Steps (after the Luna write lands and ADDENDUM-I's step 3 tag passes its floor)
1. glm3U/notes_w1.jsonl = copy of glm2N/notes_w1_tagged.jsonl.
2. `claude_rd378g_keepall.py make --notes glm3U/notes_w1.jsonl --out glm3U/judge_w1.jsonl`, then
   `claude_rd378_data.py --notes glm3U --out glm3U/rows` (repeat 3).
3. SEAL-B (PASSMARKS "Seal") covers glm3U/notes_w1.jsonl, judge_w1.jsonl and rows/ before training.
4. BensPC trains G and scores it (the held rd378g-pc job, re-pointed at glm3U/rows).

## Report only
- rows by writer (GLM / Luna) and by kind;
- notes per turn;
- turns with no note;
- the PASSMARKS report-only rows.

## What each result means (fixed now)
- PASS (G1-G4): a Claude-free note writer that helps search, trained with no grader at all.
  - It is offered to Month-end for 0.2d's notes slot (ADDENDUM-20 there), disclosed as "trained on ungraded GLM and
    Luna notes".
  - rd-378k (the cut-only step) needs a grader for its own rows, so it still waits for a grader that passes.
- FAIL: registered.
  - Suggested reading: unfiltered notes are not good enough, and a grader is needed.
  - After the GLM reset, gate3low2 runs as PASSMARKS-K says. If it passes, the graded G (as originally sealed) is
    trained and scored as the second try on LoCoMo 5-9, and reported as such.
- Proved wrong (unchanged): G any@10 <= A any@10 + 1 point.

## Disclosed
- This changes the training recipe that rd-378's Claude-trained writer (the R figure) used: R's rows were filtered by a
  judge, and G's are not. So G2 compares a filtered-Claude writer with an unfiltered GLM+Luna writer. Two things differ
  there (the writers and the filter), which is why G2 was always "as good a search aid", not a one-change comparison.
- Luna's gate result suggests Luna is stricter than the blind judges (121 of 135 misses were judge-ok notes it turned
  down). It is not used here in any way.

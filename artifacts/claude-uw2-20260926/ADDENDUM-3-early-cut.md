# uw-2 ADDENDUM-3: train on an early cut of seed 324 (written 2026-09-27 10:21 UTC, before any seed-324 row exists)

This makes one change: the amount of training data. No mark, bar, target, prompt, mix, minimum, gate, trainer,
DEV stop rule or test panel changes.

## Why
- PASSMARKS-uw2.md takes rows only after lis-320's DATA.md, which needs all 6000 seed-324 chats. That is about 45
  Luna chunks (lis-320 ADDENDUM-11), fewer at 6 calls (ADDENDUM-12), so most of a day or more.
- uw-2's minimum is 300 corrections, 80 of them correct_ref. Pilot 8 gave 58 corrections and 19 correct_ref per 60
  chats (ADDENDUM-2).
- The Thread manager suggested this cut (10:18 UTC 09-27).

## Condition
This addendum is in force only if Reading facts agrees in writing before the cut is taken. Reading facts owns lis-320,
and the DATA.md rule was agreed with it at 20:34 UTC 09-26. The run record quotes its answer with the time. If it says
no, PASSMARKS and ADDENDUM-2 stand unchanged, and uw-2 waits for DATA.md.

## The cut, fixed now
- Chunks come from origin/builder-outbox, artifacts/claude-lis320-20260926/full-luna/chunkJ/.
- K is the smallest chunk number whose CHUNK-SUMMARY line says stop=ok and worded_ok >= 1500, with chunks 1 to K all
  stop=ok. A chunk that is not ok before that point blocks the cut, and the counts go to the Thread manager.
- Why 1500 chats: at pilot 8's rate that is about 1,450 corrections and about 475 correct_ref. That is an estimate,
  about 5 times the minimum. The number is fixed before any row is seen.
- Rows: chunks 1 to K, raw.new.jsonl.gz, joined in chunk order.
  - The seeds come from the same seed_cr command as lis-320's chunk job. Their sha256 must equal
    chunk1/SEEDS.sha256.txt.
  - Then lis-320's sealed resume_clean runs, then rawcheck2 --models gpt-6-luna, which must exit 0, then check_we3,
    which writes kept.jsonl.
  - Only the chats that have a row are kept in seeds.jsonl.
  - Code: scripts/claude_uw2_cut.py (new; sealed with this file), `pick` and then `make`. It records every chunk's
    sha256 and the sha256 of raw, kept and seeds in CUT.json. That is the pin, in place of DATA.md's.
- Then everything as sealed:
  - claude_uw2_data.py build on make's output;
  - the minimum check (300 and 80);
  - the full data gate with new fresh judges (JUDGE-gate-uw2.md, at least 54 of 60);
  - the held BensPC job for training, the DEV stop rule and the panel run.
- Later chunks are not used by uw-2. Rows are training only, never test items.

## Selftest (done before sealing; counts only)
The selftest splits lis-320 pilot 8 (seed 328, 60 Luna chats, readable) into two fake chunks.
- make rebuilds pilot 8's own kept.jsonl byte for byte (sha256 a9269835…d261, 405 rows).
- pick finds K = 1 or 2 as the cut size says.
- pick refuses when chunk 1 is not ok.
- A one-chunk cut keeps only the chats that have a row.

## How a verdict reads
A verdict is about a model trained on the first K chunks, and the report states that size.
- If uw-2 fails, the FAIL stays.
- A run on more of seed 324 would be a new, separately named experiment.

# lis-320 ADDENDUM-11: how the Luna full run is chunked (reading thread, 2026-09-27 09:52 UTC)

Written after pilot 8 passed every ADDENDUM-7 mark (PILOT-REVIEW.md, "Pilot 8"). No mark, prompt, seed rule, check or
writer changes here: the full run is seed 324, 6000 dialogs, GPT-6 Luna through scripts/claude_luna_codex.py,
scripts/claude_lis320_luna2.py and scripts/claude_lis320_check_we3.py, as ADDENDUM-9 and ADDENDUM-10 fixed. This file
only records the chunk mechanics, which ADDENDUM-9 left as "at most 70 wording minutes, a 1-call probe, per-chunk new-row
files, the 85%-parsed stop rule".

- Route: each chunk is a BASH-ONLY queue job (no LLM builder; Director 2bf4f9ea7), handoff/queue/claude-lis320-luna-cK-mac.md,
  K = 1, 2, ... Each job has a 75-minute cap, so wording stops at 55 minutes (--max-minutes 55, --batch 12: the runner
  checks time between batches of 12 dialogs, about 5 minutes each at 3 parallel calls).
- Parallel calls: 3 (the Director's share for lis-320). Pilot 8 ran 2.43 dialogs a minute at 3, so 6000 dialogs is about
  41 wording hours or about 45 chunks; a larger share from the Director only changes the job's LW= line.
- Before wording: the seals (6, 8, 9, 10, 11), the no-network selftests, one live helper call (the probe), and an orphan
  check that counts only python or uv processes running claude_lis320_luna2.py (a stalled builder's prompt names the
  script, so a plain pgrep matched it twice on 09-27).
- Resume: the chunk joins every earlier chunk's full-luna/chunkJ/raw.new.jsonl.gz from origin/builder-outbox in order and
  runs scripts/claude_lis320_resume_clean.py, which drops empty, error-like and 3x-repeated replies (their dialogs are
  worded again) and keeps the last row per dialog id. Unparsed non-empty replies stay as unparsed rows.
- After wording: the chunk's new rows go to full-luna/chunkK/raw.new.jsonl.gz (no file is overwritten); rawcheck2
  (--models gpt-6-luna), check_we3 and style run on all rows so far; RESULTS.md ends with one CHUNK-SUMMARY line.
- Stop rule (ADDENDUM-9, unchanged): parsed below 85% of calls in any chunk, a rawcheck2 failure, a failed seal or
  selftest, or a seeds hash different from chunk 1's stops the queue until the Thread manager has the counts.
- The next chunk is queued only after the one before it lands. When every seed-324 dialog has a parsed row, DATA.md is
  written (kept_by_family beside the seeded counts; Luna is the only writer, since GLM chunk 1 pushed nothing,
  full-oc/RUN-NOTE-chunk1.md).

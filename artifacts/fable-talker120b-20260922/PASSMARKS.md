# Experiment 120b (talker mouth raw-decode bugs, Muse) — PASSMARKS (sealed 2026-09-22)

Single-change follow-up to exp 120. The director's sealed GPU fine-tune
(seed 12002, 470 steps, loss 3.01 -> 0.044 in 19 s) scored on the Mac as:
O1 PASS (0 after brake), O2 486/500 PASS, O3 250/250 PASS, O6 FAIL:
313/500 raw decodes unfaithful (bar <= 50).

STEP 1 (diagnosis, no model change): re-decode all 500 held-out records with
the director's checkpoint
(artifacts/claude-talker120-run-20260922/fable_talker120_ckpt_last.pt) on the
Mac CPU via scripts/fable_talker120_score.py functions by import, bucket every
unfaithful raw decode (boundary junk only / name truncation only / both /
other), trace boundary junk to its exact cause (file:line) by comparing the
training serialisation with the decode prompt token by token, and check
tokenizer pieces + copy-head attention for truncations. Table written to
design/v3/30-modes/120b-mouth-decode-muse.md. Every seed/case reported, never
averaged.

## Registered gates (decode-side fix; director's checkpoint re-scored as-is)
- O1 faithfulness: violations on 500 held-out records = 0 AFTER the brake.
- O2 status correctness: >= 480/500 final sentences.
- O3 answer presence: OK answer verbatim >= 240/250.
- O4 time: each run < 25 min wall-clock Mac CPU (OMP_NUM_THREADS=1).
- O5 wire51 replay unchanged: 0 wrong writes, same counts as
  artifacts/fable-wire51-20260921/replay-report.json (mouth returns strings).
- O6 raw-decoder faithfulness: unfaithful BEFORE the brake <= 50/500.
  A FAIL stays FAIL with one diagnosis note.

If the fix needs retraining, no GPU job is launched by this agent: the recipe
is prepared exactly like exp 120 (frozen scripts, sha256 listed, CPU smoke
100 steps) and a one-line GPU command is written for the director.

What it means / What it does not mean: these marks say whether the 313 raw
misses are a decode-side boundary bug (fixable without retraining) or a
trained-in defect; they do not re-litigate O1–O5, which the brake already holds.

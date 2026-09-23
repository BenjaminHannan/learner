# Experiment 53 (mouth: borrowed SmolLM2-360M decoder) — PASSMARKS (sealed 2026-09-22)

Registered run: data seed 5301 (3,000 train pairs + 500 held-out records),
adapter train seed 5301, Mac CPU, OMP_NUM_THREADS=1. A registered FAIL stays a FAIL.

- O1 faithfulness: violations on 500 held-out records = 0 AFTER the brake
  (report the BEFORE-brake raw-decoder count too).
- O2 status correctness: rule-based classifier recovers the held-out record's
  status on >= 480/500 final sentences.
- O3 answer presence: held-out exact answer entity verbatim in the sentence
  for OK records >= 240/250.
- O4 time: training + scoring < 25 min wall-clock on Mac CPU
  (if not, cut data to 1,500 pairs and record it).
- O5 wire51 replay (scripts/fable_wire51_run.py with our Mouth swapped in via
  scripts/fable_mouth53_replay.py, wire51 untouched): 0 wrong writes and the
  same correctness counts as artifacts/fable-wire51-20260921/replay-report.json.

What it means / What it does not mean: these marks say the mouth repeats only
what the record says, in sentences whose status Ben can read back; they do not
say the mouth reasons, checks facts, or knows anything beyond the record.

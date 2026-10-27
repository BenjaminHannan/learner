# Experiment 120 (talker mouth fine-tune PREP) — PASSMARKS (sealed 2026-09-22)

PREP for the talker's second stage: teaching OUR OWN from-scratch talker
(exp 101: 28.85M decoder + copy head, SimpleStories-EN) to SAY notebook
answers faithfully. THE ONE CHANGE vs exp 53: the mouth decoder is our own
pretrained talker, not SmolLM2-360M. Same record shape, same brake design,
same rule-based status read-back, same O1–O5 bars.

Registered run: data seed 12001 (3,000 train pairs + 500 held-out records:
250 OK + 50 each of UNKNOWN / ABSTAIN / CLARIFY / SAVED / FORGOT; train and
test name/value pools disjoint), fine-tune seed 12002 (fresh; smoke used
12001), recipe: full-model AdamW lr 1e-4 cosine+warmup, 5 epochs, bs 32,
ctx 256, bf16 (BensPC GPU), resume from the finished exp-101 full-run
checkpoint. A registered FAIL stays a FAIL.

## Smoke gates (Mac CPU, prep only, seed 12001)
- S1: 100-step fine-tune from the latest STABLE talker101 checkpoint shows
  falling loss (mean of last 20 steps < mean of first 20 steps).
- S2: 20 held-out records greedy-decode end to end without crash (no marks
  scored; every case reported).

## Registered gates (GPU fine-tune + scoring)
- O1 faithfulness: violations on 500 held-out records = 0 AFTER the brake
  (report the BEFORE-brake raw-decoder count too).
- O2 status correctness: rule-based classifier recovers the held-out record's
  status on >= 480/500 final sentences.
- O3 answer presence: held-out exact answer entity verbatim in the sentence
  for OK records >= 240/250.
- O4 time: fine-tune + scoring < 25 min wall-clock
  (measured BensPC throughput 2026-09-22: ~49,000 tok/s on the live run;
  5 epochs over ~0.23M tokens ≈ 25 s compute + scoring + replay ≈ 5 min).
- O5 wire51 replay (scripts/fable_wire51_run.py with our TalkerMouth swapped
  in via scripts/fable_talker120_replay.py, wire51 untouched): 0 wrong writes
  and the same correctness counts as artifacts/fable-wire51-20260921/replay-report.json.
- O6 raw-decoder faithfulness (NEW vs exp 53): unfaithful BEFORE the brake
  <= 50/500 (<= 10 %; exp 53's borrowed decoder was 296/500 = 59 %).

What it means / What it does not mean: these marks say OUR talker repeats
only what the record says, in sentences whose status Ben can read back, with
the brake as the permanent safety net; they do not say the mouth reasons,
checks facts, or knows anything beyond the record.

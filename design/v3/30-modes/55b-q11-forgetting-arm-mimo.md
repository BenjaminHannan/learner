# 55b — Q11 forgetting arm: QA-drilled baseline, fixed 60 s fine-tune

Date: 21 Sep 2026. Prefix `fable_demo55b_`. Artifacts:
`artifacts/fable-demo55b-20260921/`. Script:
`scripts/fable_demo55b_forgetting.py` (NEW; imports demo55/modes54 code, edits
nothing).

## Why

Demo55's Q11 "equal wall-clock" fine-tune arm got only 1 gradient step (the
notebook's whole Q11 beat was ~1 ms, a step is slower) — a stunt, honestly
labelled as one. Worse, its baseline started at 0/20 on Q10, so there was nothing
to forget: the forgetting question was vacuous. This experiment gives the
baseline a real chance first (the QA-drilled variant from demo55's dev notes,
which tied 20/20), then fine-tunes it on the 5 new teaching lines for a fixed
60 s wall-clock — thousands of steps, no stunt — and re-asks both sets. If the
net keeps the old facts AND learns the new ones, the notebook's advantage
shrinks; if fine-tuning destroys the old mapping, that is on record too.

## Reuse (imports only, never edited)

- `fable_demo55_advantage` — Q10/Q11 lines+items, STORY10/STORY11, MAX_LEN,
  `build_vocab`, `make_rows`, `train_loop` (generic full-batch Adam, reused for
  QA training), `encode_lm`, `decode_preds` (+ reference-decoder cross-check),
  `score`.
- `fable_modes54_demo` — `norm`, `tokenize`, `detok`, `TinyTransformer`,
  `TRAIN_LR=1e-3` (QA update count is ours: see below).
- `fable_modes54_scheduler.ModeScheduler`, `fable_listening_m1.Listening`,
  `fable_notebook_contract.Notebook` — the same LISTENING path.

## Protocol (frozen, sealed in PASSMARKS.md)

- Notebook: teach 120 Q10 lines, ask 20 Q10 (before), teach 5 new lines, ask 5
  new + re-ask 20 old (after). Wrong-write rule = demo55's, across the whole run.
- Baseline per seed (5401/5402/5403): QA-supervised training, exactly 250 fixed
  full-batch updates (Adam lr 1e-3, grad-clip 1.0) on the 20 Q10
  story+question->gold rows (STORY10 prefix; modes54's batch/label format,
  re-implemented as `encode_qa_batch` since modes54's helper was inline in its
  `run_baseline`). Then: eval Q10-before (STORY10) + Q11-before (STORY11);
  fine-tune with fresh Adam lr 1e-3, full-batch next-token LM on the 5 new
  teaching lines, FIXED 60 s wall-clock; eval Q11-after (STORY11) + Q10-after
  (STORY10). Prompts identical before/after per set, so gaps isolate weights.
- 250 (not 600): dev pilot 5591 gave 18/20 at 200, 20/20 at 300 updates; 250
  balances a strong start against the <600 s budget (dev seed 5592 all-in:
  133.7 s, so 3 seeds ≈ 400 s). No performance bar on the baseline (B4 = report
  completeness only).

## Marks

B1 notebook old 20/20 after new teaching; B2 notebook new 5/5; B3 wrong writes 0;
B4 baseline (20+5+5+20) integers + cross-check per seed, no mark; B5 < 600 s.

## What it means / What it does not mean

- What it means: on this frozen script, whether a notebook keeps old answers
  after learning new facts, and what 60 s of fine-tuning does to a QA-drilled
  tiny transformer's old and new answers — the stated integers, these runs only.
- What it does not mean: not broad English, not GPU-scale training, not that
  fine-tuning always/never forgets, not learned mode switching; one script,
  three seeds, Mac CPU.

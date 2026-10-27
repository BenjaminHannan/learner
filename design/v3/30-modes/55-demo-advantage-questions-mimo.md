# 55 — Two added demo beats: many-facts two-hop (Q10) + learn-after-training (Q11)

Date: 21 Sep 2026. Prefix `fable_demo55_`. Artifacts: `artifacts/fable-demo55-20260921/`.
Script: `scripts/fable_demo55_advantage.py` (NEW; imports modes54 code, edits nothing).

## Why

The modes54 demo (`artifacts/fable-modes54-20260921/`) ties the notebook and a plain
104,832-parameter transformer at 8/9 on its 8 content questions; the notebook wins only
the self-report. Ben wants the demo (uncle + dad) to show a real, honest advantage on
content questions. Two beats, one new script, additive only.

## Reuse (imports only, never edited)

- `fable_modes54_demo` — `norm`, `tokenize`, `detok`, `TinyTransformer`,
  `greedy_decode`, and the budget constants `TRAIN_SEEDS=(5401,5402,5403)`,
  `TRAIN_UPDATES=600`, `TRAIN_LR=1e-3`.
- `fable_modes54_scheduler.ModeScheduler`, `fable_listening_m1.Listening`,
  `fable_notebook_contract.Notebook` — the same LISTENING path the demo already uses
  (structured English lines, clarify-or-write, hard-coded hop loop on `ask`).

## Beat Q10 — "many facts, two hops"

- Fresh notebook. Teach 40 uniquely named people, 3 relations each = 120 facts, as 120
  `teach` lines through ModeScheduler+Listening (same doorway as modes54; `teach`
  auto-creates entities, so no `person` lines are needed).
  Relations: `mother ->` (person), `boss ->` (person), `city =` (literal), built by a
  frozen deterministic rule (mother `i -> i+1 mod 40`, boss `i -> (7i+3) mod 40`
  (a bijection, never self), city `i mod 10` of 10 cities).
- Ask 20 frozen two-hop questions through the same path: 7 "boss of X's mother"
  (`ask X mother boss`), 7 "mother of X's boss" (`ask X boss mother`), 6 "where does
  X's mother live?" (`ask X mother city`). Notebook answers = the contract's hard-coded
  hop loop. Exact word match after `norm`.
- Baseline, per the beat's specification — trained on the same 120 teaching lines,
  asked the same 20 questions — under modes54's budget rule (restated in PASSMARKS
  and in the script): same TinyTransformer (2 layers, d_model 64, 4 heads, FFN 128,
  word vocab over all demo texts; positional table 512 -> 768 because the story is
  600 tokens — stated deviation), ONE full-batch next-token sequence over the exact
  120 teaching lines the notebook heard, full-batch Adam lr 1e-3, grad-clip 1.0,
  exactly 600 updates, seeds 5401/5402/5403 reported separately, greedy decode
  <= 8 tokens, exact match. The 20 questions appear only at evaluation (prompt =
  story + SEP + question + SEP), never in training.
- Development note (pre-seal, disclosed): a variant that applied modes54's
  QA-supervised rule to the 20 pairs (story + question -> gold as training rows) was
  run on dev seeds 5591/5592/5593 before PASSMARKS was sealed and memorized all of
  them (20/20/20, tie with the notebook). That variant is NOT the registered
  protocol — the beat specifies training on the teaching lines — but its integers
  are reported in RESULTS.md so the memorization fact is on record and nothing is
  hidden.
- Marks: A1 notebook >= 18/20; A2 baseline integers reported for all 3 seeds (Q10
  20, Q11 frozen 5, Q11 fine-tuned 5) with a greedy-decode cross-check against the
  modes54 reference decoder on one row per seed — no performance threshold on A2.

## Beat Q11 — "learn after training"

- After both systems are done: teach 5 brand-new facts (5 new names not in the 40)
  through LISTENING, then ask 5 questions about them.
- Notebook: writes them (raw-line checked) and answers via lookup/hop -> mark A3 =
  5/5.
- Baseline, two reported variants, per seed:
  1. **Frozen** — not retrained. A frozen net cannot learn from one sentence; the new
     name tokens exist in the pre-built vocab (modes54 builds vocab from all demo
     texts) but their embeddings were never updated.
  2. **Fair wall-clock variant** — fine-tuned (fresh Adam lr 1e-3, full-batch
     next-token LM on the 5 new teaching lines) until wall-clock >= the time the
     notebook's Q11 beat needed (minimum 1 update; a step may overshoot). Steps and
     elapsed reported.

## A4 — wrong writes (counted across the whole demo)

A wrong write = (a) a `teach`/`correct` line that did not save exactly one fact whose
stored `raw` differs from the line, or (b) any line other than `teach`/`correct` that
saved a fact. Counted for every turn of both beats; mark A4 = 0.

## A5 — runtime

The whole added-demo registered invocation (notebook + 3-seed training + both Q11
variants) must run in < 600 s wall-clock (shell `time`) on the Mac CPU with
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`. Eval uses a batched greedy decoder proven
token-identical to modes54's per-row decoder (cross-checked per seed, folded into A2).

## Procedure

PASSMARKS.md sealed (sha256) before the registered run; predictions appended to
`artifacts/fable-predictions-ledger.md` before the run (P228+) and outcomes after;
one registered invocation, stdout saved; every seed reported, never averaged; a
registered FAIL is recorded as FAIL.

## What these marks can / cannot support

- Can: "on this frozen script the notebook answers 120-fact two-hop questions and
  five just-taught facts, under a stated budget, while this plain transformer —
  trained on the identical 120 sentences under the identical budget — scores the
  integers reported."
- Cannot: broad English, GPU-scale training, any claim beyond these runs; not that
  transformers cannot be QA-tuned into parrots of a short script (modes54's tie and
  the disclosed dev-seed QA variant both say they can); not learned mode switching.

## Anticipated deviations (all stated in RESULTS)

- Positional table widened 512 -> 768 (story length); vocab includes a reserved
  `<UNK>` id (modes54 had none) — expected unused, counted if hit.
- Fine-tune gets >= 1 update even if the notebook's Q11 wall-clock is shorter than
  one optimizer step.

# 55 — Added demo beats (Q10 two-hop, Q11 learn-after-training) — PASS MARKS (sealed BEFORE the registered run)

Written 21 Sep 2026 before the registered run of `scripts/fable_demo55_advantage.py`.
Hashed in `SEAL.sha256.txt`. Development runs (this file's authors used notebook-only
checks and dev seeds 5591/5592/5593 while writing the code) are not registered runs.
The REGISTERED run is the single clean invocation recorded in RESULTS.md, run after
this file is sealed and the script source is frozen (sha256 recorded in RESULTS.md).
A registered FAIL is reported as FAIL and is never re-run into a pass. Every seed is
reported separately, never averaged.

## The frozen experiment

One script, one fresh notebook, two beats, additive only (modes54 files are imported,
never edited):

**Q10 — "many facts, two hops."** Teach 40 uniquely named people, 3 relations each =
120 facts, as 120 frozen `teach` lines through the same LISTENING path as the modes54
demo (ModeScheduler + Listening + notebook contract; `teach` auto-creates entities).
Relations built by frozen rule: `mother ->` person `i+1 mod 40`, `boss ->` person
`(7i+3) mod 40` (bijection, never self), `city =` `i mod 10` of 10 cities. Then ask 20
frozen two-hop questions through the same path: 7 `ask X mother boss` ("Who is the
boss of X's mother?"), 7 `ask X boss mother`, 6 `ask X mother city` ("Where does X's
mother live?"). Notebook answer = the contract's hard-coded hop loop. Score = exact
word match after normalization (`norm`: lowercase, `[\w<>]+`). Golds fixed in the
script now.

**Q11 — "learn after training."** After both systems are finished: teach 5
brand-new facts (5 new names: Kip, Lark, Moth, Nyx, Opal — none among the 40) through
LISTENING, then ask 5 questions. Notebook writes them (raw-line checked) and answers.
Baseline reported twice per seed: **FROZEN** (zero updates after Q10 training) and a
**fair wall-clock variant** fine-tuned for at least the wall-clock the notebook's Q11
beat needed (10 turns: 5 teachings + 5 asks, timed in-script; minimum 1 optimizer
update; a step may overshoot that wall-clock — stated here as part of the rule).

## The baseline budget rule (frozen; restated from modes54, "(state that rule)")

- Model: modes54's `TinyTransformer` — 2 layers, d_model 64, 4 heads, FFN 128,
  word-level vocab over all demo texts + specials `<PAD> <SEP> <EOS> <UNK>`, plain
  PyTorch, CPU only. Positional table widened 512 -> 768 so the 600-token story fits
  (stated deviation from modes54's default; parameter count reported).
- Q10 training: ONE full-batch next-token sequence over the byte-identical 120
  teaching lines the notebook heard (labels = ids; CE shift predicts t+1), Adam
  lr 1e-3, grad-clip 1.0, exactly **600 fixed updates**, seeds **5401 / 5402 / 5403**
  reported separately and never averaged. The 20 questions are **never trained on**.
- Evaluation (both beats): prompt = story-so-far + `<SEP>` + question + `<SEP>`;
  greedy decode <= 8 answer tokens (batched decoder proven token-identical to modes54's
  per-row decoder, cross-checked on one row per seed); exact match after `norm`.
- Q11 frozen = zero updates. Q11 fine-tune = fresh Adam lr 1e-3, full-batch
  next-token LM on the 5 new teaching lines, updates until wall-clock >= the
  notebook's Q11 beat (minimum 1 update); steps and elapsed reported per seed.
- Training loss is not a score; only exact-match integers count.

## Marks

| # | mark | threshold |
|---|---|---|
| A1 | notebook correct on Q10's 20 two-hop questions | >= 18/20 |
| A2 | baseline integers reported per seed: Q10 20, Q11 frozen 5, Q11 fine-tuned 5, all seeds present, decode cross-check ok | 3/3 seeds complete — **no performance threshold** (the baseline's score is reported, never required to be low) |
| A3 | notebook correct on Q11's 5 just-taught facts | 5/5 |
| A4 | wrong writes to the notebook across the whole demo (rule: a `teach`/`correct` line must save exactly one fact whose stored `raw` equals the line; any other line must save zero facts) | 0 |
| A5 | whole added-demo registered invocation wall-clock (shell `time` around the python command) | < 600 s (10 minutes) on the Mac CPU with `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` |

Outcome integers (described, no threshold — reported whatever happens): notebook
Q10 correct /20; baseline Q10 correct /20 per seed; notebook Q11 /5; baseline Q11
frozen and fine-tuned /5 per seed; per-question table including every question the
baseline ties or wins.

## What the marks can and cannot support

- A1+A2 support: "on this frozen script the notebook answers >= 18 of 20 two-hop
  questions over 120 taught facts; the plain transformer trained on the identical 120
  sentences under the identical 600-update budget scores the integers reported."
- A3 supports: "after training was finished, the notebook learned 5 brand-new facts
  from 5 sentences and answered 5/5; the baseline's frozen and equal-wall-clock
  integers are on record."
- A4 supports: "every notebook write in this demo was exactly what the teaching line
  said." A5: a systems fact about this Mac run.
- Nothing here supports broad English, GPU training, learned mode switching, or any
  claim beyond these runs. Nothing claims a transformer cannot be QA-drilled to
  recite a script (modes54's tie stands; see RESULTS.md's disclosed development
  variant).

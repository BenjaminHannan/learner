# 55b — Q11 forgetting arm (QA-drilled baseline, fixed 60 s fine-tune) — PASS MARKS (sealed BEFORE the registered run)

Written 21 Sep 2026 before the registered run of `scripts/fable_demo55b_forgetting.py`.
Hashed in `SEAL.sha256.txt`. Development (notebook-only smoke to /tmp, QA-timing
pilots on dev seeds 5591/5592 while writing the code) is not the registered run.
The REGISTERED run is the single clean invocation recorded in RESULTS.md, run after
this file is sealed and the script source is frozen (sha256 recorded in RESULTS.md).
A registered FAIL is reported as FAIL and is never re-run into a pass. Every seed is
reported separately, never averaged.

## The frozen experiment

One script, one fresh notebook, additive only (demo55/modes54 files imported, never
edited). Same 120 Q10 teaching lines, same 20 Q10 questions, same 5 new Q11
teaching lines and 5 new questions as demo55 (imported from
`fable_demo55_advantage`, byte-identical).

**Notebook:** teach 120 Q10 facts through ModeScheduler+Listening, ask the 20 Q10
questions (before), teach the 5 new facts, then ask the 5 new questions AND re-ask
the 20 old questions (after). Score = exact word match after `norm`.

**Baseline (registered third arm):** the QA-drilled variant from demo55's dev notes
(the one that tied 20/20: story+question->gold rows, modes54's supervised rule).
QA-supervised training = exactly **250 fixed full-batch updates** (Adam lr 1e-3,
grad-clip 1.0) on the 20 Q10 pairs (STORY10 prefix). Then per seed a THIRD arm:
fresh Adam lr 1e-3, full-batch next-token LM on the 5 new teaching lines, for a
FIXED **60 s wall-clock** (steps counted, reported). Then ask (a) the 5 new
questions (STORY11 prefix, as in demo55) and (b) the 20 old Q10 questions again
(STORY10 prefix — identical prompt as before fine-tune, so only weights change).
Seeds **5401/5402/5403**, greedy decode <= 8 tokens, exact match after `norm`.

Why 250 QA updates (not 600): dev-seed pilot (5591, pre-seal) reached 18/20 at 200
and 20/20 at 300 updates; 250 balances a strong starting point against the <600 s
total budget (single-seed dev run 5592: 133.7 s all-in, so 3 seeds ≈ 400 s).
There is NO performance bar on the baseline — whatever it scores is reported.

## Marks

| # | mark | threshold |
|---|---|---|
| B1 | notebook correct on the 20 OLD Q10 questions AFTER the 5 new facts are taught | 20/20 |
| B2 | notebook correct on the 5 NEW questions | 5/5 |
| B3 | wrong writes to the notebook across the whole run (demo55's rule: `teach`/`correct` -> exactly one new fact whose stored `raw` equals the line; any other line -> zero new facts) | 0 |
| B4 | baseline integers reported per seed: Q10 before 20, Q11 before 5, Q11 after 5, Q10 after 20, all seeds present, decode cross-check ok | 3/3 seeds complete — **no performance threshold** (forgetting gap reported, never required) |
| B5 | whole registered invocation wall-clock (shell `time` around the python command) | < 600 s (10 minutes) on the Mac CPU with `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` |

## What the marks can and cannot support

- B1+B2 support: "on this frozen script the notebook still answers 20/20 old
  questions after learning 5 new facts, and 5/5 new." B3: "every notebook write
  was exactly what the teaching line said." B5: a systems fact about this Mac run.
- B4 supports only: "the QA-drilled baseline scored the reported integers before
  and after 60 s of fine-tuning on the 5 new lines." Any forgetting gap is evidence
  about THESE runs only.
- Nothing here supports broad English, GPU training, learned mode switching, or any
  claim beyond these runs.

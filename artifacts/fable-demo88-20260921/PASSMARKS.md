# 88 — Demo rehearsal transcript — PASS MARKS (sealed BEFORE the registered runs)

Written 22 Sep 2026 before the registered runs of `scripts/fable_demo88_rehearse.py`.
Hashed in `SEAL.sha256.txt`. Development (notebook-only smokes to scratch dirs
while writing the code) is not a registered run. The REGISTERED runs are the three
clean invocations recorded in the design report (1 full + 2 fast), run after this
file is sealed and the script source is frozen (sha256 recorded in RESULTS.md).
A registered FAIL is reported as FAIL and is never re-run into a pass. Every seed
is reported separately, never averaged.

## The frozen experiment

One new script, additive only (55b/55/modes54 files imported, never edited):

- Act 1 (family scene, fresh notebook, same LISTENING doorway): teach -> ask ->
  correct -> ask (Mira/Ana family, 8 turns: 3 teachings, 1 correction, 4 asks
  incl. one honest abstention about Tom).
- Acts 2+3 (the evidence): the 55b comparison byte-for-byte — notebook teaches the
  same 120 Q10 facts, answers the same 20 two-hop questions, teaches the same 5
  new Q11 facts, re-answers old plus new. Baseline = the 55b QA-drilled protocol
  (250 supervised updates on the 20 Q10 pairs, then fixed 60 s fine-tune per seed
  on the 5 new lines, seeds 5401/5402/5403, greedy decode <= 8, exact match).
- Fast mode = `--skip-baseline` (notebook only; transcript says the comparison
  was skipped). Full mode = with baseline.
- Output: `transcript.md` (Ben:/Agent: transcript, notebook status after each
  turn in plain words, timings, scoreboard copied from the run JSON and asserted
  equal, <= 150-word plain-English explanation) plus `fable-demo88-results.json`.

## Marks

| # | mark | threshold |
|---|---|---|
| V1 | fast mode wall-clock (shell `time`) | < 60 s on the Mac CPU with `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` |
| V1 | full mode wall-clock (shell `time`) | < 900 s (15 min) on the same setup |
| V2 | wrong answers by the notebook side in the transcript (Act 1 asks + 20 old-after + 5 new; teachings excluded) | 0 |
| V3 | transcript scoreboard numbers equal the run JSON exactly (asserted in-script) | exact |
| V4 | transcript reads without code, JSON, or status codes (in-script audit over a frozen forbidden-token list; statuses translated to words) | audit clean |

## What the marks can and cannot support

- V2+V3 support: "in this rehearsal the notebook answered every shown question
  correctly, and the printed scoreboard is exactly what the run JSON holds."
- V4 supports: "a non-technical reader can read transcript.md with no code."
- Nothing here supports broad English, GPU training, or any claim beyond these
  runs. The forgetting numbers are 55b's protocol re-run as a demo, not new
  evidence about fine-tuning in general.

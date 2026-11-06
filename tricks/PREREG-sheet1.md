# Sheet-1: does a Claude-written instruction sheet make the 4B smarter? (pre-registered 2026-10-24, before any run)

Test 3 on the RANKING.md "next cheap tests" list. One change only: the system prompt ("instruction sheet").

## Setup
- Model: Qwen3.5-4B, thinking off, greedy, `python` tool for up to 4 rounds (the final round offers no tool), 2048 tokens per turn.
  Same harness as the Tricks-1 `s_py` arm (`tricks1.run_tool_loop`). User message unchanged: question + "End with 'Final answer: <number>'."
- Questions: the 300 GSM-Hard rows of Tricks-1 (`build_sets(seed=0)`), split once with `random.Random(1)` into 100 train and
  200 test (`tricks/sheet1_data.json`). Claude never sees a test question.
- Baseline sheet: `PY_SYS` (Tricks-1: 66.3 plain, 67.3 with the tool, on all 300).
- Candidates: Claude (claude-opus-5-5) reads the 4B's saved Tricks-1 `s_py` outputs on the 100 train rows (all failures, 8
  successes) and writes 6 general sheets with different strategies, in one call (`tricks/sheet_candidates.py`, saved as
  `tricks/sheets1.json` before the GPU run).
- On the GPU: all sheets on train and test. The best candidate is chosen on **train only** (accuracy, then fewer tokens,
  then lower index).

### Amendment before any GPU run (08:55Z): two sets of sheets
The first sheet-writing prompt told Claude that GSM-Hard's gold "can be negative, fractional or implausible", and all six sheets
leaned on the same rule ("compute literally, never clamp or round"), which mostly teaches the benchmark's label quirks.
That set is kept as **quirk** (`sheets1_quirk.json`, exploratory only). The **primary** set (`sheets1.json`, `--variant general`)
was written from the same failures with one change: Claude is told some golds are odd or wrong and asked not to write rules aimed
at matching them, but to make the model a better solver of ordinary word problems. Only the 6 general sheets are eligible for the
primary pick; the best quirk sheet (picked on train among the quirk six) is reported against the baseline and against the best
general sheet as exploratory. No GPU results existed when this was decided.

A code review then noted that the general sheets still say "do not round unless asked; take the numbers at face value", which
can also help on odd golds. Added before the run, also fixed now: the primary diff and paired CI are reported again on the test
rows whose gold is a non-negative whole number ("normal-gold rows", 133 of 200). **A PASS that gains less than +2.0 points on the
normal-gold rows is reported as quirk-driven, not as a real skill gain.** Flipped question ids (wrong to right and right to
wrong) are saved so the 20-question read-through can be done. Over-long conversations (prompt over 12,256 tokens) are stubbed as
wrong instead of crashing the batch, and their count is reported.

## Pass marks (fixed now)
- Primary: best-on-train sheet minus baseline, on the 200 test questions, paired bootstrap 95% CI (2000 resamples).
  - **PASS**: ≥ +5.0 points and CI lower bound > 0.
  - **OUT**: < +2.0 points.
  - Otherwise **INCONCLUSIVE**.
- What would prove it wrong: the chosen sheet gains on train but gains < 2 points on test (it fit the 100 train questions,
  not the skill).
- Secondary (exploratory, labelled as such): every sheet's test accuracy and token cost; whether the best sheet reaches the
  plain Qwen3.6-35B's accuracy on the same 200 test questions (from the saved Tricks-1 `b_plain` rows, a different run).

## Known limits
- GSM-Hard has some wrong gold answers (numbers were swapped in without re-checking the story). Both arms face the same labels,
  but a sheet could gain by matching label quirks (e.g. "never round"). We will read the 20 questions the best sheet flips
  from wrong to right and report how many look like real fixes.
- One sheet-writing call, no iteration (the GEPA-style loop would need several GPU rounds). A PASS here is a lower bound.
- The 4B is the worker. If it passes, the same sheet is tried on the LFM2.5 boss on the Mac later; that is a separate test.

## Cost
- Claude: two calls (~11k tokens in, ~2k out each). GPU: one small box or Ben's PC, ~30 min, cap $0.50 (coordinator OK 08:42Z).

# Pass marks: can the learned reasoner combine recalled facts (dates and multi-part questions)?

Written 2026-09-28 21:25 UTC (`date -u`) by Director helper HB, **before any run they judge**. Nothing has been trained or scored on these panels; this box has no torch (only the generator, the checker and the marks arithmetic were run here). These marks are not changed after any score is seen. If one turns out badly chosen, the run is reported as it stands and a new test with a new addendum follows; nothing is re-scored.
Design: `DESIGN.md` (same folder). Code: `scripts/claude_dir_hb_kinds.py` (items, checker, selftest), `scripts/claude_dir_hb_run.py` (nets, training, eval), `scripts/claude_dir_hb_marks.py` (gate and score arithmetic).

## What is being judged

Claim under test (label: **untested**): *given the recalled facts as tokens, a learned looped reasoner answers date questions (how many days between, what date is N days after, which came first) and multi-part questions (joins, sets, counts, and two or three questions in one) more often than a plain same-size network with the same practice, and well enough to be worth building on.*
Reference point, from a different test (**shown**, `artifacts/claude-bm398d-20260926/RESULTS.md` lines 75-76): a plain 1B reading only the right chat lines is right on 17.2% of date questions and 22.6% of multi-part questions, against 65.9% on single facts. **That is not this test** (other questions, real LoCoMo text, a language model reading words). It is only why the bars below are set at half.

Four training runs: loop and plain, each with seeds 0 and 1. Same practice stream (code-made, never repeated, panel items dropped), same steps, batch, learning rate and schedule. Loop: 2 shared layers, width 512, learned stop, cap 48 rounds. Plain: 8 layers, width 256. Both about 6.3M weights. No question-kind input to either net.
Four panels, 300 items each, made by code from fixed seeds (`DEV_BASE 9601000`, `HOLD_BASE 9602000`), disjoint from practice by canonical key:
- **s0** one recall question ("when did X do Y"), 8-12 facts. The control.
- **s1** one date question (DIFF, PLUS, DIFFT, FIRST), 8-12 facts.
- **s2** multi-part: half one multi-fact question (JOIN, SETM, COUNT, COUNTM), half two or three questions of any kind in one item; 8-12 facts.
- **s3** bigger stores, 16-20 facts (practice used 6-12), half single questions, half two or three; all kinds.
An item counts as right only if **every** answer cell is right (every part of every question). Counts are "x of 300".

## Validity (failure = INCONCLUSIVE, the holdout stays unopened, nothing is tuned against it)

- **V0 generator selftest** (`python3 -B scripts/claude_dir_hb_kinds.py selftest` prints `selftest ok`; run here, log `SELFTEST-kinds.log`): checker re-derives every answer from the tokens and agrees with the stored target on 1,500 items; a one-cell change is always rejected; dates agree with Python's calendar; no key shared between dev, holdout and 3,000 practice draws; the three wrong-by-design predictors (first row's date, latest date, argument-token match) score at most 45 of 300 on every dev and holdout panel of s1, s2, s3.
- **V1 recall control** (dev panel s0): loop at least **270 of 300** and plain at least **200 of 300**, in both seeds. If a net cannot even look up "when did X do Y" the practice did not work and the comparison says nothing about combining.
- **V2 live gradients** (`claude_dir_hb_run.py selftest`, needs torch): every 2-D matrix gets a nonzero gradient in one step for both arms; padding rows do not change an answer.
- Only when `DEV-GATE.json` says PASS (dev V1 in both seeds) may the holdout be scored, once per checkpoint (a `.started` marker refuses a second run), no model or recipe selection after.

## Marks (holdout, each seed judged separately, seeds never pooled; every bar inclusive)

| Mark | Requirement in each of seeds 0 and 1 |
|---|---|
| **M1 it combines** | loop at least **150 of 300** on s1 and on s2 |
| **M2 it beats its twin** | loop minus plain at least **+30** on s1 and on s2 |
| **M3 bigger stores** | loop at least **120 of 300** on s3, and loop minus plain at least **+15** on s3 |
| **M4 recall kept** | loop at least **270 of 300** on s0 |

**Verdict:** PASS when M1, M2, M3, M4 all hold in both seeds. REFUTED-cannot-combine when in both seeds the loop is below **60 of 300** on s1 or on s2. REFUTED-no-better-than-plain when in both seeds the loop is at or below plain on s1 or on s2. Anything else: NOT-SHOWN. (`claude_dir_hb_marks.py selftest` checks every bar at its edge.)

## Why these numbers

- Noise: 300 items near 50% has a counting standard error of 2.9 points (about 9 items); a difference of two arms about 4.1 points (about 12 items). Seeds of the same arm differed by up to 2.5 points in the race data (`claude-dir-h1-heldout-20260928/PASSMARKS.md`).
- **+30 items (10 points)** is about 2.4 counting standard errors of a difference, needed in both seeds and both panels (four separate looks). Earlier loop-versus-plain gaps: +144 of 300 (sums, grids bigger) and +41 of 300 (roadmap table, 4 seeds), so 30 is real but not a copy of them.
- **150 of 300** is twice the plain 1B's rate on dates (17.2%) and multi-part (22.6%) in bm-398d and a bit under its single-fact rate (65.9%). Half is a claim worth a build; it is not a claim of beating anything yet.
- **120 of 300, +15** on bigger stores is lower on purpose: the store is 60-100% larger than practice, and the roadmap asks that a gap does not vanish with size.
- **270 of 300 (90%)** for recall: it is a lookup with 8-12 rows and one match.
- **60 of 300 (20%)** for "cannot combine": about the 1B's own combining rate.

## Predictions (guesses, not evidence; registered before any run)

| # | Guess | Confidence |
|---|---|---|
| P1 | V1 passes (recall learned by both arms in both seeds) | 80% |
| P2 | Loop s1 (dates) lands 40-80% (120-240 of 300); the digit-by-digit date arithmetic is the hard part | 50% |
| P3 | Loop s2 (multi-part) is higher than loop s1, because filtering and counting are content matches | 60% |
| P4 | M2 holds in both seeds | 55% |
| P5 | Overall PASS | 30% |
| P6 | The loop's ranking over plain shrinks on s3 (bigger stores) | 60% |

## The result that would prove the claim wrong

Stated in advance, on a run whose V1 passed:
1. **REFUTED-cannot-combine**: a learned looped net that recalls perfectly but is below 20% on dates or multi-part in both seeds. Then combining recalled facts is not what this reasoner is good at, at this size and practice, and "add a calculator for the arithmetic" or "another reasoner idea" becomes the next single change (Ben's goals page: silicon may improve on biology for arithmetic). That is a next test, not a claim.
2. **REFUTED-no-better-than-plain**: no advantage over the twin in both seeds. Then this is a data or practice effect, not a loop effect.
3. **Recall passes, dates fail, multi-fact passes** (M1 fails only on s1): reported as "the loop filters and counts but cannot do calendar arithmetic". Also counts against the claim as worded.
4. **Fine on s1/s2, collapse on s3** (M3 fails only): reported as size-bound; the claim then holds only for the practised store size.

Not evidence for the claim: any pooled-seed win; a PASS on a run whose V1 failed; scores on the dev panel; s0 alone; the wrong-by-design predictors.

## Reported for every arm and seed, never gating

Every panel as "x of 300"; per-question-kind part accuracy (`parts_by_op`); loop mean rounds, cap hits, accuracy at fixed rounds (1, 2, 4, 8, 16, 32, 48) and at any round versus the learned stop; weights (printed by the selftest); training minutes; the three baseline scores per panel. Sleep, the reader and the talker are **not** part of this test (**untested** here).

## What this test does NOT show (say it plainly)

- **Scaffolding:** the reader is replaced by code, which hands over the facts as tokens with the person, activity, date and question already split out. A chat reader that makes those tokens from real text is **untested** here (lis-320 is the piece for that; Ben's rule allows a disclosed stand-in for a single learned part).
- The panels are code-made stores of fictional people and activities, not LoCoMo or any real chat. Comparison with the 1B on LoCoMo (bm-398d) is **untested**; `claude_dir_hb_kinds.py panels` also writes the same items as plain-English chat lines and questions with canonical answers (test-only, code-templated) so plain 1B/2B models can be run on the same items in a later step.
- Practice is code-made only. Nothing here is Claude-written or Claude-judged training data, and nothing trained on MMLU-Redux, GSM8K or LongMemEval.
- No hand-written rule answers a question inside the net or the scorer; the checker's derivation is the ruler only. The op words, the flag cells and the answer columns are a fixed interface (disclosed).

# Probe-1: write the test first, then pick the try that passes it

Fixed 2026-10-26, before any probe is written or scored. Thread "Make the creative model work". Follows Pick-1
(K2 self-judge 34.4% vs random 19.7%) and Pick-2 (PROVED WRONG: more tool output or thinking did not help). Pick-2's
prereg named the next route: a check that actually runs against the end state, not a judge reading a transcript.
Small card/village models are not involved. Labels in reports: shown / suggested / untested.

## Question
Before seeing any try, K2 writes a few end-state checks ("tests") from the user's request alone. Each of the 12 tries is
replayed in the sandbox and the checks are run on its end state. Does picking the try that passes the most of K2's own
checks find a winning try more often than K2's self-judge?

## Data (unchanged from Pick-1)
The same 192 pools (48 Guess-1 target tasks x arms IND, MENU x seeds 1, 2), 12 tries each, 2,304 transcripts.
Pick-1's SELF scores (K2 P(yes)) are reused as given.

## Method
1. Replay: each try's tool calls are applied in order to a fresh `World` built from the task's start state, and its
   final reply is kept. Sanity gate (not a result): the real task checks on the replayed state must reproduce each
   try's recorded `success` for >= 99% of the 2,304 tries; otherwise stop and fix replay.
2. Probe writing: K2-Horizon-3.7B (thinking off, same serving as Guess-1) sees only: today's date, the user's request,
   the tool list, and a description of the check language (the sandbox's check types and keys, with their meaning). It
   is asked for 2-6 checks, as JSON, that would all be true if and only if the job was done right. 4 samples per task at
   temperature 0.7 (48 x 4 = 192 calls). It never sees any try, the task's reference plan, its rubric, or its checks.
   Probes that fail the sandbox's own check validator are dropped and counted.
3. Score of a try = mean over the 4 samples of (valid probes passed / valid probes in that sample); a sample with no
   valid probe is skipped; a task with no valid probe at all gets score 0.5 for every try.
4. Pickers on each pool:
   - PROBE-S (primary): highest probe score, ties broken by Pick-1 SELF score.
   - PROBE-R: highest probe score, ties broken at random (seed 0).
   - HAIKU-PROBE (reference only, does not decide): same, with probes written by Claude Haiku via the Batches API.
   Baselines from Pick-1: RAND 19.7, VOTE 22.4, SELF 34.4 (% of 192 pools).

## Pass marks (fixed now)
- P1: PROBE-S pick rate >= SELF + 5 points (>= 39.4%).
- P2: AUROC of the probe score for telling successful tries from failed ones, over all 2,304 tries, >= 0.75
  (SELF was 0.692).
PASS = P1 and P2. PROVED WRONG: PROBE-S <= SELF + 1 point (<= 35.4%). Anything else INCONCLUSIVE.

## Diagnostics (reported, do not decide)
- Probe validity rate; checks per sample.
- Reference agreement: share of valid probes that pass on the end state of the task's reference plan (a probe that
  fails the reference is a wrong test, not a picky one).
- How often the probes are uninformative (all 12 tries tie).

## If it passes
Probe-then-pick becomes the picker for the "many guesses" route, and the next test adds it on top of Guess-1's 12 tries
on fresh tasks (end-to-end success rate vs IND's single try and vs SELF picking). If proved wrong, the small model cannot
write its own tests here, and the creative route goes back to training (guess-list / set reward).

## Cost
192 short K2 generations (one T4, minutes) plus CPU replay. Haiku reference batch about 192 short calls (cents).

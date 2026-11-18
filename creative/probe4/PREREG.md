# Probe-4: many guesses + trained tests, end to end, on brand-new jobs

Fixed 2026-10-27 ~14:35Z, before any new task is generated or any try is run. Follows Probe-3 (PASS: K2 tuned on
Haiku's tests picks a winning try 48.4% of 192 pools vs self-judge 34.4%, on Guess-1's 48 target tasks; caveat: same
task generator as the training tasks). Question: on jobs from a different generator, does "12 tries, then pick with
K2's own trained tests" beat K2's single answer, and beat picking without the trained tests?
Small card experiments and the village model are not involved. Labels: shown / suggested / untested.

## New jobs (frozen before any K2 run)
- 120 tasks written by Claude Sonnet through the Batches API in the sandbox's task format (state, user, checks,
  reference plan, reference reply), asked for scenario families and wording unlike the 420 existing tasks (it sees only
  3 format examples and a list of the existing scenario names to avoid copying), about 40% traps (ambiguous person or
  file, irreversible action needing confirmation, a request that should be refused or clarified).
- Kept only if: every check passes the sandbox validator; the reference plan replayed in the sandbox passes all its
  checks; for traps, a literal "just do it" plan written by the same call fails at least one check. Drop the rest; if
  fewer than 80 survive, generate more with the same prompt until 80-120. The task file is committed (hash in RESULTS)
  before any K2 try runs.

## Runs (Ben's M3, MLX, K2-Horizon-3.7B bf16, thinking off, same tool list and system prompt as Guess-1)
- 12 plain tries per task (T0.7, top_p 0.95, up to 6 turns), all saved.
- Pickers on each task's 12 tries:
  - FIRST: try 1 (what the assistant does today: one guess).
  - RAND, VOTE (most common plan signature), SELF (K2 P(yes) judge as in Pick-1).
  - TEST-B: untuned K2 tests (Probe-2 prompt, sees start state, 4 samples), ties by SELF.
  - TEST-T (primary): K2 + Probe-3 LoRA tests, same prompt and settings, ties by SELF.
- Oracle (any of 12 passes) reported as the ceiling.

## Metric
End-to-end success = the picked try passes all the task's checks. Per task, then the share of tasks.

## Pass marks (fixed now)
- E1: TEST-T >= FIRST + 10 points.
- E2: TEST-T >= SELF + 5 points.
- E3: TEST-T >= TEST-B + 5 points (the training, not just the idea, transfers).
PASS = E1-E3. PROVED WRONG: TEST-T <= FIRST + 3 points. Otherwise INCONCLUSIVE.
Also reported: traps vs non-traps separately; generated tokens per picker (the 12 tries and the tests cost extra
compute; this test asks whether the extra compute buys success, not whether it is free).

## Cost
Claude Sonnet batch for tasks (~$1-2). M3: 120 x 12 tries (estimate 3-6 h) + 2 x 480 test generations (~1 h) + SELF.

## Addendum 1 (2026-10-27 ~15:20Z, before any task is generated)
- Generation prompt also gives each request a short everyday domain hint (landlord, restaurant, wedding, ...) to
  spread topics; the generator still sees only 3 format examples and the 8 existing scenario names.
- Sonnet on this account rejects `thinking: disabled` and temperature, so default sampling is used.
- Runtime estimate for 120 tasks is 8-10 h on the M3, beyond one overnight slot, so the kept set is capped at 96
  tasks (about 38 traps / 58 plain, same 40% split), chosen by the validator's fixed rule. Pass marks unchanged.

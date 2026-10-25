# Sleep-B addendum 14: two-step answers to 95% on K2 (written 2026-10-25 ~20:45Z, before the code, the probe and any run)

Labels: shown / suggested / untested. Model K2-Horizon-3.7B (bf16 base), Week-2 world, seed 1, the adopted recipe (ab_ob_b4_nb) exactly as
addendum 11c's k2s_bf16 run except for the flags below. Not the village model, not the card experiments.

## Why
Ben (2026-10-25 ~20:15Z) set the goal: two-step (two-hop) answers at 95%. Two-hop questions join two facts ("Where does the mentor of
Kizibra live?"), asked with the notebook closed, answered without thinking (score_week, weights mode, as in every addendum).

What the runs so far show (Week-2, 78 two-hop questions; "dreamed" = a kept REM chain dream covers both of the question's facts):

| run | two-hop right | dreamed | right when dreamed | REM pool at night 7 (chain dreams) |
|---|---|---|---|---|
| Qwen3.5-2B nb, seed 1 (addendum 9) | 30 | 32 | 30 (94%) | 375 (87) |
| Qwen3.5-2B nb, seed 2 | 28 | 28 | 27 (96%) | 397 (85) |
| Qwen3.5-2B nb x4, seed 2 (addendum 10) | 47 | 53 | 46 (87%) | 532 (217) |
| Qwen3.6-35B-A3B, 4-bit base (addendum 12) | 53 | 74 | 53 (72%) | 669 (375) |
| K2-3.7B bf16 (addendum 11c) | 3 | 5 | 3 | 14 (9) |

- **Shown:** not-dreamed questions are answered 0-4% of the time, so two-hop is about (share dreamed) x (right when dreamed).
- **Shown:** K2 keeps almost no chain dreams. With its think block closed it writes only the "Question:" line or only a name, so 3,311
  of its chain and gist replies failed to parse.
- **Shown (offline, from the k2s_bf16 JSON):** at the end of the week, 77 of the 78 test chains are reachable from K2's own eligible
  notes (both facts present, sharing the middle name); Qwen3.5-2B reaches 70. So 95% (75 of 78) is possible only on K2.
- **Suggested:** "right when dreamed" falls as the REM pool grows (94-96% -> 87% -> 72%) while REM steps stay at 510 a night. The pool
  is spread over more dreams (less rehearsal each), and the wrong answers are other names of the world (interference). Different models
  and arms, so suggested only.

## Step 0: generation probe (no training, Week-1 world only; k2_chain_probe.py)
K2 base, Week-1 days 1-7 tagged and names-passed as in a night (no dreams, no training). REM is then run 4 cycles at day 7 on the
eligible items, with `--rem-dirs both` (below), under four chain-prompt variants:
- `default`: today's bridge_prompt (Question + Answer), think block closed;
- `q`: the same facts, start, answer and middle name, but "Reply with only the question" (the answer is the given far end);
- `think`: bridge_prompt with K2's high-effort think block open (at most 512 tokens), then the Question + Answer reply;
- `q_think`: `q` with the high-effort think block (at most 512 tokens).
**Selection rule (fixed now):** the full arms use the variant with the most Week-1 two-hop tests dreamed in the forward direction (the
test's start name, the test's answer) after 4 cycles; ties go to fewer thinking tokens. `--rem-tries` is 1 if that variant dreams at least
90% of the reachable Week-1 chains forward after 4 cycles, else 2. The probe never sees Week-2.

## Arms (Week-2, seed 1, K2 bf16, both with `--think-eval`)
- **k2c (A), the K2 chain-dream port:** `--rem-chain-mode <probe winner> --rem-dirs both [--rem-tries T]`.
  - `--rem-dirs both`: every pair is dreamed in both directions. Each direction is a unit that is tried every REM cycle until it has one
    kept dream, then never again. This keeps the chain part of the pool at most 2 dreams per pair.
  - The old chain path does not work on K2 at all (9 dreams in a week), so there is no working K2 baseline to change one thing against.
    A is judged as one port package against k2s_bf16.
- **k2c_r2 (B), A plus twice the REM practice:** A's flags plus `--rem-steps-mult 2`. Each REM cycle runs twice its steps; the night's
  cosine schedule covers the new total. This is the one change between A and B.
- Gist (habit) prompts, NREM, the names pass, the tagger and the gates are unchanged.
- `--think-eval` (report-only): after the usual scoring, the two-hop questions and the C2+C4 forward questions are also asked with K2's
  high-effort thinking (at most 512 greedy tokens), weights only.

## Pass marks (fixed now)
- **G (Ben's goal):** two-hop, scored as always, >= 75 of 78 (96.2%; 74 of 78 is 94.9%).
- **C1 (the port works):** A's two-hop >= k2s_bf16's + 40 points (>= 34 of 78), paired exact McNemar p < 0.05.
  **Wrong if** A dreams at least 60 of 78 tests but answers fewer than 40% of all 78: coverage alone does not carry two-hop on K2.
- **C2 (rehearsal is the second bottleneck):** B's two-hop >= A's + 5 points, and B's right-when-dreamed share > A's.
  **Wrong if** B's right-when-dreamed share is not above A's.
- **No harm (each arm):** recall C2+C4 >= 93.5 (k2s_bf16's 96.5 - 3: addendum 10 lost 4.5 points of single-fact recall when chain dreams
  grew); ARC-Easy >= that run's pre-sleep ARC-Easy - 5; diary >= base_diary - 5.
- **Reported, not marked:** dreamed forward / reverse per test; chain yield; pool size per night; REM steps; wall time; think-eval
  two-hop and forward C2+C4 (and whether thinking finds the answer anywhere in its text); reverse, changed, routine.
- **Expectation (not a mark):** A two-hop 55-90; B 70-97.

## What comes next (not part of this test)
If B reaches G: a second seed, then the same port on the Qwen3.6 tier (which already dreams 74 of 78 but is right on only 72% of them:
B's change alone). If C2 fails: interference, not rehearsal; next is fewer, cleaner chain dreams (one per pair), untested. If C1 fails: the
K2 port itself.

## Compute
Probe: one Kaggle T4 (free, fp16) through the Kaggle thread, or a Vast GPU of at most $0.15. Arms: two RTX 5090-class Vast boxes run in
parallel, about 2.5 h each (thinking in REM and the extra REM steps add time). The coordinator's cap is $2.60 for the probe and both arms.
A box that is not running within 10 minutes is dropped. Each JSON and log is pulled after the self-stop, then the box is destroyed, and
the actual cost of each box is reported.

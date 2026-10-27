# dl-2 VERIFY (Fix-sleep thread, 2026-09-26 ~02:10 UTC)

**Registered verdict: PASS (W1-W5).**
- The builder scored it PASS (RESULTS-gpu.md).
- A blind recount agrees. The recounting agent read only PASSMARKS.md and gpu/dl2_results.json, and used its own script; it did not see the scorer, the marks key, or RESULTS.
- The proved-wrong clause is not triggered.
- The data checks hold on all 28 nights: n_test 100, n_harm 300, 7 nights × seeds 2, 3; net_harm = lost − gained; right = 200 − lost + gained.

| | Base | S seed 2 | S seed 3 | P seed 2 | P seed 3 | Bar |
|---|---|---|---|---|---|---|
| TEST right guesses (lucky), night 7 | 64 | 237 | 249 | 42 | 51 | W1 ≥ 128 each; W5 S sum ≥ 1.3 × P sum (486 vs 121), min S > max P |
| worse nights (> 15% below the previous) | | 0 | 0 | | | W2 ≤ 1 of 14 (worst: s3 night 5, 235 → 209, −11%) |
| nights with net harm > 5 | | 0 | 0 | | | W3 ≤ 1 of 14 (s3 night 6 is exactly +5) |
| final net harm | | −10 | −8 | −24 | −22 | W3 ≤ 0 each |
| puzzles reached, night 7 | 34 | 62 | 60 | 28 | 32 | W4 ≥ 34 each |
| greedy solves, night 7 (report) | 3 | 17 | 18 | 1 | 4 | |

## Losses, reported separately from gains
The outside review (Ben, 01:54 UTC, section 11) is right that net harm lets gains hide losses. On the 300-item general panel, "lost" means right at base and wrong now (base right = 200). "Gained" means the reverse.

| Night | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| S s2 lost / gained | 7 / 42 | 11 / 42 | 18 / 49 | 19 / 44 | 16 / 54 | 28 / 40 | 26 / 36 |
| S s3 lost / gained | 5 / 38 | 8 / 46 | 10 / 45 | 15 / 50 | 16 / 38 | 30 / 25 | 26 / 34 |
| P s2 lost / gained | 6 / 43 | 14 / 48 | 17 / 35 | 9 / 43 | 8 / 39 | 13 / 35 | 17 / 41 |
| P s3 lost / gained | 8 / 50 | 5 / 54 | 11 / 47 | 12 / 44 | 16 / 43 | 22 / 42 | 19 / 41 |

What this shows:
- Forgetting is real and it grows. After a week, S had lost 26 of the 200 items the base got right (13%) on each seed, up from 5-7 after night 1.
- Net harm stays ≤ 0 only because 34-36 other items were gained.
- The wrong-answer placebo P gains about as many items (35-54 per night). So the gains are mostly answer-format learning (short one-word replies), not a general improvement.
- S loses more than P by night 7 (26, 26 vs 17, 19). KL to the base rose steadily (0.04-0.05 → 0.15/0.19).
- W3 passes as registered, but "almost never worse elsewhere" is NOT shown past about 3-4 nights: losses doubled between night 3 and night 7.
- Gains on the day's work mostly level off after night 4 (227/235 → 237/249).
- Suggested next single change (not run): a replay or anchor slice of old general answers in each night, or a fresh adapter from the base each week on the growing hit bank. The mark would be lost ≤ 10 of 200 after 7 nights, with lucky ≥ 2 × L0 kept.

## What W5 can and cannot claim (review section 10)
Checked against scripts/claude_dl2_nights.py:
- Each arm gathers its day from its own, changing model (run_arm: D1.gather(s, m, ...) with that arm's m).
- P's examples come from `wrong_examples`: one legal, complete, wrong guess per puzzle, from puzzles that had any. These can be different puzzles from S's and could return fewer than asked.
- In this run P always got its full count on every night (P's trained examples equalled its own right-answer count on all 14 P nights). The count matched; the puzzles did not.

So W5 compares two night POLICIES:
- practise the day's checked right answers;
- practise the same number of the day's wrong answers.

Each runs on its own data. It shows the practise-right-answers policy works and the wrong-answer policy does not. It does not isolate answer correctness as the only difference. A clean causal test would pair the same puzzles with a checked right and a checked wrong answer, with matched exposure.

## Run facts
RTX 5090 rental, 67.1 min, about $0.65. Code origin/main 589946c9, model MiniCPM5-1B @ 87179e5c, unmodified. No weights saved. The deviations the builder listed (a relaunch from the wrong folder before any GPU work; the credit gate read credit 5.12 with balance 0) do not touch the result.

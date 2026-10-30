# Practice-2: "go learn one skill" (pre-registered Oct 26 2026, before any run)

Why: Practice-1 (RESULTS.md) practised mixed puzzles and was tested on 7 other kinds; P had only 14-31 unique wins per night and did not improve (19.0 -> 16.5%). Ben (Oct 26 17:39-17:41Z): do a TON of puzzles of one steady style; the goal is "go learn X" (e.g. spreadsheets): many attempts, tips from the web, train on the attempts.
One change from Practice-1: practise and test the SAME skill, with thousands of fresh auto-checked tasks (each puzzle seen once, so memorising answers cannot help). Tips are a later addendum, not part of this test.

## Source
Reasoning Gym (pip `reasoning-gym==0.1.25`): procedurally generated puzzle types with built-in checkers (`score_answer`; correct = score 1.0). Checkers accept any valid solution (countdown, word ladder, cryptarithm).
Candidate skills: countdown, cryptarithm, knights_knaves, zebra_puzzles, mini_sudoku, futoshiki, word_ladder, family_relationships. Default difficulty.

## Stage 0: pick the skills (no training)
Base K2 (A0, same harness and tools as Practice-1 with the python3-line fix), 40 puzzles x 1 try per candidate (seed 100).
Rule: keep the 2 skills whose A0 is closest to 30%, among those between 10% and 60%. If fewer than 2 qualify, take the nearest ones and say so.

## Arms (per chosen skill)
- A0: base model.
- P: practice with the checker. Each day 1000 fresh puzzles x 4 tries (seed 1000+day); night = fresh LoRA on cumulative lessons: SFT on one win per solved puzzle (shortest) + DPO (win vs failed try of the same puzzle). Same night recipe and steps as Practice-1, scaled to the lesson count.
- C: same practice and same training steps, checker removed (SFT on random tries, random pairs).
- 3 days, 3 nights. Smaller fallback on the Mac: 300 puzzles x 2 tries per day, said in the results.

## Test
300 fresh held-out puzzles per skill (seed 9999, any question text seen in practice removed), 2 tries each, scored at A0 and after nights 1 and 3. Secondary: the sealed test100 after night 3 (transfer and harm check).

## Pass marks (fixed now)
- S1 (primary, per skill): P3 >= A0 + 10 points, paired sign-flip p < 0.05 (Holm over the 2 skills).
- S2: P3 >= C3 + 5 points, p < 0.05 (the checker matters, not just more of the skill's text).
- S3 (no harm): test100 P3 >= A0 - 5 points, and tool calls per try >= half of A0's.
- Wrong if: P3 <= A0 + 3 on both skills (lots of practice on one skill does not help it), or P3 < C3 on both.
- Also report: practice-day solve rate by day (does it climb?), unique wins per night, per-skill curves after night 1 and 3.

## Next (separate addenda, one change at a time)
- W: tips arm (the model searches the web for "how to get better at <skill>", writes a tips sheet, which goes in the prompt), base model and P.
- Skill 2: spreadsheets (generated sheet tasks with checked answers).

## Addendum 1 (Oct 26 17:55Z, before any run): run inside Ben's OpenBot harness
Ben (17:49Z): "Put it in the open bot harness on my Mac." OpenBot drives the OpenCode agent, so practice and test tries run headless through `opencode run`: the same agent, with a short practice-agent prompt and only the bash/read/write/webfetch tools. K2 runs behind practice/k2_proxy.py, which turns K2's native tool-call text into OpenAI tool calls (mlx_lm 0.32.2 has no K2 parser). Lessons are rendered from the proxy log, exactly as served. All arms, A0 included, use this same harness, so the pass marks are unchanged. If the OpenCode prompt makes K2 fail stage 0 (every candidate under 10%), the run falls back to the Practice-1 harness and the results say so.

## Addendum 2 (Oct 27 ~03:40Z, after the M1 pilot, before pilot 2): bare final answers are not lessons
Pilot (knights_knaves, M1, opencode harness, 60 puzzles x 2 tries, 1 night, 40-puzzle test): A0 42.5% (17/40) -> P1 32.5% (13/40); tool calls per try 1.15 -> 0.125.
Ruled out (shown): the shortest-win pick (SFT wins used 1.39 tool calls, more than failures) and memorising (each of the 50 items was trained once; SFT loss 0.46 -> 0.40; the logged 0.0 was 4 empty steps).
Suggested cause: 25 trained segments (SFT + chosen) are a bare `<answer>...</answer>` turn right after the assistant header, so K2 learned "an assistant turn starts with <answer>"; first-turn answer-first went 13/40 (A0) -> 31/40 (P1).
One change: a completion that is only `<answer>...</answer>` stays in the lesson as context but gets no loss (`lessons.TRAIN_BARE_ANSWERS = False`; `--train-bare-answers` restores the old rule). Also fixed: no empty steps (steps = min(steps, max(SFT items, pairs))).
Pilot 2: the same day-1 tries, a new night with this rule, the same 40-puzzle test. Pass marks (fixed now): first-turn answer-first <= 20/40, tool calls per try >= 0.58 (half of A0's), and accuracy >= 37.5% (A0 - 5). Wrong if: tool calls per try < 0.3 again (then the bare answers are not the cause).

## Addendum 3 (Oct 27 ~04:10Z): stage-0 result and skill pick
Stage 0 (opencode harness, 10 puzzles x 1 try; word_ladder, family_relationships and futoshiki redone on the M1 after the M3 server crash): knights_knaves 2/10, zebra_puzzles 2/10, family_relationships 4/10, countdown, cryptarithm, mini_sudoku, futoshiki, word_ladder 0/10.
Three skills tie at 10 points from 30%. Tie-break (fixed now, before any main run): the lower score first, since it leaves more room to improve. So the main run uses knights_knaves and zebra_puzzles; family_relationships (fast, ~53 tokens, 0.5 tool calls per try) is the spare. Stage 0 used 10 puzzles per skill instead of 40 because the Mac is slow; the 4090 run re-measures A0 on its own 300-puzzle tests.

## Addendum 4 (Oct 27 06:20Z, before any main run): smaller days for free compute
The two rented 4090s are not coming. To fit one free GPU per skill (Ben's PC 5070 Ti, Kaggle T4 after the Oct 30-31 reset), each practice day is 500 fresh puzzles x 4 tries per arm (was 1000 x 4). Everything else is unchanged: 3 days, 3 nights, the 300-puzzle test x 2 tries, the same pass marks (S1 P3 >= A0 + 10, p < 0.05; S2 P3 >= C3 + 5; S3 no harm). The pilot had 35 wins a night; at the pilot's ~29% practice solve rate this gives about 580 tries won per day.

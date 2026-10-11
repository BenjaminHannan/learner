# Prompt for GPT (web): why didn't our "try, check, sleep" loop climb to harder rules? (2026-10-07)

Paste everything below the line into GPT. It cannot see our repo, so the prompt carries the whole setup.

---

I'm running a small research project and need a second opinion on a result that has two plausible explanations. Please
label every claim **shown** (follows from the numbers below), **suggested** (your reasoning), or **untested** (would
need a new run).

## The model and the test

- The model is a tiny from-scratch "thinker" (3.3M parameters). It reads a prompt and writes a short program in a fixed
  language. Each step picks one op (ADD, SUB, MUL, DIV, MOD, MIN, MAX, CMP) and two arguments. An argument can point at
  a number in the prompt, at one of four built-in constants (1, 2, 10, 100), or at an earlier step's result. An exact
  executor runs the program, and the last step is the answer. Programs are at most 7 steps.
- Task: "rules from a few examples". The prompt is `x1 -> y1; x2 -> y2; x3 -> y3. Now q -> ?`, inputs 2-29.
  - A try is accepted only if, with each example's x put in the query slot, it reproduces every example's y. No answer
    key is used.
  - The examples always pin down a single answer.
- Rule kinds:
  - Practised in warm-up: add (y = x + B, B 3-30) and mult (y = A*x, A 3-9). The warm-up trained on 2,048 correct
    programs written by a search solver.
  - Held out, never in warm-up:
    - square: x*x
    - last_digit: x mod 10
    - sq_plus: x*x + B, B 3-9
    - double_add: (x + B)*2, B 3-9
    - affine: A*x + B, A 3-6, B 3-15
- The solver's reference programs build B and A out of the constants. For example, 7 = 10 - 2 - 1 and 5 = 10 / 2.
  So square and last_digit are one fixed 1-step program for every question, while the other three need 2-5 steps and
  a different constant expression for each parameter value.
  - Programs that read the parameter off the examples (like x + (y1 - x1)) also pass the check, but they are longer.
- "Stepping stones" (SS): one sleep on 2,048 easier variants of the held-out kinds, made by code:
  - affine with A = 2;
  - sq_plus and double_add with B in {1, 2};
  - x mod k for k = 2-5.
  The SS variants never use the held-out parameter values. Square's program is the first step of the sq_plus stones.
- "Sleep" = fine-tuning on (prompt, program) records, with half of each batch replaying general skills data. The model
  never sees the answer key.

## Results (DEV split, 256 questions, about 51 per held-out kind; two trained copies, s100 / s101)

Step 1, cold start. Share of questions where 32 tries found an accepted, right answer:

| model | reach@32 |
|---|---|
| warm-up only | 5.1% / 9.8% |
| random programs (floor) | 4.8% |
| SS sleep | 25.4% / 19.5% (gate was 14.5%) |
| placebo (2,048 more add/mult rows instead of SS) | 4.3% / 5.1% |
| sleep on 2,048 correct solver programs for the held-out kinds themselves (PC, a ceiling) | 63% / 68% |

- SS passed only at the hottest sampling temperatures (3.0-4.0).
- Even PC's greedy first try (s100) was:
  - square 94%;
  - last_digit 100%;
  - sq_plus 18%;
  - double_add 6%;
  - affine 0%.

Step 2, the creative loop. Start from the SS model (call it N) and sample 32 tries on each of 1,024 new pool questions.
Sleep on:

- W: the tries that fit every example;
- R: the same number of tries that fail;
- H: R's tries relabelled to what they compute;
- PC: correct programs for W's questions.

The dose was 16 visits, chosen on DEV with PC.

| greedy first try right, DEV | N | W | R | H |
|---|---|---|---|---|
| pooled | 1.2% / 0.4% | 35.9% / 27.3% | 1.2% / 0.4% | 0 / 0 |

W - N per kind (points):

| kind | W - N |
|---|---|
| square | +96 / +94 |
| last_digit | +78 / +39 |
| affine | +4 / -2 |
| sq_plus | +2 / 0 |
| double_add | -6 / +4 |

- The multi-step kinds net 0 / +1 questions out of 154.
- W's records were 257 / 149 square, 87 / 39 last_digit, and only 21 / 22 of the three multi-step kinds combined
  (365 / 210 records in total).
- Night 2 (W samples again and sleeps on its new hits) gave first try:
  - affine 4% / 0%;
  - sq_plus 2% / 2%;
  - double_add 2% / 8%;
  - last_digit up from 78% to 82% and from 39% to 65%.

Forgetting:

- On 256 fresh add/mult questions, reach@32 at T 1.0 was 61% / 57% after warm-up, 11% / 11% after the SS sleep (N),
  7.0% / 7.8% after W, and 1.6% / 10% after night 2.
- A separate general-skills score barely moved (within 2 points).

## The question

The loop turned lucky hits into first answers for the two one-program kinds, but did not climb to the multi-step kinds.
Two explanations:

- (a) The parts were forgotten. Every multi-step kind is "add B" or "times A" plus a stone-taught piece, and the SS sleep
  wiped add/mult.
- (b) This model cannot learn 3-5-step programs that build a parameter out of its constants, even when shown correct
  ones (PC's first try on those kinds was 0-18%).

Our planned next run changes one thing: every sleep also replays the 2,048 warm-up add/mult rows. It has:

- a guard: add/mult reach@32 must stay >= 50%;
- a feasibility gate: correct programs for the multi-step kinds must lift their first try by >= +10 points;
- a climb mark: two nights of the loop lift multi-step first try by >= +10 points, with a paired interval above 0, on
  both copies;
- a proof that it's wrong: parts kept and an upper end below +3.

Please answer:

1. Which explanation do the numbers favour, and what in them would you weigh most? Is there a third explanation we're
   missing? Candidates: sampling temperature, the constant-built reference programs, or kind imbalance in W's records.
2. Is the planned run a clean test of (a) against (b)? If you would change it, propose exactly one change. Give pass
   marks fixed in advance and the result that would prove it wrong.
3. Is a 3.3M-parameter program writer a fair place to test "climbing", or is the parameter-building step a language
   problem? For example, a model that read B off the examples would need one program per kind, not one per value.
   Keep this to the small rule test. Don't generalise to our larger model, which is a separate project.
4. A plain-language summary for Ben, a high-school senior: 5 sentences at most, no jargon.

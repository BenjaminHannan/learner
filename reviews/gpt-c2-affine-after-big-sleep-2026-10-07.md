# A small program-writing model now learns x²+k and 2(x+k) overnight, but a·x+b stays at 12-21%. Why? (no code or file access needed)

You are an expert in program synthesis, few-shot rule induction and self-training (expert iteration, DreamCoder-style wake/sleep). You have **no access** to my code, files or machine, so everything you need is below. Don't ask me to run anything before you answer. If a fact you need is missing, say exactly what it is and how it would change your answer.

Rules for your answer:
- Mark every claim as **shown by the data below**, **suggested**, or **untested**.
- This is a small toy experiment only. Keep any advice about large language models separate and labelled as such.
- Propose **one change at a time**. For each, give a pass mark fixed in advance and the result that would prove it wrong.
- Every step must be something the model could do **on its own while deployed**. No settings taken from the test generator, no tuning on answer keys at run time.
- I am a high-school senior. End with a plain-language summary I can follow.

## 1. Task
Each question shows 3 examples of a hidden integer rule and asks for a 4th ("3 -> 16; 5 -> 26; 7 -> 36. Now 4 -> ?"). There are five rule kinds the model never practised before:
- a·x+b, with a in 3..6 and b in 3..15 (52 rules);
- x²;
- x²+k, with k in 3..9 (7 rules);
- x mod 10;
- 2(x+k), with k in 3..9 (7 rules).

Inputs are 3..29. The score is **first try**: the model writes one program, greedily, and that program is run on the query. There is no checking against the examples at test time. The day's practice is 1,024 unanswered questions of these kinds (the "pool"). The test uses new questions of the **same** rules.

## 2. Model (about 3.3M parameters)
- A looped controller reads the prompt and writes a program of up to 7 steps, each (op, pointer, pointer). The ops are add, sub, mul, exact div, mod, min and max. An exact executor runs the program.
- A program may read only x, the constants 1, 2, 10 and 100, and earlier results. It may **never** read the example numbers. So 7x+3 must be built inside the program, e.g. (10−2−1)·x + 2 + 1, and every (a, b) needs a different program.
- Before this work, it had practised only y = x+B and y = A·x, using given solver programs.

## 3. The sleep that works (one night)
1. **Night:** the model samples 32 programs per pool question, at a temperature it picks itself (the one whose tries fit the most examples on a probe). Programs that fit all 3 examples become records (W). About 420 records, almost all x² and x mod 10.
2. **Chain search:** for each pool question with no W record, it searches for the shortest P2(P1(x)), where P1 and P2 come from its library (W plus 512 old add/mult programs), that fits the 3 examples. This found a program for every remaining question (about 700 records). Checked afterwards against the pool's key: 100% right.
3. **Replay:** each record's program is run on 3 fresh input sets, drawn from the inputs seen that day, giving 3 new prompts of the same rule.
4. **Fine-tune:** about 4,500 records at batch 1,024, 80 visits per record, with half of each batch from old-skills replay. About 2,400 TFLOP. Old skills unharmed.

## 4. Results (% right first try; DEV 256 questions, ~51 per kind; holdout 512)

| Sleep | a·x+b | x² | x²+k | x mod 10 | 2(x+k) | all |
|---|---|---|---|---|---|---|
| no sleep | about 0 | about 0 | about 0 | about 0 | about 0 | 0.2 |
| old fine-tune (W only, 40 TF) | 0 | 100 | 2 | 82 | 6 | 37.5 |
| W + chain, job-6 budget | 8-10 | 92-96 | 16-24 | 94-98 | 4-10 | 42 |
| + answer key's own programs instead (512 questions, same budget) | 2 | 92 | 24 | 100 | 6 | 45.7 |
| W + chain + replay, 40 visits | 6 | 94-96 | 69 | 92-96 | 55-67 | 64.6 |
| same, without replay (same updates) | 8 | 98 | 31 | 96 | 16 | 49.6 |
| same with replay, **80 visits** (used a temperature tuned on DEV answers and the test generator's input range) | 12-21 | 92-100 | 73-82 | 86-100 | 63-80 | **72.7** (holdout 72.7, 2 seeds) |
| 40 visits + "top-up": every program with < 32 records gets replays up to 32 | 25-31 | 90-98 | 63-69 | 82-92 | 53-57 | 65.8 |
| final version, fully on its own (its own night and temperature; replay inputs only from the day's questions), 80 visits; **holdout, 6 seeds** | 15.5 | 98.7 | 76.6 | 93.1 | 72.5 | **71.3 +/- 2.5** |
| final version + top-up, DEV 2 seeds | 21-25 | 96 | 80-86 | 80-84 | 69-71 | 70.7 |

Facts:
- Among the chain records for a·x+b there are 48 distinct programs over 202 records (about 4 per rule). x²+k and 2(x+k) have 7 programs each, with about 30 records per rule.
- The a·x+b programs are 4-5 steps long, and the first steps depend on a: 5x is built as x·10/2, 6x as (x+x+x)·2, and so on.
- Blind breadth-first search over x and the constants fits 92% of pool questions at 20k states (0.03 s each).

## 5. Questions
1. Rank the causes of a·x+b staying low: too few examples per rule; inconsistent program shapes across a; first-step decisions needing a fine estimate of a from three digit pairs; model size; something else. For each, give the cheapest diagnostic using only what I have.
2. What is the single best next change that keeps every step autonomous? Consider: a canonical shortest program per rule; a per-rule example budget; a second night by the slept model (expert iteration); a curriculum from 1-constant to 2-constant rules; predicting a sub-goal (the value of a) first.
3. Is "same rules, new questions" a fair test of "learning a new kind overnight"? What split would test real generalisation to unseen rules (e.g. hold out some (a, b) pairs) without making the task impossible?

Please give one change at a time, with pass marks and the result that would prove it wrong, and end with a plain-language summary.

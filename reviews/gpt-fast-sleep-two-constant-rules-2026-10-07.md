# Why can't a small program-writing model learn "a·x + b" from its own solved examples? (no code or file access needed)

You are an expert in program synthesis, few-shot rule induction, memory-augmented networks and continual learning. You have **no access** to my code, files or machine, so everything you need is pasted below. Do not ask me to run anything before you answer. If a fact you need is missing, say exactly what it is and how it would change your answer.

Rules for your answer:
- Mark every claim as **shown by the data below**, **suggested**, or **untested**.
- This is about a small toy experiment only (the "card experiments"). Do not mix in advice about large language models unless you label it as such, separately.
- Propose **one change at a time**. For each, give a pass mark fixed in advance and the result that would prove it wrong.
- I am a high-school senior building this with AI help. End with a plain-language summary I can follow.

## 1. The task (C2)

Each question shows 3 examples of a hidden integer rule and asks for a 4th: e.g. "x=3 → 16, x=5 → 26, x=7 → 36; x=4 → ?". Five held-out kinds the model never practised:
- affine: a·x + b (a, b change per question)
- square: x²
- sq_plus: x² + k (k changes per question)
- last_digit: x mod 10
- double_add: 2(x + k)

There are 1,024 practice ("pool") questions (about 205 per kind) and a 256-question DEV split. The model practised only addition and multiplication rules before.

## 2. The model (B2, about 3.3M parameters)

- A looped controller reads the prompt and writes a short **program**: up to 7 steps, each step (op, ptr, ptr). An exact integer executor runs it.
- There are 27 slots. 0-15 hold numbers from the prompt (x is slot 6), 16-19 hold the constants 1, 2, 10 and 100, and 20-26 hold step results. There are 7 ops: add, subtract, multiply, exact divide, mod, min and max.
- **Hard rule:** a program may read only x, the four constants and earlier results. It may **never** read the example slots. So for 7x + 3 the model must *build* 7 and 3 out of 1, 2, 10 and 100 inside the program (e.g. 10 − 2 − 1). Each question with different a, b therefore needs a different program.
- Scoring: "first try". The greedy program is run on the query and checked against the key. No checking against the examples at test time.

## 3. The night and the sleep

- **Night:** the model samples 32 programs per pool question (at a tuned temperature, 3.0 on most parents). Programs that fit all 3 examples become records "W" (at most 2 per question). 18-32% of pool questions get a W record, almost all square and last_digit. Cost: about 25 TFLOP.
- **Fine-tune sleep (B):** ordinary training on W mixed half and half with old add/mult replay. 19-39 TFLOP.
- **Memory sleep (M):** no weight change. For each W record, store the controller's hidden state at each step as a key and the step's (op, ptr) as the value. At test time take the top-16 cosine neighbours and add a vote bonus (+50 × vote share) to their op and pointer logits when similarity clears a calibrated gate. 512 old add/mult solver records are stored too. Cost: about 1 TFLOP.

## 4. Results (DEV, % right; 8 parent models unless stated)

Base model N, then the two sleeps:

| Arm | affine | square | sq_plus | last_digit | double_add |
|---|---|---|---|---|---|
| N (no sleep) | 1 | 0 | 0 | 0 | 4 |
| B, fine-tune on W (6 parents) | 0-2 | 90-98 | 0-10 | 80-94 | 0-16 |
| M, memory on W | 0 | 84 | 0 | 73 | 5 |

Then I gave the night more records. For each pool question with no W record, an offline search found a program that fits the 3 examples. One search chained two stored programs (it found one for 100% of missed questions, about 200 affine and 200 sq_plus records per parent). A blind search over x and the constants found one for about 60%. These records never used the answer key.

| Arm | affine | square | sq_plus | last_digit | double_add |
|---|---|---|---|---|---|
| M on W + chain records | 0.2 | 61 | 9 | 72 | 23 |
| M on W + blind records | 0.2 | 74 | 4 | 74 | 14 |
| B on W + chain records, same cost as B (2 parents) | 2-4 | 88-94 | 20-27 | 96-98 | 2-8 |
| B on W, the same 2 parents | 0-2 | 96-98 | 0-2 | 82-90 | 0-8 |

Other facts:
- With the right library, an offline "chain two stored programs, keep the shortest that fits the examples" solves 100% of DEV. A blind breadth-first search with no notes solves 64.5% of DEV at 1,000 guesses per question, 77.3% at 6,000 and 94.9% at 50,000. So C2 is easy for anything that can check guesses against the examples.
- Copying stored programs as they are can solve at most 0-8% of DEV affine and 27-39% of sq_plus. Their constants rarely match.

## 5. My questions

1. Why does the fine-tune pick up x² + k (one constant) from about 200 correct examples, but not a·x + b (two constants)? Rank the plausible causes. For each, give the cheapest diagnostic I could run on what I already have (cached hidden states, the records, the executor).
2. Given the "never read example slots" rule, what is the smallest change that would let the model learn two-constant rules? Consider at least:
   - sub-goal prediction (predict a, then build it; ExeDec-style);
   - a learned search over executed sub-results (CrossBeam-style);
   - curriculum over constants;
   - parameterised notes (store a program "shape" and fill its constants at test time);
   - something else you think is better.
   For each, say whether it is still "learning" or is really search, and what fair search baseline it must beat.
3. My sleep must stay cheap: about 1-2 TFLOP per night, against 25 TFLOP for the night's sampling. Which of your proposals fit, and which need a rare, expensive consolidation instead?
4. Is "first try without checking" the right score for a model that is meant to learn from few examples? Or should the model check against the examples, with a blind search at the same number of guesses as the baseline? Argue both sides briefly, then pick one.

Please give one change at a time, with pass marks and the result that would prove it wrong, and end with a plain-language summary.

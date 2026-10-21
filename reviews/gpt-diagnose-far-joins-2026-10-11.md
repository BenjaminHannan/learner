# Why can't a 3M model learn to join two spreadsheet functions? (no code or file access needed)

You are an expert in small neural program-executing models, compositional generalisation and length generalisation.
You have **no access** to my code, files or machine, so everything you need is pasted below. Do not ask me to run anything
before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change
your answer. Mark every claim as **shown by the data below**, **suggested**, or **untested**.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

Scope: this is only about one small experiment, a 3.3M-parameter calculator-calling model teaching itself spreadsheets
("domain mode"). It is not about my larger "village" model; please do not mix the two.

## 1. The task

A prompt is a tiny spreadsheet and one formula. The model answers by writing calculator calls, then the answer.

| shape | example prompt | calls (the tool's working) |
|---|---|---|
| near (like the help page) | `A: 50 84 94 46 \| B: 62 90 44 56 ; =SUM(A1:A4)` | ADD 50 84; ADD 134 94; ADD 228 46 |
| two kinds joined, near grid ("F4") | `A: 49 20 65 \| B: 78 59 92 ; =SUM(B2:B3)+MAX(B2:B3)` | ADD 59 92; MAX 59 92; ADD 151 92 |
| reference to row 5 or 6 ("F2b") | `A: 35 53 89 96 62 32 \| B: 1 78 89 14 80 74 ; =B5+A2*2` | MUL 53 2; ADD 80 106 |
| far (what the test asks) | `A: 13 54 33 88 20 4 \| B: 58 50 91 19 8 43 ; =SUM(B2:B6)+PRODUCT(B2:B3)` | 4 ADDs, 1 MUL, 1 ADD |

Far test rows combine everything at once: 5-6 row grids, ranges of 5-6 cells, another column, and two kinds joined with
`+`, `*` or `MOD`. Half of the far rows need MOD or a comparison, which this setup cannot train at all (no row form), so
the far ceiling is about 50%. Seven kinds are scored: SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS.

A second domain, RPN, works the same way: `rpn: 3 4 + 2 *` -> ADD 3 4; MUL 7 2. Far RPN rows have 4-5 operators.

## 2. The model (about 3.28M parameters, width 256, 4 heads)

- Input: one token per character (108 symbols), prompt at most 208 characters. Each character also gets a "place" code
  (position counted from the right end of its word).
- Reader (0.74M): character, position and place embeddings, then 2 convolution blocks (window 5), then LayerNorm. So the
  reader itself only sees local context.
- Number slots: the first 16 digit runs of the prompt (the regex `\d+`, so the row digits inside `B5` count too), plus the
  constants 1, 2, 10, 100, plus up to 7 result slots (one per call). Prompts with more than 16 digit runs are rejected
  in practice, and every test row was built under the same cap (the largest has exactly 16).
- Thinker (2.32M): 8 control tokens and 9 register tokens; 8 loop iterations reusing the same 2 blocks. Each block
  cross-attends to the 16 number summaries, the visible tape (earlier calls as text, e.g. `59 + 92 = 151`) and the prompt
  characters, then self-attends, then an MLP.
- Heads per round (7 rounds max): an operation head (NOOP, ADD, SUB, MUL, DIV, MOD, MIN, MAX, CMP); operands are written
  as text, either by copying a whole number from the prompt or tape with a pointer, or character by character. A plain
  Python calculator runs the call and its text joins the tape for the next round. After the loop, the registers write the
  answer (up to 8 characters).
- Training (teacher forcing): the gold tape is revealed one entry per round; losses are op cross-entropy, operand
  log-likelihood (either order for ADD/MUL/MIN/MAX), and answer characters. A row is kept only if its last call's result
  equals the answer.
- It was pre-trained on about 200k rows of many small arithmetic and reading skills, but never on spreadsheets.

## 3. The self-practice loop ("domain mode")

Given only a help page (10 sheet examples, one per kind, all on the same 3-row, 2-column grid of single digits, e.g.
`A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)`; 8 RPN examples like `rpn: 3 4 +`) and the tool:
- Each day it makes practice by editing help examples (change digit-run lengths, insert or delete runs, rename letters,
  swap symbols); the tool checks each problem.
- It tries each problem; it keeps its own try only when it equals the tool's working, otherwise it trains on the tool's
  working.
- Each night it trains a low-rank add-on (rank 8, alpha 16, on every Linear layer, base frozen, lr 1e-3, AdamW) on the
  day's rows (about 800-1000 new rows a night, each visited 16 times) plus replay; a picker spends more practice on kinds
  whose own quiz is moving; it stops when its own quiz rises less than 1 point over 2 nights (max 12 nights).

## 4. What happened

### v7 (practice = help-page edits only)
Near went from 3.6% to 40%; far stayed 0-2% on both seeds. **Shown:** 0 of 12,729 practice rows had any far property.

### v9 (the one change: a "swap tool" widens the help page first)
Before day 1, a domain-free swap tool replaces one well-formed piece of a help example (whole tokens, balanced brackets)
with a piece of any help example, keeps results the tool can run, and builds ring 2 (1,162 sheet examples) and ring 3
(3,000). Practice picks rings 1-3 evenly. Ring 3 examples look like `A: 4 2 | B: 2 3 5 1 ; =ABS(A1-MIN(B1:B3))`.

Practice coverage (shown, sheet seed 200, 6,270 practice rows):

| rows | 5+ row grid | range of 5+ cells | reference to row 5+ | two kinds joined |
|---|---|---|---|---|
| ring 1 | 0% | 0% | 0% | 0% |
| ring 2 | 68% | 9% | 35% | 11% |
| ring 3 | 80% | 11% | 43% | 17% |

Test results on a fresh test draw (shown, seed 200, scored kinds; percent):

| | before | after 7 nights |
|---|---|---|
| near (420 rows) | 3.6 | 39.8 |
| far (280 rows) | 1.4 | 0.7 |
| far rows that need no MOD/compare (138) | 0.7 | 0.0 |

Probe cells, one factor changed at a time from near (shown, 60 rows per kind per cell; v7 = old run, v9 = this run):

| cell | v7 | v9 |
|---|---|---|
| F0 near | 36.0 | 36.0 |
| F1 bigger grid (5-6 rows), formula unchanged | 18.6 | 29.5 |
| F2 long range (5-6 cells) | 14.2 | 32.1 |
| F2b reference to row 5 or 6 | 7.8 | 8.9 |
| F3 other column | 29.5 | 32.6 |
| **F4 two kinds joined, near grid** | **1.7** | **1.4** |
| F5 far without MOD/compare | 0.0 | 0.5 |
| length ladder (SUM, MAX, MIN, PRODUCT), range of 2 to 6 cells on a 6-row grid | 14-19 | 33 down to 28 (nearly flat) |

The model's own tries on its practice rows, right / tried, per night (shown):

| night | all rows | two kinds joined | 5+ row grid | reference to row 5+ | range 5+ |
|---|---|---|---|---|---|
| 0 | 3/808 | 1/85 | 0/458 | 0/223 | 0/72 |
| 2 | 74/909 | 0/97 | 30/500 | 12/271 | 0/70 |
| 4 | 122/964 | 1/124 | 47/565 | 9/309 | 0/96 |
| 6 | 160/877 | 1/80 | 65/500 | 9/250 | 0/50 |

So joined formulas were practised about 660 times (trained on the tool's working) and stayed at 1%. In an earlier run,
on joined formulas the **first** call was already wrong in 362 of 413 misses: the model answers as if the formula were the
one-kind shape it knows (for `=SUM(B2:B3)+MAX(B2:B3)` it starts a plain SUM).

RPN, same loop (shown, own tries right per ring, nights 1-6): ring 1 (help shapes, 1-3 operators) 55-72%; ring 2 13-18%;
ring 3 (90% of rows have 4-5 operators) 1.5-5%, flat. In the old v7 run: help shapes 93% on the test, new operator
orders 0-5%, 4-5 operators 0%.

RPN v9 final test (shown, seed 200, 10 nights; percent): near 6.7 -> 96.0; far 0.4 -> 7.9; far rows that need no MOD or
compare (69 of 280) 0 -> 27.5, of which rows whose exact digit shape never appeared in practice (41) 0 -> 19.5. So in RPN,
where far means a longer chain of the same kind of step, the widened practice did transfer; in sheets, where far needs two
different functions joined in one formula, it did not.

## 5. Two direct tests since then (shown; marks fixed before each)

Both start from the pre-trained checkpoint and train for 4,000 updates (batch 64, no replay) on 12,000 tool-worked rows,
half joined formulas and half single-kind near rows. LA = the rank-8 add-on (lr 1e-3, base frozen); LB = every weight
(lr 1e-4). Joined test rows (F4) are held out.

**L1, joins from a hand-written generator** (`K+J` and `(K)*(J)`, all kind pairs, near grids, 2-digit values):

| arm | F4 at 500 / 1,000 / 2,000 / 4,000 updates | training slice at 4,000 | near at 4,000 |
|---|---|---|---|
| LA | 3.8 / 16.2 / 44.0 / 69.3 | 79.8 | 92.4 |
| LB | 12.4 / 46.0 / 80.2 / 88.8 | 97.4 | 98.3 |

**L2, joins made by the mode's own swap tool** (arm LA only, same dose): the test's joins 0.7 -> 2.1; its own joins
(training slice) 1.9 -> 42.1; near 4.3 -> 60.7; bigger grid 41.4, long range 53.3, other column 44.3, rows 5-6 21.7.
The 6,000 swap-made joins use 209 formula forms but are dominated by `=R+PRODUCT(R:R)` (878) and `=R+MAX(R:R)` (865), made
from the one help example with a `+` (`=A1+B2*2`); the test's `(K)*(J)` form never occurs and its `K+J` forms occur
1-9 times each. Swap-made grids are also odd (one column of 7 numbers, a B column with one number).

**L3, running now:** like L1 but the training joins use only `+` and only 14 of the 21 kind pairs. Scored on the
practised template with new numbers (S), held-out pairs (HP), the unseen `(K)*(J)` arrangement on practised pairs (HO),
and both (HPO). Marks: joining carries to new pairs if HP >= 30 and >= S/2; proved wrong if HP <= 5 while S >= 40; the
same for HO.

## 6. What I want from you

1. Explain L1 vs L2: the model learns joins from 6,000 generator rows (69%) but its own 6,000 swap-made joins teach it
   only those shapes (42%) and not the test's (2%). Rank the explanations (too few templates; template frequencies;
   odd grids; something in the architecture, e.g. the local reader or the 16 number slots) and label each shown /
   suggested / untested.
2. Predict L3 for both arms before seeing it (S, HP, HO, HPO), with your reasoning. What result would change your mind?
3. A self-practice loop only has the help page (10 examples) and the tool. How should it make practice that teaches
   joining as a skill rather than a few templates, without anyone hand-writing the domain's grammar? Give at most three
   changes, one at a time, each with pass marks fixed in advance and the result that would prove it wrong. Prefer
   changes the model applies itself (an outside tool it calls, or its own practice choices); the deployed model must run
   itself. Also say whether you would instead try a bigger model (I can test 10M and 30M later) or an outside tool that
   splits a formula into pieces the model already solves.
4. Rows 5-6: references to rows 5 or 6 stay low (8.9% in v9; 21.7% in L2 versus 60.7% near). Why, and the cheapest test?
5. A plain-language summary for me (a high-school senior), under 150 words.

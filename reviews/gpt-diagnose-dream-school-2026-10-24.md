# Prompt for GPT (web): why does practice on made-up puzzles hurt, while practice on the right answers helps?

Paste everything below into GPT. It cannot see our code, so everything it needs is here.

---

I'm working on a small program-writing model (3.3M parameters) and have a puzzling result. Please diagnose it.

**The task.** The model reads a few-shot number puzzle in text, e.g. `Examples: 4 -> 20; 5 -> 24; 16 -> 68. Now 15 -> ?`, and writes a short program in a
tiny language. Each step is (op, operand slot, operand slot), with ops + - × ÷(exact) mod min max. Operands can be the query input x, the constants
1, 2, 10, 100 (no other constants), or an earlier step's result. The answer is a pointer to one result slot. The program may NOT read the example
numbers. So for `4x+4` it has to work out A=4 and B=4 in its head and build them from the constants (4 = 2+2), e.g. 3 steps. Training gives
supervision on every step: op and both pointers are forced targets (teacher forcing).

**Kinds.** Practised with labels: `add` (x+B, B 3..30) and `mult` (A·x, A 3..9), whose programs are 1-4 steps. Held out (never labelled): `square`
(x·x, 1 step), `last_digit` (x mod 10, 1 step), and three "hard" kinds: `affine` (A·x+B, 3-5 steps), `sq_plus` (x·x+B, 2-4 steps) and `double_add`
((x+B)·2, 3-4 steps). The model starts from a pretrained parent, gets a warm-up on add/mult, then two "nights": it samples programs on an unlabelled
pool of held-out-kind puzzles (search: 32 tries, plus 480 more where none fits), keeps tries that fit the shown examples, and trains on them
(lr 1e-3, 32 visits per record). Every training batch is half these records and half replay of older skills. Score = greedy first try, right and
fitting, on 768 held-out-kind puzzles.

**The change tested:** a "dream school" before night 1, i.e. training on made-up puzzles (DreamCoder-style fantasies). Draw a random program, run it on
random inputs to make a puzzle, and train on (puzzle → program). A strict variant removes any dream whose function equals a held-out kind's form.

**Results** (Hard = mean of affine, sq_plus, double_add; Easy = mean of square, last_digit; percent):

| Arm | Hard | Easy | school's training loss at the end |
|---|---|---|---|
| no school (2 seeds) | 11.1 | 79.4 | n/a |
| 1-2 step random dreams, 1,000 per night, no school (2 seeds) | 12.3 | 84.8 | n/a |
| school: 40,000 random 1-5 step dreams, 2 visits, lr 3e-4 (2 seeds) | 1.2 | 78.7 | ~7.0 (flat) |
| same, strict (2 seeds) | 1.5 | 81.1 | ~6.9 |
| same, short-to-long curriculum (2 seeds) | 1.5 | 81.3 | |
| ORACLE: school = the pool puzzles' true shortest programs (uses the answer kind; a ceiling), ~68 distinct programs, ~79 visits each (2 seeds) | 45.5 | 99.0 | below 0 |
| (1 seed, smaller) no school | 11.8 | 87.9 | n/a |
| (1 seed) school: 8,000 dreams relabelled with the SHORTEST program that fits each dream (breadth-first search), balanced 2,000 each by shortest length 1/2/3/4, strict, lr 1e-3, 4 visits | 2.4 | 92.5 | 4.03 after 1,000 updates |

Other facts: after the random school, night 1 found fewer fitting tries on the pool (W records 699 real vs 815 without school). About 6% of the
non-strict dreams equal a held-out form. Skills harm was small (≤ 2-3 points) in every arm.

**My questions.**
1. Why would any dream school make the hard kinds WORSE than no school, even when the labels are canonical (shortest program) and the loss is still
   high? List the plausible explanations (e.g. the school moves the sampler away from the pool's distribution so night search fits less; too few
   updates for a too-wide dream distribution; dream inputs/outputs distributed differently from the real puzzles; label ambiguity; interference
   with the warm-up; capacity), and say what in the tables supports or contradicts each.
2. Why does the oracle work? Is it just memorising ~68 programs, and what does that imply?
3. Propose ONE next change at a time (at most three, ranked), each with a pass mark fixed in advance and the result that would prove it wrong.
   Budget: a CPU laptop, ~3 h per arm. Candidates I'm considering: dreams whose constants and shapes are drawn to match the pool's statistics
   (input domain 3..29, outputs ≤ 999); hindsight relabelling of the model's own near-miss tries on the pool; many more school updates until the
   loss falls below 2; mixing dreams into the nights instead of a separate school.
4. Label every claim as **shown** (by these tables), **suggested**, or **untested**.
5. End with a plain-language summary (5 sentences) for a high-school senior.

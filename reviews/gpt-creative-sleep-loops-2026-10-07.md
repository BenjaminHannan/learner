# Prompt for GPT (web): can sleep teach a small model's "creative mode" to search better on new problems? (2026-10-07)

Paste everything below the line into GPT. It cannot see our repo, so the prompt carries the whole setup.

---

I'm running a small research project and want a second opinion on a design before we train anything. Please label
every claim **shown** (follows from the facts below), **suggested** (your reasoning) or **untested** (would need a run).

## The model and the task (a small rule test; keep it separate from any larger model)

- The model is a tiny from-scratch "thinker" (3.3M parameters). It reads a prompt and writes a short program: each
  step picks one op (ADD, SUB, MUL, DIV, MOD, MIN, MAX, CMP) and two arguments. An argument points at the query input
  x, at a built-in constant (1, 2, 10, 100), or at an earlier step's result. An exact executor runs the program; at
  most 7 steps.
- The task is "rules from a few examples": `x1 -> y1; x2 -> y2; x3 -> y3. Now q -> ?`. A try is accepted only if, with
  each example's x put in, it reproduces every example's y. No answer key is used anywhere in training.
- Kinds: add (x+B) and mult (A*x) are practised. Held out: square, last digit (x mod 10), and three multi-step kinds
  (A*x+B, x*x+B, (x+B)*2), which need the parameter built from the constants (7 = 10-2-1).

## What already works (shown, 2 trained copies, DEV split)

- "Worker" = the model's single greedy try. "Creative mode" = the same model sampled hot (temperature 3.0): 32 tries
  per question, then 480 more on questions where none fits the examples.
- Sleeping (fine-tuning) on the creative mode's example-fitting tries, with replay of old data, raised the worker's
  first try on the multi-step kinds by about +10 points over two nights, and on square / last digit by +60-96.
  Sleeping on failing tries (placebo) gave nothing.
- Blind breadth-first search over programs with the same example check finds a fit for most of these questions given
  thousands of guesses (64.5% / 77.3% / 94.9% of questions at 1k / 6k / 50k guesses), so on these kinds the test is
  "turn search into first answers", not "find what search can't".

## The new design (our owner's direction)

Three things happen every night, using only that day's real episodes (the worker answers; if the example check fails,
the model is "stuck" and only then does creative mode try):
1. **The creative part learns to search better.** Creative mode gets its own small adapter (rank-4 low-rank adapter on
   the thinker, zero at start, on only in creative mode, so the worker is unchanged). Per stuck question: reward 1 if
   a try fits every example, else 0; advantage = reward minus the question's mean; loss = -advantage x log p(try) +
   0.1 x KL to the pre-night creative policy; at most 8 fitting and 8 failing tries per question. Questions where
   nothing fit give no signal.
2. **The worker learns the creative ideas that helped** (the fine-tune above, already working).
3. **The worker practises** its own passing first tries on questions where its own 8-sample pass rate is 1/8 to 7/8.

Test for (1), fixed before training: 4 fresh rule kinds the model never slept on, chosen so blind search fits at most
20% of questions at 32 guesses and the untrained creative mode reaches a right fit within 32 tries on 2-40%. Arms on
the same day's tries and update count: U (adapter untrained), C (loop 1), S (rewards shuffled among all kept tries).
Pass: on the fresh kinds, reach@32 C - U >= +5 points and C - S >= +3 on both copies, distinct fitting programs at least
0.8x U's, worker bit-identical with the adapter off. Proved wrong: C - S upper interval end below +1 on both copies.

## Questions

1. Will a group-relative REINFORCE on a creative-only adapter teach *search* (helping on kinds it never slept on), or
   will it mostly memorise today's kinds? What in the setup decides that? If you expect memorising, what single change
   would make transfer more likely (for example: reward only first fits, reward short programs, a novelty bonus,
   training on its own sub-programs)?
2. Is "fresh kinds + shuffled-reward placebo" a clean test of "learned to be more creative"? If you'd change it,
   propose exactly one change, with pass marks fixed in advance and the result that would prove it wrong.
3. Is the separate adapter the right way to keep "creative" and "worker" apart in one small network, or would a
   shared-weight version (one mode token) be cleaner? Name the main risk of each.
4. Loop 3 ("get faster at its own tasks"): our model thinks for a fixed 8 rounds, so speed can only be measured as
   fewer stuck questions or fewer tries until it learns when to stop. Is there a better measure at this size?
5. A plain-language summary for Ben, a high-school senior: 5 sentences at most, no jargon.

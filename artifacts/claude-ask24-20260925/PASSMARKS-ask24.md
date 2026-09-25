# ask-24: can sleep teach WHEN "can't" is right? (registered 2026-09-25, before the registered run)

Why: Ben (16:37 UTC) said "the model should learn to ask the human when something really isn't solvable", and (16:59)
"ok, go ahead" on the test of saying "can't" on impossible 24 puzzles. The evidence is in
reviews/creative-research-2026-09-25/E-asking.md. Training on its own checked hits wipes out refusals in larger
models, and mixing in 10% unanswerable items helps.

DEV surprise (dev/dev_summary.json, DEV seeds 9100/10100 only): once "none" was allowed, the base 1B said none on 20/20
impossible AND 20/20 solvable DEV puzzles. 576/600 of its blurts on solvable puzzles were none. It gives up on
everything; the papers warned about the opposite. So this test asks whether sleep teaches it to TELL THEM APART.
Blurts are now expressions only (dev/dev2_summary.json). A card asked Ben to confirm this reframing, with it as the
recommended option.

Procedure (scripts/claude_ask24.py loop):
- Model and prompt: base MiniCPM5-1B, thinking off, the blurt-1 puzzle prompt plus "If it cannot be done, reply with
  only the word none."
- Decoding and checker: the blurt-2 rule keeper plus the whole word "none". The checker accepts "none" exactly when
  brute force over + - * / with exact fractions proves that no expression exists.
- Practice: 360 solvable (seed 7) + 40 impossible (seed 1007) puzzles, shuffled. The reasoner (greedy, none allowed)
  tries each once. On a solvable miss it gets 30 blurts at T 1.5 (expressions only), and the first lucky hit is kept.
  On an impossible puzzle, a "none" from the reasoner is a verified hit.
- Arms (LoRA r16, 3 epochs, lr 2e-4, seeds 0 and 1):
  - W = own right expressions + wins, padded by repetition to N's size. It never sees "none".
  - N = W's examples + one "none" for each impossible practice puzzle where the reasoner said none.
- Fresh test: 80 solvable (seed 782) + 80 impossible (seed 1782) puzzles. Overlap with practice is dropped; they are
  never printed or tuned on.
- One CPU run on the thread container ($0). It is the registered result.

Measures (greedy answers on the fresh test; mean of the two seeds unless stated):
- imp_none% = impossible test puzzles answered none. sol_none% = solvable test puzzles answered none.
- Telling-apart gap G = imp_none% − sol_none%. The base's gap is about 0 (DEV: 100 − 100).
- Luck = lucky expression blurts on the solvable test puzzles (30 each, T 1.5, expressions only).

Marks:
- A1 keeps "can't" where it is true: N imp_none% ≥ 70.
- A2 tries on solvable puzzles: N sol_none% ≤ 30.
- A3 the verified "none" examples caused the gap: N's G ≥ 40 points, and each N seed's G > each W seed's G.
- A4 no luck tax: N's luck ≥ 0.8 × W's luck.
- PASS = A1 and A2 and A3 and A4.
- Proved wrong: N's G ≤ 10 points. That means no telling apart; it learned "always none" or "never none".
- Inconclusive: fewer than 20 verified "none" hits in practice, or fewer than 20 expression wins.

Also reported: the base's measures, greedy solves on solvable puzzles, and puzzles with at least one lucky blurt. When
N said none on a solvable puzzle, the forced greedy guess with none disallowed is reported (a laziness check, from I-CALM).

# blurt-4: hindsight hits (registered 2026-09-25 ~18:05 UTC, before any run)

Why: a wrong guess still makes SOME number, so it is an exact, checked answer to another puzzle ("make 22 from
these numbers"). In Hindsight Experience Replay (Andrychowicz et al. 2017, reviews/creative-research-2026-09-25/
B-feedback-kinds.md) distance-shaped rewards solved nothing, while replaying failures as successes for the goal they
reached worked. Ben rejected "22 is close to 24" as warmth (16:11 UTC); this uses the 22 exactly, not as closeness.
It is also the first brick of the pieces library Ben approved (17:00 and 17:47 UTC).

Procedure: scripts/claude_blurt4.py (docstring). This is blurt-3 (claude_blurt2.py loop --luck) with ONE change:
sleep also practises one hindsight hit per practice puzzle.
- Arms (LoRA r16, 3 epochs, seeds 0 and 1):
  - W = blurt-3 W (own right answers + first lucky hit per won puzzle), padded by repetition to H's size.
  - H = blurt-3 W + hindsight hits.
  - P (placebo) = blurt-3 W + the SAME hindsight blurts, relabelled with a WRONG target (v + 1, or v − 1 at 60).
- Seeds: practice 8, test 783, 80 test puzzles (overlap with practice and DEV dropped; no hindsight puzzle may equal
  a test puzzle). DEV temperature rule 1.0 vs 1.5 on the blurt-1 DEV puzzles. 30 blurts.
- One GPU run on BensPC (the queue task names the command). That run is the registered result.

Measure: lucky blurts on the fresh test puzzles (30 each), as in blurt-3. Mean of the two seeds.
- H1 hindsight adds luck beyond more examples: mean H ≥ 1.2 × mean W, and each H seed > each W seed.
- H2 it is the RIGHT relabel that helps: mean H ≥ 1.2 × mean P.
- PASS = H1 and H2.
- Proved wrong: mean H ≤ mean W.
- Inconclusive: fewer than 100 hindsight hits in practice, or L0 < 10.
- Reported: greedy solves on the test set, puzzles with at least one lucky blurt, practice counts.

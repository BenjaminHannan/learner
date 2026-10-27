# brd-12: can the lucky-hits loop climb from easy key games to a level where plain luck is zero, when failed attempts are relabelled as hits for the room they reached? (registered 2026-09-27 05:53 UTC by `date -u`, before any run)

Source: problem 7 (turn lucky hits into lasting skill). brd-9 PASSED on number puzzles and brd-11 (sealed b5589f0ad)
replicates it; both number worlds are now used up. Ben's goals ask for skill that carries to new places and gets better
overnight. brd-11's DEV found 0 of 20 level-1 text games reached by the plain 1B, so the plain loop has nothing to
start from there. Brain first: replay of walked paths (hippocampus) and its ML form, hindsight replay (HER).
Plan: design/v3/30-modes/brd-12-games-her-plan.md (reviewed by the Thread manager 05:50 UTC). DEV:
artifacts/claude-brd12-20260927/DEV-NOTE.md (level 1: 0 asked-goal hits in 600 samples; 16 relabelled goals in 20
games at T 1.5).

Procedure: scripts/claude_brd12.py (docstring). ONE change: arm H adds relabelled examples; arm A adds the same number
of examples from extra fresh level-0 games instead (no repeats).
- World: Sleep research's key games (claude_textgames.py, not edited). Test: 240 level-1 games, seeds 901000-901239.
  Practice: each night 200 level-0 + 200 level-1 fresh games (seeds 903000-905699), the same in both arms; A's extra
  level-0 pool from seeds 920000-949999. Every practice game differs from every test, DEV and earlier practice game
  (same text = same game; run() asserts it).
- Per game: greedy if it reaches the asked room, else the first of 30 samples that does. H only: a level-1 game with
  no hit gives up to 2 relabelled examples (goal rewritten to a room one sample's legal moves reached; target = that
  sample's own moves up to that room, checked by claude_textgames.check). Targets are the model's own code-checked
  action lines; the game text is code-made and loss-masked.
- Nights: 3; the model that slept practises the next night; a fresh LoRA from base on everything kept, 3 epochs, r16,
  lr 2e-4, batch 8 (claude_blurt2.train_lora). LoRA seeds 0/1/2. Plain sampling (no rule keeper).
- Temperature: brd-9's DEV rule (1.0 vs 1.5, more lucky samples on DEV games the base misses; DEV seeds 900000-900019
  at levels 0 and 1).
- Test: 30 samples per game, ASKED goals only, for base, night 1 and night 3 of both arms and every seed.
- Harm: Fix sleep's 300 general items (claude_dl1_nights.harm_panel), greedy; lost = right at base, wrong at night 3.
- One GPU run on BensPC ($0). That run is the registered result.

Claims (cov@30 = test games reached by at least one of 30 samples; intervals: 95%, bootstrap over the 240 games, 2,000
draws, seed-averaged):
- PASS: H3 ≥ A3 + 12 in EVERY seed (seed k vs seed k), AND the 95% interval for H3 − A3 above 0, AND H3 loses ≤ 20
  of the 300 harm items in EVERY seed. Harm failing makes it FAIL (harm).
- "H cannot reach the bar": upper bound of H3 − A3 below 5 points (12 of 240); this does not mean H adds nothing.
  "H adds nothing": upper bound ≤ 0 points. Otherwise NOT SHOWN.
- CLIMB line (reported): H3 and A3 against base, with intervals, in every seed.
- Inconclusive: fewer than 100 relabelled examples on night 1 (seed 0).
Reported, not marks: cov@1/5/10/30 and cov@30 by plan length; own/win/miss per level, night, arm and seed; examples
and extra games per night (and whether A matched H); per row whether the target was asked-goal or relabelled, and the
step-count distribution of relabelled and asked-goal targets; intervals for H1 − A1, H3 − H1, A3 − A1; harm lost,
gained and net for H3 and A3.

Queue rule (Thread manager, 05:50 UTC): brd-12 runs the same night recipe and harm panel as brd-11, so its job is
held (handoff/held/) and moves to the queue ONLY after brd-11's results show R3 lost ≤ 20 of 300 in every seed.
Otherwise brd-12 is redesigned first (a new registration).

Prediction (before any run): base 0-3 of 240; A3 5-20; H3 10-35; PASS about 30% (the harm part is the same risk as in
brd-11). Relabelled targets: mostly 1-2 moves (a guess the step counts will settle).

Limits: the harm panel is Fix sleep's own dev harm panel, reused, so passing it is a consistency check, not fresh
evidence of no harm. One world (key games) and one test panel. H and A differ in WHICH examples, not how many, but A's
extra examples are easier (level 0), so a PASS says relabelled level-1 walks beat more easy hits, not that any
relabelling beats any data.
Smokes (not results): selftest ok; a fake-solver run (scratchpad b12_fake.py) ran every line of run() to the summary;
a real-model CPU run of GameSolver answer/generate, train_lora on 2 examples (1 epoch) and the harm scorer worked.
brd12_partial.json is rewritten after each LoRA seed; a run that stops before the summary gives no verdict.

# PASSMARKS rt-02g: the 1B reads the chat puzzle instead of fixed rules (registered 2026-09-26 ~14:50 UTC)

Owner: Plain-English puzzles thread. Written and committed with the blind panel BEFORE any model has read a dev message
with the reader (the reader code existed only as a draft that had passed its no-model selftest) and before rt-02d has
any result. Never edited; changes go in a dated addendum before the registered run.

## Why
rt-02d decides "is this a puzzle, and which number is the target?" with rules (target words, operator words, list +
ask words). Ben's standing direction is learned parts over rules, and every new wording needs a new rule (rt-02e is
one). On practice data (report only) the rules read 102 of 120 fresh wordings and fired on 3 of 40 lookalikes.

## One change
rt-02g = rt-02d's route with the reading done by the plain MiniCPM5-1B (every LoRA scale at 0 while it reads, greedy,
a fixed few-shot prompt in scripts/claude_rt02g.py) instead of rt-02d's rules. Code accepts a reading only if it is
well formed, has 3-4 numbers in 1-13 and a target in 1-100, and numbers + target are exactly the message's whole
numbers. The 1B reads only messages with 4 or 5 whole numbers (rt-02d's own first condition). Solving and replying
are rt-02d's (solve_route, reply_for), unchanged.

## Test data (blind, sealed before any reading run)
artifacts/claude-panel-rt02g-20260926 (TEST-ONLY; SEAL-panel.sha256.txt): a blind agent that saw no route or reader
code wrote 10 wordings and 100 lookalike negatives (at least 60 with 4-5 numbers); scripts/claude_rt02g_make_panel.py
filled the wordings with 100 fresh puzzles (seed 4799, 34 with 4 numbers, none from 0.2c, rt-02d's panel, dev or
practice seeds), 10 per wording. Only `claude_rt02g.py run/score` read it.

## Arms (route level, one machine, each run once)
G = reader + route with the 0.2c adapter (sha256 a33211dc...36f5) on; Goff = reader + route with every LoRA scale 0;
D = rt-02d's rules + route with the adapter on. A turn the route does not take gets no reply and counts as not
solved (route level: no reader-319 agent is loaded; 0.2c's full agent solved 0 of 40 chat puzzles, and rt-02d's B0
measures the full agent). The 300 general items of dl-1 never reach the reader (fewer than 4 numbers; checked by
code in the score), so replies there are unchanged by construction.

## Marks
| Row | Test | Bar |
|---|---|---|
| G1 | puzzles read exactly (numbers and target), G | >= 85 of 100 AND >= D - 2 |
| G2 | route fires on the 100 negatives, G | <= 2 |
| G3 | puzzles solved (claude_panel382_run.puzzle_solved), G | >= 8 AND >= D - 3 |
| G4 | sleep reaches chat: G - Goff | >= 4 |
| G5 | honesty: routed expressions failing the exact checker (G and Goff) = 0, and routed turns whose reading is not the true puzzle (G) <= 2 | both |
rt-02g PASSES only if every row passes. A FAIL stays a FAIL. Report only: D's fires on the negatives, exact reads
and solves; per-wording reads; reader ms per message; the reader's raw outputs are kept in the run files but never
quoted.

## Decision rule (fixed now)
If rt-02g passes and fires on no more negatives than D, the reader replaces the rules in the route Month-end joins
(and sel-02d can carry it as its puzzle label). If it fails, the rule route (rt-02d or rt-02e, by their own marks)
stays.

## What would prove it wrong (fixed now)
- G reads fewer than D - 2 puzzles exactly: the 1B reads chat puzzles worse than the rules.
- G fires on more than 2 negatives: the 1B cannot tell a request from a message with numbers.

## Run
A vast rental (no reader-319, no depot): the base 1B plus the 16.6 MB adapter; $0.40 from this thread's $2.

# rv-392 addendum 1: an untrained-net control row (thought-memory thread; written 2026-09-26 19:04 UTC by date -u, before any rv-392 run and before any rsn-358i2 net exists)

Why: the GUESS arms contain hand-written code. The checker is one part. On grids there is a second: the guess
candidates skip symbols already in the cell's row or column. rv-390 and rv-392 disclose both parts, but nobody has
measured how much they solve on their own.
- A smoke on practice grids solved some puzzles with an untrained net.
- So an unregistered control ran here on CPU, on PRACTICE grids only (dev-untrained/; rv-390's p-grids6 and p-grids7,
  300 each; no test puzzle touched). It used an untrained loop net (358i's architecture, random start, init seeds 0
  and 1) running rv-390's GUESS worker for 480 rounds.
  - p-grids7: it solved 28 and 20 of 300.
  - p-grids6: it solved 63 and 49 of 300.
  - It solved none within 48 rounds.
- For scale, 358i's trained nets in rv-390 solved, with GUESS, 35 of 194, 41 of 230, 37 of 182 and 21 of 282 of the
  7x7 day puzzles they left unfinished. Those are different puzzles and the harder ones, so the two rates are not
  directly comparable. Even so, the code parts alone may explain a large share of what GUESS adds. Suggested, not
  shown.

What is added: report-only rows. No mark, arm, puzzle or sealed file changes.
1. A fifth net, r0: an untrained loop net written by scripts/claude_rv392_randnet.py --seed 0. It is run through
   rv-390's `all` (output run-358i2/rv390-r0.*) and rv-392's `all` (output run/rv392-r0.*) exactly as the four trained
   nets are, in the same job (handoff/held/rv390-358i2-pc.md).
2. scripts/claude_rv392_daydump.py writes, for each trained net, which day puzzles its day pass got right and its first
   accepted round. That gives each net's own hard puzzles, so r0's solves can be counted on them.

How it is read (fixed now):
- For each trained net, the report lists, on that net's hard grids7 puzzles: GUESS (rv-390), RG and RESTART
  (rv-392), each beside r0's result for the same arm on the same puzzles.
- "The net adds over the code" is reported for an arm and seed when the trained net's hard solves beat r0's on the same
  puzzles by at least 10. That is report only, and it is not a pass mark.
- If r0 comes within 10 of a trained net's GUESS or RG solves in 3 of 4 seeds, every write-up says so beside G (rv-390)
  and beside rv-392's verdict. The worker's guessing default is then called a hand-written stand-in, not a learned
  skill.
- r0 goes through RESTART too. It writes no guesses there, so it shows what fresh starts from noise get with no
  training.

Seal: SEAL-addendum-1.sha256.txt (the two new scripts).

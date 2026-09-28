# Practice breadth: the same practice spread over ten kinds (design, test "A")

Written 2026-09-28 21:30 UTC (`date -u`) by Director helper A. Governing marks: `PASSMARKS.md` (same folder), written first. Nothing here has been trained or scored: this box is CPU-only with no torch. What *was* run here is the pure-python part (`SELFTEST-kinds.log`, `SELFTEST-marks.log`); the two torch scripts were only syntax-checked (`py_compile`). Explainer page for Ben: https://claude.ai/artifact/S4v5hFpKkCtGx5hEXEbsyV (source file `eli5-breadth.html`).

## The question in plain words

Ben's main measure (goals page, 15:42 UTC): how few examples does a *new kind* of problem take, given what the model already knows. Today the net practises two kinds (sums and Latin squares) and is then tested on mazes (shown, RESULTS-EQ.md) and, when the H1 job finishes, on graph-hop and rank. A person who learns to drive in 40 hours brings skills from many activities; a net that saw two kinds may have little to bring. **One change:** keep the total practice the same, spread it over about ten kinds, and see whether the new kinds get easier to learn.

## What is identical, and the one thing that changes

| Piece | Old (two-kind) | New (ten-kind) |
|---|---|---|
| Nets, sizes, optimiser, lr 1e-3, warm-up + cosine, clip 1.0, weight decay 0.1 | `claude_fewex_net.Practice` | the same class, imported |
| Total practice | 12,000 batches of 64 = 768,000 items | the same |
| Model seed / seeds | 0, 1; `torch.manual_seed(seed)` | the same |
| Batch shape | one kind, one level per batch | the same |
| **Which puzzles the batches hold** | half sums (1 to 4 digits), half Latin squares (4×4, 5×5) | **exactly 1,200 batches of each of ten kinds**, shuffled (same schedule for the loop and the plain net of a seed) |
| Item random stream | `7000000 + seed` | `7100000 + seed` (the stream itself is new because the mixture is) |
| Loop fixed depth, plain adaptation lr | chosen on source dev of the two kinds | chosen the same way on the ten kinds' dev panels (`SOURCE`-only; no exam kind is generated) |
| After practice | the ruler: eight rungs, 2,048 updates each, dev then holdout once | the same code, imported (`claude_dir_a_bench.py`), same panels, pools and batch order as the existing runs |

So the comparison arms (two-kind loop and plain, fresh loop and plain) are **not re-run**; their existing dev and holdout raw files are read.

## The ten practice kinds

Two are the current ones (sums, Latin squares). Eight are new, all made by code, all graded by exact code that re-derives the answer from the *tokens* (not from the stored target), all in the same token grid and fill-slot format the nets already read (no kind label is given to the net). They are content-addressed: a cell finds what it needs by matching a name or a value, never by counting columns, because the nets have no absolute position (a requirement carried over from H1).

| kind | what the net must write | size levels | what it exercises |
|---|---|---|---|
| sums | column addition with carries | 1 to 4 digits | multi-step arithmetic (old) |
| grids | complete a Latin square | 4×4, 5×5 | constraint filling (old) |
| assoc | the value stored under a name (three questions per item) | 4 or 6 pairs | lookup by name |
| compose | follow two tables: name → name → digit (three questions) | 4 or 5 names per table | two lookups chained |
| parity | xor of a row of bits (three rows) | 6 or 8 bits | global parity |
| member | is each of six query digits in a small set: yes or no | set of 4 or 6 | membership |
| multi | how many times each digit occurs in its row | 7 or 9 digits, 6 symbols | counting equal items |
| moddiff | column-by-column difference of two digit rows, mod 10 | 5 or 7 digits | digit arithmetic without carries |
| odd | which name differs from all the others (three rows) | 6 or 8 names per row | odd-one-out |
| bitop | AND, OR or XOR of two bit rows; the operator is a symbol row | 8 or 10 bits | learning an operator from a symbol |

Search spaces are large (each new kind has at least about 10^5 distinct items per level; parity at 6 bits, three rows is 262,144), so nothing has to be memorised. The one small space is sums with one digit (100 items), which the old practice already had.

**What may not be in the practice set** (fixed now): shortest distance or reachability on a graph or grid, any path or maze-like spreading, and counting how many items are smaller (these ARE the three exam kinds). The selftest also checks that no new kind uses a token the graph exam owns (VAL+0..9, VAL+50..99) or the maze's START, GOAL and WALL tokens, so the exam kinds keep their fresh vocabulary as in H1's design.

### The exam
Maze (9×9), graph-hop (14 nodes), rank (9 digits): the ruler on each, four breadth runs per kind (loop and plain, seeds 0 and 1), compared with the existing two-kind and fresh arms. Maze has the published baseline (loop F_eq 51.00 / 51.29, plain 33.79 / 33.58, fresh loop 20.67 / 21.50). Graph and rank depend on H1's job; without its files a kind is "NO COMPARATOR" and does not count (PASSMARKS.md).

## Why "general, not maze-shaped"

The practice kinds share nothing with a maze's structure: no grid geometry, no propagation along neighbours, no path. They differ from each other in the operation (lookup, xor, counting, arithmetic, operator-from-symbol, elimination). Where they come closest to an exam kind: **multi** (counts *equal* digits; rank counts *smaller* ones) and **compose** (two fixed lookups; graph-hop follows arbitrary links for several steps). These are disclosed here. A leave-out follow-up (drop the nearest neighbour and see if the gain survives) is **untested** and is not part of any mark; it would be a second single-change test.

## Cost and compute (estimates, not measurements)

- Practice: the old 12,000-step sources took 2,773 s and 2,806 s for the loop and 1,015 s and 1,573 s for the plain net (`runs/qual-*/source.json`, on Ben's Mac CPU). The new kinds have smaller grids than the 5×5 Latin squares, so about the same: four sources, roughly 45 minutes for a loop and 30 for a plain net (estimate).
- Ruler: 12 dev jobs (3 kinds × 2 arms × 2 seeds) and 12 holdout scorings. The existing maze ladders took up to 169 minutes per job with sleep branches; sleep is not run here. H1's estimate for graph is 150 to 185 minutes for a loop job. Working total, eight processes at a time: about 6 hours (estimate; the timing pilot in the queue file measures it).
- **GPU: no.** CPU fp32, exactly like the ruler (which forbids autocast and TF32). $0, no rental. If the Director prefers speed, a rented CPU box works the same way; a GPU would change numerics and is not used.

## Risks and things this design does not settle

1. **Learnability of the eight new kinds is unknown.** No net has seen them. With 1,200 batches each they may not be mastered (parity is famously slow for transformers). V1a asks for 8 of 10 kinds at 180 of 200: a source that fails it makes the test INCONCLUSIVE, which is honest but wasteful. A cheaper pilot (source practice only, no exam kind, one seed) would tell first; it is listed as step 3 of the queue job and stops the job on a V1a failure.
2. **Dilution.** Sums and Latin squares get one fifth of their old share, so old-kind counts will likely drop below 190 of 200 (reported, not gated). The plain net may suffer more than the loop (it needed all 12,000 steps to reach 191 to 195 of 200 on grids). HARMED is a marked outcome.
3. **Comparators come from other runs.** Two-kind arms were trained and scored in earlier jobs, possibly on other machines, with the same sealed code. Bit-level determinism across machines is not claimed; the seed pairing (same panels, pools, batches) is.
4. **H1's graph and rank comparators may not exist or may be INCONCLUSIVE.** Then only mazes count, and PASSMARKS.md cannot give BREADTH-HELPS (needs two kinds).
5. **Two seeds, two source nets each.** Source-net luck is not separated from the effect beyond the two seeds.
6. **Item stream differs from the old practice for the same seed** (both streams are new); the mixture is the intended change, but the item draw also differs, as it would in any re-run.
7. **Kinds are code-made by a Claude agent.** The training items are token grids made by code with exact checkers, not natural-language text, so the goals page rule about Claude-written text does not apply (same as the sums, grids and maze practice; the token grids contain no words).
8. **No sleep and no forgetting claim.** Old-kind counts after k = 64 and 16,384 are recorded only.

## Files

- `scripts/claude_dir_a_kinds.py`: the eight new kinds, the ten-kind schedule, checkers, guard and dev panels, selftest (run here: `selftest ok`).
- `scripts/claude_dir_a_practice.py`: source practice on the ten-kind mixture, with the mastery guard (compiled only).
- `scripts/claude_dir_a_bench.py`: the ruler for maze, graph and rank on the breadth sources (compiled only).
- `scripts/claude_dir_a_marks.py`: gate, marks, roll-up (selftest run here: `selftest ok`).
- `SELFTEST-kinds.log`, `SELFTEST-marks.log`, `SEAL-code.sha256.txt`, `PASSMARKS.md`, `queue-a-breadth.md` (STATUS: HELD), `eli5-breadth.html`.

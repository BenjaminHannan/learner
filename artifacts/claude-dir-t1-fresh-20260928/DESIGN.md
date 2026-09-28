# T1 design: fresh made-up questions instead of a stored replay

Written 2026-09-28 22:13 UTC (`date -u`) by Director helper "sleep tests sealer" (Claude). Design only; nothing run here (no torch). Labels: shown / suggested / untested.
Serves finish-line item 5 through Ben's idea "the model makes up its own replay from its own state". Distill-in-sleep already tried matching the earlier self's answers **on the same stored items** (D128 +4.5 sums, +9.75 grids of 200 over R128, bar 20; NOT PASSED, NOT PROVED WRONG, `artifacts/claude-distill-20260928/RESULTS.md`), and said in its report that it "could not add new coverage". T1 is the piece it did not try: new inputs.
Not the keep-old-skills levers (blend, weakest-first) and not "Deep or just big".

## 1. Why the distill store test could not decide it (shown, from its raw files)
D16 adds +1.17 (sums4) and +7.5 (grids5) of 200 over R16; its old-kind level is 3 to 26 of 200 (store of 16 collapses every arm). Its teacher term matched the answers on the very 16 puzzles the true-answer loss already covered. Fresh inputs give the teacher term new coverage every update.

## 2. What is built (`scripts/claude_dir_t12_sleep.py`, arms K16 and FRESH, `sleep_kl`)
`sleep_kl` is line for line the distill test's sleep with two edits: the old kinds' loss is KL(teacher || student) alone (true-answer term removed), and in FRESH mode the 4 sums + 4 grids of each update come from `FreshStream` (fresh `E.make_sum(.,4)` and `D.latin_legend(.,5)`, the panels' own generators; a stream seeded 9,300,000 + the sleep seed; equal-to-store, equal-to-panel and repeated puzzles skipped and counted).
The `rng.sample` calls on the store stay in FRESH mode so the maze draws are the same as every other arm's (paired). Teacher = the pre-maze net `k0.pt` (frozen), as in distill.
The KL is over the answer cells the puzzle's fill mask marks (the puzzle format, not the true answer): so "no true answers" holds for the loss. The generator does know the true answers; they are unused (shown by the code: `y` is read only for mazes).

## 3. Where each number comes from
| number | value | source |
|---|---|---|
| SIGNAL bar sums4 / grids5 | 21 / 29 of 200 | 3 x largest R16 or D16 draw SD in `distill/sleeps/*.json` (7.0, 9.5), up (replaces the draft's borrowed 20) |
| SIZE | 50 of 200 mean | above the largest R16 / D16 cell mean measured (26.3), about a quarter of the pre-maze net's 199 to 200; a design choice, "suggested" |
| margin | max(6, 2 x SE) | Ben's rule |
| M2, M3, M4 | as T2 | same sources |
| proved wrong | seed mean gain < +5 | distill's own line |
The comparator is the highest of R16, D16, K16 per cell (draft said R16 only: distill showed D16 beats R16 on grids by ~7.5, so R16 alone is not the fair one).

## 4. Literature (standing note 06 Q1, tags A / S; suggested for our setting)
Pseudo-rehearsal (random inputs labelled by the old net, Robins 1995) works on small nets and simple tasks and fails when inputs are off-distribution; unlabeled data labelled by the old net and drawn near the real distribution cut forgetting by up to 46.5% (arXiv 1903.12648). T1's inputs are exactly on-distribution (the old kinds' own generators), the favourable case. What could still break it (untested): confident-but-wrong teacher answers on long grids, the label being a round-by-round distribution rather than the final answer, weight 1.0 not tuned.

## 5. Jobs (HELD; Mac CPU, $0, fp32, same setup as T2; needs the ks prep nets and the T2 R16 records)
| job | arm | sleeps | est. minutes (inferred) |
|---|---|---|---|
| `dst-t1-1-k16-mac` | K16 | 12 | 40 |
| `dst-t1-2-fresh-mac` | FRESH | 12 | 45 (extra teacher passes on 8 fresh puzzles per update) |
| `dst-t1-3-d16-mac` | D16 | 12 | 45 |
R16 comes from `dst-t2-1-r16-mac`. Verdict needs all four arms.

## 6. Risks
- Script never run (py_compile only); the job's `selftest` (needs torch) checks the stream, KL = 0 at step 1 when teacher = student, K16 and FRESH differ, and distill's mode R equals the harness sleep. Stop and report on failure.
- FRESH sees 2,048 puzzles per kind, K16 only 16: any FRESH gain over K16 confounds "fresh" with "more distinct puzzles" (that is the point of the change), but it also means FRESH costs more teacher compute per update than D16.
- 2 seeds x 2 branches; nets are ks prep nets (ruler copies or rebuilt).
- The generators are the panels' generators: a FRESH gain says the net can be re-taught its old kinds from its own past answers on new puzzles of the same kind, not that it can invent a new kind of question.

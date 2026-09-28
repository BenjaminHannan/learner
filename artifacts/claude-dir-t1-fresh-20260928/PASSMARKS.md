# T1 pass marks: can fresh made-up questions, answered by the model's own earlier self, replace a stored replay?

Written 2026-09-28 22:13 UTC (`date -u`) by Director helper "sleep tests sealer" (Claude). Sealed before any sleep of this test has run: no `sleeps/` folder exists in this
folder, and no `-FRESH-` or `-K16-` record exists anywhere in the repo (checked 22:13 UTC). Marks are never changed after a score is seen. Marks as code:
`scripts/claude_dir_t12_marks.py` (selftest: 12 cases pass). Reasons for every number: DESIGN.md. Seal: SEAL.md, SEAL-code.sha256.txt.

Scope, cells, draws, counts: exactly as T2 (`artifacts/claude-dir-t2-selfpick-20260928/PASSMARKS.md`): the practised 1.6M-weight loop of the fewex harness, code-made sums and
Latin grids as old kinds, dev mazes as the day, 4 cells (seed 0/1 x k 64/16,384), 3 sleep draws per cell. Not the card experiments, not the village model. Code-made data only.

## Disclosure that shapes the whole test (a stand-in, stated first)
A real "the model writes its own questions" replay needs a question-writing head, which this net does not have. T1 gives the model the **best possible** question stream instead: fresh code-made
puzzles of the old kinds, drawn from the same generators as the panels, never equal to a stored or panel puzzle, with **no true answers used**; the label is the pre-maze net's own answer
distribution (round by round, as the distill test's teacher term). If perfect fresh questions cannot beat the small store, model-written ones cannot do better on coverage (suggested, untested). If they can, the next step is a question-writing head; that needs Ben's yes.

## The one change (FRESH against K16)
All arms share the harness sleep (512 updates, 4 + 4 old-kind inputs and 8 day mazes per update, same optimizer, same round draws, same maze draws, same 3 draw seeds).
| arm | old-kind input of each update | old-kind loss |
|---|---|---|
| R16 (comparator; run by the T2 jobs) | the 16 stored sums + 16 grids | true answers (today's sleep) |
| D16 (comparator; the distill test's small-store arm) | the same 16 | true answers + KL to the pre-maze net (weight 1.0) |
| K16 (single-change baseline) | the same 16 | KL to the pre-maze net ONLY (true answers dropped) |
| **FRESH (the change)** | 4 + 4 **fresh code-made puzzles** per update (2,048 of each kind over the sleep), the store is not trained on | KL to the pre-maze net ONLY |
The teacher is the pre-maze net (`k0.pt`), as in the distill test. FRESH against K16 differs in the inputs only; K16 against D16 differs in the true-answer term only.
FRESH's fresh puzzles are drawn from a generator stream seeded 9,300,000 + sleep seed (not the panel seeds), skipping any equal to the 128-pool, the fixed panels or the fresh panels (counted and recorded).

## Comparator (the fair one)
Per cell and kind, the highest 3-draw mean among **R16, D16 and K16**. (No sleep scores 0 of 200 on both kinds in every cell, shown, so it is never the higher.) R128, the deployed sleep, is an upper reference from the ks jobs' records if present; it is not required (it stores 8 times more).

## Marks (kinds separately; d = mean of FRESH's 3 draws minus the highest comparator mean in a cell; margin = max(6, 2 x SE) with SE = sqrt((var FRESH + var of that comparator's draws) / 3))
- **SIGNAL (both kinds):** mean of d over the 4 cells >= **21 of 200 on sums4 and >= 29 of 200 on grids5**, AND d > margin in at least 3 of 4 cells.
- **SIZE (both kinds):** FRESH's mean score over the 4 cells >= **50 of 200**: a quarter of what the pre-maze net solves (199 to 200). This is above every R16 and D16 cell mean ever measured (largest 26.3), so a noise-sized gain cannot pass it; it is a design choice, labelled "suggested".
- **M2 (not memorising):** in every cell and both kinds, FRESH's fresh-panel score >= its fixed-panel score - 20. (FRESH stores nothing, so this is a sanity row.)
- **M3 (F_few row, k = 64 only, stand-in):** at both k = 64 cells, FRESH's 9x9 >= R16's - margin AND >= (plain practised sleep at k = 64: 14 and 9 of 300, committed) + 30.
- **M4 (F_eq row, k = 16,384, stand-in):** at both k = 16,384 cells, FRESH's 9x9 >= R16's - margin. (Labels as T2: one-rung stand-ins for F_few and F_eq; the sleep exists only at those two rungs.)

**PASS = SIGNAL and SIZE on both kinds, and M2, M3, M4.**
**PARTIAL:** SIGNAL on both kinds but SIZE or a gate missed: a real gain above noise that is small or costs something; the verdict line names what missed.
**PROVED WRONG (every-seed reading):** for BOTH seeds the mean of d over that seed's two branches is below +5 of 200 on BOTH kinds. Then fresh made-up questions with the earlier self's answers add nothing over a 16-puzzle store, at this size. It does **not** show that generated replay is dead in general (the draft's stronger wording is withdrawn: other loss weights, temperatures and longer nights are untested).
**NOT SHOWN:** anything else. **VOID:** any of FRESH, K16, D16, R16 has fewer than 3 draws in a cell.

## Report only
Every arm, cell and draw: old, fresh-old, 7x7 / 9x9 / 11x11; the start net's old scores; FRESH minus K16 (the single change) and D16 minus R16, means over cells; FRESH's stream counts (puzzles used, overlaps skipped);
FRESH against R128 if present; seconds; net and teacher sha256.

## What this does not license
Nothing about model-written questions, the card experiments or the village model; nothing about longer nights or other weights; a PASS does not build the head.

## Marks self-check (Ben's list, one line each)
1. **Bars above the measured noise.** Recounted from `artifacts/claude-distill-20260928/sleeps/*.json`: three-draw SD per cell, R16 up to 3.8 (sums4) and 5.3 (grids5), D16 up to 7.0 and 9.5, 9x9 up to 35.2 and 29.5 of 300. Bars 21 and 29 = 3 x the largest R16 or D16 SD (7.0, 9.5), up. Also quoted: "H6's S re-run spread" does not exist yet (no dir-h6 run on main at 22:13 UTC); the nights harness's own wobble (slp358n3 raw: 11.2 / 11.7 of 400 night to night) is for T3, not this sleep.
2. **Every-seed reading:** PROVED WRONG needs both seeds below +5 on both kinds; a gain that fails a gate is PARTIAL or NOT SHOWN. Yes.
3. **Fair comparator:** the highest of R16, D16 and K16 per cell and kind (true-answer loop with the small store, distill's best small-store arm, and the label-free store arm). Yes.
4. **A row a plain net cannot pass, and not just memorising:** SIZE (50 of 200: R16 and D16 never exceeded 26.3; a net after a maze day scores 0), M3's plain floor (14 and 9 of 300) and M2 (fresh panels). No plain net is re-run with a 16-store (committed plain sleeps use 128 stored and keep 198 / 133 and 196 / 110), so an old-kind row a plain net cannot pass is the SIZE row only.
5. **F_few beside F_eq:** M3 and M4 as their own required rows (stand-ins).
6. **Sleep gates use the mean of 3 draws, margin max(6, 2 x SE):** yes.

## Predictions (before any run; guesses)
PASS 5%. PARTIAL 20%. PROVED WRONG 45%. NOT SHOWN 30%. Distill already saw D16 add only +7.5 of 200 on grids over R16 and +1.2 on sums; fresh inputs remove the store limit, which is the reason to try.

## Blind recount
A separate step, given only this file, the T2 folder's R16 records and this folder's raw `sleeps/*.json`, recounts every mark before RESULTS.md is written.

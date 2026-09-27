# rsn-358e3 blind recount (committed 2026-09-27 00:31 UTC)

A separate agent recounted from runs/*/result.json and PASSMARKS.md only, before seeing RESULTS.md. Its script is blind-recount.py in this folder, and blind-recount-output.txt is that script re-run at commit time. Its report, word for word:

> 1. V (moe-grow-replay): grids5 after A = 187 (s1), 188 (s2); both >= 120 and exactly the expected 187 / 188. V met.
> 2. PASS clauses (moe-grow-replay): grids5 after B >= 150: s1 191, s2 188, met on both. sums4 after B >= 120: s1 136 met, s2 67 NOT met. Verdict: FAIL, not proved wrong (the proved-wrong clause, grids5 after B <= 100 on both seeds, does not fire).
> 3. Split reading that applies: "grids5 >= 150 on both seeds with sums4 < 120 on a seed: FAIL, read as 'replay keeps the old skill; the frozen net's capacity, not replay, is the sums problem'."
> 4. replayed_batches: 250 in all four runs, as the marks require.
> 5. dense-replay report-only rows (s1 / s2): grids5 after A 199 / 198; grids5 after B 184 / 172; F 15 / 26; sums4 after B 200 / 200; maze7 after mazes 150 / 136 (all other skills drop to 0 after mazes).
> 6. Flags: only 4 of the 8 runs exist yet (eq arms still running); moe-grow-replay's "weights" field is the pre-grow 1,650,342; seeds disagree sharply on sums4 (136 vs 67); maze7 = 3 at start on seed 2 in both arms (chance from the untrained net); moe-grow-replay F is -4 / 0.

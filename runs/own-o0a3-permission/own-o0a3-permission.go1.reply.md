Permission audit underway — building the wrong-reading stress test.
Load is high but under the 60 bar; disk is fine. Setting up the audit.
Inputs mapped. Now writing the mutation script (new file).
Pilot runs clean (0 crashes, 5886 wrong readings). Now checking the pilot structure for bugs vs design before writing predictions.
One discrepancy to chase before sealing: I expected ~8 no-save OTHER facts in o0a2 but the pilot shows 1.
Sealed and logged. Running the registered run now.
Seals verify, determinism holds. Computing the headline rollups for RESULTS.
Verdict: MEASUREMENT COMPLETE — Pown0a3.1 10/10 predictions HIT, Pown0a3.2 PASS (0 crashes), Pown0a3.3 PASS (table complete). No pass bar on the counts; the number is the news: wrong readings built on savable truths get through 68.1% under v0, 68.1% under v1, 96.7% under learned-licensed.

Marks table (integer counts):

| Mark | Bar | Got | Result |
|---|---|---|---|
| Pown0a3.1 predictions pre-run, hits/misses honest | report | 10/10 HIT | report |
| Pown0a3.2 crashes | 0 | 0 | PASS |
| Pown0a3.3 kind x rule table complete | complete | 11 rows x 3 rules | PASS |

Every move (clean = mutant whose gold fact is itself writable under that rule):
- m1 (813 made): clean-through 363/363 v0, 737/737 v1, 764/764 licensed. 0 blocked anywhere clean.
- m2 (1639): clean-through 844/844, 1442/1442, 1507/1507. 0 blocked clean.
- m3 (353): clean-through 185/185, 308/308, 328/328. 0 blocked clean.
- m4 (137): clean-through 109/109, 129/129, 132/132. 0 blocked clean.
- m5 (1659): clean-blocked 828/828 v0, 1428/1428 v1; clean-through 1503/1503 licensed.
- m6 me2we (180): blocked 180/180 all rules (clean 91/91, 168/168, 173/173). name2me (353): clean-through 185/185, 308/308, 328/328. we2me (20): raw through 15/20, 19/20, 20/20; clean base empty by construction.
- m7 (542: trim 40, extend-next 232, extend-prev 270): clean-through 100% in all 9 sub-cells.
- m8 (190): structural 65 (55 empty-value incl. 7 also-OTHER, 1 OTHER-valued, 9 WE-owned) blocked 100% all rules; rest (125) through 65/125 v0 (52.0%), 109/125 v1 (87.2%), 125/125 licensed (100%).

Every miss: none vs sealed predictions. One disclosed refinement: the brief's guess said m8 "mostly gets through every rule", but the sanctioned pilot showed rest-v0 ≈52%, so sealed P8 carried 40–65% for v0 — scored against the seal, HIT.

Deviations: registered summary.json byte-identical to pilot (determinism check passed); seals 2/2 OK post-run; no sealed file changed; no TEST-ONLY panel/panel folder/own-bench opened; CPU only; disk 11 GB free; load ~50 (< 60 bar). Additive only: 1 new script, 1 new artifacts dir, 2 ledger lines appended. PUSH for the watcher: artifacts/claude-own-o0a3-20260923, scripts/claude_own_o0a3_mutate.py, artifacts/fable-predictions-ledger.md.

What it means (plain high-school English): the write rules check the *shape* of a reading — spans present, cue word present, mode says statement, owner isn't "we" — never its *truth*. Any wrong reading with the right shape gets saved: wrong person, wrong value, backwards fact, "mine" for someone else's fact, off-by-one-word value, or a question rewritten as a statement. Only a missing cue word, a "we" owner, or question-mode/empty/unknown-relation ever stops one. So the coverage v1 and licensed bought (O0a2: 68% → 90%+) is paid for exactly here.

What it doesn't mean: it doesn't mean the system saves falsehoods 97% of the time — the fakes bypassed the reader, and how often a real ear *makes* these misreadings is a separate experiment. It doesn't mean v1 is less safe than v0 (identical 68.1% clean-through; v1's extras are true facts). Only the reader — or an independent checker that re-reads the turn — can stop a wrong-shaped-right reading.

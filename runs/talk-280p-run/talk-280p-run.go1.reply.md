Registered 280p re-test starting — verifying seals and freezing your scorer.
Seal docs mapped — now checking the 280m seal and building the 280p scorer.
Overlap detection checks out — now testing the remaining scorer paths.
Scorer validated and passmarks written — sealing the 280p run.
Panel seal verified — launching the one registered five-arm run.
All marks green — confirming seals held and writing the results.
**Verdict: PASS (M1–M4 all pass).** Registered re-test 280p of the SEALED 280m join agent, no code change to any agent, CPU only.

Marks table (integer counts):

| mark | bar | result |
|---|---|---|
| M1 agreement (280m == mechanical owner) | 90/90 | **90/90** |
| M1 overlaps | 0 | **0** |
| M1 question-turn writes (280m) | 0 | **0** |
| M1 smalltalk-turn writes (280m) | 0 | **0** |
| M1 store diffs vs 260 | report | **0** |
| M1 old-sheet hits | report (director) | **0** |
| M2 sessions152 | exactly the 3 | **3 exact ids, 0 write changes** |
| M2 bench / rt136 / rt143 | 0 / 0 / 0 | **0 / 0 / 0 (rt136 n=145, rt143 n=124)** |
| M2 vp / vs | N06+E04 / 0 | **N06+E04 / 0** |
| M2 GATE | identical to 260's | **identical** |
| M3 wellbeing | 280m ≥ 260 | **17/20 vs 16/20** |
| M3 other identical | 36/36 | **36/36** |
| M3 writes/setup/store diffs | 0 | **0/0/0** |
| M4 notebook-zero | 0 | **0** |

Every move / every miss:
- M1 by category: ability 25/25, called 12/12, teach 8/8, smalltalk 25/25, mixed 10/10, control 10/10. Miss ids: none. Overlap ids: none.
- Mechanical owners: 280b 24, 281 4, 282b 5, 260 57 (sums to 90). CAN-line counts (report only): 280m 24 vs 260 20, all inherited via agreeing owners, no new behaviour.
- M2 moves: S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9 (reply-only, stored identical). Nothing else moved anywhere.
- M3: the 1 wellbeing move is the same row 282 moved before; 280m miss ids s234-015, s234-016, s234-020 (ids only). No 5x follow-up (no unpredicted abstain flip).
- Seals: 280m 12/12 OK before and after; panel seal 2/2 OK; own seal 3/3 OK after. No sealed file changed. Panel ran ONCE per arm; suites ran ONCE post-seal with 280m's sealed runall/regscore; st234 ran once per arm. Scorer pre-tested on mocks in /tmp: clean 6/6 PASS, overlap 6/7 FAIL listed, writes-diff owner PASS, empty exit 4, schema exits 3.

Deviations: none on the runs. One recorded pre-seal deviation: st234 never piloted (run-once rule). No push performed — standing rules forbid commits/pushes; ready for the director to push: `artifacts/claude-join280p-20260923` (PASSMARKS, RESULTS, SEAL, run/), `scripts/claude_join280p_score.py`, `scripts/claude_280p_panel.sh`, `artifacts/fable-predictions-ledger.md` (P280p.1–P280p.5 appended).

What it means: the join does exactly what it claims — on 90 new turns it always replays the responsible piece (90/90, 0 fights), and nothing else broke.
What it doesn't mean: not proof the answers are always factually right (that's the director's claim check over `run/panel-280m.json`, 0 scan hits here), not new understanding beyond the pieces, and 90 turns can't prove overlaps are impossible — just 0 in these 90 (0 in 270 across all three panels).

# rsn-358e4 pass marks: with every earlier kind replayed, do frozen experts beat a plain dense loop at equal size? (fixed before any run; sleep research thread, 2026-09-27 00:28 UTC)

**Why:** rsn-358e3 (artifacts/claude-rsn358e3-20260926/RESULTS.md) showed a trade only in report rows. Replay protected what was replayed: dense-replay kept grids5 at 184/172 after B, but dropped it to 0/0 after mazes, where it had no replay. Frozen experts kept a skill nobody practised (185/160 after mazes) but learned new kinds badly. The Thread manager (00:26 UTC) asked for that trade on a graded mark, at equal size, with replay of every earlier kind. That is what Ben's sleep design does ("practise everything checkable").
**Brain angle:** cortex with sleep replay (dense + replay) vs separate circuits gated by a router, plus replay. A guess either way.

**Code:** scripts/claude_rsn358e4_replayall.py, importing claude_rsn358e3_replay.py (sealed 963833138), claude_rsn358e2_arms.py and claude_rsn358e_moe.py unchanged. CPU, 1 thread, small nets, steps 2,500 / 2,500 / 1,500, batch 64, dev seed 48000.
**Replay, the same for both arms:** phase B: every 10th step is grids (250 of 2,500). Phase C: every 10th step is an earlier kind, alternating grids and sums (75 + 75 of 1,500). Batches come from the phase-A grids training pool and the sums generator, never a dev set. result.json records the counts.
**Arms (equal total weights), seeds 3, 4, 5, 6** (fresh; seeds 1-2 of dense-replay through phase B are already read):

| arm | total weights | trainable in B and C |
|---|---|---|
| dense-replayall | 1,646,750 | 1,646,750 |
| eq-replayall (frozen experts; one router group and 4 experts of hidden 4d/12 open per phase) | 1,654,446 | 352,944 |

## Marks (dev, right of 200, the net's own stop); T = grids5 + sums4 + maze7 after phase C (of 600)
- **V:** on every seed, grids5 after A >= 120 in both arms, and sums4 after B >= 120 in dense-replayall. Otherwise INCONCLUSIVE. Known risk: eq's phase-A MLP is a third as wide (NOTE-moe-grow-eq-caveat.md), so eq may miss V. That would make the test INCONCLUSIVE, which is itself a capacity finding.
- **PASS (frozen experts help at equal size with full replay):** mean T_eq >= mean T_dense + 30 AND T_eq > T_dense on >= 3 of 4 seeds.
- **Proved wrong:** mean T_eq <= mean T_dense - 30 (at equal size with full replay, the experts cost more than they keep).
- Anything else is a FAIL, not proved wrong: no difference shown.

## Report only
- Each kind after each phase; keep = grids5 + sums4 after C; learn = maze7 after C; F per phase; expert_share and S; replay counts.

**Predictions:** PASS 10%; proved wrong 60%. With every kind replayed the frozen experts' one advantage (keeping an unpractised skill) is gone, and they still train only 352,944 weights per phase.
**What each outcome means:** PASS: separate experts earn a place in the reasoner even with sleep replay. That would be a question for Ben (architecture), not a build edit. Proved wrong: with replay, the plain dense loop is the better reasoner, and the experts idea is parked for this reasoner. FAIL between: no difference shown at this size.
**Cost:** $0, CPU. 8 runs, 4 at a time, after rsn-358e3's eq arms finish (about 2 x 1.5 h, estimate).

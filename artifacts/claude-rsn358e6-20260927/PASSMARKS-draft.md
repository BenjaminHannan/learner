# rsn-358e6 marks, DRAFT for the Thread manager (written 2026-09-27 02:54:03 UTC; not sealed; nothing run)

**One change from rsn-358e4's eq-replayall: shared layers keep training** (scripts/claude_rsn358e6_sharedtrain.py; selftest passes). After each grow step, the attention (qkv, out, the row and column position biases br and bc) and every LayerNorm (ln1, ln2, ln_out, ln_state) train again in phases B and C. Still frozen: old experts, old router rows, token/slot/env embeddings, the output head and the stop head. Asked by the Thread manager at 02:52 UTC.

| phase | eq-replayall (358e4) trainable | **eq-replayall-shared** trainable | dense-replayall |
|---|---|---|---|
| A | 948,558 | 948,558 (same) | 1,646,750 |
| B, C | 352,944 (21%) | **882,640 (53%)** | 1,646,750 |

**Controls:** rsn-358e4's own eq-replayall and dense-replayall runs, seeds 3-8, not rerun. CPU, 1 thread, torch 2.14. Runs after rsn-358e4 has finished. /bin/bash. No hand-given labels are used.

**Marks**, where N = sums4 after B + maze7 after C (of 400; dev seed 48000, already read, so not a held-out test):
- **REPRO (else INCONCLUSIVE, stop):** on every seed, every after-A dev score equals rsn-358e4 eq-replayall's.
- **PASS:** mean N_shared >= mean N_eq + 50, AND N_shared > N_eq on at least 5 of 6 seeds.
- **Proved wrong:** mean N_shared <= mean N_eq + 10, AND N_shared <= N_eq + 10 on at least 5 of 6 seeds. Meaning: frozen attention and norms were not what blocked the new kinds.
- Anything else is FAIL.
- **Report only, never graded:**
  - T = grids5 + sums4 + maze7 after C, against dense-replayall, with 358e4's bars (+40, 5 of 6) shown as a row;
  - grids5 after A, after B and after C against both controls. Old skills now depend on attention that changes, so grids kept may fall.
  - the routing count from 358e4 ADDENDUM-3 (new group at least 5% of the new kind, per seed);
  - trainable_next_phase.
- **Predictions:** PASS 60%; proved wrong 15%. Grids kept: lower than eq-replayall's but higher than dense-replayall's after C (a guess, 50%).

**Brain link (a guess):** the cortex does not freeze its shared early and middle layers when it learns a new skill. Plasticity keeps going in shared sensory and association areas, while the specialist circuits that hold old skills are protected by replay. This test is closer to that picture than freezing everything old.

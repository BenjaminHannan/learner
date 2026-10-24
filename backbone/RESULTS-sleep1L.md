# Sleep-1L on LFM2.5-24B-A2B (4-bit, MLX, Mac) — partial

The run was hard-killed at about 13:19Z on 2026-10-24, around step 200 of s2t, and the Mac rebooted. s2t, ic and s1 never finished.

| arm | forward | reverse | two-hop | ARC (greedy) | wall |
|---|---|---|---|---|---|
| s0 (no sleep) | 0.000 | 0.000 | 0.000 | 0.934 | 383 s |
| s2 (sleep, dream QA) | 0.092 | 0.050 | 0.000 | **0.782** | 4106 s |
| s2 + notes in context | 0.025 | 0.008 | 0.017 | | |

- Dreams (s2): 120 facts with 108 parse failures; 48/48 paraphrases kept, 24/48 QA kept.
- s2t two-hop dreams: 0 kept (46 had no true chain, 5 leaked test items), covering 0/60 chains. **s2t was invalid**, because it trained without any two-hop data.
- Peak training memory: 19.5 GB.

Shown (1 run): on LFM2.5, closed-book sleep stored little (forward recall 9%), cost 15 ARC points, and broke reading from notes. This matches Sleep-B, where open-book rehearsal or a context KL is needed and the add-on must stay low-rank.
Raw files are on the Mac in ~/learner-ops/sleep1L/out.

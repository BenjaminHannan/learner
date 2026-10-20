# E2 verdict against the pre-set bars (FORGETTING-SOLVE-2026-10-16.md, "E2 bars"), 2026-10-17. DRAFT, coordinator review pending.

8 runs, far L5 protocol, parent s200, 8,000 updates, harm on 1,360 (historical ruler) and 6,800 (ship instrument, Oct 16 ruling).
Raw numbers: SUMMARY.txt. Per-row hits: rows/ (hash-checked; L11-s31001 checked by hit counts only).

| bar | result | verdict |
|---|---|---|
| V0 validity | L13@93301: every 4k cell equals the record (HO 59/420 = 14.05, drop 0.44); 4k per-row hits identical to the M0 re-score of the recorded checkpoint on all 1,360 and 6,800 rows. L7-LB@93301 drop 52.9 (>= 40). | **PASS** |
| V1 protection | A1F (replay + freeze, no mask): s31001 futility stop at 2k (drop 3.01); s93301 drop(A1F) - drop(L11) on 6,800 @4k = +3.99 [+3.39, +4.58] (@8k +5.46 [+4.78, +6.13]). | **PROVED WRONG: the mask carries the protection** |
| V2 tax (reading) | HO(A1F) - HO(L11), s93301 only (A1F-s31001 stopped): -10.9 @4k, -25.4 @8k. Removing the mask LOWERS new learning. | "no tax" side (< 2), one seed; soft-1 mask has no learning tax vs replay+freeze |
| V3 delay | L13 HO @8k 32.1 / 31.4 (both >= 25; ceiling bar 19.1 not met). Harm @8k: 1,360 passes both seeds (0.44 / 0.66); 6,800 FAILS both seeds (fewshot_number_rule 7.5 / 6.5). | learning = **delay, not ceiling**; but under the ship instrument harm fails, so V3's "delay with harm passing" is **not met** |

Additional readings (reported, not bars):
- Same item, same guard, different seed: lost-set Jaccard L11 s93301 vs s31001 = 0.88 (6,800 @4k), L13 s93301 vs s31001 = 0.82 (@4k) / 0.83 (@8k);
  L11 vs L13 same seed 0.29, A1F vs L11 0.13.
  Residual loss under a fixed guard is structural (mask + diary decide it), not seed noise.
- drop(L13) - drop(L11), s93301, 6,800: +0.04 [-0.27, +0.35] @4k, -0.16 [-0.50, +0.18] @8k: soft-10 buys no protection over soft-1
  but costs HO 26.4 -> 14.1 @4k and 46.4 -> 32.1 @8k.
- L11 HO seed spread @4k: 26.4 vs 19.3. Unguarded L7-LB HO is non-monotone (43.1 -> 31.9 from 6k to 8k at s93301).

Outcome -> action (pre-set table): "V1 proved wrong -> mask needed; keep the NK-soft dial; next single change w_noop=1 in the replay KL".
DEVIATION, flagged: the M0 trace shows the residual losses keep the parent's call programs (11/12 "calls identical -> readout");
w_noop only reweights the op head on zero-call rows, i.e. the part that does NOT drift. It is demoted. Round G (PREREG-G.md)
tests two changes aimed at the measured failure instead (slow growth of a readout leak): KL 30, and parent-fixed K-FAC factors.

L13 vs L14 under the ruling: L13 fails on 6,800 at 4k (s93301) and 6k/8k (both seeds). L14 passes at 4k (one seed, 0.29) but has no
long run, so its learning curve is unread (HO 9.8 @4k). Neither is adoptable on this data; round G's G1 (soft-1 + KL30) sits between them.

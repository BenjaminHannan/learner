# dl-4 blind recount: agrees, registered FAIL (F1, F2). Not proved wrong.
A blind agent read only PASSMARKS.md and gpu/dl4_results.json and recomputed every mark from the per-night fields.
- Not INCONCLUSIVE: L0 59; S night-7 lost 16 + 17 = 33 (>= 20); pool 880.
- F1 FAIL: K night-7 lost 6 and 19 (sum 25) vs S 16 and 17 (sum 33); needed <= 16.5, and K seed 7 is not below either S seed.
- F2 FAIL: 4 of K's 14 nights lost > 10 (limit 1); K s6 4,5,7,9,3,8,6; K s7 4,9,8,12,19,16,19.
- F3 PASS: K lucky 208 and 298 (>= 118); K gain 388 vs S 419 (needed >= 335.2).
- F4 PASS: 0 of 14 drops over 15% (largest 236 -> 208, 11.9%). F5 PASS: reached 64 and 59 (>= 37).
- Proved wrong: no (K >= S only on seed 7, 19 vs 17).
- Night-7 KL to base on general replies: K 0.035 / 0.031 vs S 0.175 / 0.186.
- One label bug, not a verdict change: the marks block's field "K_nights_lost_over_15" (from claude_dl3_replay.score's
  variable name) counts nights with lost > 10, as F2's text says; 3 of K's nights had lost > 15.

## Post-hoc look (report only, after the verdict; the panel is our own code-made harm panel, not a blind TEST panel)
Night-7 lost items across the 4 arm-seeds come from a union of only 29 items; 5 are lost in all four, and pairs share
5-11. 19 of the 29 are capitals (capitals are 70 of the 300 items), mostly less famous ones (Morocco, Algeria, Ecuador,
Jordan, Nigeria, Nepal...). Suggested, not shown: nights knock out the base's weakest facts whatever the night rule,
and the anchor held average drift (KL 5x lower) without protecting those weak facts. dl-2's wrong-answer placebo
also lost 17/19, which fits "any training flips fragile items". Testable at $0: whether lost items are the ones the
base answers with the lowest confidence.

# Sleep-1 results (2026-10-24, Vast box 57448228, Qwen/Qwen3.5-2B; prereg `PREREG-sleep1.md`)

120 fictional facts in 6 relations. Tests: forward (120), reverse (120), two-hop (60), and ARC-Easy (500) for general knowledge.

| arm | forward | reverse | two-hop | ARC-Easy |
|---|---|---|---|---|
| S0 base, never saw the facts | 0.0 | 0.0 | 0.0 | 89.4 |
| IC facts pasted in the prompt (ceiling) | 95.0 | 90.0 | 40.0 | 89.4 |
| S1 plain LoRA on the 120 teaching sentences | 8.3 | 0.8 | 0.0 | 89.2 |
| S2 sleep: dreamed Q&A, self-verified, KL guard | **89.2** | **78.3** | 0.0 | **92.0** |

## Verdicts (marks fixed before the run)
- M1 PASS: S2 forward 89.2 >= 70 and >= S1 + 15.
- M2 PASS: S2 reverse 78.3 >= 40.
- M3 FAIL: S2 two-hop is 0, needing >= S1 + 10. Facts learned in sleep can be recalled and reversed, but not chained in one step. Even with the facts in the prompt, two-hop is only 40.
- M4 PASS: ARC 92.0 >= base - 2. Nothing general was lost; ARC actually rose 2.6, which is likely noise at n=500 (SE about 1.4).
- Neither "wrong if" condition holds.

Plain reading: training on the raw sentences barely teaches the facts (8%). The sleep recipe of rehearsing many question forms,
checking them against the source, and guarding against drift teaches them almost as well as having the notes open (89 vs 95).

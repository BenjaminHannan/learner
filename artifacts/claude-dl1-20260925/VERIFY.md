# dl-1 VERIFY: registered FAIL (blind recount agrees)

Run: rental, $0.83, 92.5 min (builder report RESULTS-gpu.md; raw gpu/dl1_results.json). Recount: a blind Opus agent
recomputed every mark from the per-night raw fields without using score(); the thread also recomputed it. Both agree
with the JSON marks block.

| Mark | Result |
|---|---|
| R1 R final ≥ 1.5 × L0 and ≥ 0.8 × S | FAIL: R 63, 148 (mean 105.5) vs 0.8 × S mean 164.5 = 131.6 |
| R2 harm (S net harm < 10, so fallback R ≤ 5 each seed) | PASS: R −19, −26; the safety comparison was not testable (S's net harm was −25, −10, i.e. the panel improved) |
| R3 R reached ≥ base 35 | FAIL: 5, 22 |
| R4 R ≥ 1.2 × Z and each R seed > each Z seed | FAIL: means 105.5 vs 70.5 pass; R seed 0 (63) < Z seed 1 (79) |
| R5 ≤ 1 R night falling > 15% | PASS: 1 (R seed 0 night 3, 110 → 63) |
Inconclusive: no (L0 69; R day-1 mixed groups 75, 81). Proved wrong: no.
Verdict: **FAIL**. REINFORCE with a group baseline (the registered treatment) did not beat copy practice.

Deviation: TEST had 95 puzzles, not 100 (overlap with practice/DEV puzzles removed 5). Marks unaffected.

Per night, TEST lucky/reached/greedy (base 69/35/8) and harm-panel lost/gained (base 200/300 right):
| arm-seed | night 1 | night 2 | night 3 |
|---|---|---|---|
| S0 | 106/40/5, 8/23 | 101/43/7, 12/39 | 160/44/9, 8/33 |
| S1 | 106/44/11, 6/35 | 154/57/11, 12/40 | 169/58/12, 16/26 |
| R0 | 78/17/4, 1/19 | 110/32/6, 2/22 | 63/5/3, 9/28 |
| R1 | 95/25/6, 2/16 | 119/22/7, 5/25 | 148/22/8, 3/29 |
| Z0 | 73/37/5, 2/1 | 76/35/5, 1/0 | 62/37/9, 3/1 |
| Z1 | 76/34/5, 2/8 | 82/35/7, 11/7 | 79/28/8, 40/12 |

Observations (not registered claims; one run, 2 seeds, 3 nights):
- Copy practice (S) improved on all 6 nights vs base. No S night fell more than 15% (worst −5%). Final lucky 160/169
  vs 69; puzzles reached 44/58 vs 35; greedy 9/12 vs 8. The general panel went UP (210-229 right vs 200).
- REINFORCE narrowed variety (reached 5/22) and its greedy fell (3/8); its day's mixed groups halved after night 1.
- Shuffled rewards (Z) did nothing useful and on one seed cost the general panel 28 net items (172 right).
- The panel gain under real training may be answer-format learning (short replies) rather than knowledge; untested.
Next: dl-2 = copy practice for 7 nights with a wrong-answer placebo (does it keep improving, night after night?).

# rsn-296 verification (reasoning thread, 2026-09-24)

**296 = registered FAIL on P296.4 for both plain seeds** (fresh-panel total 225 and 217 vs ≥228). That verdict stands whatever the recount shows for P296.1.

## What I could check
- The builder's panel JSONs were lost when the rental was destroyed (runs/*/DATA-LOSS.txt), so I could NOT recount from files yet.
- The checkpoints are kept on the Mac and match the run seal (builder's claim). A CPU re-eval of all 8 checkpoints is queued (rsn-296-reeval) so the recount can happen from files.
- The builder's category counts are internally consistent. Code-doable: s1 173 = 30+30+30+30+23+30 and s2 169 = 30+30+30+30+19+30. Adding before/after, comparing, counting and three-step gives 225 and 217.
- The spend was about $2.09 over 4 rentals, under the $4 cap.

## P296.1 is disputed (the builder reports FAIL: 5 and 6 invented answers on the fresh panel)
- The sealed scorer (claude_rsn294_run.py score) counts "answered without a fact" only when the gold is UNKNOWN.
- On reasonpanel296 v2, the only items with an UNKNOWN gold are the 30 missing_fact items. I checked the gold field only, by category.
- The builder reports missing 30/30 checked right on both seeds. Checked invented answers must therefore be 0. The 5 and 6 are most likely the RAW counts, before the fact-check. P294.1 was scored on checked answers.
- Provisional reading: P296.1 PASS on checked answers. The re-eval settles it.

## Marks (builder numbers, provisional until the re-eval)
| mark | bar | plain s1 | plain s2 |
|---|---|---|---|
| P296.1 invented (checked) | ≤2 | disputed, likely 0 | disputed, likely 0 |
| P296.2 transfer, reasonpanel294 | ≥204 / ≥209 | 238 PASS (+54 over 294) | 238 PASS (+49) |
| P296.3 fresh code-doable | ≥168/178 | 173 PASS | 169 PASS |
| P296.4 fresh total | ≥228/298 | 225 FAIL | 217 FAIL |

## Diagnosis
- **D1. Varied practice fixed 294's main failure.** The idea-killer mark passed by about 50 on both seeds. Two-step went from 6/30 and 11/30 in 294 to 30/30. Big notebooks went to 15/15.
- **D2. The misses are the kinds that were never learned well.** Three-step is 0/30 (never practised, as designed). Counting is 12/30. Comparing is 16/30, near chance (294's D3 bandit-signal problem, still unfixed). Corrections are 23/28 and 19/28.
- **D3. The loop arm reproduced 294's D2.** Copy loss stayed at 1.85 and 1.97. It had no pass mark.
- **For the month-end join:** the plain model beats the rules' total on the fresh panel (225 and 217 vs 208), because it answers counting, comparing and before/after, which the rules can't do at all. The rules are exact on everything else. So the fitting use is "behind the rule checker": rules first, and the model only for kinds the rules can't answer. That is a join decision to test end-to-end, not a new training run.

# rsn-294 verification (reasoning thread, 2026-09-24 ~01:30 UTC)

**294 = registered FAIL.** The builder's marks match my own recount from the raw panel JSONs, all four runs, category by category.
- Run seal: 8 checkpoint lines. The builder copied the checkpoints to the Mac and checked them against the seal; the weights are not in the cloud.
- Spend: about $1.32 on the builder's ledger line, or $1.50 on the guard's dph_total. The earlier tries cost $0.40. Every job stayed under Ben's $4 combined cap.

| run | copy-only right | final right | invented (after fact-check) | missing_fact "I don't know" | held-out (three-step + big notebook) |
|---|---|---|---|---|---|
| code arm | 210 | 210 | 0 | 30/30 | 30/30 |
| loop seed 1 | 45 | 92 | 0 | 30/30 | 0/30 |
| loop seed 2 | 107 | 111 | 0 | 30/30 | 1/30 |
| plain seed 1 | 165 | 184 | 0 | 30/30 | 5/30 |
| plain seed 2 | 156 | 189 | 0 | 30/30 | 8/30 |

Marks, both loop seeds:
- P294.1 PASS (0 invented; the fact-check caught 22 and 4 raw inventions).
- P294.2 FAIL (92 and 111 vs 240 needed).
- P294.3 PASS (30/30).
- P294.4 FAIL (−5 and −7 vs the plain twin).
- P294.5 FAIL (all four categories, both seeds).
- P294.6 PASS on seed 1 (+47) and FAIL on seed 2 (+4).

## Diagnosis (evidence is from the dev JSONs and train logs; no panel item was read)

- **D1. Learned reasoners fit the practice generator's style and don't carry it to blind notebooks.** On fresh generated dev, both plain seeds score 100/100 on two-step, big notebooks and corrections. On the panel they get:
  - two-step: 6/30 (seed 1) and 11/30 (seed 2);
  - big notebooks: 5/15 and 8/15;
  - corrections: 20/30 and 30/30.
  The hand-written code gets full marks on all of these. **This is the main finding.** It hits both arms, so it says nothing for or against looping.
- **D2. The loop did not learn to copy on seed 1.** Its copy loss sat at about 1.0 from step 1,000 to 6,000; plain's went to 0.002. Seed 2 learned (0.12). So the loop-vs-plain comparison is mostly about the loop training badly at this width and learning rate, not about looping itself.
- **D3. Comparing stayed at exact chance for all 4 runs on dev (50/100).** Likely cause (untested): with a two-way pick, all 8 practice tries often agree, so the group baseline gives zero signal and practice stops teaching it.
- **D4. Three-step was 0 for every run on dev and panel,** as predicted. Nothing in practice reaches three steps.

What it does NOT mean: that a brain-style loop can't beat a plain model. The loop was never trained to its potential (D2), and both arms failed the blind test for a reason unrelated to looping (D1).

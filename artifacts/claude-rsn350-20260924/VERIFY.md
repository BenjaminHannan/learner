# rsn-350 verification (sleep research thread, 2026-09-24 22:55 UTC)

**rsn-350 = registered FAIL.** The pre-registered "size is the bottleneck" refutation is met, and the 10x trigger is not.

Checked:
- Code seal: SEAL-code.sha256.txt 6/6 OK on main. Run seal: 4 checkpoints listed; the files are kept on the Mac, not re-hashed here.
- Recount from the panel JSONs on builder-outbox (my own parse). The builder's numbers match exactly.

| mark | bar | s1 | s2 |
|---|---|---|---|
| Z1 fresh total | ≥235 / ≥227 | 211 FAIL (296: 225) | 209 FAIL (296: 217) |
| Z2 three-step | ≥6/30, one seed | 0 FAIL | 0 FAIL |
| Z3 transfer | ≥233 | 227 FAIL (296: 238) | 229 FAIL (296: 238) |
| Z4 invented (checked) | ≤2 | 0 / 0 PASS | 0 / 0 PASS |

- Copy phase learned fine: copy loss reached 0.0042 and 0.0036.
- Practice ended lower than 296's: reward 0.81 and 0.85, against 0.93 and 0.98, and noisier (s2 dropped to 0.73 at step 3,000).
- Counting got worse: 4/30 on both seeds, against 12/30. Comparing held at 16/30. Three-step stayed 0/30.
- Spend: $0.96, including one broken box. Guard OK.

What it means:
- **Shown:** with the same recipe, 3x the size did not help. It scored 14 and 8 lower on the fresh panel, and three-step stayed at 0.
- **Suggested, untested:** the recipe (lr 3e-4, 6,000 practice steps, batch 128) was tuned for 30M. A bigger net may need a lower learning rate or more steps, so this does not show that size can never help. It does show that size is not the current bottleneck.
- The failures that remain (three-step never practised, counting, comparing readout) fit the reasoning thread's order: fix loop training, then add the thinking stop token and a passes-per-hop ladder, then grow.

# Experiment 43E — results (2026-09-21)

All 6 runs valid (base old-skills 0.982–1.000). Registered bases, 100 clean episodes (80 used by sleep, 20 held out), 3,000 updates.
"fresh" = exact match on 200 never-seen inputs of trained lengths. Seeds 4102 / 4103 / 4104.

| | 4102 | 4103 | 4104 |
|---|---|---|---|
| plain, loss pick (update) | 0.490 (3000) | 0.650 (2500) | 0.410 (2250) |
| plain, match pick | 0.505 (1750) | 0.650 (2500) | 0.435 (3000) |
| plain, best possible | 0.505 | 0.695 | 0.435 |
| rank-4, loss pick | 0.485 (500) | 0.905 (3000) | 0.885 (3000) |
| rank-4, match pick | 0.715 (2250) | 0.905 (3000) | 0.885 (3000) |
| rank-4, final update | 0.710 | 0.905 | 0.885 |
| plain, final update | 0.490 | 0.585 | 0.435 |

Marks:
- E1 (match rule beats loss rule by >= 0.05, plain arm): +0.015 / 0.000 / +0.025 -> FAIL. On clean data the two rules pick about equally well.
  Not in the mark: on rank-4 seed 4102 the loss rule picked update 500 (0.485) while the match rule picked 0.715.
- E2 (match rule within 0.05 of best possible): 0.000 / 0.045 / 0.000 -> PASS.
- E3 (rank-4 >= plain + 0.10 in >= 2/3 seeds): +0.210 / +0.255 / +0.450 -> PASS 3/3.
- E4 (old skills kept): worst change +0.000 -> PASS.
- Long inputs (9–10 digits): <= 0.05 everywhere. Length wall untouched, as expected.

Sealed decision: E1 failed, so the match rule does NOT replace the loss rule on this evidence.
E3 passed, so rank-4 earns ONE confirmation run on fresh seeds (4111/4112/4113, new bases). No claim before that.

What it may mean: keeping each weight matrix's total change to rank 4 makes 80 episodes go much further (0.44–0.65 -> 0.72–0.91).
What it does not mean: not confirmed; toy only; one skill; clean data; does nothing for longer inputs; rank 4 was not compared with
other ranks or with other regularisers (weight decay, early stop), so "low rank" may not be the active ingredient.

## Confirmation on fresh seeds 4111 / 4112 / 4113 (new bases, same script hash, marks in PASSMARKS-CONFIRM.md)

Ops note: the first launcher died instantly (macOS xargs length limit) before any training; fixed launcher, marks untouched.
All 3 seeds valid (base old-skills 1.000 / 1.000 / 0.977).

| fresh accuracy | 4111 | 4112 | 4113 |
|---|---|---|---|
| plain, match pick | 0.210 | 0.480 | 0.630 |
| rank-4, match pick | 0.395 | 0.680 | 0.755 |
| plain, final update | 0.205 | 0.510 | 0.655 |
| rank-4, final update | 0.395 | 0.680 | 0.755 |

- K1 (match pick, >= +0.10 in >= 2/3): +0.185 / +0.200 / +0.125 -> PASS 3/3.
- K2 (final update): +0.190 / +0.170 / +0.100 -> PASS (3/3; seed 4113 exactly on the line, two seeds clear it regardless).
- K3 (old skills kept): worst change -0.007 -> PASS.

Allowed sentence (earned): "On the CardFold toy, limiting sleep's weight change to rank 4 improved new-skill accuracy on
unseen inputs from 80 episodes, in 6/6 seeds."
Still not shown: that LOW RANK is the active ingredient (vs any limit on the change); any other rank; fewer episodes;
noisy data on this base; longer inputs (<= 0.05 everywhere); anything beyond this toy. Absolute level is still far from
the 400-episode 0.995, and varies a lot by seed (0.40–0.91).

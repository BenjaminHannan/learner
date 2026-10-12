# Game-world result (run /Users/ben-hannan/gw8/runs/gwp8-s200)

Sealed scoring on 100 worlds; one seed only.

| mark | verdict | value | bar |
|---|---|---|---|
| GW1 | PROVED WRONG | 0.4 | pass: d >= 1.5 and interval low end > 0; proved wrong: d < 0.5 |
| GW2 | FAIL | 3.0 | pass: share >= 10%; proved wrong: <= 2% |
| GW3 | PASS | 0.27 | pass: e >= 0; proved wrong: e <= -1.0 and interval high end < 0 |
| GW4 | PASS | 0.0 | pass: in_dist drop <= 1.5 and no family fired (routed by the run switch); proved wrong: drop > 5 |
| GW5 | PASS | 0 | pass: game.audit finds no problem; proved wrong: sealed or quiz world in a training row, or changed constants |
| GW6 | PASS |  | pass: p_S >= best - 3 and p_S - p_(S-1) <= 3; proved wrong: rise > 5, or S >= best night + 4 and p_S < best - 5 |

GW1: {"lo": 0.05}

GW3: {"hi": 0.6}

GW4: {"fired": []}

## Per-achievement unlock share (percent of sealed worlds)

| achievement | before | after | random | ppo |
|---|---|---|---|---|
| collect_coal | 0.0 | 0.0 | 0.0 | 0.0 |
| collect_diamond | 0.0 | 0.0 | 0.0 | 0.0 |
| collect_drink | 39.0 | 38.0 | 12.0 | 28.0 |
| collect_iron | 0.0 | 0.0 | 0.0 | 0.0 |
| collect_sapling | 98.0 | 98.0 | 51.3 | 90.0 |
| collect_stone | 0.0 | 0.0 | 0.0 | 0.0 |
| collect_wood | 60.0 | 52.0 | 22.3 | 49.0 |
| defeat_skeleton | 0.0 | 1.0 | 0.0 | 0.0 |
| defeat_zombie | 13.0 | 11.0 | 0.0 | 4.0 |
| eat_cow | 12.0 | 14.0 | 0.0 | 8.0 |
| eat_plant | 0.0 | 0.0 | 0.0 | 0.0 |
| make_iron_pickaxe | 0.0 | 0.0 | 0.0 | 0.0 |
| make_iron_sword | 0.0 | 0.0 | 0.0 | 0.0 |
| make_stone_pickaxe | 0.0 | 0.0 | 0.0 | 0.0 |
| make_stone_sword | 0.0 | 0.0 | 0.0 | 0.0 |
| make_wood_pickaxe | 4.0 | 3.0 | 0.3 | 5.0 |
| make_wood_sword | 1.0 | 3.0 | 0.3 | 2.0 |
| place_furnace | 0.0 | 0.0 | 0.0 | 0.0 |
| place_plant | 48.0 | 86.0 | 46.3 | 84.0 |
| place_stone | 0.0 | 0.0 | 0.0 | 0.0 |
| place_table | 21.0 | 18.0 | 4.0 | 23.0 |
| wake_up | 79.0 | 91.0 | 94.0 | 95.0 |

| arm | unlocks/episode | progress % | Crafter score % | mean length | own-action share |
|---|---|---|---|---|---|
| before | 3.750 | 17.05 | 3.14 | 184.8 | 0.896 |
| after | 4.150 | 18.86 | 3.45 | 169.4 | 0.897 |
| random | 2.307 | 10.48 | 1.51 | 168.0 | 0.000 |
| ppo | 3.880 | 17.64 | 3.03 | 177.7 | 0.897 |

## Paired differences in unlocks per episode (95% bootstrap, 2000 draws)

| difference | mean | low | high |
|---|---|---|---|
| after - before | +0.400 | +0.050 | +0.750 |
| after - random | +1.843 | +1.560 | +2.140 |
| after - ppo | +0.270 | -0.070 | +0.600 |
| after - gwp | +0.280 | -0.060 | +0.620 |
| after - gws3 | +0.860 | +0.550 | +1.190 |
| after - old | +0.650 | +0.290 | +1.010 |
| after - ppo_argmax | +1.620 | +1.300 | +1.940 |
| after - before_T0_cloud | +0.400 | +0.050 | +0.750 |
| after - before_greedy | +1.940 | +1.620 | +2.270 |

## The run

stop reason: fixed_nights; nights run: 8
quiz curve (progress %, night 0 first): [16.903, 17.472, 15.767, 17.898, 17.614, 18.04, 17.472, 18.466, 17.472]
rows per night: [9816, 10159, 9507, 9549, 9585, 9323, 9461, 9486]
game steps used: practice 90262, quiz 49127
sealed progress on first 50 worlds per night: [16.55, 17.0, 17.27, 18.0, 18.36, 17.45, 18.82, 17.82, 19.27]
old skills: routed drop 0.00 (fired []); add-on always on: drop 0.51 (fired []); switch sent 0.000 of DEV rows to the add-on

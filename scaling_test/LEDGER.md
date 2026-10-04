# Vast ledger: fair scaling test (cap about $7; shared balance must stay above $1)

Balance before renting (14:44 UTC 10-04): $22.05, shared with other threads. Checked again 14:50: $21.53.

| box | offer | GPU | purpose | created (UTC) | destroyed (UTC) | cost |
|---|---|---|---|---|---|---|
| 54161637 | 45669402 | RTX 5090 (Korea) $0.47/h | smoke: 4 sizes x 30 updates, no claims. Param counts matched the formula (9,007,790 / 17,949,662 / 35,833,406 / E32 34,247,390); all four ran together | 14:44 | 14:55 | ~$0.10 |
| 54162416 | 49140888 | RTX 5090 (US) $0.44/h | seed 0: L2, L4, L8 + lm_fewshot | 14:51 | | |
| 54162417 | 47347947 | RTX 5090 (California) $0.45/h | seed 1 | 14:51 | | |
| 54162418 | 43688755 | RTX 5090 (Korea) $0.47/h | seed 2 | 14:51 | | |
| 54162419 | 50472576 | RTX 5090 (Korea) $0.47/h | seed 3 | 14:51 | | |
| 54162420 | 48989622 | RTX 5090 (Korea) $0.47/h | seed 4 | 14:51 | | |
| 54162423 | 45668954 | RTX 5090 (Korea) $0.47/h | seed 5 | 14:51 | | |

Forecast: smoke ran all four sizes in 93 s for 30 updates, so about 1.5 to 2 h per box for 2000 updates at three sizes, about $0.8 per box, about $5 for six (below the $7 cap). Pull needs the box stopped first (execute is stopped-only on vast now).

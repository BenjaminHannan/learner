# Vast ledger: fair scaling test (cap about $7; shared balance must stay above $1)

Balance before renting (14:44 UTC 10-04): $22.05, shared with other threads. Checked again 14:50: $21.53.

| box | offer | GPU | purpose | created (UTC) | destroyed (UTC) | cost |
|---|---|---|---|---|---|---|
| 54161637 | 45669402 | RTX 5090 (Korea) $0.47/h | smoke: 4 sizes x 30 updates, no claims. Param counts matched the formula (9,007,790 / 17,949,662 / 35,833,406 / E32 34,247,390); all four ran together | 14:44 | 14:55 | ~$0.10 |
| 54162416 | 49140888 | RTX 5090 (US) $0.44/h | seed 0: L2, L4, L8 + lm_fewshot; never finished loading | 14:51 | 16:55 (destroyed, nothing ran) | ~$0.4 loading | |
| 54162417 | 47347947 | RTX 5090 (California) $0.45/h | seed 1 | 14:51 | | |
| 54162418 | 43688755 | RTX 5090 (Korea) $0.47/h | seed 2 | 14:51 | | |
| 54162419 | 50472576 | RTX 5090 (Korea) $0.47/h | seed 3 | 14:51 | | |
| 54162420 | 48989622 | RTX 5090 (Korea) $0.47/h | seed 4 | 14:51 | | |
| 54162423 | 45668954 | RTX 5090 (Korea) $0.47/h | seed 5 | 14:51 | | |

Forecast: smoke ran all four sizes in 93 s for 30 updates, so about 1.5 to 2 h per box for 2000 updates at three sizes, about $0.8 per box, about $5 for six (below the $7 cap). Pull needs the box stopped first (execute is stopped-only on vast now).

Boxes for seeds 1 to 5 finished training about 15:55 to 16:20 but were stopped, pulled and destroyed only at 16:57 (my watcher was killed by its time limit), so each idled about 40 to 60 minutes: about $1.0 per box including loading. Seed 0 re-run: box 54176245 (RTX 5090, US, $0.45/h) created 16:55, job started 18:34 after a long load, ran about 5x slower than the others, destroyed 19:01 with nothing usable.
Estimated total for this thread about $7.0 (vast does not itemise per thread; shared balance $22.05 at 14:44, $7.60 at 19:00 across all threads). No further spend without approval.

# brd-5 GPU result (registered run, 2026-09-26)

Registered question (PASSMARKS-brd5.md): does sleep widen coverage because it sees MANY DIFFERENT new wins?
Arm N = W's own greedy-correct examples + only 20 distinct won puzzles repeated to W's size. C = blurt-5s C reference.

## Whole brd5_summary.json

```json
{
    "dev_missed": 58,
    "dev_lucky_by_temp": {
        "1.0": 45,
        "1.5": 46
    },
    "temp_chosen": 1.5,
    "n_train": 400,
    "n_test": 240,
    "temp": 1.5,
    "n_test_3num": 160,
    "base": {
        "cov@1": 11,
        "cov@5": 30,
        "cov@10": 60,
        "cov@30": 123,
        "lucky": 263
    },
    "own": 20,
    "wins": 167,
    "examples": 187,
    "N_distinct_wins": 20,
    "N_distinct_puzzles": 40,
    "W_distinct_puzzles": 187,
    "W_seed0": {
        "cov@1": 15,
        "cov@5": 70,
        "cov@10": 98,
        "cov@30": 144,
        "lucky": 425
    },
    "W_seed1": {
        "cov@1": 14,
        "cov@5": 70,
        "cov@10": 94,
        "cov@30": 145,
        "lucky": 521
    },
    "W_seed2": {
        "cov@1": 17,
        "cov@5": 59,
        "cov@10": 90,
        "cov@30": 136,
        "lucky": 493
    },
    "N_seed0": {
        "cov@1": 20,
        "cov@5": 47,
        "cov@10": 63,
        "cov@30": 91,
        "lucky": 518
    },
    "N_seed1": {
        "cov@1": 20,
        "cov@5": 41,
        "cov@10": 56,
        "cov@30": 83,
        "lucky": 518
    },
    "N_seed2": {
        "cov@1": 13,
        "cov@5": 44,
        "cov@10": 64,
        "cov@30": 97,
        "lucky": 518
    },
    "C_seed0": {
        "cov@1": 11,
        "cov@5": 16,
        "cov@10": 18,
        "cov@30": 22,
        "lucky": 313
    },
    "C_seed1": {
        "cov@1": 12,
        "cov@5": 13,
        "cov@10": 16,
        "cov@30": 22,
        "lucky": 296
    },
    "C_seed2": {
        "cov@1": 9,
        "cov@5": 12,
        "cov@10": 14,
        "cov@30": 18,
        "lucky": 284
    },
    "ci95_W_minus_N_cov30_pct": [
        16.52,
        26.15
    ],
    "ci95_W_minus_base_cov30_pct": [
        2.17,
        13.5
    ],
    "ci95_N_minus_base_cov30_pct": [
        -20.18,
        -6.81
    ],
    "minutes": 20.0
}
```

## Marks with the numbers (D = 24 puzzles = 10% of 240; base cov@30 = 123, so base + 24 = 147)

- PASS ("breadth matters": W's cov@30 >= N's cov@30 + 24 in EVERY seed, AND 95% interval for W - N above 0):
  seed 0: 144 vs 91 + 24 = 115 -> 144 >= 115 TRUE (+53).
  seed 1: 145 vs 83 + 24 = 107 -> 145 >= 107 TRUE (+62).
  seed 2: 136 vs 97 + 24 = 121 -> 136 >= 121 TRUE (+39).
  CI W - N = [16.52, 26.15], lower bound above 0 TRUE.
  All four PASS sub-conditions numerically TRUE.
- Proved wrong ("a few new wins repeated teach as well as many": upper 95% bound of W - N below +5pp):
  upper bound 26.15, NOT below +5 -> clause FALSE.
- Inconclusive (fewer than 40 won practice puzzles [wins = 167, FALSE],
  fewer than 10 own greedy-correct answers [own = 20, FALSE],
  or W's cov@30 not at least base + 24 = 147 in every seed:
  W seeds 144, 145, 136, all < 147 -> TRUE):
  the third condition FIRES, so the run is INCONCLUSIVE by the marks
  (the W-vs-base effect being explained did not replicate: W - base only +21/+22/+13;
  CI W - base = [2.17, 13.5]pp; CI N - base = [-20.18, -6.81]pp, N below base).

## Registered verdict

INCONCLUSIVE (replication bar missed: no W seed reached base + 24 = 147).
Conditional reading, had it passed: N cov@30 (91/83/97) sits well above C (22/22/18),
so breadth and newness would both matter -- but per the marks this reading does not license a PASS.

## Run facts

- GPU: NVIDIA GeForce RTX 5090 (vast.ai instance 52678258, offer 44173765, reliability 0.9985).
- Wall minutes: 20.0 (script-measured); rental ~27 min create-to-destroy.
- Dollars: ~0.46 h x $0.5037/h (dph_total) = ~$0.23 of the $1.00 budget; 1 rental, no re-rents.
- Model commit hash: 87179e5c1f455ef22e6223592d2d61351b525bfc
  (openbmb/MiniCPM5-1B snapshot; BASE path
  /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c...; no other model downloaded).
- Code: unmodified origin/main scripts (selftest "selftest ok"; test-panel md5
  968b9f2fb798f0c30b58e99a11185050 verified on the rental before launch).
- Files back in artifacts/claude-brd5-20260926/gpu/ (md5-verified rental-vs-local before destroy):
  brd5_summary.json, streams.json (base 240 + W/N/C x 3 seeds), narrow_picks.jsonl (20 lines), log.txt.
- No weights saved or pushed. Instance destroyed and confirmed gone (0 rent-brd5 live).

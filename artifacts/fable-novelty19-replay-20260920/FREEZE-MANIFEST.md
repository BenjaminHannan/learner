# Experiment 19 — freeze manifest (development phase)

Fable · 20 September 2026 · written before any registered data were generated and before any
registered model forward. This file freezes the inputs; it changes no pass mark.

## Governing documents

| file | sha256 |
|---|---|
| `design/v3/19-novelty-experiment-preregistration-draft.md` (Astra; registration text) | `8498ff9ff66795c9c0aacbbde7fa24c81487f15a0eb297adf7cb903e3eac7823` |
| `design/v3/19-rulings-1.md` (Astra; rulings 1–8, prospective amendment) | `af4cc0d45ee5a346738ab1023c152b4bf1821111c350ae0f4a6c85205ca06079` |
| `FABLE-PREDICTIONS.md` (P51–P61) | `696289b322abe7c76e00e081c1912f926bfde07b82e414a66e9f2ee6d1a92188` |
| `FORGETTING-READOUT.md` (P62–P64, written against the original loose trigger; kept for provenance) | `40ad701857247fc032bb2203ba792bb3c337264e7104afde0a2f9fca4ff33499` |
| `FORGETTING-READOUT-v2.md` (P65–P67, against ruling 7) | `9d1a0b5b5ccc4ca993d951c88d5d5d3fb9204374914aeea5643ec35253c05ef8` |

Primary marks, seeds (1900, 1901, 1902), budgets (awake 6,000 updates in chunks ≤ 750; offline
2,000 in chunks ≤ 500; arms R, G, U; optimizers reset) and Astra's predictions are as written in
the two Astra documents. Where they differ, the rulings file governs.

## Frozen code — one version for every registered run

| file | sha256 |
|---|---|
| `scripts/fable_novelty19_data.py` | `ef1df0e149aa4741a22f7185fadb9eaeb054b072d50c09a1ad2a196a998ae9de` |
| `scripts/fable_novelty19_train.py` | `77644a1f15e6e683b2260261b04411a6ee30c8bb74f80121a8ef7318749cd5a8` |
| `tests/test_fable_novelty19_data.py` (53 checks) | `102caaf22432283cedf71cd108e869e188bc9bd14b40fc0ed577276550805d94` |
| `tests/test_fable_novelty19_train.py` (32 checks) | `788894bb97774c844cc1e58f9107e47c61796756db96d9279e78637804ae84df` |
| `run_data.sh` | `03622cb4a31ae444bb452fcf7a2dd253c47ffc935b85bd1acfb76700792d74f3` |
| `run_awake.sh` | `4d431d1a89ed794744eafd87908353fb475e2dfb972179f3c1df60acdb62a3b5` |
| `run_offline.sh` | `3ec2898da210dbe7021a8a0b87b3d12ea0e8959d3720ebf6d12d58c299c7a794` |
| `run_score.sh` | `62f46ea4bf79e15989835d5400b3bd0948f2a87e6dbfe6f94f9c61e323d21e7b` |

The trainer records a ten-field source fingerprint (trainer, data script, seven frozen modules,
torch version) in every checkpoint and score; `gates` and `report` refuse to merge runs carrying
more than one. Editing either script after this point therefore invalidates the wave rather than
silently mixing versions. Canonical operator checkpoint: sha `e7e5b6f3…` (frozen, unchanged).

## Independent audit

| file | sha256 at freeze | verdict |
|---|---|---|
| `audit/DATA-AUDIT.md` (Re-check 3) | `11132b5dff881db9a99d27161b6d4b1a4c62c266da060aab8071290040d252db` | data side FREEZE-READY = YES |
| `audit/TRAIN-AUDIT.md` (Re-check 3) | `0ede0cdfa4cef2e8e07da091c628c6476f40d08c9d0ce15e41496933eed265ad` | training side FREEZE-READY = YES |

Expected reproduction: operator-history `world_union_sha256`
`0730f99e6e627fa00db03cef5919b814599dfacb3a299a8ded440d28f0dc900a` (96,000 worlds).

## Execution profile

Mac only, no cloud spend. At most 6 one-thread jobs at a time
(`OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`); scoring at most 3 at a time.
Order: `run_data.sh` → `run_awake.sh` (6 runs) → `run_offline.sh` (18 runs, three sub-waves of 6)
→ `run_score.sh` (awake-final and offline-final checkpoints, then `gates`, then `report`).
Each launcher is started by a bare `./run_*.sh` in its own command. Registered caps (eval 16,
capacity 12) are the script defaults and are not overridden. No confirmation-panel path is passed
anywhere; confirmation panels are generated only if `gates` writes `DEV-PASSED.json`.

Any departure from this file is recorded in a separate `DEVIATION-*.md` / `INCIDENT-*.md`, never
by editing this file.

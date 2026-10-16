# Recipe 2: six R2a replica checkpoints (logic line)

Written by the Whole-model roadmap thread, 2026-10-16 (1:50 AM ET). Full record: `logic_transfer/MARKS-LT2-2026-10-14.md` Addendum 11 section 7 (branch `claude/lt2-r2a-replica`, and the copy at `/mnt/project-files/logic-transfer/MARKS-LT2-2026-10-14.md`).

## What exists now
- Six replicas of the sealed R2a runs (rung 6, two facts, 50% share, lr 1e-4, 8,000 updates; parents T1SDR s200 / s201 / s204 x course seeds 1, 2), trained with the sealed code and exported as full checkpoints.
- Checkpoints: branch `claude/lt2-r2a-replica-checkpoints`, commit `ed492051d6`, `logic_transfer/replicas/r2a/<run>/checkpoint.pt` (13,286,967 bytes each; `step` field 32000), with `SHA256SUMS`, `VERIFIED.json` and the rung-6 result block under `result/`. Not on main.
- Each file was hash-checked against the box's own hash, loaded with torch, and re-hashed after re-fetching the pushed branch from GitHub (all match).

| run | sha256 of checkpoint.pt |
|---|---|
| s200-s1 | 5726ad71a2cab96fefad38f4d973aa1d39bb4504f497333e5e644625d2493a5c |
| s200-s2 | 4070924625960040f7abb3807e8d236df626f4fc95b9af90f26f07001b468b3b |
| s201-s1 | c35ba81d9a40e4859c4338fe6a6f81e79d711b3dec0ccd5832967b2ff7dc50de |
| s201-s2 | 9afa380d8a3a0da1c3a603f499d180fcbe5b6e18325a9d64f49c1be8856fab30 |
| s204-s1 | 765733c3e1dd1f94e7a0708e8659a35b4b73b75241485b9291d8bb3fc6626b5d |
| s204-s2 | 5c9f69579d7be8b95543c16db5cb8f057ed542ee14f3b5f35d5787e3492ba4f2 |

## Marks (fixed before the box; Addendum 11 section 3), from the box's own final evals
- M1 mean dev within 3 of 66.1: 65.46, holds.
- M2 mean hard within 6 of 20.8: 18.23, holds.
- M3 none of six meets dev >= 90 and hard >= 80: 0 of 6, holds.
- M4 each dev within 6 of its sealed twin: largest gap 3.4, holds.
- s204-s1 hard is 4 rows lower than its sealed twin (6/32 against 10/32); no mark covers per-run hard.

The replicas reproduce R2a (FAIL 0/6); they never re-verdict it.

## Cost
Vast box 56190880 (RTX 3090, billed $0.3926/h), 11:01 PM ET 10-15 to 1:47 AM ET 10-16, 2.77 h, about $1.09 (computed). Destroyed; instance list empty; credit $34.26. Ceiling was $5.58.

## Not done
The answer-word scorer and per-item predictions (Addendum 11 section 4): the scorer code does not exist yet. It is a free-CPU task and waits for Muse's word.

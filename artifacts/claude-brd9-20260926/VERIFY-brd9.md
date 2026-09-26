# VERIFY brd-9 (creative research thread; written 2026-09-26 17:21 UTC by `date -u`)

Checked: SEAL-brd9.md sha256 for all 8 sealed files (all OK on main), the rental's RESULTS-gpu.md and
brd9_summary.json, and a recount from streams.json, transfer_streams.json and practice.json with the sealed code
(claude_blurt5s.boot_ci, 2,000 draws). The recount matches the rental's numbers. Plain MiniCPM5-1B commit 87179e5c;
RTX 5090; script 46.7 min; 2 rentals (first never reachable); ~$0.63 of the $0.90 task budget. Torch was
reinstalled on the rental (2.11.0+cu128) because the image's build had no Blackwell kernels; code unedited.

## Registered verdict: PASS
- Base cov@30 96 of 240 (3-number 56/80, 4-number 40/160). Unreached 144, so the bar = 0.2 × 144 = 28.8.
- N3 (three nights): 139 / 135 / 131, i.e. +43 / +39 / +35 over base. Every seed clears 28.8; the 95% interval for
  N3 − base is [+10.56, +21.81] points, above 0. **PASS.**
- G7 (+24 in every seed, interval above 0): **MET**.
- NIGHTS (N3 ≥ N1 + 12 in every seed, interval above 0): **NOT MET**. N3 − N1 = +28 / +21 / +9 (seed 2 short by 3),
  interval [+4.58, +11.84].
- Proved wrong: no (upper bound 21.81 vs 12.0). Inconclusive: no (185 night-1 wins).
- Practice: all saved answers pass the exact checker (0 bad).

## Reported rows
- After each night: N1 111 / 114 / 122 (+15 / +18 / +26; one night alone would miss 28.8 in two seeds), N2 142 / 124 /
  132, N3 139 / 135 / 131. Most of the gain comes by night 2; night 3 held it (−3 / +11 / −1 vs N2).
- By kind (N3): 3-number 75 / 72 / 72 of 80 (base 56); 4-number 64 / 63 / 59 of 160 (base 40). Both kinds gain.
- Practice got better each night: wins + own on the 400 new puzzles were 205 (night 1, base model), 243-260
  (night 2), 272-286 (night 3).
- Near carry-over (addendum T, report only): 4 numbers with a target other than 24, a target no practice puzzle had.
  Base 13 of 80 -> N3 45 / 32 / 32; N3 − base interval [+18.14, +40.08], above 0, so near carry-over is seen. This
  is the same skill with a different goal, not a new kind.

## What it means, and limits
- Three nights of the model's own checked hits clear problem 7's bar on a fresh panel that leans to the harder
  four-number puzzles, with the bar set on the room the base model leaves. G7 (+24) is met as well.
- N3 has seen three times the puzzles and training steps of N1. That is what nights are, and brd-8 showed that
  which model collects the hits made no clear difference. So the gain is "more nights of own hits", not compounding.
- One panel, one puzzle world (numbers, which is now used up). Per the plan (design/v3/30-modes/brd-10-fallback-plan.md),
  problem 7 counts as solved only after a replication passes in a new world: the shared number squares
  (scripts/claude_world_latin.py), plain sampling (no RuleKeeper), test seeds 901000+.

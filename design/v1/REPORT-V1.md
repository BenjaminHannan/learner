# V1 report (dev results; sealed split NOT opened)

Branch `claude/v1-assembly`. Spec `V1_SPEC.md` (frozen), params `V1_PARAMS.md` + AMENDMENT-1. Marks unchanged: W1-dev >= 18.95% (best no-learning dev baseline 8.95% + 10), W2-dev >= 20% creative first-try by the official scorer. All numbers below are DEV (and D validation); nothing sealed was read.

## For Ben (plain words)
After fixing two bugs, both arms trained for the full 12,000 steps with no abort rule firing, and both clear both dev marks. The FULL arm (everything on) beat the FLOOR arm (same without Muon/S2) on the main model by about 11.7 points, and tied it on the creative side. By the rule fixed in advance, FULL is the arm that would open the sealed test. **It has not been opened**, because I destroyed FULL's rented box after saving only its small results file, not its model weights, and the sealed read needs those weights. That is my mistake; it is fixable but costs one more run (below). Dev numbers are not the final answer: the sealed test is.

## Results (fixed code, commit e6b4fc81d = cc631cb37 + result files only)
| | FLOOR | FULL |
|---|---|---|
| Steps / aborts | 12,000 / none | 12,000 / none |
| D dev accuracy (42,653 q) | 68.4% | **80.1%** |
| D validation (8,675 q) | 30.9% | 44.7% |
| D dev, bridge off (lesion) | 27.0% | 26.1% |
| W1-dev (>= 18.95%) | PASS | PASS |
| Creative dev first-try (256) | 34.0% | 34.8% |
| Creative, bridge off | 2.3% | 3.9% |
| W2-dev (>= 20%) | PASS | PASS |
| KL share (warm-up / N' / W1 / W2 sleep) | 16 / 12 / 22 / 16 % | 20 / 17 / 27 / 24 % |
Creative by kind (FULL): last_digit 98%, square 73%, double_add 2%, sq_plus 2%, affine 0%. FLOOR similar (84%, 80%, 4%, 2%, 0%). Most of the creative gain is two easy kinds.
A3 (KL share > 50%) never fired (max 27%). A1/A2/A4 did not fire. A5: one box died (see below), one relaunch used.

Mechanical D5 (`v1/decide.py`, `results2/decision/DECISION.json`): chosen = **full** (higher D dev accuracy); W1 and W2 both met on dev -> seal opens in principle; `DEV_PASS.json` written. `SEALED_READ.json` does NOT exist.

Floor-vs-full (dev, fixed code only; the first-arm comparison is void): FULL +11.7 points on D dev, +0.8 points creative (within noise, n=256). Bridge-off lesion costs both arms most of their accuracy (D: -54 points FULL, -41 FLOOR; creative: -31 FULL, -32 FLOOR), so the bridge matters on dev for both. Not separated here: how much of FULL's edge is Muon vs S2 (they were switched on together by design).

## What went wrong (honest account)
1. Two bugs in the first arms (found by the offline bridge diagnostic): (a) samplers ignored the bridge, so creative dev/search ran without it; (b) the bridge registered D/B2 as submodules so a second optimizer touched every D weight. Both fixed, tested (tests fail on old code), reviewed (no blocking findings). First-arm results are void (KNOWN_ISSUES 20-23).
2. FULL's first re-run box went silent (log frozen 00:04 UTC, billing on), was stopped, its disk could not be read, destroyed with --abandon (A5), relaunched once from scratch.
3. **My error:** after the relaunched FULL finished I pulled only `out.tar.gz` (final_dev.json, logs, spend; sha-verified) and destroyed the box. The sealed read (`v1/sealed_read.py`) needs `D-final.pt` and `creative/W2.pt`, which were in the box's separate `ckpt.tar.gz`. They are gone. FLOOR's weights are also not held.
4. GPU resume is not bit-exact (KNOWN_ISSUES 19; mark 1e-3 missed, not loosened).

## Spend (re-run, estimates from uptime x price; Vast credit ~$54)
FLOOR box ~$1.7; dead FULL box ~$1.5; relaunched FULL ~$1.3. Total ~$4.5 of the $5.50 cap. Gate S and first arms were earlier.

## Not done / open
- Sealed read (D6): NOT done; blocked by (3). Options for the coordinator/Ben: (A) re-run FULL once more (~$1.5-1.9, needs the cap raised above $5.50) and pull D-final.pt + W2.pt before destroying; the re-run will not reproduce these numbers exactly (GPU nondeterminism), so it must be re-judged on dev by the same marks before the seal opens, and D5 re-applied; (B) leave the seal shut and report dev-only results.
- E0 diagnostic: not run (needs weights).
- KNOWN_ISSUES still apply (G1 premise, Muon D-only, bridge notes).

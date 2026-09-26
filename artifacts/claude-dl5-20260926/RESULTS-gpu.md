# dl-5 grid nights from go-back search hits: GPU result (rental, 2026-09-26)

Registered rule: artifacts/claude-dl5-20260926/PASSMARKS.md (origin/main).
Code: scripts/claude_dl5_gridnights.py (Fix-sleep thread) + scripts/claude_gridday.py (thought-memory thread)
+ scripts/claude_blurt1.py + scripts/claude_blurt2.py + scripts/claude_dl1_nights.py
+ scripts/claude_rsn358a_envs.py + scripts/claude_rv385.py, all from origin/main, unmodified, never edited.
Command: `python -B scripts/claude_dl5_gridnights.py --model BASE --out gpu`
BASE = local snapshot of openbmb/MiniCPM5-1B at pinned revision
87179e5c1f455ef22e6223592d2d61351b525bfc (same files as dl-2, thinking off).
Python: rental image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime
(torch 2.8.0+cu128, CUDA True, transformers 5.17.0 pip-installed, image had none).
Blind recount of dl5_results.json against PASSMARKS.md before this report: every number below
recomputed by hand from the per-night rows; all match the stored marks block exactly.

## marks block (whole block from gpu/dl5_results.json)

```json
{
 "night0_pts": 48.8,
 "S_final_pts": [
  93.8,
  93.4
 ],
 "P_final_pts": [
  6.6,
  7.2
 ],
 "S_final_open_pts": [
  67.8,
  65.0
 ],
 "P_final_open_pts": [
  35.0,
  38.5
 ],
 "S_final_lost": [
  98,
  61
 ],
 "S_night1_rows": [
  1144,
  925
 ],
 "G1 slept model better: S final >= night 0 + 15 points on each seed": true,
 "G2 right answers caused it: S final >= P final + 10 points on each seed": true,
 "G2b right answers beat legal-looking wrong ones: S final >= P final + 10 points on OPEN states, each seed": true,
 "G3 no harm: S final lost <= 20 of the base-right panel items on each seed": false,
 "verdict": "FAIL",
 "proved_wrong": false
}
```

- Night 0 (plain 1B, 60 fresh test grids seed 38990, 762 states): right 372/762 = 48.8 pts
  (forced 314/619, open 58/143). HARM panel right 200/300.
- S final: s8 715/762 = 93.8 pts (forced 618/619, open 97/143);
  s9 712/762 = 93.4 pts (forced 619/619, open 93/143).
- P final: s8 50/762 = 6.6 pts (forced 0/619, open 50/143);
  s9 55/762 = 7.2 pts (forced 0/619, open 55/143).
- S final lost (right at base, wrong now): 98 (s8), 61 (s9). S night-1 rows: 1144 (s8), 925 (s9).

- G1 slept model better (S final >= night 0 + 15 pts = 63.8 on each seed):
  s8 93.8 >= 63.8 and s9 93.4 >= 63.8. **G1 PASS.**
- G2 right answers caused it (S >= P + 10 pts on each seed):
  s8 93.8 >= 16.6 and s9 93.4 >= 17.2. **G2 PASS.**
- G2b right answers beat legal-looking wrong ones (OPEN states, S >= P + 10 pts on each seed):
  s8 67.8 >= 45.0 and s9 65.0 >= 48.5. **G2b PASS.**
- G3 no harm (S final lost <= 20 on each seed): s8 lost 98 > 20, s9 lost 61 > 20. **G3 FAIL.**

Registered verdict: **FAIL** (G1, G2, G2b pass; G3 fails).
Not INCONCLUSIVE: S night-1 rows 1144, 925, both >= 100.
Proved-wrong clause (on open states, S <= P on both seeds): s8 97 > 50 and s9 93 > 55.
**Not proved wrong.**

## Report only (no marks)

- K arm, seed 8 (answer-key ceiling, every day grid): per-night right 705, 715, 705, 715, 706 / 762
  (forced 619/619 every night; open 86, 96, 86, 96, 87 / 143);
  lost 8, 49, 51, 102, 135; gained 60, 17, 23, 17, 4. K rows 1875, 1916, 1948, 1898, 1934.
- Forced vs open, every arm and night: S ends forced 618/619 (s8), 619/619 (s9);
  P ends forced 0/619 both seeds (the wrong-number nights erase forced-state accuracy entirely);
  base forced 314/619, open 58/143.
- S per-night right: s8: 714, 709, 711, 710, 715 / 762; s9: 710, 699, 708, 712, 712 / 762.
  S per-night lost/gained: s8 8/60, 21/29, 38/28, 46/26, 98/18; s9 7/58, 14/66, 46/34, 48/22, 61/14.
  P per-night right: s8 89, 42, 57, 96, 50 / 762; s9 56, 52, 52, 56, 55 / 762.
- Grids solved per S day (150 grids, budget 60 choices each):
  s8: 101, 103, 105, 107, 113 (choices used 6509, 4742, 5008, 4656, 4703);
  s9: 85, 101, 92, 101, 104 (choices used 6780, 4785, 5373, 5070, 4893).
  S rows per night: s8 1144, 1165, 1226, 1226, 1337; s9 925, 1146, 1054, 1204, 1207.
- P legal-looking vs any-wrong counts per night (rows sampled down to S's count):
  s8 legal 224, 247, 260, 269, 269 vs any-wrong 920, 918, 966, 957, 1068;
  s9 legal 182, 236, 242, 250, 272 vs any-wrong 743, 910, 812, 954, 935.
- Test grids also found in a day: 0 (as expected).
- The rv-386 first-choice gate on the final S adapters and on adapter02c was not run here;
  the saved adapters below are kept locally for it (never pushed).

## Run facts

- GPU: NVIDIA GeForce RTX 5090 (rental, South Korea; driver 580.173.02).
- Wall: 87.7 minutes (run; rental span ~96 min incl. setup).
- Dollars: rental 1 (contract 52770457, RTX 5090, dph $0.4361, ~0.10 h, host docker-proxy pull refusal,
  destroyed un-run) ~$0.04 + rental 2 (contract 52771192, RTX 5090, dph $0.4806,
  created ~15:35Z running 15:39Z destroyed 17:11Z, ~1.60 h) ~$0.77;
  task total ~$0.81 of $1.60 budget. 2 rentals of max 3.
- Code commit hash (origin/main): 76d9d98f69b4dc2aeb6c4adcf7f5bea3f6384d98.
- Model commit hash (HF snapshot revision): 87179e5c1f455ef22e6223592d2d61351b525bfc.
- Adapters (kept locally, NEVER pushed): gpu/dl5-S-s8.pt 16575557 bytes
  sha256 c74b1783da59423ec2e5f7ac3758157679c61715e157a8295c2ec424e1a541eb (192 tensors);
  gpu/dl5-S-s9.pt 16575557 bytes
  sha256 5352be4413a6b2f5c7c5f9dd5e6584cc6fd5d731dd472ca42b81cc8b0eee52a6 (192 tensors).
- Files: artifacts/claude-dl5-20260926/gpu/dl5_results.json (sha256
  e52d11d5030a7ad1dffd7cc1df09becf991613e447efb5d7c492f38be30059bf), gpu/log.txt (sha256
  7ad2f7342a943394973b0dde798a8b3a39440f008bfff0edeb7b1b7edf4a3df4),
  gpu/dl5-S-s8.json, gpu/dl5-S-s9.json (sidecars pushed), gpu/dl5-S-s8.pt, gpu/dl5-S-s9.pt
  (weights local only). Hashes match both ends. Rental destroyed, 0 claude-fixsleep-dl5 live.
  Credit at gate 8.60 (balance 0). Test grids were made inside the run and never printed.

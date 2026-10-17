# PREREG: trace A2, the noise-referenced restart gate, and the re-judgment of g2fa8's 0.0282 (written 2026-10-17 ~21:05 UTC, before any probe number exists)

Status: **DRAFT recommendation for Ben.** No bar has moved. Nothing here halts, arms, clears or restarts anything. Bars are Ben's to change.
Written by the restart-gate solve session. Inputs: `pc-job-cards/g2fa4/` at ccdbd06e9b (README, TRACE-A-READING-2026-10-14.md, `g2fa4_supervisor.py` `trace_a`/`resume_probe_verdict`/`probe_resume`), the coordinator's packet (accum-8 stop 0.0282, diagnosis verdict SYSTEMATIC), `sims/` in this folder.
When this file was written, the CPU positive-control experiment (`posctrl/`) was still running and had no results. Nothing below was tuned on its numbers.

## 1. What the gate certifies (the claim under test)
A resume is healthy if the resumed process is **exchangeable with the process that never stopped**: the run C that continued in memory and any fresh resume R of the checkpoint are two draws of the same nondeterministic process. On this trainer (bf16 autocast, no determinism flags, `custom_io/train.py` at 74d6e92c75, `g8a/configs.py:368` bf16=True), the uninterrupted run is not reproducible either. So "bit-for-bit" is not a property the run itself has, and it cannot be the bar. The measurable question is whether resume-vs-logged looks like resume-vs-resume.

## 2. Two layers
**Layer R, the running gate (stops the run). Unchanged items:** no NaN/Inf; the loss falls (mean 251-300 below mean 1-50); the **first redone update within 0.01** (`resume_first_diff`). This is the restore detector. The forward pass is deterministic, so with complete restore the first redone update is exact (accum 4 on the PC card: 0.0, TRACE-A-READING). A wrong data position, lost RNG streams or wrong weights show up there.
**Changed (recommended):** the redone-window mean |ΔL| (`resume_mean_abs`, 0.02) and max |ΔL| (`resume_max_abs`, 0.10) become **recorded, not gated** at run time. These are the statistics that rounding noise grows into, and a running stop on them costs days of idle card per false stop (g2fa8 has been stopped since 10-15 15:43 ET).

**Layer P, the reading gate (decides whether the result is read). Run on the PC card at the run's accum, after the run or on Ben's halt go:** `probe-resume --step 200 --upto 250` (two fresh resumes R1, R2 of the run's own step-200 checkpoint; C = the run's logged updates 201-250). The result is read only if all three hold:
- **P1 exact first update.** |R1-C| = |R2-C| = 0 at update 201. Non-zero means the wrong checkpoint or an incomplete restore. Investigate before reading; it is not a noise question.
- **P2 (registered 10-14, unchanged).** d = max|Ri-C| ≤ max(0.10, 3n), n = max|R1-R2|.
- **P3 mean form (new, pre-registered here).** D̄ ≤ max(0.02, 2·N̄), with D̄ = mean(mean|R1-C|, mean|R2-C|) and N̄ = mean|R1-R2| over 201-250. All three numbers are already written by `resume_probe_verdict` (`mean_abs_r1_c`, `mean_abs_r2_c`, `mean_abs_r1_r2`).

## 3. Where the limit comes from (the derived noise budget)
The bar in house form:
**L(a, w) = max(0.02, 2.0 × the largest of the 6 pairwise mean |Ri-Rj| from 4 fresh resumes of one checkpoint over window w, at accum a, on the PC card).**
- *Derived from:* measured resume-vs-resume noise (not a constant), plus exchangeability. Under exchangeability a healthy D̄ has the same distribution as any one pair's mean. `sims/fa_sim2.py` gives the healthy false-alarm rate P(D̄ > 2 × max of 6 pairs): **5.2 % in the worst case** (the 50 redone updates carry one effective sample, lag-1 ρ = 1), 1.8 % at ρ = 0.95, 0.1 % at ρ = 0.8. The 0.02 floor keeps a near-deterministic card (N̄ ≈ 0) from being held to zero. It is the old CPU-era constant, demoted from limit to floor.
- *Why not the 2-resume ratio alone:* with only R1, R2 as the noise reference, P(D̄ > 2N̄) is 29 % at ρ = 1, 13 % at ρ = 0.95 and 2.3 % at ρ = 0.8 (`sims/fa_sim2.py`, K = 2). P3 is therefore a reading check whose reliability depends on the measured ρ (the probe JSON lets us compute it). The calibrated L is the bar.
- *Falsified by:* (a) a healthy resume (P1 exact) exceeding L in more than 1 of 10 repeat probes (false alarms too frequent, so exchangeability or the calibration is wrong); (b) a positive-control broken resume (a fault class that P1 does not catch) landing under L (the bar cannot see it); (c) R1 and R2 **bit-identical** on the card (n = 0). That would mean fresh GPU processes do not differ, so the 0.0282 is not per-call rounding noise and the SYSTEMATIC diagnosis is wrong.

**Calibration run (optional, for the bar's constant; about 40 min card time at accum 8):** 4 resumes of step-200 over 201-250 (with C), plus 4 resumes of step-300 over 301-350 (noise only; C is not needed for R-R pairs). It can be done as two invocations of the existing probe per window, with each `PROBE-RESUME-g2fa8.json` copied aside before the next one (the probe overwrites it). Pair the four R lists offline.

**Provisional accum-8 number until the calibration exists (recommendation, not a change): 0.05 on the trace-A window 101-150.** Derived as 0.0167 (the only same-card measurement, accum 4) × 2 (top of the diagnosis's √2-2 accum-8/accum-4 noise scaling) × 1.5 (one-draw spread: q95 of the ratio of two exchangeable means at ρ ≈ 0.8, `sims/fa_sim.py`). Falsified by the calibration giving 2 × max-pair > 0.05 at 201-250 (too tight), or by a positive-control fault class that only the mean can see landing under 0.05 (too loose).

## 4. Re-judgment rule for g2fa8's 0.0282 (fixed now)
Apply to `PROBE-RESUME-g2fa8.json` (`drafts/rejudge_probe.py` implements it):
- **INSIDE healthy noise:** P1, P2 and P3 hold, D̄/N̄ ≤ 2, **and** 0.0282 ≤ max(0.02, 2·N̄(201-250)).
- **UNRESOLVED:** P1-P3 hold but 0.0282 > max(0.02, 2·N̄(201-250)). The probe window 201-250 is likely calmer than the trace-A window 101-150 (loss 3.9 → 3.0, the model changes more slowly). Only a same-window measurement settles it: a fresh run with two extra resumes of step-100. This is not a FAIL.
- **OUTSIDE:** P1 fails, or P2/P3 fail with R1 ≈ R2 (the resumes agree with each other but not with the logged run, meaning restored state differs from continuing).

## 5. Safety conditions for the probe (from reading the code, not optional)
- **Use g2fa8's own step-200.** The README's documented `--keep work\g2fa4\ckpt-keep` holds **g2fa4's accum-4** step-200. `probe_resume` does not check this, and `overlay/train.py:472` only *warns* on an accum mismatch (`--accum` is not in the config hash, `:131`). Without `--job`, the probe picks g2fa8 (the first unskipped job). Run literally, the documented command resumes an accum-4 checkpoint under accum 8 and reports a false FAIL. Copy (never move) `...\8aB3G2A8-pc\8aB3G2A8-3M-s400\B3G2\ckpt\step-200.pt` and `step-200.json` into a new folder (e.g. `work\g2fa4\ckpt-keep-g2fa8`). Check that the sidecar says `"accum": 8`. Pass `--job g2fa8`. (`drafts/` adds a guard that refuses the mismatch.)
- **Copy step-200 before any `clear`/re-arm of g2fa8.** The overlay keeps the newest 2 checkpoints (`CKPT_KEEP = 2`). A continued run writes step-400 and deletes step-200.
- **An accum-4 probe is refused as the plan stands.** g2fa4 is `skip: true`, and `probe_resume` refuses skipped jobs. It is not needed for the accum-8 verdict.

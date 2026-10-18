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
- **C must be one continuous segment over 201-250.** `probe_resume` takes C as the first logged line per step. For g2fa8 that holds: the only restart was the planned one at 150, which redid 101-150. Check `events.jsonl` for any other `resumed` event between 200 and 250 before reading.
- **An accum-4 probe is refused as the plan stands.** g2fa4 is `skip: true`, and `probe_resume` refuses skipped jobs. It is not needed for the accum-8 verdict.

---

## Amendment 1 (2026-10-17 ~22:05 UTC): after the CPU positive controls (`posctrl/RESULTS.md`), before any GPU probe number
Everything above stays as written. These changes are made because the positive controls showed two gaps in the design (shown on CPU, emulated noise):

**A1.1 The first redone update cannot see optimizer-state faults.** Its loss is a forward pass computed before the optimizer step. Lost AdamW state (`opt_reset`, `opt_moments_zero`) and an off-by-one lr schedule (`lr_step_off`) gave **exactly 0** at the first redone update. They first showed at the second: `opt_reset` 0.0145-0.98, `opt_moments_zero` 0.106-1.01, `lr_step_off` 0.028-0.077, against a healthy maximum of 7e-5 to 0.009 at that update for noise up to 1 (posctrl Table C). So:
- **Layer R adds an early-window item (hard):** max |ΔL| over the 2nd and 3rd redone updates (GPU: 102-103) **≤ 0.005**. Derived from: GPU healthy at accum 4 ≤ 2e-4 over 101-107 (TRACE-A-READING), which leaves about 25x headroom (about 15x at accum 8 with the diagnosis's 1.7x). The smallest optimizer/lr fault signature on CPU at that update (0.0145 and 0.028) is about 3-6x above it. Falsified by: a healthy GPU resume over 0.005 at 102-103, or a GPU positive control with lost optimizer state under it. The CPU-to-GPU scale transfer is **untested**.
- **Layer R adds an exact-field item (hard):** at the first redone update, the logged fields that are data/RNG-derived (`lr`, `rounds`, `plan_*`) must be **equal**. They carry no rounding noise. `lr_step_off` showed in `lr` at that update, and the RNG faults in `rounds` and `plan_*` (posctrl). The pack's own CPU test already treats these fields as exact.
- **Layer P adds P1b:** the same early-window item on probe updates 202-203.

**A1.2 Tighten the first-update item from 0.01 to exact (recommendation; Ben's bar).** A 1e-3 relative weight corruption gave 7.3e-4 to 0.0145 at the first redone update (linear in its size; posctrl Table D). Part of that range is under 0.01, and the mean statistic cannot see it (bug-to-noise ratio about 1 once noise is about 0.1 % of the loss). On the PC card at accum 4 the first redone update was 0.0 exactly. Proposed: ≤ 1e-4 (the log resolution allows exact; 1e-4 leaves room for logging).

**A1.3 A ratio failure alone means "measure more", not "broken".** One healthy CPU cell gave D/N = 3.13 with C the most distant of five runs. Three replicates of that cell gave 0.85-1.24. This is the heavy tail `sims/` predicts. Re-judgment rule §4 is amended:
- **OUTSIDE** only if P1 or P1b fails, or if after the 4-resume calibration D̄ > L(a, w).
- If P1, P1b and P2 pass and P3 (or D̄/N̄ ≤ 2) fails, the verdict is **UNRESOLVED: run the calibration** (2 more resumes at step-200, judge D̄ against L).
- INSIDE as before.
- **Clarification (2026-10-18, after the code review; coordinator ruling):** the 4-resume calibration resolves **only** the borderline UNRESOLVED_CALIBRATE case. It is never applied to a two-resume verdict of INSIDE, OUTSIDE or UNRESOLVED (window). An UNRESOLVED (window) still needs the same-window measurement of §4, so adding resumes cannot turn it into INSIDE.

**Status:** Amendment 1 remains a DRAFT recommendation. Adopting it is Ben's decision. The registered probe rule (P2) is unchanged.

**What the positive controls say about where bugs are caught:** every fault class tried was caught by the start-of-redo checks: the exact first update (data, RNG, weights), the exact fields (lr, RNG), and the early window (optimizer, lr). Each was caught with ≥ 3x margin at bf16-like noise. The window mean caught nothing those miss. This supports moving the mean from the running gate to the record (shown on CPU; untested on GPU).

# The restart-drift gate (trace A): what it should certify, a noise-referenced bar, and the re-judged 0.0282 (2026-10-17)

Solve session for Muse's Ultracode packet "the restart-drift gate (trace A)" and the /goal that followed it. Labels: **shown** = measured (in the record, or by this session on CPU); **suggested** = reasoning or arithmetic on shown numbers; **untested** = nothing measured.
**No CUDA number here was produced by this session.** Nothing on the PC was touched. No money was spent. Bars are Ben's; everything below that changes a bar is a recommendation.

Files in this folder:
| file | what | status |
|---|---|---|
| `BRIEF-FOR-BEN.md` | the one page for Ben | final |
| `PREREG-trace-a2.md` | the corrected gate, the measurement plan and the 0.0282 re-judgment rule, committed (8bdabbe2fd, 21:00 UTC) **before** any probe or positive-control number | pre-registered draft |
| `sims/` | false-alarm simulations behind the bar's multiplier | shown (simulation) |
| `posctrl/` | CPU positive controls: what a really broken restore looks like next to emulated GPU noise | shown (CPU, emulated noise) |
| `drafts/` | draft code (probe checkpoint guard, mean-form fields, soft-able mean item, `rejudge_probe.py`) + tests | draft, for code review |

---

## 0. Packet claims that the code or the record contradicts

| # | packet says | record / code says | evidence |
|---|---|---|---|
| 1 | "the accum-4 pass value 0.0167"; accum-4 is "the healthy accum-4 evidence" | 0.0167 passed **one item**. The accum-4 run's trace A as a whole **FAILED and stopped the run**: the largest single redone difference was 0.1191 > 0.10, and whole-card memory was 15,757 > 12,288 MiB. Its health is inferred (first redone update exact) and was never measured: no probe ever ran. The reference point for re-judging 0.0282 is itself only suggested-healthy. | `TRACE-A-READING-2026-10-14.md` table; README "Update 10-15" |
| 2 | "It [probe-resume] has never been run for either job" (implying it can run for either) | As the plan stands it **cannot run for g2fa4**. g2fa4 is `skip: true` (`--skip-g2fa4`), and `probe_resume` refuses a skipped job. Only g2fa8 can be probed without a plan change. | `g2fa4_supervisor.py` `probe_resume`: `if job.get('skip'): ... refused` |
| 3 | probe-resume "resumes the kept step-200 checkpoint" | The kept folder in the runbook (`work\g2fa4\ckpt-keep`) holds **g2fa4's accum-4** step-200, copied by the Mac on 10-14. `probe_resume` never checks that the checkpoint belongs to the job. `--accum` is not in the resume config hash, and an accum mismatch only **warns**. The documented command line, run for g2fa8 (the default job without `--job`), would resume an accum-4 checkpoint under accum 8 and report a false FAIL. | `probe_resume` (no sidecar check); `overlay/train.py:131` (accum left out of the hash), `:472` (warning only) |
| 4 | Speed record "accum 4 = 2.24 s/update; accum 8 = 3.26; accum 16 = 6.01", used as the PC cost basis | These are **rented 4090** numbers (GPU-RUN-3). The only PC figure is a visual read of about 2.2 s/update at accum 4. The README's own suggestion for the 5070 Ti at accum 8 is 3.5-4 s/update, untested. Costs below use the settled 4090 record as asked and flag this. | `GPU-RUN-3-2026-10-15.md` header ("never on the PC's 5070 Ti"); README g2fa8 step 6 |
| 5 | "the 0.02 limit ... was set ... from a CPU test" | Confirmed, with one sharpening. The CPU test it came from was **bit-exact** in the sandbox (zero noise), so 0.02 had no measured noise basis on CPU either. The author wrote "the resume limits are mine". | `TRACE-A-READING` ("mine, set on 10-14 from the CPU test"); `tests/logs/ckpt_b3g2_exact_mode.log` ("machine noise: none") |
| 6 | "the trainer runs bf16 autocast with zero determinism settings" | Confirmed from code. `train.py --bf16` defaults to off, but the g8a builder appends it (`g8a/configs.py:368,384`, `bf16=True`). No `use_deterministic_algorithms`, `cudnn.deterministic`, `benchmark` or TF32 setting exists in `custom_io` at 74d6e92c75. | grep at 74d6e92c75 |
| 7 | (implicit) the accum-8 stop record is on file | The 0.0282 and the diagnosis memo `hidden_files/trace-a-accum8-diagnosis.md` are **not in the repo or in Drive/Gmail**. A prior solve (LAUNCH-BOUND-SOLVE §0 #6) found the same thing. I take 0.0282 and the diagnosis as settled, per the packet. The accum-8 first redone difference, max difference and per-update series are on the PC only (`TRACE-A-g2fa8.md`, `state.json`, `events.jsonl`). | record search of all 115 branches, Drive and Gmail |

None of these overturns the diagnosis. Items 2 and 3 change the probe procedure (PREREG §5). Item 1 weakens the reference point the goal's re-judgment leans on.

---

## 1. What a restart gate should certify, and which meaning this project needs

**What the official G2f read is used for.** At update 24,000 the run's marks are read (B3G2-1..7, thinker rounds at inference, stop-head accuracy) and compared with other arms and recipes of the big-run line. Every comparison on record is made **at the scale of seed-to-seed variation**: the gate-3 line is 0.06, against an accum-4 seed pair that differs by 0.04 (GPU-RUN-3). No comparison on record is, or could be, made at the precision of floating-point rounding.

**The three candidate meanings:**
- *Bit-for-bit.* The uninterrupted run does not have this property. On this trainer the same command from the same state gives a different trajectory on every call, because nondeterministic kernels re-round on each backward, in-process as well as across processes. Demanding that a resume be closer to the logged run than the logged run is to itself is incoherent. It would need the determinism retrofit of §3, and nothing downstream needs it.
- *Close enough that downstream reads are unaffected.* This is the real goal, but it cannot be measured in a 50-update window. Its effect only shows at update 24,000.
- *Statistically the same run.* The resumed run is one more draw of the same nondeterministic process as the uninterrupted one. **This is the meaning the project needs, and it is sufficient for the downstream one** (suggested, by this argument). If a resume is exchangeable with continuing, a restart changes the final read no more than rerunning the identical command would. That is at most seed variation, which every downstream comparison already has to tolerate. If a resume is *not* exchangeable (state was lost), the run is a different run, and the read must not count.

**Trace A's job, for a non-specialist:** when the training run is stopped and picked up again from a save point, trace A checks that the save point really held everything, so the picked-up run is a genuine continuation and not a slightly different run in disguise. The graphics card never does the same arithmetic twice in exactly the same order. So two honest continuations already drift apart a little, and the check has to ask whether the restarted run is further from the original than one honest rerun is from another. The old limit (0.02) was picked before anyone had measured how far honest reruns drift. Measured on this card, honest drift can be bigger than 0.02, so the old check cannot tell a healthy restart from a broken one.

## 2. The corrected gate and its derived noise budget

Full text, fixed before any number: `PREREG-trace-a2.md`. In short:

**Layer R, the running gate (stops the run).** These are the start-of-redo checks, where a broken restore is loud and rounding noise is zero or nearly so:
- NaN/Inf and loss falls (unchanged);
- the **first redone update** (kept at 0.01; recommended tightened to ≤ 1e-4, since on the PC at accum 4 it was exactly 0.0);
- **exact `lr`/`rounds`/`plan_*` at the first redone update** (new, Amendment 1);
- **max |ΔL| ≤ 0.005 on redone updates 2-3** (new, Amendment 1; this is what catches lost optimizer state).

The redone-window **mean and max become recorded, not gated** (recommendation).

**Layer P, the reading gate (decides whether the result counts):** probe-resume at step 200 on the card.
- P1: update 201 exact for both resumes.
- P1b: updates 202-203 within 0.005.
- P2: the registered d ≤ max(0.10, 3n), unchanged.
- P3: D̄ ≤ max(0.02, 2·N̄) (mean form, new). A P3 failure alone triggers the 4-resume calibration; it is not a fail.

**The bar in house form:** *L(a, w) = max(0.02, 2.0 × largest of 6 pairwise mean |Ri−Rj| from 4 fresh resumes, accum a, window w, PC card).*
- **Derived from:** measured resume-vs-resume noise plus exchangeability. Healthy false-alarm rate ≤ 5.2 % even if the 50 updates carry one effective sample, 0.1 % at lag-1 ρ = 0.8 (`sims/fa_sim2.out.txt`).
- **Falsified by:** a healthy resume (P1 exact) over L in more than 1 of 10 repeat probes; a positive-control fault class that P1 misses landing under L; or **R1 ≡ R2 bit-identical on the card** (n = 0), which would kill the GPU-nondeterminism diagnosis itself.
- **How many repeats, which windows:** the registered probe (2 resumes, 201-250, about 10 min) re-judges g2fa8. The calibration that fixes the constant is 4 resumes at step-200 (201-250, with C) plus 4 at step-300 (301-350, R-R pairs only; C is not needed), about 40 min at accum 8. Two windows, because the noise level depends on where in training the window sits. The trace-A window 101-150 cannot be re-measured for g2fa8: step-100 has rotated away (`CKPT_KEEP = 2`).
- **Why a calibrated noise scale, not a fresh 2-resume ratio:** with only one R-R pair as the reference, the healthy ratio D̄/N̄ is heavy-tailed when the difference series is strongly autocorrelated. P(ratio > 2) is 29 % at ρ = 1 and 13 % at ρ = 0.95 (`sims/fa_sim2.out.txt`, K = 2). A per-run ratio is a useful reading check. It is too noisy to be the bar.

**Proposed limit for accum 8 specifically (recommendation for Ben, not a change):**
- Structure: trace-A mean recorded at run time; reading gated by P1-P3.
- If Ben prefers to keep a running stop on the mean until the calibration exists: **0.05** on 101-150. Derived as 0.0167 (the only same-card measurement) × 2 (top of the diagnosis's √2-2 accum scaling) × 1.5 (one-draw spread, q95 at ρ ≈ 0.8).
- Falsified if the calibration gives 2 × max-pair > 0.05, or if a fault class that only the mean can see lands under 0.05.

### 2a. The re-judged verdict on 0.0282
**Verdict: inside healthy noise. Suggested (strong) from the record; not yet shown.** It becomes shown or overturned by one probe under the pre-registered rule (PREREG §4).
- The diagnosis's scaling, applied to the only same-card measurement, predicts a healthy accum-8 value of 0.0167 × [√2, 2] = **[0.0236, 0.0334]**. 0.0282 is in the middle (1.69×). (Caveat: the 1.69 ratio is computed from these same two numbers. The independent part is the √2-2 band from the micro-batch count.)
- A broken restore would show at the first redone update. The packet reports the accum-8 stop reason as the average only. A first-update miss would also have been listed in `why_fail` (`trace_a`). So it very likely passed ≤ 0.01, but **this must be confirmed from `TRACE-A-g2fa8.md` on the PC**. On accum 4 it was exactly 0.
- The CPU test reproduces kill+resume bit-for-bit at accum 8 (settled).
- Under the corrected gate: Layer R **would not have stopped the run**. Against the provisional 0.05, 0.0282 passes (56 % of the limit). Layer P: pending the probe.
- **The goal's criterion 2:** the corrected gate passes accum-4's 0.0167. Under Layer R the mean is recorded only. Under the provisional numeric rule 0.0167 is below the 0.02 floor. That pass is **by construction** (floor ≥ 0.0167) and is not an independent test of the gate. The honest test is the probe.
- **What would make the verdict OUTSIDE (as amended):** update 201 not exact, updates 202-203 over 0.005, or (after the 4-resume calibration) D̄ > L.
- **UNRESOLVED, not FAIL**, in two cases:
  - a ratio or P2 failure with the start-of-redo checks clean. Next step: calibrate.
  - N̄(201-250) < 0.0141, so the calmer probe window cannot vouch for 101-150. Settling that needs a fresh run with two extra resumes of step-100.
- **Read the accum-8 record too.** If update 101 was exact and 102-103 are under 0.005 in the PC's own trace-A record, the re-judgment strengthens before any probe. The positive controls say those are exactly the places a restore bug would show.

### 2b. Positive controls (CPU, $0): can the gate tell a broken restore from noise?
Full tables: `posctrl/RESULTS.md`. Setup:
- **Model and data:** the pack's tiny b3g2 on CPU (torch 2.14.1), checkpoint at 30, redo 31-60, accum 4 and 8. Restore is bit-exact with no noise (shown).
- **Emulated GPU noise:** `grad += eps·rms(grad)·N(0,1)` after every micro-batch backward, with per-process entropy, at eps 0 / 0.01 (bf16-like) / 0.3 / 1 / 8.
- **Faults injected right after the checkpoint loads:** optimizer state cleared, Adam moments zeroed, data position +1, RNG streams not restored (all / global / model-only), lr schedule off by one, weights × (1 + 1e-3·N).

| fault class | first redone update (31) | 2nd redone update (32) vs healthy max there | window mean, bug ÷ healthy (eps 0.01 / 0.3 / 1) |
|---|---|---|---|
| data position, RNG streams | loud (0.88-45) | — | 138-3907 |
| model-only RNG streams | small (0.0015-0.064); `plan_*` fields differ | — | 10-236 |
| weights × (1+1e-3) | 7.3e-4-0.0145 | — | **0.9-9.8 (invisible to the mean)** |
| optimizer state cleared / moments zeroed | **exactly 0 (invisible)** | 0.0145-1.01 vs ≤ 0.009 | 1.4-778 |
| lr off by one | 0 in the loss; the `lr` field differs | 0.028-0.077 vs ≤ 0.009 | 5.8-280 |
| healthy | exactly 0 in every resume at every eps | — | — (D/N 0.60-1.24, one draw 3.13) |

What this means for the gate (shown on CPU; the scale transfer to the GPU is untested):
- **Every bug class was caught at the start of the redo.** The exact first update catches data, RNG and weights faults. The exact fields catch lr and RNG faults. Updates k+2..k+3 catch optimizer and lr faults, each with ≥ 3x margin over healthy noise at bf16-like eps.
- **The window mean added nothing.** It was blind to a 1e-3 weight corruption.
- **The old first-update limit of 0.01 is too loose for the weight fault**, which landed partly under it. Hence PREREG **Amendment 1**: Layer R gains an early-window item (≤ 0.005 on updates k+2..k+3) and an exact-field item (`lr`, `rounds`, `plan_*`), and I recommend tightening the first update to ≤ 1e-4. Layer P gains P1b (the early window on 202-203).
- **A failed ratio means "calibrate", not "broken".** The 3.13 healthy draw is the heavy tail the simulations predict.
- **Caveat on scale:** to make the toy's healthy drift as large as the GPU's 0.017-0.028, the emulated noise had to be strong enough to damage training (loss level 19-22 vs 7.9). At bf16-like eps the toy drifts 40-90x less than the GPU. So the CPU run shows **where** bugs appear and how sharply. It does not show that the GPU's 0.0282 contains no small bug. That part is the probe's job.

## 3. The determinism option, priced

Costs below use the settled 4090 record (2.24 / 3.26 / 6.01 s/update). The PC is unmeasured at accum 8.

| option | what to set | code it touches | speed vs record | covers the noise source? | comparability |
|---|---|---|---|---|---|
| D1 deterministic algorithms | `torch.use_deterministic_algorithms(True)`, `CUBLAS_WORKSPACE_CONFIG=:4096:8` (queue `# ENV` line), `cudnn.deterministic=True` (benchmark is already off by default) | `train.py` (~5 lines) + queue ENV | **untested.** Suggested +5 to +30 %: deterministic variants add kernels, and the trainer is launch-bound (~76k kernels/update, ≥ 37 % non-kernel wall, LAUNCH-BOUND-SOLVE). That would be accum 8 ≈ 3.4-4.2 s/update, ≈ 23-28 h per 24,000 updates. More if masked SDPA falls back to the math kernel | **unknown until a census.** Candidates in this code: masked SDPA backward (`writer.py:71`, the mem-efficient kernel, atomics), `gather` backward (`writer.py:144`), `index_add` (`b3g2.py:561`), embedding and row-subset index backward, cuBLAS workspace. With `warn_only=False`, an op without a deterministic implementation raises, which is itself the census | numbers-changing: fresh runs only, new name |
| D2 fp32 (drop `--bf16`) | `bf16=False` for this arm | `g8a/configs.py` call / queue | **untested.** Suggested −10 % to +40 %: TF32 on/off moved speed +0.1 % (launch-bound), and removing autocast deletes ~13,148 cast kernels/update (~17 % of launches), while fp32 matmuls are slower. Memory up (accum 8: 4.47 GiB → maybe 7-9 GiB, suggested) | **No.** Atomics remain. Per-op noise shrinks by ~2^16, so the 50-update drift would shrink by orders of magnitude (suggested from the accum-4 growth profile: ~e^7 over 40 updates). Trace A would pass, but not by being deterministic | breaks the bf16 G2f line (every arm in PASS-MARKS is bf16): new recipe |
| D3 launch config | nothing useful: single GPU, one stream, no NCCL, benchmark already off. CUDA graphs / compile would change kernels and are numbers-changing | n/a | n/a | no | n/a |
| D1+D2 | both | both | sum of both | bit-exact plausible (only if the census is complete) | new recipe |

**Pricing the census itself (only if Ben wants this branch):** one rented 4090 or 5070 Ti, 20-update `warn_only=True` census + 4 arms × 3 rounds × 40 updates timing at accum 8. About 45 min, **about $0.35-1 on Vast**. That is a **bid to the coordinator** under the $50/week cap and has **not** been requested. A PC run instead needs Ben's halt.

**The hybrid: deterministic only around restarts.**
- *Deterministic only in the redo (R deterministic, C not):* **incoherent.** C ran the nondeterministic kernels and R runs different, deterministic ones. R−C then contains a kernel-switch difference of the same order as the noise, and nothing is removed.
- *Deterministic verification segment (updates 101-150 deterministic in **both** the original segment and the redo, `CUBLAS_WORKSPACE_CONFIG` set for the whole run):* **coherent.** The switch happens at the same update in both. If the census shows full coverage, R and C must then be **bit-identical**, which is a zero-tolerance GPU certificate of restore completeness. Cost: < 1 min per run. Code: a `--det-window A:B` flag in `train.py` that toggles `use_deterministic_algorithms` at step boundaries. Fresh runs only (numbers-changing for 50 updates). It certifies only that window's restore. The step-200 probe sits outside it and keeps its noise-referenced form. **Not needed now.** It is the upgrade if Ben ever wants bit-for-bit.

## 4. The run-design option

Wall-clock figures are at accum 8 on the 4090 record (3.26 s/update); the PC is probably slower.

| design | wall-clock on the PC | a mid-run crash loses | gate | comparable with G2f-line runs on record |
|---|---|---|---|---|
| now: ckpt every 100, planned kill at 150 | +50 redone updates ≈ 2.7 min | ≤ 100 updates ≈ 5.4 min (accum 4: 3.7, accum 16: 10) | stops on a mis-set bar (cost so far: card idle since 10-15 15:43 ET, about two days) | yes (checkpoint flags are bit-neutral, shown on CPU) |
| cadence 50 | + a few s per extra 50 MB write | ≤ 50 updates ≈ 2.7 min | redo ≤ 50, so less drift, but does not fix the bar | yes |
| segmented runs (clean exit + restart at boundaries) | small overhead per boundary | ≤ one segment's tail | **no help**: drift comes from nondeterministic kernels, and every boundary is a fresh process exactly like a resume | yes |
| never resume on purpose (no planned kill; resume only after a real crash) | −2.7 min | ≤ 100 updates, at an uncontrolled point | no running trace-A stop; the post-run probe tests the resume path better (2 resumes, noise-referenced) | yes |

The expensive design choice is not cadence or segmentation. It is a **running stop on a statistic that rounding noise grows into**, because each false stop costs human latency (days), not minutes. Moving that statistic to the reading gate (Layer P) removes the trap for every future long run on this pack. It costs one ~10-min probe per run, and the README already declares that probe for reading g2fa4/g2fa8.

## 5. Recommendation: gate-fix (with the probe as the decider)

**Gate-fix (recommended).**
1. Read-only, no halt: the Mac reads `TRACE-A-g2fa8.md`, the `state.json` traceA entry and the g2fa8 `events.jsonl` lines 101-150 from the PC. Bring back: the first redone difference (update 101) and the `lr`/`rounds`/`plan_*` fields there, |ΔL| at 102-103, the max difference, and the per-update R and C. If 101 is exact, the fields are equal, 102-103 are under 0.005, and the growth profile looks like accum 4's, the re-judgment strengthens at $0. Those are exactly the places the positive controls say a restore bug shows.
2. Coordinator's call, no halt: **copy** (never move) g2fa8's `B3G2\ckpt\step-200.pt/.json` (and step-300) into `work\g2fa4\ckpt-keep-g2fa8\`. Check the sidecar says `"accum": 8`.
3. **Ben's halt go**, then `probe-resume --keep ...\ckpt-keep-g2fa8 --step 200 --upto 250 --job g2fa8` (~10 min, $0). Then `drafts/rejudge_probe.py PROBE-RESUME-g2fa8.json`, which gives INSIDE / UNRESOLVED / OUTSIDE.
4. If INSIDE, Ben decides two things: (a) adopt trace A2 (mean recorded at run time, reading gated by P1-P3); (b) **continue g2fa8 from step 300** (`arm` on his typed words + `clear g2fa8`; ccdbd06e9b tested that a clear after a recorded trace-A FAIL continues to ALL-DONE without re-evaluating trace A). The alternative is a fresh rerun under the new variant (needs the reviewed drafts installed).
- *Probe's role:* **decisive** for whether the restore is healthy at step 200, and therefore whether 0.0282 is the noise mechanism, and for the reading gate. **Not decisive** for the 101-150 vs 201-250 window question (UNRESOLVED case), for accum 4 (refused, skipped job), or for determinism cost.

**Determinism (not recommended now).** Next action, only on Ben's ask: a bid to the coordinator for the ~$0.35-1 census + timing box. Probe's role: none for pricing. Afterwards it would show the deterministic run's n = 0.

**Redesign (fold into the gate-fix for future runs).** Keep the planned kill (a cheap live test). Make the mean item soft. Optionally use cadence 50. No action now. Probe's role: it replaces the running mean stop as the resume test.

**Ben's decisions, and only his:** the halt go for the probe; adopting trace A2 / the provisional 0.05 (any change to a bar); continuing g2fa8 from step 300 vs a fresh run; whether the determinism branch gets a spend bid.

## 6. Kill list

**Made unnecessary:**
- A same-config rerun of g2fa8 "to see if it passes 0.02". The expected value is ~0.02-0.03, so the coin-flip outcome says nothing about health.
- Any further audit of the checkpoint code (settled; bit-exact on CPU at accum 4 and 8).
- A determinism retrofit or an fp32 switch of the mainline in order to pass trace A.
- Segmented-run redesigns.
- Arguing for a better constant than 0.02 (replaced by the measurement rule).
- An accum-4 probe for this verdict (and it is refused anyway).

**Deliberately left open:**
- Which CUDA kernel dominates the noise (census; only matters for determinism).
- Whether 101-150 is noisier than 201-250 (the window factor).
- Whether the accum-8 recipe matches accum 32 at update 24,000 (the gate-3 deviation; Ben/big-run's).
- The memory reading (RESULT `peak_mem_mib`).
- The probe's Windows behaviour (untested).
- The 5070 Ti speed at accum 8.

## The single next action
**Read the accum-8 trace-A record off the PC (step 1 above: read-only, no halt, $0).** Then put the halt-for-probe decision to Ben with `BRIEF-FOR-BEN.md`.

## The first result that would prove this framing wrong
**In the probe, R1 and R2 come out bit-identical (n = 0) while d > 0, or update 201 is not exact.** Fresh GPU processes would then not differ from each other, so the drift is not per-call rounding noise. Something about resuming (lost state, or a warm-vs-cold process difference) would be making the resumed run a different run, and the whole "measure the noise, set the bar from it" framing, including the settled SYSTEMATIC diagnosis, would be wrong.

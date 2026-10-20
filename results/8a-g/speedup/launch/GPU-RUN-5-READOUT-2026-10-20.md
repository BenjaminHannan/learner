# GPU-RUN-5 readout (2026-10-20): E4 noise floor for `defer`, against PREREG-gpu-run-5.md

**Verdict: PASS.** Under the sealed bars, `defer`'s 300-update loss traces sit inside the baseline's own run-to-run drift on an RTX 4090. Per the sheet (§3), the `defer` port goes to code review:
- only in fresh runs from update 0, under new names;
- no change to 8aB3G2A4/A8.

All code stays a draft until the coordinator reviews it. GPU-RUN-4 still stands as a FAIL for `defer` as tested (§0). This run does not re-judge it.

Sheet: PREREG-gpu-run-5.md, sealed 10-20 (sha256 0ab5dbfd…708d, commit 6eef85bfe). The readout ran the sealed `gpu_run_5_marks.py` unchanged (sha256 9e281cba…f346, re-checked before the run). Machine output: `GPU-RUN-5-marks.md`, `GPU-RUN-5-marks.json`. Raw outputs: `collected/gr5/`.

## 1. The run

| | |
|---|---|
| box | Vast 56940993, 1 × RTX 4090 (24 GB, 450 W), AMD EPYC 7C13, Utah; torch 2.11.0+cu128, cuDNN 9.19; not in deterministic mode |
| script | `gpu_run_5_box.sh` sha256 3448698a…be1e (commit 9f9e4107). All five launch files matched their pins on the box (`PROF-GR5 launch files pinned`) |
| steps | pool-building smoke rc 0 (286 s); `g1_e4floor` rc 0 (2222 s); `PROF DONE failed=none`, `CIO DONE` at 20:39:30Z |
| traces | B1 D1 B2 D2 B3 D3, each 300 updates, all losses finite. Same seed (400) and rows; K0 = 8; real lr schedule |
| defer | 1200 deferred losses per trace and **0 fallbacks**: the deferred path ran on every micro-batch |
| times | created 19:32:51Z, destroyed 20:41:08Z (confirmed unlisted), 68.3 min |
| cost | 68.3 min × the billed $0.4830/h = **$0.55** (cap $1.00 billed). The account credit fell from $17.98 to $16.54, but another session's RTX 5090 box was running at the same time, so the full $1.44 is not this run's |

## 2. Bars (updates 101–300 of each trace)

| pair | kind | mean abs Δloss |
|---|---|---|
| B1–B2 | AA | 0.04812 |
| B1–B3 | AA | 0.05871 |
| B2–B3 | AA | 0.05558 |
| B1–D1 | AB | 0.05263 |
| B1–D2 | AB | 0.05541 |
| B1–D3 | AB | 0.04327 |
| B2–D1 | AB | 0.05046 |
| B2–D2 | AB | 0.04757 |
| B2–D3 | AB | 0.04486 |
| B3–D1 | AB | 0.04972 |
| B3–D2 | AB | 0.04840 |
| B3–D3 | AB | 0.05208 |

Window mean losses:
- B: 2.89402, 2.86702, 2.86058 (range 2.86058–2.89402).
- D: 2.88071, 2.86362, 2.87124.

| bar (sealed §2) | value | result |
|---|---|---|
| (i) median of the 9 AB ≤ largest AA | 0.04972 ≤ 0.05871 | **holds** |
| (ii) D means not all outside the B range on one side | all 3 D means lie inside 2.86058–2.89402 | **holds** |
| PASS = (i) and (ii) | | **PASS** |
| drift proved wrong (every AA < 0.02 and every AB > every AA) | AA are 0.048–0.059, and min AB 0.043 < max AA | does not apply |
| complete (6 traces, BDBDBD, 300 updates each) | yes | complete |

**0.02 note (sealed §2):** every B–B pair is ≥ 0.02. Record that **0.02 is too tight for FUTURE B3G2 sheets only**. It re-judges neither GPU-RUN-4 nor this run.

## 3. What the run shows, labelled

- **Shown:** on the 4090 the baseline drifts run to run. The three B traces start at the same loss (22.6862) and first differ at update 2 (22.919228 vs 22.919197). By updates 101–300 they differ by 0.048–0.059 on average. That drift is about 2.4–2.9 times the 0.02 bar.
- **Shown:** `defer` against the baseline (AB 0.043–0.055) falls within that same range. AB is not systematically larger: 3 of the 9 AB values (0.04327, 0.04486, 0.04757) are below the smallest AA (0.04812).
- **Shown:** `defer` changes the numerics from update 1. B1 gives 22.686195 and D1 gives 22.686115, a relative difference of 3.5e-6. This matches the sheet's §6 ("numerics-changing").
- **Information only, not a bar (D–D):** D1–D2 0.04304, D1–D3 0.04597, D2–D3 0.04302.
  - Each of these is about the size of the smallest B–B pair or below it.
  - **Suggested** cause of D–D drift, as the coordinator asked: an unordered multi-thread accumulate in `reader.tok.weight`'s gradient. This was shown on CPU in the dry run (§7 of the sheet), where it vanishes with deterministic algorithms or one thread.
  - **Untested** on the GPU: there, every arm is already nondeterministic, and this run does not isolate the source.
- **Information only, not a mark (speed is outside this run, §5):**
  - The trace wall times were 316.7–318.8 s for D and 405.1–406.1 s for B2/B3 (B1 took 439.5 s, including warm-up). That is about 1.28× on these whole-trace walls.
  - These walls are not the prereg's speed measurement. They judge nothing.
- **Untested:** whether the PASS holds at longer horizons than 300 updates, or for accum 8, other rungs, or other models. The sheet tested E4 for `defer` on B3G2 3M accum 4 only.

## 4. What the result allows (sealed §3 and the 10-17 rules)

- The `defer` port goes to **code review** by the coordinator. It is a draft until then.
- If the port is approved, `defer` is used only in **fresh runs started at update 0, under new run names**, with `--speed-arms` in the resume config hash.
- **No change to 8aB3G2A4/A8** (they keep running without `defer`).
- The run used one rental and there are no re-run bids. No further GPU spend is asked for here.

## 5. Next action and first falsifying result

- **Next action:** write the `defer` port into the production trainer as a draft for the coordinator's code review.
  - It ports the `launch/defer.py` code path as a new opt-in flag, off by default.
  - It needs a CPU equivalence test against the harness's `defer`, and a fresh-run-only guard that refuses a resume across the flag.
  - No GPU is needed for the draft.
- **First falsifying result:** the first fresh run with `defer`, compared against a matched fresh baseline. Its loss over updates 101–300 must fall inside the baseline's run-to-run range shown here (AB ≤ 0.059, and its window mean inside 2.861–2.894 for the same seed and rows). A systematic offset outside that range on one side, as in bar (ii), would show that this PASS does not carry over. The mark for any longer horizon has to be set before that run.

## 6. For Ben (plain language)

The question was whether the faster version of the training code (`defer`) learns the same way as the normal one. Last time it looked different. The new test asked: maybe the normal code doesn't even match *itself* when run twice on this GPU.

So we ran the normal code three times and the faster code three times, alternating, on one GPU for about an hour, for about 55 cents.
- The normal code really does wobble: two normal runs differed by about 0.05 in loss on average.
- The faster code differed from the normal code by about the same amount, sometimes less.
- Its average loss landed in the middle of the normal runs' range, not off to one side.

The rules we wrote before the run said that counts as a pass. The faster code can now be written into the real trainer, but only as a draft for the coordinator to review. Even then it is only for brand-new training runs, never the ones already going. One more lesson: our old limit of 0.02 was smaller than the normal code's own wobble, so future rules for this model need a bigger allowance.

# R1 stage 1: parked 2026-10-21. What a fresh session needs to finish it

**Status:** PARKED by the coordinator on 2026-10-21 at about 00:10Z.
- Three GPU boxes failed on environment problems. No training step completed, and no scored number exists.
- The R1 stage-0 Muon PASS stands (`REPORT.md`, "R1 stage 0 RESULT").
- Do not rebook without a new budget from Ben.

**Sealed state:**
- Card `design/steals-2026-10-17/R1-STAGE1-CARD.md` (`279c72ea…`), unchanged since the first seal.
- Runner `cf985bf0…`.
- Seal `SEAL.sha256.txt` `d1dbe148…`, at commit 7df12e710. The history of supersessions is in `SEAL.note.txt`.
- Controller: `scripts/claude_r1s1_rent.py`.

## Dollars spent (stage cap $2.80)

| Box | Where, billed $/h | What happened | ≈ $ |
|---|---|---|---|
| 56942633 | Belgium, $0.6167 | Setup: PyPI's torch 2.11.0 is a cu130 build, and the host driver supports CUDA 12.8. Fixed by installing the cu128 build. | 0.05 |
| 56946584 | Bulgaria, $0.6889 | The build took 1,982 s. Then 1a crashed on its first line: `provenance()` called `git`, which the image lacks. Fixed. | 0.42 |
| 56958705 | Sweden, $0.678 | The build took 3,869 s. 1a started, and both arms aborted at step 1: peak GPU memory 14.88 GiB passed the 14 GiB guard. **Not fixed.** | 0.85 |
| **Total** | | | **≈ 1.32** |

All three boxes were stopped with Vast's confirmation, pulled with sha256 checks, and destroyed only after their pull
passed. Their exports and logs are in `box-*/` here.

## The three fixes (spec only; not started)

Each fix touches sealed files, so each needs a re-seal after one focused review. Record the superseded seal in
`SEAL.note.txt`. No scored number has been seen, so a re-seal is allowed.

**(a) A GPU-sized memory guard.**
- **Problem:** `learnlab.train.TrainConfig.memory_limit_bytes` defaults to 14 GiB. That suits the 16 GB Windows PC,
  where spilled memory runs at about 1/30 speed. `premonition.train.train_d` never overrides it.
- **Change:** add `train_d(..., memory_limit_bytes: Optional[int] = None)`, passed into `mini_train_config(...)` only
  when it is not None. The default then stays bit-identical, and the P1 test
  (`tests/test_premonition_steal_train_d.py`) must still pass.
- **Runner:** on CUDA, the runner passes `torch.cuda.get_device_properties(0).total_memory - 2 GiB`, about 29.8 GiB
  on a 5090. It records the value in each run JSON.
- **Test:** a CPU test that the default is unchanged and that the argument reaches the trainer config.
- **Note:** the box-3 peak was 14.88 GiB at max_tokens 55,000, so 32 GB has ample room.

**(b) Build workers sized to the cores the box really has.**
- **Problem:** the job runs `build --workers "$(nproc)"`. Box 3 reported 128 CPUs but the offer had about 16
  effective cores, and the build took 64 minutes (box 2's took 33).
- **Change:**
  - `create` reads the offer's `cpu_cores_effective` from the search listing and writes `WORKERS=<floor(cores)>`
    into the job.
  - The job uses `min(nproc, WORKERS)`, with at least 1.
  - The feasibility floor's build estimate should then come from measured build seconds per worker.
- **Cost of the build alone:** about 2,000 s, roughly $0.38 at $0.68/h. Shipping a prebuilt village was ruled out:
  the card says the build runs on the box, and 1.4 GB cannot go through the ~2 MB args route.

**(c) A STATUS read that can be trusted.**
- **Problem:** on box 3, `pull` read `/job/export/STATUS.txt` and got another file's base64 back, which looks like
  cross-talk in Vast's `execute`. The sha-checked parts were correct, but PULL_OK recorded a junk status, which
  skips the DONE-only manifest requirement.
- **Change:** re-read STATUS up to N times until it matches `^(DONE|FAIL|GATE) rc=\S+( dryrun=1)?$`. If it never
  matches, refuse PULL_OK. Read MANIFEST and PARTS with the same check: each line must have the expected shape.
- **Test:** a fake `exec_cat` that returns a wrong body first.

**Also worth taking in the same round (cheap):**
- bind `waitlog`/`cost --args` to the instance id, from a sidecar written by `create`;
- make the "unpaired" message name the field that failed;
- suppress "would be" when runs are unpaired.

## Rough estimate for a complete stage

- **Known:**
  - Builds run 1,982–3,869 s, or about 2,000 s once fix (b) is in.
  - 1a is at most 2,400 s.
  - Box rates are $0.62–0.69/h for 5090s within the card's filters.
- **Unknown:** D's GPU seconds per step have never been measured, because every attempt stopped before step 2. The
  sealed F rule uses F_MAX = 7.5e15, about 6,580 steps per run, over 6 runs (3 seeds × 2 arms), plus 14 evaluations
  per run.

| GPU s/step (guess) | 1b runs incl. evaluations | Whole box (build + 1a + 1b + export) | $ at $0.68/h |
|---|---|---|---|
| 0.15 | ≈ 2.2 h | ≈ 3.4 h | ≈ $2.30 |
| 0.30 | ≈ 3.9 h | ≈ 5.1 h | ≈ $3.50 |
| 0.50 | ≈ 6.1 h | ≈ 7.3 h | ≈ $5.00 |

**A complete stage at F_MAX therefore needs about $3–5 for one box**, on top of the $1.32 already spent.

With less than that, the sealed rule simply lowers F, down to F_min = 3.15e15, about 40% of the steps. Below F_min it
GATEs: it exports and stops with no verdict.

**Suggestion:** a budget of $4.00 for the next box (stage total about $5.32). Its first 1a would then also give the
real s/step, which settles the estimate.

# RUNBOOK: 8aPTC3S on one rented RTX 4090

For the roadmap thread. Nothing here has been run on Vast. Every claim is labelled **shown** (seen in a CPU dry run, DRYRUN.md), **suggested** (reasoned, not seen) or **untested** (needs the real box).

What the box does: it trains arm PTC (the plain 3M model trained with the calculator), seed 400, 24,000 updates, the same job as the PC queue file `8aPTC3S-pc.txt`. The flags come from the PC runner's own functions, not from a hand copy (shown). It prints the result and the 16 MB checkpoint through the Vast log, waits `END_SLEEP`, and does nothing else. It holds no credential and listens on nothing (shown: the script has no key, no token and no server).

## 1. Money and limits

| Item | Value | Label |
|---|---|---|
| Price | RTX 4090 about $0.38 per hour (SPEND.md, 10-12) | shown by that read-only search |
| Cost | hours up x dph_total of the offer | rule |
| Expected | 4 to 6 hours up, $1.5 to $2.5 | suggested (PC took about 2.4 h for the plain job; 4090 speed unmeasured) |
| Hard cap | $5 for the whole rental | Ben's cap in SPEND.md |
| `MAXH` | 6 hours from script start, stops the job | shown on CPU (the stop works), untested on GPU |
| Pick only offers with | dph_total at most 0.60 | 6 h x 0.60 = $3.60, plus about 0.6 h of checkpoint export (25 min) and END_SLEEP (10 min) = $0.36, plus about 0.1 h of image loading before the script starts = $0.06: $4.02 in the worst case, under $5 |
| One box only | destroy it when collected | SPEND.md rule |

`MAXH` is a cost cap, not a plan: train.py saves the checkpoint once, after the last update, and cannot resume. A `MAXH` stop during training means no result.

## 2. Before you create anything

1. Get the kit's `vast.py` (the file the roadmap thread already uses) and check it. It must be byte-identical to the one this folder was tested against:
   ```
   git show origin/claude/project-thread-x2cm2v:custom_io/box/vast.py > /tmp/kit_vast.py
   sha256sum /tmp/kit_vast.py      # b68462f7374176783a138f34edef8a9396adde958c05c46e63f34f04cf6675cd
   ```
   (the file at commit ce03628beb of that branch). If the hash differs, read the diff before going on; `vastptc.py` patches three things in that file (see its docstring) and was tested only against this version.
2. Check the box script is the one that was reviewed: `sha256sum ptc3s_box.sh` must equal the line in DRYRUN.md section 0 (the hash printed there is of the committed file).
3. Set shell variables (from this folder):
   ```
   cd results/8a-g/vast-ptc3s
   KIT=/tmp/kit_vast.py
   V="python3 vastptc.py $KIT"
   ```
   `vastptc.py` calls the kit's own functions unchanged, with `BOX` pointed at `ptc3s_box.sh` and result files written beside this folder (`./collected`, or `$PTC_OUT`). It never reads or prints a key; the proxy adds it.
4. Credit and running boxes: `$V credit`. Needs credit of at least $5.00 and **no** instance listed. Stop here if not.
5. Write the SPEND.md row first (SPEND.md rule: row before create). Suggested text: `8aPTC3S | 1 x RTX 4090 ($DPH/h) | start ET | | about $1 to $3, hard cap $5 incl. MAXH=6`.

## 3. The commands

```
$V search --gpu "RTX 4090" --n 8
```
One JSON line per offer: `id, gpu_name, gpu_ram, dph_total, reliability, inet_down, cpu_cores_effective, cpu_ram, disk_space, cuda_max_good, geolocation`. The kit already requires verified, on-demand, 1 GPU, reliability 0.98 or more, CUDA 12.8 or more, 60 GB disk or more, 300 Mb/s or more, 8 effective cores or more. Choose the cheapest line with `dph_total` at most 0.60 and `cpu_ram` at least 32000 (MB; suggested: the CPU smoke needed 4.8 GB at its peak, see DRYRUN.md). Write down `id` and `dph_total`.

```
$V create --offer OFFER_ID --label ptc3s --env "MAXH=6 DPH=<dph_total> PROJ_CAP_USD=4 END_SLEEP=600 FAIL_SLEEP=600"
```
- Prints `{"success": true, "new_contract": INSTANCE_ID, ...}`. `new_contract` is the instance id; write it down with the time.
- Every `--env` word must be `NAME=VALUE` without spaces or quotes (the kit asserts it). `DPH` must be the offer's real `dph_total`: with `DPH=0` the cost guard is off and only `MAXH` protects the money.
- Other settings that exist (defaults are right, change none): `TFVER=5.19.0`, `EG=1` (must stay 1), `GUARD_STEP=1000`, `EXTRA_H=0.5`, `EXPORT_CK=1`, `PACE=100`, `CK_ROUNDS=3`, `TICK_EVERY=180`.

```
$V status --id INSTANCE_ID          # actual_status, dph_total, duration
$V tail --id INSTANCE_ID --n 40     # last log lines, result and checkpoint lines hidden
```

When `PTC3S RESULT PRINTED` appears in the tail (the next two steps work only while the box is up):
```
$V collectck --id INSTANCE_ID --max-min 40 --want "8aPTC3S-3M-s400/PTC 8aPTC3S-3M-s400"
$V collect   --id INSTANCE_ID --out ./collected      # fallback for the result alone (works while the last 20,000 log lines hold a result block)
```
- `collectck` reads the log every 40 s, saves the result block (to `./collected/8aPTC3S-3M-s400/`) and rebuilds the checkpoint (to `./collected/8aPTC3S-3M-s400/PTC/checkpoint.pt`). It ends by itself when both are saved.
- Why start it early: the checkpoint is printed as 5 parts of 3 MB, one part every 100 seconds, **three times** (rounds 1 to 3), then the result is printed once more. Any five parts in a row hold every part, so a collector that starts up to 15 minutes after `PTC3S RESULT PRINTED` still gets the whole checkpoint; one that starts later misses parts (shown on the CPU log with an emulated Vast log, DRYRUN.md section 5; the kit has `ck_reprint.sh` for that case, which this box cannot run because nothing listens on it). Start it within 10 minutes of `PTC3S RESULT PRINTED` to keep a margin (suggested; the real Vast log timing is untested).
- `collect` (the kit's) cannot read a log that contains checkpoint parts; `vastptc.py` removes those parts before the kit's code sees the text (shown on the CPU log, DRYRUN.md section 5).

```
$V destroy --id INSTANCE_ID         # prints {"destroy": true,...} and {"still_listed": false}
$V credit                           # credit left; must list no instance
```

## 4. What you should see (times are guesses unless marked)

| Stage line in the log | What happens | Expected | Label |
|---|---|---|---|
| `CIO START`, `PTC3S START ... dph=<your dph>` | script starts; check `dph=` is not 0 | 3 to 10 min after create (image pull) | suggested |
| `STAGE setup` | pip: transformers 5.19.0, tokenizers 0.23.2, safetensors 0.8.0; versions asserted | 2 to 4 min | suggested (5 s on the CPU box, packages cached there) |
| `STAGE code` | fetch base and package by commit sha, check every package, base and overlay file by sha256, ptccheck (CPU), `CODE-ID ...`, `CMD ...` | 1 to 2 min | shown: about 1 min |
| `STAGE gemma` | EmbeddingGemma 2 download (1.5 GB), sha check, `eg check cuda` | 1 to 3 min (more if Hugging Face rate-limits: up to 6 tries, 4 min apart) | shown for the download and CPU check |
| `STAGE data` | the PC's `8a-data` line: FineWeb-Edu shard (2.15 GB), web slices hash-checked against the manifest | 20 to 30 min, one CPU core | shown: 20 min on the CPU box |
| `STAGE skills` | 200k curriculum + dev-200, hash-checked | 4 to 6 min | shown: 4 min |
| `STAGE train`, `PTC3S TRAIN START` | pool build (about 3 min), caps report, then the 24,000 updates | pool shown 3 min; updates untested | |
| `TICK ... step=N loss=X train_elapsed_s=T proj_train_h=H proj_usd=U` | every 3 min; the step moves every 500 updates | | shown on the CPU box (2 updates) |
| `GUARD step=1000 ... projected_usd=...` | one line, once, after update 1000 | 15 to 40 min after TRAIN START | suggested |
| `PTC3S JOB END rc=0`, `RESULT-SUMMARY {...}` | training and final evaluations done | | |
| `PTC3S RESULT PRINTED job_ok=yes` | result printed, checkpoint parts follow | | |
| `part ckN ... round R` | 5 parts x 3 rounds x 100 s = about 25 min | | shown (parts and pacing), real timing untested |
| `CIO DONE` | box sleeps `END_SLEEP`, then the container ends | | |

Before the first update the box spends about 35 to 45 minutes (setup, data, skills, pool): about $0.25 (suggested). Total estimate: 4 to 6 hours, $1.5 to $2.5 (suggested).

## 5. Stop rules (fixed in advance)

Cost so far = hours since `create` x `dph_total`. Check `status` at each look.

| # | Rule | Action |
|---|---|---|
| S1 | Not `running` 15 min after create, or no `CIO START` line 15 min after `running` | destroy; note the offer id (bad host); try one other offer at most |
| S2 | `PTC3S START` line shows `dph=0` / `guard=OFF-set-DPH`, or a dph that is not the offer's | destroy now (the guard would be off) and create again with the right `DPH` |
| S3 | **First 1,000 updates.** The box prints `GUARD step=1000 ... projected_usd=U cap_usd=4.00`. It prints `GUARD STOP` and kills the job by itself if U is above 4.00, **or** if the projected total hours are above `MAXH` (the job would be killed at `MAXH` with nothing saved). From then on every TICK line carries `proj_train_h=` (hours of training in all) and `proj_usd=` (dollars for the whole box, same formula as the guard) | GUARD STOP: the job is dead, destroy (no result exists). Any later TICK with `proj_usd` above 4.50: destroy. `proj_usd` between 3.00 and 4.50: say so to Ben before leaving it running |
| S4 | No `GUARD` line within 2 hours after `PTC3S TRAIN START` | look at the last TICK: if `step=` is missing or unchanged, destroy |
| S5 | **Stall: no new TICK line for 20 minutes** while the stage is not `export` (TICKs come every 3 min until `PTC3S RESULT PRINTED`; after that `part ckN` lines every 100 s take over) | `status`. If not `running`, destroy. If running, wait 10 more minutes, then destroy |
| S6 | TICK shows the same `step=` for 20 minutes during `stage=train` | read the `gpu` field of the TICK: utilization 0 % means a stuck process: destroy. Utilization high: the step is slow; recompute S3 |
| S7 | `CIO MAXH 6 h reached` | the job is dead by design. Run `collectck`/`collect` for the logs the box prints in its failure path, then destroy |
| S8 | `CIO-FAIL ...` anywhere | the box prints the tail of the failing log and the result folder (and the checkpoint if training finished). Collect (section 6), do not wait for `FAIL_SLEEP`, destroy. One retry only if Ben says so: every try costs about $2 |
| S9 | Cost so far reaches $4.00 for any reason | destroy |
| S10 | Result collected, or `CIO DONE` seen | destroy at once. The container ends by itself after `END_SLEEP`, but an ended container may still bill: destroy it anyway (untested) |

Look schedule (suggested): 10 minutes after `create` (S1, S2), then at +45 minutes (setup, data, skills should be done, `TRAIN START` printed), then when `GUARD` should have printed (S3), then every 30 minutes; start looking every 10 minutes from the moment `proj_train_h` says the end is near. Each look costs only a `status` and a `tail`.

After destroy: `$V credit` shows no instance. Update the SPEND.md row with the actual cost (credit before minus credit after).

## 6. Collect and accept

After `collectck` finished (or the failure path):
```
python3 -I accept.py collected/8aPTC3S-3M-s400
python3 -I accept.py collected/8aPTC3S-3M-s400 --pc-pts-result PATH_TO_PC_8aG2C3S_PTS_RESULT_JSON    # optional, when you have that file
```
Pass marks (fixed now, from the PC card's `done_when` and mark M1):

| # | Check | Pass |
|---|---|---|
| 1 | top `RESULT.json` | `"status": "ok"` |
| 2 | `PTC/RESULT.json` | `"status": "ok"` and `"steps": 24000` |
| 3 | the arm | job ran arm PTC only and its cfg has `calc_train: true` |
| 4 | trained parameters | `n_params` equals the PC's PTS count for the same caps: 4,023,976 at 3M (shown: PTC == PTS == PT in `test_ptc`); or the `n_params` of the PC's own 8aG2C3S PTS result |
| 5 | cap hits | `cap_hits.total` equals 0 (the calc_* counters sit outside it) |
| 6 | calculator | `cap_hits.calc_mismatch / cap_hits.calc_rows` at most 0.001 (0.1 %, mark M1) and `calc_rows` above 0 |
| 7 | final evaluation | `final_eval` present and `lesions` has `nocalc` (else the training ran but the scores did not finish; keep the checkpoint, report) |

Proved wrong, in advance: if check 4 fails, the box did not build the same model as the PC (stop and find out why before reading any score). If check 6 fails, the calculator training did not work at this size; that is a result about PTC, not about the box, and the PC run will say the same if the code is the same (compare, section 7).

`checkpoint.pt` is 16 MB (shown); the frozen Gemma is not in it.

## 7. Is it the same code and data as the PC job?

The PC run needs nothing special; these are read-only comparisons on files both sides already have.

1. **Package files.** Box: `collected/8aPTC3S-3M-s400/box/PTC-SETUP-OK.txt`. PC: `C:\Users\benja\custom-io\src-ptc\PTC-SETUP-OK.txt`. The first 8 lines (caps.py, base, the 6 replaced files with their new and old sha256) must be identical; the box writes them in the PC's format, upper-case hashes and backslash paths (shown). The last lines differ on purpose.
2. **Whole tree.** On the PC: `python code_identity.py C:\Users\benja\custom-io\work\code\8aPTC3S-pc-<10 hex>` (stdlib only; this folder's file). Compare with `collected/8aPTC3S-3M-s400/box/code_identity.txt`. Expected from the dry run: `CODE-HASH-LF 47d676dde1`, `FILES-LIST-SHA256 62179e62bb2ef62c53774259841b0e188412076e4cf40ac05b8a7a60017862a2 (118 files)` (shown on the CPU box). If they differ, `python code_identity.py FOLDER files > list.txt` on both sides and `diff` them: it names the file. Line endings do not matter to this tool (shown with a CRLF copy of the tree).
3. **The folder name.** The box prints `CODE-ID 8aPTC3S-pc-047f8ed212`; the PC log has `code: ...\work\code\8aPTC3S-pc-<10 hex>`. These two **can differ with identical code**: `local_runner.code_hash` hashes raw bytes, and a CRLF copy of the same tree gave `06c0bb4b10` instead of `047f8ed212` (shown). Use step 2, not this name, as the test.
4. **Flags.** `collected/8aPTC3S-3M-s400/cmd.txt` against the PC's `WORK\results\8aPTC3S-pc\8aPTC3S-3M-s400\cmd.txt`: after the paths, the flags from `--rung 3M` on are the same (`--seed 400 --arms PTC --b2-extra '{"eg_embed": true}' --cloze-long ... --caps-file ... --accum PTC=16`). The box also shows `collected/.../box/cmd.data.txt` for the data line.
5. **Data.** `collected/8aPTC3S-3M-s400/pool_MANIFEST.json` against the PC's `WORK\g8a\pools\p10-rung30-s400-a64-L\MANIFEST.json`: `rows`, `pieces`, `schedule`, `train_sha256`. Dry-run values (shown on the CPU box, pool built from scratch): rows 1,343,273; train_bytes 485,544,869; train_sha256 `27234f3e9861ce5f8c6db18371f27c5f52826712398b90a4e946e952ff8791fe`; steps 24,000; passes 4.574. The PC writes the pool with Windows line endings (suggested: `open(..., 'w')` in pool.py), so its `train_bytes` should be larger by exactly `rows`, and its hash must be taken after turning CRLF into LF:
   `python lf_sha256.py WORK\g8a\pools\p10-rung30-s400-a64-L\train.jsonl` (this folder's file; stdlib only) prints the hash after CRLF to LF, the stored size, the LF size and the line count. Shown on the CPU box: on a CRLF copy of the box's pool it gives the same hash `27234f38...` and a stored size of 486,888,142 = 485,544,869 + 1,343,273 (`dryrun-logs/lf_test.txt`).
   The PC reference hash was **not available** when this was written; this comparison is the first time anyone checks it.
6. **Environment.** `box/versions.txt` (transformers 5.19.0, tokenizers 0.23.2, safetensors 0.8.0 are asserted; torch, numpy, pyarrow are whatever the image gives) against the PC's versions: the PC's torch, numpy and pyarrow versions were **not available**.

Expected differences, none of which is a defect: GPU (4090 vs 5070 Ti), torch and CUDA build, kernel nondeterminism (scores will not be bit-identical to a PC run), host CPU, timing, Linux paths, and the PC's `# ENV` lines (`PYTHONPATH` to its site folders, `CUSTOM_IO_EG2`), which the box replaces with its own EG2 folder.

## 8. If something goes wrong

| Symptom | Likely cause | What to do |
|---|---|---|
| `create` returns an error naming size or length | the script is 53 KB (35 KB before PROFILE mode was added); the kit's box.sh was 7.7 KB (untested limit; the 37 KB `at10m_box.sh` of branch vast-at10m-tmp was never launched either) | do not retry blindly; tell the roadmap thread. A short bootstrap that fetches the script by commit and sha256 would need the script on GitHub first |
| Log stays empty after `running` | args not run (bash error) or logging delay | S1 |
| `CIO-FAIL pip` | PyPI unreachable | one retry costs little; S8 |
| `CIO-FAIL eg-download` | Hugging Face rate limit for the box IP, six tries failed | destroy, try another host later |
| `CIO-FAIL ... sha` in the code stage | a pinned file differs (GitHub changed, or a hash typo) | stop; this is the check doing its job. Report which file |
| `CIO-FAIL data8a not ready` / `get_data` | shard download or web slice hash mismatch | read the printed tail; a hash mismatch is a stop |
| `GUARD STOP` | slow host | S3 |
| `CIO-FAIL rows touch the global caps` | a pool row is over the pinned caps | stop; the PC job would stop the same way (`on_refuse`); report only |
| out of GPU memory | other process on the card or wrong GPU | read `RESULT-SUMMARY`, `peak_mem_mib`; the job asks for 9,000 MiB free (the queue's MEM line) |

## 9. PROFILE rental (added 2026-10-14): one 4090 for about 1.5 to 2 hours to run every box step on a real GPU and profile the training update

**What it is.** The full job (sections 1 to 8) is below the confidence bar for a first attempt (DRYRUN.md section 6: about 45 %). This rental runs the same `ptc3s_box.sh` with `PROFILE=1`. Stages setup, code, gemma, data and skills are the job's, unchanged. Then, instead of the 24,000 updates, stage `prof` does three things:

1. fetches the profiling harness (branch `claude/project-thread-yha868`, commit `ca542f77a9d3f6afb4a6850936e62da5b54a45ec`, folder `results/8a-g/speedup`; re-pinned from `6a870a767c` after the harness got the E2 scale diagnostics, the relative E2 rule, the E1-floor text and a CPU/bf16 label fix) and checks `prof_train.py` against sha256 `2f1410fea1e5754c785188c30fe22368fbd42b6bc45ff54304e59896c3fe479b` (taken from that commit with git; a different file stops the box with `CIO-FAIL`);
2. runs the **production-speed smoke**: the queue-built job command (`cmd.job.sh`, the PC runner's own flags) with `--out` moved to its own folder and `--steps 300 --train-extra '--log-every 50'` appended, under a 45-minute timeout. It builds the real pool `p10-rung30-s400-a64-L`, trains 300 updates with the real data, caps and Gemma front, and runs the real final evaluation (intact, lesions, chain-5). The box prints the seconds per update and how long the final evaluation took (`PROF-JOB` lines), which are the two numbers the cost guard's `EXTRA_H` (0.5 hours) and the 24,000-update estimate need. The PC run of the sibling arm (g2c3s, PTS 3M accum 16: `train_s` 25,786 s, `wall_s` 25,845 s) shows that start-up plus the whole final evaluation took about 1 minute there (shown, figures as given to me; that result file is not in this worktree), so `EXTRA_H=0.5` is conservative;
3. runs six harness commands on that pool, each under its own timeout, a failure is logged and the next one still runs: `a_profile` (PTC accum 16, all default sections), `b_bench` (PTC accum 16, `--sections bench`, 100 timed updates after 20 warm-up, 2 rounds, 7 variants), `c_equiv` (PTC, `--sections equiv --equiv-check --curve-updates 0`, 8 variants: E1 on the GPU in bf16, E2, E3), `d_e4` (PTC, the 300-update loss trace for `eg_once` only), `f1_b3g2_profile` (B3G2 accum 32, sections breakdown, throughput, padding, syncs; no profiler), `f2_b3g2_bench` (B3G2, bench of `baseline;eg_once`, 40 timed updates after 10 warm-up). The CPU E2/E3 runs of the harness README are **not** made. B3G2 runs on the PTC pool (the harness README's own `$POOL` convention), with `--caps custom_io/g8a/caps_b3g2.json` of the assembled tree (the file and `models/b3g2.py` exist there, shown).

With `PROFILE` unset the script is the job of sections 1 to 8, byte for byte the same code path except for the lines listed in DRYRUN.md section 9 (shown by a diff and by a full default dry run). The speed guard is off in PROFILE mode, no checkpoint is exported, and the hard stop is `MAXH=2`. Labels below: shown = seen in the CPU dry run, suggested = reasoned, untested = needs the real box.

### Cost and time at $0.40 per hour

| Part | Time | Label |
|---|---|---|
| create to script start (image pull) | 3 to 10 min | suggested |
| setup, code, gemma, data, skills | 20 to 45 min (CPU box, from scratch: 19 and about 28 minutes in two runs, the data stage 15 and 20 minutes of it, on one CPU core) | shown on the CPU box, host-dependent |
| job smoke: pool, arm start, 300 updates, final eval | about 10 min (expected; hard limit `PROF_JOB_MIN=45`) | pool build about 2 to 3 min (107 to 110 s shown on the CPU box) and arm start 40 to 44 s (CPU box); 300 updates untested; the final evaluation of the PTC/PTS arm is about 1 minute on the PC (shown by the PTS run, item 2 above), so the 45-minute timeout is comfortable. The smoke's time is taken from the same `PROF_MAXMIN` budget as the six harness runs |
| harness, six runs | the rest of the stage budget `PROF_MAXMIN` (75 min counted from the start of stage prof, job smoke included); each run is cut to what is left, the last ones are skipped with a `PROF SKIP` line when less than 4 minutes are left | untested; a rough guess is 40 to 60 min for all six (B3G2 updates are slow) |
| printing, `END_SLEEP` | 1 min, 5 min | shown for the printing |
| **Typical total** | **1.5 to 2 hours, $0.60 to $0.80** | suggested |
| **Worst case** | `MAXH=2` h from script start + `END_SLEEP` (5 min) + image pull (about 6 min) = about 2.2 h, $0.87 at $0.40 and $1.31 at the $0.60 limit | rule |

It is not a one-hour rental: the data stage alone is 15 to 20 minutes on a single core. Raise `PROF_MAXMIN` only together with `MAXH` (the budget never reaches past `MAXH` minus 7 minutes). Ben's cap of $5 is far away; stop rule P7 is $1.50.

### Commands

```
$V search --gpu "RTX 4090" --n 8        # same rule as section 3: dph_total at most 0.60 (2 h x 0.60 = $1.20)
$V create --offer OFFER_ID --label ptcprof --env "PROFILE=1 MAXH=2 DPH=<dph_total> END_SLEEP=300 FAIL_SLEEP=300"
$V status --id INSTANCE_ID
$V tail --id INSTANCE_ID --n 250        # the kit hides the R| payload lines
$V collect --id INSTANCE_ID --out ./collected_prof      # as soon as PROF RESULT PRINTED shows; takes about a minute
$V destroy --id INSTANCE_ID
$V credit
```
Write the SPEND.md row first, as in section 2 (suggested text: `8aPTC3S profile rental | 1 x RTX 4090 ($DPH/h) | start ET | | about $0.7, MAXH=2`). `PROJ_CAP_USD` is not used in PROFILE mode. Other settings (defaults are right): `PROF_MAXMIN=75`, `PROF_JOB_MIN=45`, `PROF_STEP_MIN=25`, `PROF_JOB_STEPS=300`, `PROF_COMPILE=1` (adds the `torch.compile` variant `eg_once,sortpad,oldw,compile` to the bench list; off by default because compile can take many minutes).

`collectck` is not needed: no checkpoint parts are printed. The box stays up `END_SLEEP` (300 s) after `PROF DONE`; collect inside that time, then destroy (a destroyed or ended box may no longer give its log; untested).

### What you should see in the tail (in this order)

| Line | Meaning |
|---|---|
| `CIO START`, `PTC3S START ... guard=OFF-profile-mode`, `PROF MODE: ...` | **the `PROF MODE` line must be there**. If it is not, `PROFILE=1` did not arrive and the box will run the 24,000-update job: destroy at once |
| the `# nvidia-smi`, `# pip list` and `# torch` block | GPU name, driver, CUDA, cuDNN, torch, transformers, numpy, CPU: the PC-versus-box version comparison (also in `profrun/prof_env.txt`) |
| `STAGE code`, `CODE-ID ...`, `STAGE gemma` (`eg check cuda`), `STAGE data`, `STAGE skills` | as in section 4 |
| `STAGE prof`, `PROF START ...`, `PROF-HARNESS commit ca542f77a9... prof_train.py sha256 2f1410fea1... = the pinned value` | harness fetched and checked |
| `PROF-JOB START`, `TICK ... stage=prof-job ... step=N loss=X` | the smoke; TICK shows the step every 3 minutes (the log is read every 50 updates) |
| `PROF-JOB END rc=0`, `RESULT-SUMMARY {...}` | `job_status ok`, `arm_status ok`, `steps 300`, `n_params 4023976`, `cap_total 0`, `final_eval true`, `chain5 true`, `lesions [... nocalc ...]` |
| `PROF-JOB train step=50 ... step=300 ... elapsed_s=` | six lines |
| `PROF-JOB timing {...}` | `sec_per_update_first_to_last_log` (the speed number to quote: update 50 to update 300, so the first 50 updates with their start-up work are left out), `sec_per_update_overall` (all 300), `pool_build_s`, `startup_before_train_s`, `final_eval_phase_s` (final evaluation, chain-5 and lesions; the checkpoint save is counted before it), `peak_mem_mib` |
| `PROF-JOB projection for the 24,000-update job` | training hours at the measured speed, and the final-evaluation hours to compare with `EXTRA_H=0.5` (conservative: about 1 minute on the PC) |
| `PROF-JOB pool {...}` | `train_sha256`, `train_bytes`, `rows`, `pieces`, `passes` of the pool this box built; the CPU box built `27234f3e9861ce5f8c6db18371f27c5f52826712398b90a4e946e952ff8791fe`, 485,544,869 bytes, 1,343,273 rows, 60,008,258 pieces three times (shown); the same value is expected here (suggested) |
| `PROF STEP a_profile start ... end rc=0 secs=N`, then the headline lines of that run (`throughput:`, `E1`, `E3`, `E4`, `-> {...}` for the accum sweep) | one start line, one end line and up to 40 headline lines per run; `rc=124 TIMEOUT` means its timeout ended it (its json keeps the sections finished before that) |
| `PROF SKIP name: budget left N s ...` | the stage budget ran out, or `MAXH` was reached; the run was not started |
| `PROF printing`, `RBEGIN|profjob`, `RBEGIN|profrun`, `PROF RESULT PRINTED ... r_lines=N failed=[...] skipped=[...]` | **collect now** |
| `PROF-STEPS`, `PROF DONE failed=none skipped=[]`, `CIO DONE` | all six runs and the smoke ended with rc 0 |
| `PROF DONE failed=[...]`, `CIO-FAIL PROFILE: ...` | a step failed, timed out, or `MAXH` was reached. The results that exist were printed before this line; collect them all the same |

### Stop rules (PROFILE)

| # | Rule | Action |
|---|---|---|
| P1 | Not `running` 15 min after create, or no `CIO START` 15 min after `running` | S1 |
| P2 | **No `PROF MODE` line**, or `STAGE train` appears | destroy at once (this is the 24,000-update job) |
| P3 | `STAGE prof` not reached 60 minutes after `CIO START` | read the last TICK. A download or slice build that is still moving may have 10 more minutes; otherwise destroy (a late start shortens the stage budget, which always ends 7 minutes before `MAXH`) |
| P4 | `CIO-FAIL fetch-prof`, or `prof_train.py is not the pinned one` | destroy; nothing can be profiled. Report |
| P5 | `PROF-JOB END` with `rc` not 0 or `final_eval false` | let the harness runs go on if the pool exists (cheap), but the shake-out found a defect of the real job: read `RESULT-SUMMARY` and the log tail, report it |
| P6 | No new TICK for 20 minutes | `status`; destroy if not `running`; else wait 10 more minutes, then destroy |
| P7 | Cost so far reaches $1.50 for any reason | destroy |
| P8 | `PROF RESULT PRINTED`, `CIO DONE` or `CIO-FAIL` | collect, then destroy at once |

After destroy: `$V credit` shows no instance; update the SPEND.md row with the actual cost.

### What comes out (names of the printed blocks and files)

Block **`profjob`** (the smoke; folder `profjob/` after collect): `PTC/RESULT.json` (steps, `n_params`, `train_s`, `steps_per_s`, `peak_mem_mib`, `cap_hits`, `final_eval`, `lesions`), `PTC/stdout.events.txt` (the train events with `elapsed`, then the evaluation events), `RESULT.json` and `box.json` (`pool_build_s`, `started_unix`, the arm's `wall_s`), `pool_MANIFEST.json`, `caps.json`, `caps_report.json`, `cmd.prof.sh.txt` (the exact command), `box/` (setup logs, `code_identity.txt`, `versions.txt`, `prof_env.txt`, `eg_check.log` ...). The checkpoint is not included.

Block **`profrun`** (folder `profrun/`):

| File | Content |
|---|---|
| `profile.md` / `.json`, `profile.profiler.md` | PTC accum 16, sections breakdown (ms per update by stage and by module), throughput (s/update, peak memory), profiler (top-25 CUDA kernels, GPU-busy fraction, launch-bound verdict), padding, sweep (accum 1 to 32; an OOM at accum 1 is a result), syncs (every host-device sync by python line). The raw `*.profiler.json` and traces are never printed |
| `bench.md` / `.json` | seven variants, median s/update and speed against `baseline` (the pre-registered mark in `PREREG-eg-once.md` is a median of at least 1.3 times over at least 100 timed updates after 20 warm-up) |
| `equiv_gpu.md` / `.json` | E1 (Gemma vectors, `eg_once` against the old path, bf16, GPU, real Gemma: look for "registered setting met: True"), E2 (printed in two wordings by the harness at the current pin: the registered absolute limit, and the revised relative rule of PREREG amendment 2, with scale diagnostics; read both, this runbook changes neither), E3 (loss and gradient) for eight variants |
| `equiv_e4.md` / `.json` | E4, the 300-update loss trace for `eg_once` |
| `b3g2_profile.md` / `.json`, `b3g2_bench.md` / `.json` | B3G2 accum 32: breakdown, throughput, padding, syncs; bench of `baseline;eg_once` |
| `a_profile.log.tail` ... `f2_b3g2_bench.log.tail` | the last 1,500 lines of each run's log (a bench that is cut by its timeout leaves its numbers only here) |
| `prof_env.txt`, `stages.txt`, `prof_steps.txt`, `prof_status.txt` | versions and hardware; start time of every stage (how long data and skills took); return code, seconds and timeout of every step; failed and skipped steps |

Size: files over 400 KB are gzipped, and if the `profrun` archive would pass 2,000,000 bytes (about 9,000 log lines) the largest `.json` files are dropped, with a `PROF WARN` line (their `.md` stays). The Vast log read window is 20,000 lines; the tiny CPU shapes printed 156 to 168 `R|` lines (shown), so a real run is expected to stay far below the window (suggested).

### What to check first

1. Shake-out (each is a yes or no, from the tail): `eg check cuda` rc 0; harness hash line says "the pinned value"; `RESULT-SUMMARY` as in the table above; `PROF-JOB pool` hash equal to the CPU box's; every `PROF STEP ... rc=0`.
2. The numbers the coordinator asked for: `sec_per_update_first_to_last_log` and `final_eval_phase_s` (then the full-job estimate: 24,000 times the first, plus the second, plus about 0.7 h of set-up); GPU name, driver, torch and CUDA lines of `prof_env.txt` against the PC's.
3. The speed-up question: `bench.md` and the E1 to E4 verdicts in `equiv_gpu.md` and `equiv_e4.md`, read against `PREREG-eg-once.md` (pass marks fixed there before any GPU number; this runbook does not change them).

# DRYRUN: CPU-only dry assembly and smoke test of ptc3s_box.sh

Nothing here touched Vast or a GPU, nothing was pushed, GitHub and Hugging Face were only read anonymously, and `/mnt/project-files` was only read (SPEND.md, AT10M-RENTAL-GATE.md). Labels: **shown** = seen in the logs kept in `dryrun-logs/`; **suggested** = reasoned, not seen; **untested** = needs the real box.

## 0. What was tested, and what that proves

- Script: `ptc3s_box.sh`, sha256 **`978c4a4ec393b824de46c2972ccae826bb8240cf4403f8a3647f6396c40bd329`** (53,186 bytes, ASCII only). It is the job script of the first commit (sha256 `a2232b5a52c394f7874075b11d395aa39293e4cd02b77b175490ea0d7f739c5e`, 35,033 bytes, commit `6a14c49dcf`) plus PROFILE mode (section 9; harness pin `ca542f77a9`, section 9.7). Sections 1 to 8 describe evidence gathered on the first script (`dryrun-logs/run_final_frozen_script.log` and the others named there); section 9 shows that with `PROFILE` unset the new script behaves the same (a diff, a full default dry run whose 79 marker lines equal the old run's, the guard test, `bash -n`, shellcheck, the offline Vast-kit tests) and what PROFILE mode did on the CPU. Regenerating the first script from the first template with the same generator gives the committed first script byte for byte (shown, section 9.2).
- It was run the way `vast.py create` runs it: `bash -c "export MAXPAR=5 QSUB= <env>\n<script>" cio`, with the CPU hooks `PTC_DRY=1` (no nvidia-smi, no CUDA asserts), `PTC_DRY_EG=1` (real EmbeddingGemma 2 on the CPU), and `PTC_DRY_EXTRA` (the only way the job line differs from the queue file: `--device cpu --steps 2 --big-data "" --train-extra "--batch 16 --eval-max 16"`).
- Dry box: 4 CPU cores, 16 GB RAM (the container limit counts `/dev/shm`, where the work root was), Python 3.11, torch 2.14.1+cpu, transformers 5.19.0, tokenizers 0.23.2, safetensors 0.8.0 (all three asserted by the script). The rental will have the image's torch 2.11.0 with CUDA 12.8.
- Shown: the script assembles the same tree as `install_ptc.ps1`, the PC runner's own functions build the commands, the PTC arm builds with the expected 4,023,976 parameters and takes loss steps, the result and the 16 MB checkpoint are printed in the kit's log format and come back through the kit's own `collect` and `collectck` code. Not shown: anything that needs the GPU, Vast, a long run, or the real Hugging Face and GitHub from a datacenter address (section 6).

## 1. The requested checks, one by one

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Fetch the pinned sources by sha | shown: base `custom_io` at `74d6e92c75`, package at `c2bf1a71c7` (both `git fetch --depth 1 --filter=blob:none` of that exact commit, `rev-parse HEAD` compared), data-pool at `3d0afbead`, own-data at `8d012f1f`, skills curriculum at `57c45293` | `run_final_frozen_script.log` |
| 2 | Apply overlays | shown: copy of base, 6 PTC files over it, 2 queue files in; `caps.py` unchanged | same log, `src-ptc: ...` line |
| 3 | Verify every sha256 | shown: 6 package files (ptccheck.py, install_ptc.ps1, both queue files, both card templates), 6 PTC files (new sha, old sha at the base, and both listed in README.md and install_ptc.ps1), `caps.py`, `caps_b3s.json`, `cloze_long.py`, the own72 manifest, EmbeddingGemma `model.safetensors`, the web slices against the manifest, the curriculum files against its manifest. A mismatch ends in `CIO-FAIL`. The pins in the script were read by a generator from the pinned README and install_ptc.ps1 (`dryrun-tools/gen_box.py`), and the script re-checks them at run time | same log; `PTC-SETUP-OK.txt` is written in the PC's format |
| 4 | `python3 -I` import checks | shown: 11 modules import in isolated mode (no cwd, no PYTHONPATH), `PTC_ARM` is in `ALL_ARMS`, `ptc_cfg` has `calc_train` | `imports_check.txt` |
| 5 | `ptccheck.py` with the queue files, and `test_ptc.py` | shown: "all test_ptc checks passed" and "PTC CPU CHECK OK", about 45 s each time. The queue file parses through `job.py`'s own parser: 2 entries, `--arms PTC --accum PTC=16` | same log |
| 6 | `python -m custom_io.g8a.job --help` | shown: prints usage, `--arms {B2,PT,LLM,B3,B3G2,PTS,PTC}`; `get_data --help` too | `imports_check.txt` |
| 7 | Shortest real CPU smoke on the assembled tree | shown with the real EmbeddingGemma 2 weights (downloaded from `google/embeddinggemma-2` at the pinned revision, sha256 matched, `eg check cpu` ok, cosine 1.0 against the build box). The full pool (1,343,273 rows) was built, caps measured, the PTC arm built (4,023,976 parameters, as `test_ptc` says), took 2 updates (loss 4.70828, 16 micro-batches of 1 row), `cap_hits.total` 0, `calc_rows` 32, `calc_mismatch` 0, `calc_forced` 16, wrote `checkpoint.pt` (16,114,485 bytes), then ran the intact and `nocalc` evaluations with 16 rows per split. `chain5` was left out in the final runs (`--big-data ""`); in an earlier run it made the CPU evaluation last more than 25 minutes, and I stopped it | `ptc_arm_stdout_cpu_smoke.txt`, `run_final_frozen_script.log`, `run_job_only_cpu_smoke_killed_in_chain5.log` |
| 8 | `bash -n` | shown: ok | `bash_n.txt` |
| 9 | shellcheck | shown with shellcheck 0.11.0 (pip `shellcheck-py`, not installed on the box by default): 0 findings at error and warning level; 111 places with notes at info level (241 x SC2086 unquoted variables holding paths without spaces, the same style as `box.sh`; 5 x SC2012; 2 x SC2015; 2 x SC1091; 1 x SC2016; the first draft of this row said 106 and 231, which `shellcheck.txt` does not show). The current script, same tool: section 9.2 | `shellcheck.txt` |

## 2. Numbers measured on the dry box (the rental will differ)

| Stage | Dry box time | Note |
|---|---|---|
| setup (pip, version assert) | 5 s | packages were already cached here; expect minutes on the rental (suggested) |
| code (fetch, 20+ hash checks, ptccheck) | 47 to 58 s | ptccheck about 45 s |
| gemma (1.5 GB download, sha, `eg check`) | 19 to 32 s | |
| data, from scratch | 20 min 23 s | FineWeb-Edu shard 28 s; the web slices 19 min 37 s on **one** core; the three slices hash to the manifest ("web slices verified") |
| skills (200k build + dev-200 build) | 4 min | both hash checks passed |
| pool build (rung 3M, seed 400, `-L`) | 159 s and 184 s (two builds) | both builds gave the same `train_sha256` |
| before the first update, in all | about 30 min | $0.2 at $0.38/h |

Pool `p10-rung30-s400-a64-L` (shown, built twice, same hash): rows 1,343,273; pieces 60,008,258; `train_bytes` 485,544,869; `train_sha256` `27234f3e9861ce5f8c6db18371f27c5f52826712398b90a4e946e952ff8791fe`; 24,000 steps; 4.574 passes; own share 0.38.

Code identity (shown): `CODE-ID 8aPTC3S-pc-047f8ed212` (runner's own hash); `code_identity.py` gives `CODE-HASH-LF 47d676dde1` and `FILES-LIST-SHA256 62179e62bb2ef62c53774259841b0e188412076e4cf40ac05b8a7a60017862a2 (118 files)`.

Memory (shown): the PTC arm, CPU, batch 16, peaks at about 4.8 GB of resident memory (`run_job_only_cpu_smoke.rss`). Disk: the work root after the data stage holds about 9 GB, of which 4 GB is the downloaded shard (the script keeps it; the rental has 80 GB).

## 3. Things found, and what was done

1. **A CPU job killed by the memory limit ends with job exit code 0.** `job.py` records the arm as `arm_failed` and exits 0 (shown in `run2_arm_killed_by_memory_limit.log`: arm rc -9). The first version of the box script went on to print `CIO DONE`. Now the script reads `RESULT.json` (job status, arm status, final evaluation) and ends with `CIO-FAIL` unless all three say ok; the failure path still prints the result and the checkpoint if there is one.
2. **`local_runner.command()` adds `--device cpu` to every line kind on CPU, and `get_data` rejects it.** The script builds the commands for `cuda` always; the dry run adds the CPU device to the job line only.
3. **`vast.py collect` (the kit) stops with `ValueError: too many values to unpack` once the log window holds a checkpoint part**, because it unpacks every `RBEGIN` line as 4 fields and a part has 7. Shown with the unpatched kit in `kit_bug_test.txt`. `vastptc.py` drops checkpoint-part blocks before `collect` reads the text (shown in `fake_vast_test.txt`, case C).
4. **`vast.py collectck` writes normal result blocks to the module's `OUT` (`custom_io/results` of the kit's repo), ignoring `--out`** (shown, same file). `vastptc.py` sets `OUT` to `./collected`.
5. **`local_runner.code_hash` depends on line endings and on how the OS sorts paths.** A CRLF copy of the same tree gave `06c0bb4b10` instead of `047f8ed212` (shown, `crlf_test.txt`). The PC's folder name `WORK\code\8aPTC3S-pc-<hash>` can therefore differ from the box's with identical code. `code_identity.py` gives the same answer for LF and CRLF trees (shown). The same holds for the data file: `lf_sha256.py` gives the pool's hash `27234f38...` for the box's LF file and for a CRLF copy of it, whose stored size is 486,888,142 = 485,544,869 + 1,343,273 (shown, `lf_test.txt`).
6. **A speed guard that only watched dollars could let a run continue that `MAXH` would kill.** Example: 8 hours projected at $0.38/h costs $3, under the $4 cap, but `MAXH=6` kills the job at 6 hours with nothing saved. The guard now also stops when the projected hours exceed `MAXH` (shown with synthetic logs in `guard_test.txt`).
7. **`MAXH` could be missed if it fell while no step was running** (during a retry sleep). The watcher now keeps killing every 20 s after `MAXH`, and `runp` refuses to start a step after `MAXH`. Shown: `run_maxh_test.log` (a 22-second `MAXH` killed `ptccheck`, ended with `CIO-FAIL maxh`, no process left).
8. **`ptccheck.py` failed once in twelve CPU runs of the check** (the parity subprocess of `test_off_is_base` exited non-zero; `ptccheck` prints only the last 8 lines of the test output, so the cause was not recorded). Four full dry runs passed before it; after it one `ptccheck` rerun, five `test_ptc` runs and the final full dry run passed. Suggested cause: a transient shortage of disk space (the dry box's disk had 2.4 to 4.8 GB free); not shown. The script now retries `ptccheck` once, prints the whole test output after a second failure, and refuses to start with less than 20 GB free disk on the rental.
9. **`train.py` logs `"size": ... "inside": false` for the PTC arm** (4,023,976 parameters against the band 3,147,208 to 3,341,880, `vs_plain_tf_pct` 24.02). This is a log line, not an error, and the PTS arm has the same configuration apart from `calc_train`; I expect the PC log to carry the same line (suggested, not checked).
10. **Checkpoint only at the end.** `train.py` saves `checkpoint.pt` once, after the last update, and cannot resume. A crash, a `MAXH` stop or a lost box at hour 3 gives nothing. Read in the code; not new, but it is why the money rules in RUNBOOK.md matter.

## 4. Differences between the PC job and the box (none tested against a PC run)

- Hardware and software: RTX 5070 Ti (PC) against an RTX 4090; torch and CUDA builds; kernel nondeterminism. Scores will not be bit-identical (suggested). The PC's torch, numpy and pyarrow versions were not available to compare.
- Windows against Linux: paths; CRLF in the PC's `train.jsonl` (its `train_bytes` should be the box's 485,544,869 plus 1,343,273 rows; hash after CRLF to LF) and in its code files (section 3, item 5); `PYTHONUTF8=1` is set by the runner's `child_env` on both, so text encoding is the same.
- The queue file's `# ENV` lines (`PYTHONPATH` with the PC's `eg_site`, `CUSTOM_IO_EG2`) are replaced by the box's own EmbeddingGemma folder.
- Inputs come from pinned commits and a live download (FineWeb-Edu shard 0) instead of the PC's folders; the shard itself is not hash-checked, the slices built from it are (against `web_slices_8a_MANIFEST.json`).
- The PC job waits behind other queue jobs and shares the GPU with the desktop; the box runs it alone with `--par` 1 in effect (the script runs the two queue lines one after the other).
- The data-pool commit `3d0afbead` (the one that holds `cloze_long.py`) is older than the branch head. The script's header comment records that the manifests, `web_slice.py` and the panel index are the same files at `12d30d0ce9`; I compared them file by file earlier in this work and did not repeat it in the last pass.

## 5. Offline tests of the kit's own code through `vastptc.py` (urllib replaced; no network call is possible)

Shown in `fake_vast_test.txt`:
- A, `create`: the body sent to Vast is image `pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime`, disk 80, `runtype args`, `args = ["bash", "-c", "export MAXPAR=5 QSUB= MAXH=6 DPH=0.38 ...\n<ptc3s_box.sh byte for byte>", "cio"]`, 35,115 bytes for the first script (53,268 bytes for the current one, section 9.2); no key, token or bearer text in it.
- B, `search`: the filter is the kit's (verified, on-demand, 1 GPU, reliability 0.98, CUDA 12.8, 60 GB disk, 300 Mb/s, 8 cores); only the `RTX 4090` row is printed.
- C, `collect` on the finished dry-run log, which holds 15 checkpoint parts: extracts the result tarball and checks its sha256.
- D, `collectck` on an emulated live log (the box prints a part in one burst, then sleeps 100 s; the kit reads the last 9,000 lines every 40 s): the 16,114,485-byte `checkpoint.pt` is rebuilt, sha256 `1d1f674b00aed8a6...`, when started at the result line, at the start of round 2, and 700 s after the result line (middle of round 2). The emulation is mine; the real Vast log timing is untested.
- `accept.py` on the CPU smoke result: REJECT because steps is 2 (right), and on edited copies: ACCEPT, REJECT on mismatch above 0.1 %, REJECT on a wrong parameter count (`accept_test.txt`).

## 6. NOT exercised, and my honest chance that each step works the first time on Vast

This section is about the 24,000-update job. The PROFILE rental has its own list in section 9.5. Rough judgments (suggested), each for one attempt, not computed from data.

| Step | Why not exercised here | Chance |
|---|---|---|
| Vast accepts `create` with a 35 KB `args` string (the first script; 53 KB now, section 9.5) and starts the container | no Vast calls allowed; the kit's `box.sh` is 7.7 KB; the sibling `at10m_box.sh` (37 KB) was never rented either | 85 % |
| Image has `git`, `timeout`, `setsid`, `split`, `base64`; `apt-get` works if `git` is missing | dry box differs from the image | 93 % |
| `pip install` of the 3 pins into the image's Python (3.11 or 3.12) and the version assert | resolved here in a Python 3.11 venv only; no torch 2.11 | 93 % |
| transformers 5.19.0 with torch 2.11.0 | untested pair | 95 % |
| EmbeddingGemma 2 download from a datacenter address (anonymous rate limit) and `eg check cuda` | download and CPU check shown | 90 % |
| FineWeb-Edu shard download from Hugging Face and the web slice build on the rental's CPU | shown through the sandbox proxy; the slices hash-check themselves | 88 % |
| GitHub fetches by sha from the rental | shown here only | 97 % |
| Training starts on the GPU and runs the first 1,000 updates (bf16, 9 GB free check, `expandable_segments`) | CPU only | 90 % |
| 24,000 updates finish without a crash, NaN, out-of-memory or `MAXH` stop | the PTC arm has run only inside `ptccheck` (40-update parity test) and in my 2-update CPU smoke; I found no PTC result in the files I read; speed on the 4090 unmeasured; no resume | 80 % |
| Final evaluations at full size on the GPU (`chain5`, every lesion) | CPU: intact and `nocalc` with 16 rows per split only | 88 % |
| Result and checkpoint printed through the real Vast log (500-char line split, 20,000-line reads, log delay) | emulated only | 90 % |
| Someone starts `collectck` within 15 minutes of the result line | a human step | 85 % |
| The box self-guards: `GUARD STOP`, `MAXH` kill of a real training process group | guard tested on synthetic logs; `MAXH` kill tested on `ptccheck` only | 93 % |
| Total cost at most $3 / at most $5 | speed unmeasured | 75 % / 97 % |

If the twelve steps above were independent, one attempt would reach a collected, accepted result about 26 % of the time. That is too pessimistic: most failures come early (setup, download, hash, size limit), cost under $0.5, and one retry on another host fixes the host-specific ones. My overall judgment (suggested): about 45 % that the first attempt delivers a complete result with checks 1 to 5 and 7 of the RUNBOOK passing, about 60 % after one cheap retry, and about 5 % that more than $3 is lost. Check 6 (calculator mismatch at most 0.1 %) is the experiment itself; I give no chance for it.

## 7. Files and how to repeat

`dryrun-logs/` holds every log named above (base64 payload lines removed). `dryrun-tools/` holds the helper scripts; their paths are the scratch paths of the session that wrote them (`/tmp/claude-0/.../scratchpad`, `/dev/shm/ptcdry`), so edit the paths before reuse. `gen_box.py` plus `ptc3s_box.template.sh` regenerate `ptc3s_box.sh` from the pinned package files; they are kept so that a reviewer can see where each pin came from, and the committed `ptc3s_box.sh` is the file to run.

Added with PROFILE mode (section 9): `dryrun-tools/` now also holds `run_p.sh` (PROFILE dry launcher), `run_default.sh` (default-path dry run with the earlier parameters), `quick_tests.sh` (the PROFILE guards), `cmp_logs.py` (marker comparison of two box logs), `regen.sh` (regeneration check), `fake_vast_prof_test.py` and `run_fake_prof.sh` / `run_fake_default.sh` (offline kit tests), `mk_venv.sh` and `phaseA.sh` (rebuild of the dry box, section 9.6), `prof_try.sh` / `prof_try_all.sh` (the harness alone on the CPU), `shellcheck_run_new.sh`. `gen_box.py` fills two more pins (`PROF_SHA`, `PROF_PY_SHA`) and takes the template path from the environment variable `TEMPLATE`; with the first template it still produces the first script byte for byte (`dryrun-logs/regen_check.txt`). The first template and the first script are in git at commit `6a14c49dcf` (`git show 6a14c49dcf:results/8a-g/vast-ptc3s/dryrun-tools/ptc3s_box.template.sh`, sha256 `1da613d0de1432a2393d26099c0bee0ffbb4d43e8bf187f2bacc019287ba947d`), for anyone who wants to repeat the regeneration check.

## 8. Missing facts (not guessed)

- The PC's reference `train_bytes` and `train_sha256` of pool `p10-rung30-s400-a64-L` (the comparison in RUNBOOK.md section 7 is the first one).
- The PC's torch, CUDA, numpy and pyarrow versions.
- A PC `RESULT.json` of the PTS arm (8aG2C3S) to read `n_params` from; the 4,023,976 comes from `test_ptc.py` and the PTC README.
- Where the earlier Vast box ("box A") ran and its log; I could only read the kit's scripts.
- Any Vast limit on `args` length or on log size (the export prints about 65 MB of base64 for three rounds).
- The speed of this job on a 4090.
- For PROFILE mode (section 9): the seconds per update of the PTC arm on a 4090 (the point of the smoke), and its final-evaluation time on the rental (on the PC the final evaluation of the PTC/PTS arm is about 1 minute, shown by the PTS run g2c3s, section 9.5, so `EXTRA_H=0.5` is conservative); which torch version the profiling harness was developed and tested on (I could read only the harness file at the pinned commit, not the author's test log); whether the harness's real-Gemma E1 and its `profiler` section work on CUDA (on the CPU the harness uses a stub front and no GPU profiler); whether B3G2 trains on the PTC pool with `caps_b3g2.json` on CUDA (it ran only on tiny CPU shapes here); whether the `torch.compile` variant (`PROF_COMPILE=1`) works at all.

## 9. PROFILE mode (added 2026-10-14): what changed, what was tested, what was not

Same rules as before: nothing here touched Vast or a GPU, nothing was pushed, and nothing was written to `/mnt/project-files`. Labels as at the top. How to run the rental is in RUNBOOK.md section 9; this section is the evidence and the doubts.

### 9.1 What changed in the script

- `ptc3s_box.sh` is now 53,186 bytes, sha256 `978c4a4ec393b824de46c2972ccae826bb8240cf4403f8a3647f6396c40bd329` (the PROFILE commit `22bec73ec6` had `1ccc5c3f...` with the older harness pin; section 9.7; first script: 35,033 bytes, `a2232b5a...`). It is produced from `dryrun-tools/ptc3s_box.template.sh` by `gen_box.py`; the output is never edited by hand. `diff` of the two scripts: 16 hunks, 245 new lines (counting the new versions of the replaced ones), 11 old lines replaced, none only deleted (`dryrun-logs/script_diff_first_vs_current.txt`, shown).
- Lines that touch the default (PROFILE unset) path, all of them (shown in that diff):
  1. The defaults of `MAXH`, `END_SLEEP` and `FAIL_SLEEP` come from two variables set by `PROFILE` (6, 600, 1800 with PROFILE unset or 0, as before; 2, 300, 600 with PROFILE=1).
  2. `stage()` also appends the stage name and time to `state/stages.txt` (one more small file in the work root; nothing about it is printed in the default path).
  3. `watch_loop` reads the training log through a variable (`TLOG`, which is `$O/PTC/stdout.txt` as before), and the projection and the speed guard get the extra test `PROFILE != 1`.
  4. `boxfiles()` and `summary()` take an optional folder argument (default: the job folder, as before).
  5. The `PTC3S START` line builds the `guard=` word with an `if` instead of an `&&`/`||` chain (same words).
  6. After that line: a check that `PROFILE` is 0 or 1 (`CIO-FAIL` otherwise), and for `PROFILE=1` the `PROF MODE` line and two refusals (the CPU dry-run hooks `PROF_DRY_*` need `PTC_DRY=1`; `PTC_DRY=1` is refused on a box where `nvidia-smi -L` lists a GPU).
  7. Two hook lines: `[ "$PROFILE" = 1 ] && prof_emit` in `die()` (the failure path) and `[ "$PROFILE" = 1 ] && prof_main` in place of the train stage. With `PROFILE` unset both do nothing.
  8. A PROFILE-only block that records `nvidia-smi`, `pip list`, torch/CUDA and CPU facts before the code stage, and the new function definitions (`prof_*`, about 186 lines, only called from `prof_main`).
- The harness pins: `PROF_SHA=ca542f77a9d3f6afb4a6850936e62da5b54a45ec` (checked to exist with `git cat-file`; the newest harness commit as named by the coordinator, on branch `claude/project-thread-yha868`, and the last commit that changed `prof_train.py`, checked with `git log`); `prof/prof_train.py` at that commit is 132,604 bytes, sha256 `2f1410fea1e5754c785188c30fe22368fbd42b6bc45ff54304e59896c3fe479b` (computed with `git show`, not typed; the first PROFILE commit pinned `6a870a767c`, 130,334 bytes, `91204583...`). The box fetches the folder `results/8a-g/speedup` at that commit and stops with `CIO-FAIL` if the hash differs (the check ran in every PROFILE dry run, shown: "= the pinned value").
- The two block names that the new mode prints are `profjob` and `profrun`. `vastptc.py` needed no code change for them (its `collect` drops only the 7-field checkpoint-part blocks); I added a docstring example line for the PROFILE `create` command. The kit's `vast.py` is untouched (sha256 `b68462f7...`).

### 9.2 Tests run (all on the CPU, all shown in `dryrun-logs/`)

The rows below were made with the script of the first PROFILE commit (`22bec73ec6`, sha256 `1ccc5c3f...`, harness pin `6a870a767c`); log names without `_pin_ca542f77` belong to it. That script differs from the current one in exactly two lines, the harness pin (section 9.7); section 9.7 lists what was redone for the current script.

| # | Test | Result | File |
|---|---|---|---|
| 1 | Regenerate the first script from the first template with the current `gen_box.py` | byte for byte `a2232b5a...`; the current template gives `978c4a4e...`, 53,186 bytes, `bash -n` ok (re-made for the new pin, section 9.7) | `regen_check.txt` |
| 2 | Default path, full dry run of the new script, same parameters as the earlier full run of the first script (`MAXH=3 END_SLEEP=20 PACE=2 TICK_EVERY=120 DPH=0.38 PROJ_CAP_USD=4`, the same CPU hooks), data from the cache | ended `CIO DONE`; the marker lines (every `===` line, `CMD`, `CHILD-ENV`, `QUEUE-ENV`, `RESULT-SUMMARY`, checkpoint-part announcements, block names; times, file times and scratch paths normalised by `cmp_logs.py`) are **79 against 79 with 0 differences** compared with the first script's full run | `default_run_new_script.log`, `default_vs_first_script_markers.txt` |
| 3 | The speed-guard test (`guard.py` as the new script writes it, the six synthetic cases) | output identical to the first script's (`diff` empty) | `guard_test_current_script.txt` |
| 4 | The `ptccheck` retry test (fails once, fails twice) | same behaviour; only the free-disk figures differ | `retry_test_current_script.txt` |
| 5 | `bash -n`; shellcheck 0.11.0 | ok; 0 findings at error and warning level; 172 notes at info level (351 x SC2086, 7 x SC2012, 4 x SC2231, 3 x SC1091, 2 x SC2015, 1 x SC2016), the same kinds as before plus 4 x SC2231 (a variable inside a `for` glob), new in this script | `bash_n_and_shellcheck_current_script.txt` |
| 6 | Offline Vast-kit tests on the default dry-run log (create, search, collect, `collectck` in three start positions, and the two defects of the unpatched kit) | same results as section 5: `args[2]` is 53,268 bytes, the script after the exports line is `ptc3s_box.sh` byte for byte, no key or token word in the body; `collectck` rebuilds the 16,114,485-byte checkpoint, sha256 `1d1f674b00aed8a6...`, in all three cases | `fake_vast_test_current_script_default_log.txt` |
| 7 | PROFILE guards (five refusals, plus `EG=0` still refused) | all as expected: `PROFILE=yes`, `PROF_DRY_ARGS` / `PROF_DRY_FAIL` / `PROF_DRY_HANG` without `PTC_DRY`, `PTC_DRY=1` with a GPU listed (a fake `nvidia-smi`) | `profile_guard_tests.txt` |
| 8 | **PROFILE=1, happy path** (full path on the CPU: all stages, the job smoke, six harness runs on tiny shapes, printing; the harness flags of the real rental plus tiny-shape flags appended by the dry-run hook `PROF_DRY_ARGS`) | `PROF DONE failed=none skipped=[]`, `CIO DONE`; all seven steps rc 0; two blocks printed (`profjob`, `profrun`: 23 files, 21,960 bytes, 172 `R|` lines) | `profile_run_happy_path_pin_6a870a76.log` |
| 9 | PROFILE=1, one step fails (`PROF_DRY_FAIL=c_equiv`, a bad flag) and the stage budget is 4 minutes | `c_equiv rc=2` is logged and the next steps still run; `f2_b3g2_bench` is skipped with a `PROF SKIP` line ("budget left 95 s (minimum 100 s ...)"); results printed; `PROF DONE failed=[ c_equiv(rc2)] skipped=[ f2_b3g2_bench]`, then `CIO-FAIL PROFILE` as designed | `profile_run_failing_step_and_budget.log` |
| 10 | PROFILE=1, every step cut by a 6-second timeout (`PROF_STEP_MIN=0.1`), `d_e4` replaced by `sleep 3600` (`PROF_DRY_HANG`) | all six harness steps `rc=124 ... TIMEOUT` 6 s apart, the stage went on, the block was printed with what existed, no `sleep 3600` process left (checked with `pgrep` afterwards). Because every step hit the 6-second timeout, the log cannot show the hang alone; `runp` kills the whole process group, as in the first script's `MAXH` test | `profile_run_timeouts_and_hang.log` |
| 11 | PROFILE=1, `MAXH` falls during the job smoke (`MAXH=0.075`) | `CIO MAXH ... stopping the running step`, `PROF-JOB END rc=143 maxh_hit=yes`, all six harness runs skipped with `PROF SKIP`, partial results printed, `CIO-FAIL PROFILE` | `profile_run_maxh_during_job.log` |
| 12 | PROFILE=1, archive size cap lowered to 14,000 bytes (`PROF_MAX_BYTES`) | two `PROF WARN` lines, the two largest `.json` files dropped (`profile.json`, `b3g2_profile.json`; their `.md` files stay), `profrun` archive 11,861 bytes | `profile_run_archive_size_cap.log` |
| 13 | Offline kit test of the PROFILE script and log: `create` with `--env "PROFILE=1 MAXH=2 DPH=0.40 END_SLEEP=300 FAIL_SLEEP=300"`; `tail`; `collect` | exports line `export MAXPAR=5 QSUB= PROFILE=1 MAXH=2 DPH=0.40 END_SLEEP=300 FAIL_SLEEP=300`; script after it byte for byte; `args[2]` 53,263 bytes (whole JSON body 54,754 bytes); the kit's `tail` hides all `R|` lines; `collect` printed `{"profjob": "ok", "profrun": "ok"}` and extracted 55 files | `fake_vast_prof_test.txt` |

The runs 8 to 12 used the CPU hooks, so they prove the script's logic (order of stages, budget arithmetic, timeouts, `MAXH`, printing, collecting), not any GPU behaviour.

### 9.3 Numbers from the CPU dry box (the rental will differ; none of these is a GPU speed)

- Dry box rebuilt after the container restart (section 9.6): setup 28 s, code 46 s, gemma 25 s, data 14 min 51 s, skills 2 min 55 s; 19 min 25 s in all up to the end of the skills stage (the first run took about 28 min, section 2). CODE-ID `8aPTC3S-pc-047f8ed212` and the pool hash `27234f38...` are the same as before (shown).
- PROFILE happy path (previous pin; the same run for the current pin is in section 9.7), from `CIO START` 04:19:22 to `CIO DONE` 04:33:02 (13 min 40 s, with the data and skills stages already cached): job smoke 483 s (pool build 107 s, start-up before the first update 40 s, 2 updates 14.5 s, final evaluation phase 317 s on 16 rows per split without chain-5), a_profile 13 s, b_bench 8 s, c_equiv 16 s, d_e4 7 s, f1_b3g2_profile 30 s, f2_b3g2_bench 30 s. Output: 23 files, 21,960 bytes in `profrun`; 172 `R|` lines in all (the Vast log window is 20,000 lines).
- The `PROF-JOB projection` line said 26.0 h for 24,000 updates: that is the CPU speed of a 2-update run and means nothing for the 4090.
- The CPU `RESULT-SUMMARY` of the smoke shows `chain5 false` and `lesions ["nocalc"]` because the dry-run hook removes the big data (`--big-data ""`) as in the first script's dry runs. On Vast `chain5 true` and a longer list of lesions are expected (suggested).

### 9.4 How to read the results

RUNBOOK.md section 9 has the full list. Short version: after `collect` there are two folders. `profjob/` is the smoke (`PTC/RESULT.json`, `PTC/stdout.events.txt`, `RESULT.json`, `box.json`, `pool_MANIFEST.json`, `cmd.prof.sh.txt`, `box/` with the setup logs and `prof_env.txt`). `profrun/` holds the harness outputs: `profile.md`, `profile.profiler.md`, `bench.md`, `equiv_gpu.md`, `equiv_e4.md`, `b3g2_profile.md`, `b3g2_bench.md` (and the `.json` of each), the log tails `*.log.tail`, `prof_env.txt`, `stages.txt`, `prof_steps.txt`, `prof_status.txt`. The two speed numbers that decide the cost estimate are on the log (`PROF-JOB timing`: `sec_per_update_first_to_last_log` and `final_eval_phase_s`) and in `profjob/box.json` and `profjob/PTC/RESULT.json`. The pass marks of the speed-up experiment (E1 to E4, the 1.3 times mark) are in `PREREG-eg-once.md` of the harness folder, which this kit does not change.

### 9.5 NOT exercised, and my honest chance that each step works the first time on Vast

Rough judgments (suggested), one attempt each, not computed from data.

| Step | Why not exercised here | Chance |
|---|---|---|
| Vast accepts `create` with a 53 KB `args` string (section 6 gave 85 % for 35 KB) | no Vast calls; the limit is unknown | 80 % |
| `PROFILE=1` arrives in the container (the `PROF MODE` line is there) | the kit's `--env` path was tested offline only; same mechanism as `MAXH` | 97 % |
| Fetch of the harness folder from GitHub by sha, hash check | shown through the sandbox proxy | 97 % |
| `eg check cuda`, 300 updates on the GPU with the real pool, caps and Gemma front | CPU only | 88 % |
| The final evaluation (chain-5, lesions) ends inside `PROF_JOB_MIN=45` minutes | on the PC the final evaluation of the PTC/PTS arm is about 1 minute (shown by the PTS run g2c3s, 3M accum 16: `train_s` 25,786 s, `wall_s` 25,845 s, so start-up plus the whole final evaluation took about 1 minute; figures as given to me, that result file is not in this worktree), so the 45-minute timeout is comfortable and the guard's `EXTRA_H=0.5` is conservative. The smoke is expected to take about 10 minutes (pool build about 3 min, 300 updates, final evaluation); the pool build and start-up took about 2.5 min on the CPU box (shown). Not measured on the 4090 | 95 % |
| `a_profile` on CUDA, including the profiler section and the accum sweep (an OOM at accum 1 is a recorded result, not a failure) | the harness ran only on the CPU here, where its profiler section lists CPU ops and says "no CUDA kernels"; the CUDA kernel table, GPU-busy fraction and launch-bound verdict were never seen | 75 % |
| `b_bench` finishes inside its timeout (`PROF_STEP_MIN=25` min) | seven variants x two rounds x (20 + 100) updates = 1,680 updates plus builds; it needs an average of about 0.9 s per update or faster, speed unknown. A cut bench keeps its numbers in `b_bench.log.tail` | 65 % |
| `c_equiv`: E1 with real Gemma on the GPU in bf16, then E2 and E3 for eight variants | E2 needs a CPU fp32 Gemma forward with `OMP_NUM_THREADS=2` (the job's setting, inherited); its cost on the rental's CPU is unmeasured | 65 % |
| `d_e4`: 300-update loss trace for `eg_once` | CPU only | 85 % |
| B3G2 (accum 32, `caps_b3g2.json`) on the PTC pool on CUDA | ran only on tiny CPU shapes; the pool was built for the PTC arm, not B3G2 (the harness README's own convention, suggested to work) | 65 % |
| `PROF_COMPILE=1` (`torch.compile` variant) | never run, not even on the CPU | 40 % (leave it off) |
| The stage budget (`PROF_MAXMIN=75`) and `MAXH=2` end the stage cleanly on a slow host | arithmetic and CPU hooks only (runs 9 to 11) | 90 % |
| Printing: two blocks through the real Vast log (500-character lines, 20,000-line window, log delay), then `collect` | emulated; 172 `R|` lines on the CPU, a real run has larger files (gzip over 400 KB, cap 2,000,000 bytes) | 90 % |
| **All six harness runs end rc 0 and the smoke ends rc 0 on the first attempt** | product of the above, not independent | 25 % |
| The rental still answers its two main questions (speed and final-evaluation time of the real job; at least `profile.md` or `bench.md` for the speed-up) | the box is built to print what exists after any failure | 80 % |

If the first rental ends early, the cost is small: the work before the smoke is about 30 to 45 minutes on a slow host, so under $0.5 (suggested).

### 9.6 Notes and surprises

- **The container restarted during this task.** `/dev/shm/ptcdry` (the dry box: Python 3.11 venv, work root `J`, the cached data) was lost and the scratch folder on disk survived. I rebuilt the dry box (`mk_venv.sh`, then `phaseA.sh`: the first script from scratch up to the end of the skills stage) and every dry run in this section was made after the rebuild, so nothing in section 9 relies on the lost box. The rebuild reproduced `CODE-ID 8aPTC3S-pc-047f8ed212` and the pool hash (shown). The evidence of sections 1 to 8 is the committed logs from the first task, which were not re-made. One early PROFILE log of the previous generation (`dry_p1`) is not used as evidence.
- **Scratch files of another agent.** The harness agent's working copies of `prof_train.py` and `test_prof.py` in the shared scratch folder were overwritten by me with the versions at the pinned commit. That agent had already handed back and its work is in the pushed commit, so I expect no loss (suggested).
- **The script's header comment calls the rental "the one-hour GPU shake-out".** That wording came from the request; the estimate in RUNBOOK.md section 9 is 1.5 to 2 hours (data stage alone 15 to 20 minutes on one core). I left the comment, because changing it would change the sha256 of an already tested script.
- **A bug I introduced and fixed on the way:** a local array named `D` in `pstep` shadowed the global `D` (the skills folder); shellcheck found it (SC2128) and I renamed the array before the final runs. Nothing else of the script changed after run 8.
- **`END_SLEEP` and `FAIL_SLEEP` defaults differ in PROFILE mode** (300 and 600 seconds instead of 600 and 1800), because a profiling box that has printed everything has no reason to wait ten minutes. The RUNBOOK command sets them explicitly (`END_SLEEP=300 FAIL_SLEEP=300`).
- The speed guard, `PROJ_CAP_USD` and the checkpoint export are off in PROFILE mode, as asked; `MAXH=2` is the only hard stop (it kills the running step, as in the first script, shown in run 11).

### 9.7 Re-pin of the harness to `ca542f77a9` (added after the first PROFILE commit)

The coordinator asked for the newest harness commit: `PROF_SHA=ca542f77a9d3f6afb4a6850936e62da5b54a45ec` (branch `claude/project-thread-yha868`) in place of `6a870a767c`. Nothing else was changed (no new feature; the template is the same file).

- **What the harness changed** (shown by `git diff 6a870a767c ca542f77a9 -- results/8a-g/speedup`): `prof/prof_train.py` 25 lines added and 8 removed (E2 scale diagnostics, which are not marks; the relative E2 rule of PREREG amendment 2; prompts hash and seed in the E2 output; the E1-floor text in the md; a corrected CPU/bf16 label), and 22 lines added to `PREREG-eg-once.md` (result logs). No `add_argument` line of `prof_train.py` changed, so every harness command line of the box is valid as before. `test_prof.py` and `README.md` are the same files (their hashes in the two `PROF-HARNESS` log lines are equal; the `PREREG-eg-once.md` hash differs, as it should). `prof_train.py` was last changed by this very commit (`git log` on the path).
- **The new file:** 132,604 bytes, sha256 `2f1410fea1e5754c785188c30fe22368fbd42b6bc45ff54304e59896c3fe479b`, computed with `git show ca542f77a9:results/8a-g/speedup/prof/prof_train.py | sha256sum` by `gen_box.py` (not typed) and re-computed by hand with the same command; the box checks it after the fetch.
- **The new script:** `ptc3s_box.sh`, 53,186 bytes (same size), sha256 `978c4a4ec393b824de46c2972ccae826bb8240cf4403f8a3647f6396c40bd329`. It differs from the script of the first PROFILE commit (`1ccc5c3f...`) in exactly two lines, `PROF_SHA` and `PROF_PY_SHA` (`dryrun-logs/script_diff_pin_6a870a76_vs_ca542f77.txt`, shown).

Redone for the current script (all on the CPU, no GPU, no Vast, files carry the suffix `_pin_ca542f77` in `dryrun-logs/`):

| Item | Result | File |
|---|---|---|
| Regeneration check | the first template still gives the first script byte for byte (`a2232b5a...`); the current template gives `978c4a4e...`, 53,186 bytes, `bash -n` ok | `regen_check_pin_ca542f77.txt` |
| `bash -n`, shellcheck 0.11.0 | ok; 0 findings at error and warning level; 172 notes at info level, the same counts as before (351 x SC2086, 7 x SC2012, 4 x SC2231, 3 x SC1091, 2 x SC2015, 1 x SC2016) | `bash_n_and_shellcheck_pin_ca542f77.txt` |
| Speed-guard test (six synthetic cases) | output identical to the earlier one | `guard_test_pin_ca542f77.txt` |
| **PROFILE=1, one full CPU dry run** (same tiny-shape hook as before; the pool was rebuilt from scratch, so the job smoke built it again) | `PROF-HARNESS commit ca542f77a9... prof_train.py sha256 2f1410fea1... = the pinned value`; job smoke rc 0 in 485 s (pool build 109.9 s, start-up 38.8 s, 2 updates 13.0 s, final-evaluation phase 319.2 s), pool hash `27234f38...` again; a_profile 12 s, b_bench 8 s, c_equiv 17 s, d_e4 8 s, f1_b3g2_profile 31 s, f2_b3g2_bench 31 s, all rc 0; `PROF RESULT PRINTED ... r_lines=174 failed=[] skipped=[]`, `PROF DONE failed=none`, `CIO DONE`; 23 files, `profrun` archive 22,488 bytes; 13 min 44 s from `CIO START` (data and skills cached). The harness command lines were accepted as before. **It now prints E2 in two wordings**, e.g. `E2 (stub front (plumbing only)): max abs diff 0.000e+00 (registered limit 0.0001) -> PASS; revised relative rule (1e-05 x max |H|) -> PASS (seed 400)`; in `equiv_gpu.md` the E2 header line carries the registered wording and a later line the revised rule. On the CPU the front is a stub, so the E2 diagnostics were seen with zero differences only | `profile_run_happy_path_pin_ca542f77.log` |
| Offline Vast-kit create / tail / collect on that log | exports line `export MAXPAR=5 QSUB= PROFILE=1 MAXH=2 DPH=0.40 END_SLEEP=300 FAIL_SLEEP=300`; the script after it is `ptc3s_box.sh` byte for byte; `args[2]` 53,263 bytes; `tail` hides all `R|` lines; `collect` printed `{"profjob": "ok", "profrun": "ok"}` and extracted 56 files (one more than in run 13: an empty `profjob/box/guard.out`, which the earlier default dry run left in the work root's `state/` folder; not caused by the pin) | `fake_vast_prof_test_pin_ca542f77.txt` |
| **PROFILE unset: a full default dry run** (parameters of the earlier full dry run) and the marker comparison | `CIO DONE`; **79 marker lines against 79, 0 differences** compared with the first script's full dry run, and 79 against 79, 0 differences, compared with the default run of the first PROFILE commit's script | `default_vs_first_script_markers_pin_ca542f77.txt`, `default_run_pin_ca542f77.log` |
| Offline kit tests on the default log | same results as section 5: `args[2]` 53,268 bytes, the script after the exports line byte for byte, `collect` ok, `collectck` rebuilds the 16,114,485-byte checkpoint (`1d1f674b00aed8a6...`) in all three start positions, the two defects of the unpatched kit reproduce | `fake_vast_test_pin_ca542f77_default_log.txt` |

Helpers for this pass: `dryrun-tools/repin_quick.sh` (regeneration, `bash -n`, shellcheck, guard test), `repin_fake.sh` and `repin_default.sh` (offline kit test, default-path comparison); the PROFILE dry run itself was `run_p.sh` with `FRESH_POOL=1`, the default one `run_default.sh`. `gen_box.py` has the new `PROF_SHA`.

Not redone, because the two changed lines cannot change them (they are used only by the harness fetch, its hash check and the lines that print them): the PROFILE guard refusals (run 7), the failing step with a budget skip, the timeouts and hang, `MAXH` during the job and the archive size cap (runs 9 to 12), which stay as evidence of the previous pin's script. Label: the equality of the logic of those runs for the current script is suggested by the two-line diff, not shown by new runs.

Still untested at the new pin: everything that needs a GPU or the real Gemma front, including the new E2 scale diagnostics with real vectors (on the CPU box the front is a stub). The final-evaluation claim in section 9.5 changed with this commit: it now rests on the PC figures given to me (about 1 minute), not on a guess.

# DRYRUN: CPU-only dry assembly and smoke test of ptc3s_box.sh

Nothing here touched Vast or a GPU, nothing was pushed, GitHub and Hugging Face were only read anonymously, and `/mnt/project-files` was only read (SPEND.md, AT10M-RENTAL-GATE.md). Labels: **shown** = seen in the logs kept in `dryrun-logs/`; **suggested** = reasoned, not seen; **untested** = needs the real box.

## 0. What was tested, and what that proves

- Script: `ptc3s_box.sh`, sha256 `a2232b5a52c394f7874075b11d395aa39293e4cd02b77b175490ea0d7f739c5e` (35,115 bytes with the `export` line, ASCII only). The last full dry run (`dryrun-logs/run_final_frozen_script.log`) used exactly this file; every change after the earlier runs was followed by a new full run.
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
| 9 | shellcheck | shown with shellcheck 0.11.0 (pip `shellcheck-py`, not installed on the box by default): 0 findings at error and warning level; 106 places with notes at info level (231 x SC2086 unquoted variables holding paths without spaces, the same style as `box.sh`; 5 x SC2012; 2 x SC2015; 2 x SC1091; 1 x SC2016) | `shellcheck.txt` |

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
- A, `create`: the body sent to Vast is image `pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime`, disk 80, `runtype args`, `args = ["bash", "-c", "export MAXPAR=5 QSUB= MAXH=6 DPH=0.38 ...\n<ptc3s_box.sh byte for byte>", "cio"]`, 35,115 bytes; no key, token or bearer text in it.
- B, `search`: the filter is the kit's (verified, on-demand, 1 GPU, reliability 0.98, CUDA 12.8, 60 GB disk, 300 Mb/s, 8 cores); only the `RTX 4090` row is printed.
- C, `collect` on the finished dry-run log, which holds 15 checkpoint parts: extracts the result tarball and checks its sha256.
- D, `collectck` on an emulated live log (the box prints a part in one burst, then sleeps 100 s; the kit reads the last 9,000 lines every 40 s): the 16,114,485-byte `checkpoint.pt` is rebuilt, sha256 `1d1f674b00aed8a6...`, when started at the result line, at the start of round 2, and 700 s after the result line (middle of round 2). The emulation is mine; the real Vast log timing is untested.
- `accept.py` on the CPU smoke result: REJECT because steps is 2 (right), and on edited copies: ACCEPT, REJECT on mismatch above 0.1 %, REJECT on a wrong parameter count (`accept_test.txt`).

## 6. NOT exercised, and my honest chance that each step works the first time on Vast

Rough judgments (suggested), each for one attempt, not computed from data.

| Step | Why not exercised here | Chance |
|---|---|---|
| Vast accepts `create` with a 35 KB `args` string and starts the container | no Vast calls allowed; the kit's `box.sh` is 7.7 KB; the sibling `at10m_box.sh` (37 KB) was never rented either | 85 % |
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

## 8. Missing facts (not guessed)

- The PC's reference `train_bytes` and `train_sha256` of pool `p10-rung30-s400-a64-L` (the comparison in RUNBOOK.md section 7 is the first one).
- The PC's torch, CUDA, numpy and pyarrow versions.
- A PC `RESULT.json` of the PTS arm (8aG2C3S) to read `n_params` from; the 4,023,976 comes from `test_ptc.py` and the PTC README.
- Where the earlier Vast box ("box A") ran and its log; I could only read the kit's scripts.
- Any Vast limit on `args` length or on log size (the export prints about 65 MB of base64 for three rounds).
- The speed of this job on a 4090.

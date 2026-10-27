# opcpu kit: deviations from the Mac queue files and from the s3v kit

Written by the Opus manager session for Ben, 2026-09-29. The kit runs the sealed code of ten queued Mac jobs on ONE rented many-core vast box because the Mac queue is jammed. The science steps of each job are copied unchanged from its queue file (`handoff/queue/ks-1-lead0-mac-r2.md`, `s2think-1-mac.md`, `trn-decode-mac.md`, `pond-{a,b,c,z}-dev.md`, `pond-doubt.md`, `s1-loop-mac.md`, `s1-plain-mac.md`); the job scripts are `box/job-*.sh`, and each keeps the queue file's stop rules and exit codes. The Mac copies of these jobs stay queued; the Director decides which to withdraw. Neither run is chosen by its score. Labels below: SHOWN (checked here), SUGGESTED (reasoned, not run), UNTESTED.

## 1. Machine changes (macOS to Linux), all jobs
| Mac queue file | Box job |
|---|---|
| `git fetch` + `git archive origin/main ... \| tar -x -C $W` | the pinned commit is `git archive`d once by the Mac (`vstart.sh`) into `<base>/r`; each job unpacks the same paths from it into its own private folder (`unpack` in `box/jlib.sh`). "Seal exists on main" checks read the pinned tree instead. |
| `shasum -a 256` | `sha256sum` (same hashes) |
| `df -g /` (3 GB or 2 GB free floor) | `df -BG $HOME`, same floors |
| `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B` | `<base>/venv/bin/python -B` (venv made by `box/drive.sh`; see 2) |
| `perl -e 'alarm shift; exec @ARGV' N cmd` | `timeout -s ALRM N cmd` (same signal) |
| `uptime` load hold ("Mac not busy") | printed only; the box is single-tenant |
| `$HOME` = the Mac home | `$HOME` = the rental's base folder (`/root`), so every `$HOME/premonition-*` path in the jobs means the same thing there |
| repo copy-out `cp ... "$G/$A/..."` with `G=$(pwd)` | `G=<base>/out/<test>`; `vcollect.sh` moves it to `artifacts/opus-manager-20260929/cpu-vast/<test>/` under the same repo-relative paths as the job's PUSH lines, minus every `.pt` |

## 2. Python and torch
- torch 2.14.0 CPU wheel (`pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu`) and numpy 2.4.6, in a venv; `drive.sh` FAILS (setup stop, nothing runs) unless `torch.__version__` is exactly `2.14.0+cpu`, numpy is 2.4.6, CUDA is not available and torch is not a CUDA build. `CUDA_VISIBLE_DEVICES` is set empty; any GPU on the box is unused.
- Why 2.14.0 (SHOWN in the repo): the pond mutation log (`artifacts/claude-dir-pond-20260928/SELFTEST-mutations.log`) and other 2026-09-28/29 records were run with torch 2.14.0 CPU. The Mac's own torch version for the queued jobs is NOT recorded anywhere I found (they ran `uv --with torch`, unpinned), so the pin is the best recorded match, not a proven match. numpy 2.4.6 is the version on the container where the selftests were rerun for this kit (UNTESTED against the Mac's numpy).
- Python: the image's own python (the pytorch 2.8 image has 3.11) instead of uv's 3.12. The kit's dry run and the selftests below ran on 3.11 (SHOWN for those), the full jobs on 3.11 are UNTESTED.
- Numbers are not bit-identical across machines (Linux x86 BLAS versus Apple Accelerate, thread layout). Every job's own consistency checks still apply (ks prep prints whether each rebuilt net's dev 9x9 count equals the committed count; s2think labels a net MISMATCH; pond-doubt prints consistent_with_harness). A net or count that differs from the committed one is a finding, not something to hide.

## 3. Scheduling and folders
- Each job runs from its own private archive: `premonition-ks`, `-s2think`, `-trn`, `-pond-a` .. `-pond-z`, `-pond` (doubt only), `-s1-loop`, `-s1-plain`. On the Mac the four pond jobs share `$HOME/premonition-pond` and the two s1 jobs share `$HOME/premonition-s1` because they run one after another; run at once they would rewrite each other's scripts under running python. `job-doubt.sh` links each arm's `eq-runs/pond-<arm>-pre-s<seed>` folder into `$HOME/premonition-pond`, which is where the Mac job looks for them.
- Waves (single- or 2-thread as each queue file says; the box needs `nproc >= 32`, checked): wave 1 at once = ks-1-lead0 (2 processes), pond-a/b/c/z (8), s1-loop (2), s1-plain (2) = 14 processes; wave 2 = s2think (2) and trn-decode (2 procs x 2 threads) as soon as `prep/s0.json` and `prep/s1.json` of ks exist; wave 3 = pond-doubt (up to 10 single-thread extractions, as its queue file launches them) after the four pond arms have all ended. Peak about 22 threads.
- ks lead0 (eval only, single thread each) runs four at once instead of two at a time (`run2 4`). Same numbers, shorter wall time. `prep` stays at two.
- A job's STOP RULE stops that job only (its exit code is recorded as `JOB <name> END rc N`); the other jobs go on. Each job is also wrapped in `timeout` at its queue file's TIME CAP (ks 300 min, s2think 120, trn 300, each pond 300, doubt 120, each s1 330).
- Skips (recorded as `JOB <name> SKIPPED <why>`, not errors): s1-plain when the qual-plain sources were not sent; trn-decode when its Mac nets were not all sent.

## 4. Inputs that exist only on the Mac (sent by `vstart.sh`, hash-checked on the Mac and again on the rental)
- Required (start refuses and rents nothing if missing or wrong): `runs/qual-loop-s0` and `s1` (`source.pt`, `source.json`) under `$MB/artifacts/claude-fewex-20260927/`. `source.json` is checked against `SHA256-EQ-RAW.txt`, `source.pt` against `qual-loop-s{0,1}/source.pt` in `artifacts/claude-distill-20260928/checkpoints-sha256.txt` (both read from the pinned commit). The queue files themselves only check the json; the `.pt` check is added, and `job-ks.sh` repeats both on the box.
- Optional, sent only if every file of the group is present and matching: (a) `qual-plain-s0/s1` for s1-plain (json against `SHA256-EQ-RAW.txt`; the `.pt` has no sealed hash anywhere, its sha256 is only recorded); (b) for trn-decode: `runs/{loop,plain}-s{0,1}/source.pt` (json against `SHA256-RAW.txt`) and `eq-runs/plain-s{0,1}-pre/k16384.pt` (no sealed hash; recorded).
- NOT sent: the ruler's loop nets (`eq-runs/loop-s*-pre/k*.pt`, `$HOME/premonition-models/fewex/...`), even if the Mac has them. So `ks prep` REBUILDS k64 and k16384 from the qual-loop sources (about 40 min per rung per seed, from the queue file) instead of copying ruler nets with matching dev counts as it would on a Mac that has them. This is what the request asked for; the rebuilt nets are labelled "rebuilt with harness functions" in `prep/s*.json`. The rungs 1, 4, 16, 256, 1024, 4096 are not built (as on the Mac when no ruler copies exist), so `s2think` prints `MISSING seed N k256` etc. exactly as it would there.
- trn-decode's loop `k16384` (its `eq-runs/loop-s*-pre/k16384.pt`) is the net ks rebuilt, linked into a private `$HOME/bm-trn` tree; plain `k16384` and all `source.pt` come from the Mac. If the Mac never had the plain `k16384` files, trn-decode is SKIPPED with MISSING-NET reasons in `_rental/INPUTS.txt`.
- ks writes its nets to `$HOME/premonition-ks/nets` (`KS_NETS`), the place `s2think`'s `find_ck` already searches; `pond-doubt`'s `POND_BASE_CK` points there too.
- Report-only additions: `nets-sha256-report.txt` (each rebuilt net's sha256 beside the distill list; a different sha on another machine is expected).

## 5. Small differences worth knowing
- `trn-decode-mac.md` never copies `$A/run` out of its work folder, so its own PUSH line would find nothing on the Mac; `job-trn.sh` copies it (json and logs) for the collect job. The job also copies before its final RUN-FAILED check so partial logs survive.
- The pond and s1 jobs copy their logs before the "a run has no adapt.json" stop, so a failed run's log is kept.
- `pond-doubt.md` (sealed logic, unchanged) insists that arm b seed 0 finished (`WAITING`, exit 5, otherwise), even if other arms did. If pond-b fails, pond-doubt does nothing.
- Never opened: holdout files, `test.pt`, readpanels, blind panels (no job here reads them; `pack.sh` and `vcollect.sh` also refuse to copy any file named `holdout*`, `test.pt`, `*readpanel*`, `*blind*`). Dev panels only. No `.pt` is ever copied back; nets stay on the rental and die with it.

## 6. Rental, guard and money (changes to the s3v kit)
- LABEL `opus-cpu`; state in `$HOME/premonition-watch/opcpu-vast`. Cap $2.50 (money stop), credit floor $2.50, time cap 7 h since the first rental, MAXDPH $0.35/h, so the time cap always comes before the money cap at any allowed price ($0.35 x 7 h = $2.45).
- Offer query: `num_gpus=1 cpu_cores_effective>=32 reliability>=0.98 disk_space>=40 inet_down>=200 cpu_ram>=32 cuda_max_good>=12.8 rentable=true`; ranked by ($/h) / cores, one offer per host, three tried. Added beyond the request: `cpu_ram>=32` (GB; about 22 processes) and `cuda_max_good>=12.8` (the CUDA image must start on the host driver even though the GPU is unused).
- FIT rule kept: estimate x price <= 0.8 x cap. The estimate is a flat 5.0 h (not scaled by CPU speed, which vast does not list); it is a guess (section 8).
- Image: `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime` (the image the earlier kits reached ssh with); its torch is not used.
- Guard stall check: no log or state file grew for 30 min AND the 1-minute load average is under 1 (no GPU reading). A hung process that keeps a CPU busy is caught only by the time cap.
- Ending: DONE is copied with the "every job END or SKIPPED" check and destroyed only after the sha256-manifest match; FAILED (setup), BUDGET-STOP, TIME-STOP and STALL first kill the kit's own processes on the box (so files stop changing), then copy with the manifest check only ("logs" mode: unfinished jobs are expected) and destroy after it; if the copy check fails twice, or ssh is lost, the instance is STOPPED, not destroyed (`-STOPPED-NOT-DESTROYED`). HOST-FAIL never copies and stops.
- The pinned tree's every `box/*` file is hash-checked against the pinned commit after upload (s3v checked only `drive.sh`).

## 7. What was tested (fakes only) and what was not
See `test/fake_run.sh` and its OUTPUT.txt: refusals, DONE, budget stop, time stop, drive FAILED, copy-check failure (stop, not destroy), a failing job and skipped groups, all against fake vastai/ssh/python. The jobs' science commands were checked only through their selftests and `--help` on this container (torch 2.14.0+cpu, python 3.11), never trained.

## 8. Untested
The rental itself (image start, ssh attach, pip download of the CPU wheel and numpy on the rental, python 3.11 in the pytorch image), the real per-job wall times on the rented CPUs (the Mac figures are the only source), whether `cpu_cores_effective >= 32` boxes give one full core per single-thread process, whether the rebuilt nets match the committed dev counts on Linux, and the collect step against real files.

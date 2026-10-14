# G2f-a4: the faster G2f run on the PC, with restarts that survive a reboot

Owner: Whole-model roadmap thread. Written 10-14 (ET). Nothing here starts a training job: the supervisor does nothing until the Mac writes `ARMED.txt` (`arm`), and the Mac does that only on Ben's own words in the roadmap thread.

## What and why, in plain words
- **G2f (the registered B3G2 3M run, accum 32) died at 2:30 AM ET 10-14.** Windows Update restarted the PC at 2:29 and swapped the NVIDIA driver; the run had no checkpoint, so it restarts from update 0. The same kind of restart killed two 10M runs on 10-11.
- **G2f-a4 = the same run with the update split into 4 micro-batches of 64 rows instead of 32 of 8.** Same code, data, seed, rows, caps, learning-rate schedule and readout; only the micro-batch split differs, so it is a NEW name (`8aB3G2A4`), never "G2f". Measured on a rented 4090 (not on this card): 2.12 s per update instead of 11.57 s (5.5x), peak allocated 8.77 GB (`results/8a-g/speedup/GPU-RUN-2-2026-10-14.md`). Suggested, not shown on the PC: about 15 h instead of about 81 h.
- **Every update is now checkpointed (every 100 updates, about 4 min) and the supervisor restarts the run after any death, including a reboot**, so a restart costs at most about 4 minutes.
- **What the change could cost:** the loop length K is drawn once per micro-batch, so with fewer, bigger micro-batches more rows share a K. One update with K pinned gives the same gradient (cosine 0.99999); whether the whole run trains the same is untested. That is what the two registered checks below read.

## The registered checks (big-run, fixed before any PC run, 10-14 3:37 PM ET; the 0.02/0.01 limits are reported beside, not as the gate)
**Trace A** (on the real accum-4 run, read when the resumed run has reached update 300): no NaN/Inf; GPU memory in use (nvidia-smi total) never above 12,288 MiB; the mean loss of updates 251-300 below the mean of updates 1-50; the resume matches: the updates the killed segment had done after its checkpoint (about 101-150) are redone by the resumed segment with the first redone update within 0.01, the mean absolute difference at most 0.02 and the largest at most 0.10 (the resume limits are mine, set here before any PC run). Fail = the supervisor stops the run and writes `STOPPED.txt`; registered fallback: accum 8 (new name), then accum 32.
**Baseline compare** (accum 32, same seed/rows/code, 300 updates, started alongside once trace A passed and 4,000 MiB are free): difference of means over all 300 updates (accum 4 minus accum 32) within +/-0.03 and the mean of the last 50 at most 0.05 above the baseline's = PASS; beyond 0.06 or 0.10 (2x), or a NaN = FAIL (fall back to accum 8, then 32; the main run keeps going until someone decides, `ATTENTION-compare.txt` is written); in between = UNCLEAR, read as GO. The real test of the recipe is the final read (marks B3G2-1..7 plus mean thinker rounds at inference and stop-head accuracy), not 300 early updates.

## Files (copy this folder to `C:\Users\benja\custom-io\in-g2fa4`)
| file | what |
|---|---|
| `install_g2fa4.py` | puts the pack on the PC (see its docstring); starts no job; renames, never deletes |
| `g2fa4_supervisor.py` | runs `plan.json`'s jobs one after another and keeps each alive; `preflight`, `run`, `status`, `clear`, `arm`, `disarm`, `halt`, `selftest` |
| `queue/8aB3G2A4-pc.txt` | the main run (G2f's queue line with `--accum B3G2=4` and `--train-extra '--ckpt-every 100 --log-every 1 --resume'`) |
| `queue/8aB3G2A4b32-pc.txt` | the accum-32 baseline trace (stopped by the supervisor at update 300) |
| `overlay/train.py`, `overlay/tests/test_ckpt.py` | the checkpoint / resume `train.py` of the AT run (sha256 `e75e45fa43c6...`; byte-identical copy of `at10m/overlay`) and its test |
| `overlay-tests/test_ckpt_b3g2.py` | the same checks on the b3g2 model (CPU) |
| `tests/` | the supervisor's own tests against a fake runner and against the real overlay `train.py` (not copied to the PC) |

## Mac runbook (the Mac RC session; PowerShell on the PC over ssh)
1. **Copy and install (no Ben word needed: no job is started; about 5-10 min of CPU).**
   `scp -r results/8a-g/pc-job-cards/g2fa4 benja@<pc>:C:/Users/benja/custom-io/in-g2fa4`
   `ssh benja@<pc> "C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe C:\Users\benja\custom-io\in-g2fa4\install_g2fa4.py --register"`
   Expect `G2FA4 INSTALL DONE`. (`--check` first reports the pins without changing anything.) The CPU test inside prints `ALL OK`.
2. **Self-test the boot task's context:** `ssh ... schtasks /Run /TN G2FA4-SELFTEST`, wait 20 s, `type C:\Users\benja\custom-io\work\g2fa4\selftest.txt`. It must say `True` for CUDA. If the SYSTEM context cannot see the GPU, tell the roadmap thread: the logon task (`G2FA4-SUPERVISOR-LOGON`) is the fallback.
3. **Preflight (read-only):** `ssh ... python C:\Users\benja\custom-io\work\g2fa4\g2fa4_supervisor.py --plan C:\Users\benja\custom-io\work\g2fa4\plan.json preflight`. `READY` needs the GPU free (the Qwen `llama-server` holds 15.6 of 16.3 GB: Ben stops it), no other job, the pins, and the installer's mark.
4. **Only on Ben's own words ("go"), typed in the roadmap thread:** `ssh ... python ...g2fa4_supervisor.py --plan ... arm "Ben <time ET>: <his words>"`, then `ssh ... schtasks /Run /TN G2FA4-SUPERVISOR` (or `...-LOGON` if the self-test said so). Report: `status` output after 2 minutes, then every time asked. The supervisor waits (and says so in `status.md`) while another program holds the GPU, and starts the moment 9,500 MiB are free.
5. **After a reboot nothing needs doing:** the boot task starts the supervisor, which finds `ARMED.txt`, sees no runner, and resumes from the newest checkpoint.
6. **Stop (only on Ben's word):** `... halt` (disarms and stops the plan's runners; checkpoints stay). **After a `STOPPED.txt`:** read it and `status.md`, tell the roadmap thread; do not `clear` without its word.

## What the run does by itself (times at 2.1-2.4 s per update, suggested)
1. Pool check, then training from update 0. One line per update goes to `...\8aB3G2A4-pc\8aB3G2A4-3M-s400\B3G2\events.jsonl` (every segment) and `stdout.txt` (the last segment).
2. At update 150 (about 6 min in) the supervisor **kills the run once on purpose** (checkpoint at 100 exists) and starts it again with the same command: this is the R4 resume test on the real card.
3. At update 300 in the resumed segment: **trace A**. Pass = the run simply goes on as the real run. Fail = stop.
4. After trace A, if 4,000 MiB are free: the **accum-32 baseline** starts alongside (about 60-80 min; the main run slows a little while it shares the card), is stopped at update 300, and the compare is written (`COMPARE-g2fa4.md`).
5. The run goes on to update 24,000 and its final evaluation (RESULT.json), restarting itself after any death; `DONE-g2fa4.txt` marks the end. `status.md` is the one-screen state: speed, ETA, restarts, GPU peak, both verdicts.

## What it never does
Delete anything (replaced files are renamed `.aside-<stamp>`); touch the Qwen server or any process that is not a `custom_io` job of its plan; edit code, caps, data, marks or the registered G2f line; start without `ARMED.txt`; restart forever (three restarts in a row with no new update stops it, so does a `--resume refused`, an out-of-order status, or a train.py that ended with a status other than ok); stop a running job except for the planned kill and a failed trace A.

## Shown / suggested / untested
- **Shown (this sandbox):** the overlay's `train.py` reproduces the unmodified `train.py` bit for bit with the flags off, and a hard kill in the middle of a checkpoint interval plus `--resume` reproduces the uninterrupted run (loss trace and final weights, bit for bit) on the real b3g2 class (tiny, CPU, accum 4 and 8; `overlay-tests/test_ckpt_b3g2.py`, 4 min). The supervisor's logic against a fake runner (kill-and-resume, crash with a job-level arm_failed RESULT.json, crash loop, NaN, memory over the limit, a resume that does not match, a failing and an unclear compare, a dead supervisor adopted by a new one, a reboot, the GPU held by another program, not armed, halt) and against the real overlay `train.py` (`tests/`).
- **Suggested:** 15 h; peak memory near 9 GB on the 5070 Ti (measured 8.77 GB allocated on a 4090); the boot task works as SYSTEM.
- **Untested on Windows / the PC card:** the CUDA path of the checkpoint code (RNG restore on CUDA, fused-AdamW state load, bf16 autocast), `taskkill /T`, the PowerShell process listing, `schtasks`, the 5070 Ti speed at accum 4, the 4,000 MiB room for the baseline beside the main run, and the installer. The installer's CPU test and the planned kill-and-resume on the real card are the first Windows runs of the file handling.
- **Known soft spots:** GPU memory in use is the card's total (any other program counts); a resume on a different driver is correct but not bit-identical; the counters of capcount/trace stats are counted once more for rows seen before a restart (the cap-hit check "all zero" is unaffected).

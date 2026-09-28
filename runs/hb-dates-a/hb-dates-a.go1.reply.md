Sealed GPU protocol — verifying hold conditions and seals before any training.
This worktree lacks the sealed artifacts — pulling the task spec and seals from origin to check hold status.
Hold released for BensPC — checking for in-flight runs and GPU availability.
GPU is reserved for this job and idle — setting up the sealed tree on BensPC.
BensPC has no repo clone — streaming the sealed tree from this Mac instead.
Direct streaming failed — switching to file copy.
HB seal passes 4/4 and the imported Block matches — fetching the remaining sealed reference files to complete the check.
Seals fully verified — running the CPU selftests.
CPU checks pass with matching panel hashes — running torch selftest and timing.
Torch selftest fails on the loop arm — confirming details before stopping per protocol.
Verdict: STOP — sealed-code failure at step 3, nothing trained, holdout never opened.

What happened, with counts:
- SEAL-hb: 4 of 4 lines OK on BensPC (`kinds.py`, `run.py`, `marks.py`, `PASSMARKS.md`).
- SEAL-code: 20 of 20 lines OK (all 8 scripts incl. `claude_rsn358a_run.py` OK; see deviation 1 for the other 12).
- CPU checks: 2 of 2 pass. `kinds.py selftest` prints `selftest ok (1500 generator/checker items)`; its dev and hold panel-sha lines match the reference `SELFTEST-kinds.log` 4 of 4. `marks.py selftest` prints `selftest ok`.
- Torch selftest: 1 of 2 arms. Plain prints `selftest ok plain: 6381303 weights`. Loop fails twice identically: `AssertionError: ['halt.weight']` at `scripts/claude_dir_hb_run.py:280` (dead-gradient assert in `selftest`). Env: BensPC RTX 5070 Ti, torch 2.11.0+cu128, CUDA True, venv Python 3.10.9.
- Timing: 0 of 2 arms run. Training: 0 of 4 nets, 0 steps. Dev evals: 0. Gate: never run. Holdout panels: 0 opened, 0 items read.

Deviations (2, both reported, no code touched):
1. Step 1's literal archive command omits the 12 artifact files listed in `SEAL-code.sha256.txt`, so "every line OK" could never pass with it. I additionally archived those 12 paths from the same `origin/main` commit and re-extracted; then 20 of 20 OK. The 8 script lines (the ones the nets import) were OK even before this.
2. `git archive | ssh benspc tar -x` fails (PowerShell mangles the binary pipe). I wrote the tar locally, `scp`d it over, and extracted on BensPC via git-bash. Same bytes — seals verify.

Cleanup and state:
- No duplicate run was going (Mac `pgrep`: no hb match; BensPC: only 2 idle `pythonw` from 09-23, GPU util 0%).
- `GPU-BUSY.txt` names this job (`hb-dates-a` since 21:35:56Z), so per the header I proceeded; left the file to the watcher.
- Removed BensPC `hb-dates-W` and both tar files by exact path and confirmed gone; removed local tars. GPU was never loaded beyond the selftests.
- Retrieved `SELFTEST-kinds-run.log` (6 lines, ok) to Mac `/tmp/hb-SELFTEST-kinds-run.log`; committed nothing.

What it means in plain words: the loop net has a learned "stop" switch, and in the one-step check that switch gets zero learning signal, so the validity gate (V2: every weight matrix learns) fails for the loop arm. Training now would prove nothing about loop-vs-plain, so I stopped without patching, per the sealed-code rule. What remains: helper HB needs to fix the loop selftest/code in a new sealed version; then steps 3–9 can run. The holdout is untouched.

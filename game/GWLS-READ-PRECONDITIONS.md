# GW-LS sealed read: the run's preconditions, fixed before the Q115 re-review (written 2026-10-18T07:52:31Z)

Under coordinator ruling Q115, a review finding holds the read only if it could actually corrupt **this one read** as specified here.
Everything below is checked and printed again immediately before the read fires, and the read is aborted if any item differs.

- **Read code:** commit 8680fb335 (the P1-P6 fixes). The one command, run once, by this session (single operator, single invocation), from
  the repo root, with no `-O` and `PYTHONOPTIMIZE` unset (verified unset):
  `PYTHONPATH=. SCRATCH/venv/bin/python -m game.gwls_final --root SCRATCH/gwls`
  - SCRATCH = /tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad.
  - The default persist dir is `game/results/gwls`. The play path is used, not `--analyze-only`.
- **Training finished:**
  - both seeds: `state.pt` k = 8; no round > 8 file;
  - no process whose command line contains `imitate`;
  - `/proc` mounted `rw,relatime` with no hidepid; running as root.
- **Inputs (sha256):**

  | file | sha256 |
  |---|---|
  | `gwls/s200/checkpoint-iter8.pt` | 5766b9a0005e0a1e561c4c0c5205f24fa9a7c777c615290c187bd6441c299c59 |
  | `gwls/s201/checkpoint-iter8.pt` | 2a66f40fb4e942bb4c6c58ee5be21ca9501106de288101c777706d4071246adb |
  | arm C s200 `glprobe/s200/n64000/score-sample.json` | 516f7329d74486d74075243217ee4e62559b92316efed9fad47a0c470ab631dc (= the record) |
  | arm C s201 `glprobe/s201/n64000/score-sample.json` | 4ec56fd9b260d04d38c3a9dd57c25c9c679e7b11167936caf9e6da7e6522f7f1 (= the record) |
  | `game/constants.json` | 700a1845cd60c8f2b78b17204690976a0db4350b6e02314a9b870633ebe41081 (explore 0.10, episode_cap 1000) |

- **Nothing from a previous read exists** in SCRATCH/gwls or `game/results/gwls`: no score-sample.json, no lock, no read-record.json,
  no final.json.
- **The gate:** `--dry-run` reads "all preconditions hold", round-4 branch CONTINUE. Sealed marks are unchanged
  (`game/WALL-SOLVE-RESULT.md`, section 3).

## Amendment (Q118): launch mode, written before firing
The one command is launched **detached**, never in the foreground, so no tool time limit can kill it after the start record is
written (the read takes about 13-14 min):
`cd <repo> && env -u PYTHONOPTIMIZE PYTHONPATH=. setsid nohup SCRATCH/venv/bin/python -m game.gwls_final --root SCRATCH/gwls > SCRATCH/gwls/final-run.log 2>&1 < /dev/null &`
- **Monitoring:** a background waiter, with no foreground wait on the scorers.
- **Re-checked at fire time and printed into the log of this session before launch:**
  - every item above (sha256 of the inputs, constants, no prior read artifacts, no `imitate` process, /proc visibility, `PYTHONOPTIMIZE`
    unset);
  - `--dry-run` reading "all preconditions hold".
- **Abort:** the launch is aborted if any item differs.

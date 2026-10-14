# BensPC status, 2026-10-16 06:34 ET
PC: reachable
GPU: 23% use, 2240/16303 MiB, shared 0 MiB, 40 C | GPU-BUSY: free (file absent)
Disk C: 139.5 GB free

## Jobs
- b3g2 (Whole-model roadmap thread for the big-run thread): failed. Queue 8aB3G2s400-pc ended 10/14 02:30 ET ("queue 8aB3G2s400-pc done"). Arm 8aB3G2s400-3M-s400 RESULT.json says "status": "arm_failed" (re-read this check); no custom_io process running; next queue 8aB3G2s400b not started, GPU idle about 52 h. No action taken: the card's restart covers CUDA out-of-memory only, and its crash rule says report only.
- 8aB3G2A8 (owner unknown, no card): not running (no GPU process in pc-check). Last result file 10/15 15:18 PC time. Not re-read this check. NEEDS ATTENTION. No action taken.
- 8aB3G2A4 (owner unknown, no card): not running (no GPU process in pc-check). Last result file 10/14 17:30 PC time. Not re-read this check. NEEDS ATTENTION. No action taken.

## Needs attention
- b3g2: arm 8aB3G2s400-3M-s400 (seed 400, rung 3M, B3G2) ended "arm_failed" at 10/14 02:30 ET after 24000 steps. The error text could not be re-confirmed this check (grep of the queue log found 0 "out of memory" and 0 "CUDA error" lines; pc-check saw a Traceback in the log tail; last status recorded "CUDA error: unknown error" in layer_norm). Either way it is not an out-of-memory restart, so the card does not cover a rerun. -> Owner decides the cause (driver or GPU fault possible; Windows event log not queried), whether to write a new card and rerun, and whether the chain resumes. Also: the card's stall_check path is wrong (it names results\Q-pc\, but the real folder is results\8aB3G2s400-pc\), and a stale copy pc-jobs\done\b3g2.md (10/12) sits beside the live card pc-jobs\b3g2.md -> owner fixes the stall_check path and removes or relabels the stale copy (not deleted by me).
- 8aB3G2A8: no card; not running; trace A failed earlier (per last status). -> Owner decides the cause, then whether to run "python g2fa4_supervisor.py clear g2fa8", and writes a card before any rerun.
- 8aB3G2A4: no card; not running; trace A failed earlier (per last status). -> Owner decides the cause, then whether to run "python g2fa4_supervisor.py clear g2fa4", and writes a card before any rerun.

# lis-320 ADDENDUM-6: the opencode route with reasoning effort "low"; diagnosis verdicts; pilot 4
# (written before pilot 4 exists; no lis-320 training row or reader read exists)

Written 2026-09-26 22:03 UTC by the reading thread.

## Diagnosis verdicts (builder-outbox)
- ocdiag (1f792bfed): 12 calls one at a time, default thinking: 10 exit 0 in 88-263 s, 2 timeouts at 300 s, no tool use.
  "> build · glm-5.3-flash" is opencode chrome, printed on successes too; it was never the error.
- ocdiag2 (9a9b6c4aa) against the mark fixed at 21:19 UTC in ANSWERS-TM-2118.md (helper v1.1 parses 2 of 2 sequential and
  at least 3 of 4 parallel calls, median under 240 s). I meant the median of the parallel calls, since the mark was about
  running in parallel. Parallel v1.1 times were 156.9, 457.7, 404.7 and 71.3 s: median 280.8 s. 4 of 4 finished and
  parsed, but the builder did not enforce the 300 s cap there; under v1.1's real 300 s timeout only 2 of 4 finish
  in time. Verdict: FAIL (median and the within-300-s count both miss). Sequential v1.1 2 of 2 and v1 2 of 2 (report only).
- Pilot 3's exit-1 bursts (helper v1, 4 workers, Mac load near 185): not reproduced at loads 22-87; cause unknown.
- ocdiag3 (a5a07655c): opencode offers variants low / high / max for opencode-go/glm-5.3-flash (low = reasoningEffort
  low). With --variant low the same 4 prompts parsed 4 of 4 in 5, 10, 15 and 15 s with 0-9 reasoning tokens. The long
  default thinking explains the 88-460 s calls.

## The change: --variant low, which is a return to pilot 2's setting
Pilot 2 (passed) ran on OpenRouter with reasoning effort "low". The opencode default is a higher effort. Setting
--variant low returns the route to the reasoning setting pilot 2 passed with; it is not a new change to the wording
recipe. Temperature and max tokens remain the route's defaults (ADDENDUM-2). New file scripts/claude_lis320_glm_oclow.py
is helper v1.1's call() with "--variant low" added to the run line (selftest checks the exact command); the helper
itself is not edited. The data-quality check stays where it is: pilot 4's parse and threshold counts, not these 4 prompts.

## Pilot 4 (fixed now, before it runs)
handoff/queue/lis320-pilot4-mac.md: seeds from claude_lis320_seed_cr.py, seed 323, 60 dialogs, --ask-back, same avoid
lists; wording through claude_lis320_glm_oclow.py; claude_lis320_rawcheck.py, claude_lis320_check_cr.py and
claude_lis320_style.py. Before any wording call: the seal files check, Trustworthy notes' claude_glm_leakcheck.py (exit 0),
and a count N of running `opencode run` processes on the Mac (every thread); workers = min(6, 16 - N), waiting while
that is below 1.
Pass (all of): PILOT-THRESHOLDS items 1-5 (every family including correct_ref at 40% or more of its turns kept; item 5's
hand read by a fresh agent that has seen no pilot rows); at least 54 of 60 dialogs parsed; at most 6 of 60 dialogs failed
or timed out; rawcheck OK. If it passes, the full run (seed 324, same wrapper and settings) is queued in chunks.
If it fails, one thing changes, it is named, and pilot 4 is re-run on seed 325.

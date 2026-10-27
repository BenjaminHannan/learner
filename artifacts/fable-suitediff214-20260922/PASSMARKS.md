# Exp 214 PASSMARKS — SHARED SUITE-DIFF TOOL (sealed BEFORE any registered run)

Tool: `scripts/fable_suitediff.py`
Usage future pieces will copy:
`python -B scripts/fable_suitediff.py --agent <scripts/fable_loopXXX_agent.py> --config <config json> --base <138h|138i> --out <dir> [--only rt136|rt143|sessions152|bench|marks123|all]`

Bases: 138h = artifacts/fable-agent138h-20260922/, 138i = artifacts/fable-agent138i-20260922/.
V3 wrapper (scratch-only, outside scripts/): artifacts/fable-suitediff214-20260922/wrap214_boss.py
(appends " (test)" to the last reply line of any turn whose input contains "boss"; writes untouched).

## V1 reproduce (P214.1)
`--agent scripts/fable_loop138i_agent.py --config artifacts/fable-agent138i-20260922/loop138i-config.json --base 138i --only all`
(all = rt136, rt143, sessions152, bench, marks123-subset p4+q1+bench+rt81):
0 moves on every suite (replies and stored triples identical per case).

## V2 second base (P214.2)
`--agent scripts/fable_loop138h_agent.py --config artifacts/fable-agent138h-20260922/loop138h-config.json --base 138h --only rt136,rt143,sessions152,bench`:
0 moves on every suite.

## V3 positive control (P214.3)
`--agent artifacts/fable-suitediff214-20260922/wrap214_boss.py --config artifacts/fable-agent138i-20260922/loop138i-config.json --base 138i --only rt136,rt143,sessions152`:
moved cases EXACTLY the 13 redteam136 inputs containing "boss" (pure-function count over suite inputs, case-insensitive substring):
C077 C078 C081 C082 C089 C095 C098 C099 C122 C129 C133 C136 C144.
All 13 classed reply-only move (rt136 verdicts are stored-based; writes untouched).
rt143: 0 moves (no "boss" in any teach/question). sessions152: 0 moves (no "boss" in any turn).
0 moves elsewhere. No new WRONG / WRONG-WRITE / junk writes outside this predicted set.

## V4 time (P214.4)
rt136 + rt143 + sessions152 + bench together < 900 s wall per agent, Mac CPU,
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, one suite at a time. marks123-subset time reported, no bar.

## Verdict rule
PASS iff V1-V4 all pass; any miss is FAIL with one diagnosis note.
Registered FAIL is recorded as FAIL, never re-run into a pass.

## No-tune sets (never opened, printed, or tuned on)
reading94, reading94b, artifacts/fable-naturalpanel208-20260922/.

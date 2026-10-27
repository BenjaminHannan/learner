---
name: revert-and-retry-line
description: Ben's 09-25 backtracking idea (revert to an old thought, go a different way): thread "Memory for its own thoughts", tests rv-385..391, state and agreements
metadata:
  type: project
  modified: 2026-09-27T17:18:00Z
---
Thread "Memory for its own thoughts" (cmsg_01FuvegZXjMmeUzStiEFVnEWJS3BsSnTqE3AZxNMeN97mY, session cse_01FzxESmJ1EoaDyNNZfyamFX).
- 09-27 17:16: rv-392 PASS on 358i2 (BensPC 174; RG vs RESTART hard grids7 55/36, 43/34, 48/33, 43/27); worker default = fresh starts with guesses. r0 solved 0 of every net's hard puzzles in all arms (its solves are day-pass-easy; note added to RESULTS-358i2). Results 3a1e6a05f. p2 not needed (told TM). No blind recount (usage rule). Nothing ready to launch.
- 09-27 16:48: rv-390 on 358i2: H PROVED WRONG, G PASS, I PASS. rv-391: no net signal -> W=16 NOT registered (hand-written). RESULTS-358i2.md b0cf10cb4.
- Ben 14:34 usage rule: only research, launching tests, reading results; no polling; TM msgs only verdict/launch/blocker <=8 lines.
- Ben 09-25 19:28: "revert to an old one with the old thread as an input, and go a different direction" = BACKTRACKING inside thinking, not a diary. Plan: design/v3/30-modes/384b-revert-and-retry.md.
- Verdicts rv-385..rv-391 dev: see [[revert-and-retry-verdicts]]. rv-391 CLOSED 09-27 (no net signal on 358i or 358i2; W=16 time slice not registered, hand-written). rv-393 pencil marks PROVED WRONG. Mac 358i nets: ~/premonition-models/rsn358i/claude-rsn358i-20260926/W/loop-sN/final.pt.
- GUESS is hand-written scaffolding (when/where by code; net gives symbol); a learned 'commit' output was proposed to TM (needs Ben's yes).
- rv-389 waits on Sleep research's 24 env.
- Any training: pin torch 2.11 or autocast cache off.
- Rental kit that worked: handoff/held/rent-rv390b-p1.md (BASH-ONLY vast, best TFLOPS/$, stop-not-destroy once a step started, manifest copy check). Patterns: [[benspc-bash-only-jobs]].
**Why:** a new session must not redo rv-385..388 or re-open the go-back trigger question without rv-391's measurement.
**How to apply:** check run/ folders on main for new raw results; count, blind-recount, one line to the Thread manager. See [[reasoner-thinks-until-done]], [[creative-egg-search-design]].

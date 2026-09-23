---
name: director-role
description: "2026-09-21 — Ben: 'You just keep managing the project… act as a muse agent director and thinker'; I direct, Muse agents build; board file + wake-up loop is the mechanism"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-22T02:06:20.991Z
---

Ben (2026-09-21 22:10): "You just keep managing the project. I encourage you to use as many muse agents as is helpful… act as a muse agent director and thinker."

**Why:** his Claude usage should go to thinking/verifying/deciding, not building; Muse Spark agents are unlimited and can run in parallel ([[mimo-skill]]).

**How to apply:** (1) Living board `design/v3/30-modes/00-director-board.md` (running / verified / next-up / blocked) — update on every wake-up; read it first after any compaction. (2) Never build myself; write one self-contained task file per problem (scratchpad `mimo/queue/NN-*.md`, runner `mimo/run1.sh`), launch in parallel, get woken by a waiter script + a ScheduleWakeup fallback. (3) On each wake-up: verify every landed report (seal from repo root, numbers from JSON, claims ≤ evidence), update board, dispatch the next wave — FAIL → one diagnosis-driven single-change follow-up; PASS → scale. (4) Report to Ben in short result-first summaries; questions that are truly his go on the board under "Open questions". Ben may switch the director session to Opus mid-run (asked 2026-09-21 23:18; I said fine): the board + memory are the handoff; keep the habits — claims ≤ evidence, one change per follow-up, re-run before believing an agent. Wake-up mechanism: `mimo/watch.sh` under the Monitor tool (30-min re-arm) + `.done` markers in `mimo/queue/`. Related: [[overnight-loop-directive]], [[minimize-usage]], [[explain-each-step]].

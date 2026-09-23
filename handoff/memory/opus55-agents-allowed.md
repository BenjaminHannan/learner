---
name: opus55-agents-allowed
description: 2026-09-22 15:08 — Ben: "You should use opus subagents now"; Opus 5.5 subagents are now the DEFAULT for all new work (builds, verification probes); Muse only finishes runs already in flight
metadata:
  type: feedback
---

Ben (2026-09-22 ~14:15, mid-run): "you can use opus 5.5 agents now".

**Why:** Muse agents keep making grading slips. 208 missed 2 junk saves, and 210 missed 26 junk "R of" saves plus router misroutes. Opus 5.5 is the stronger worker for jobs that need judgment.

**How to apply:** use Opus 5.5 subagents (Agent tool, `opus-medium` type with model `opus`) for judgment-heavy work:
- merges;
- design and data work (the relation table);
- demo-script dry runs;
- independent verification audits.

Keep Muse on OpenCode Go for routine single-change pieces. Opus agents get the same rules in their prompt, because there is no CLAUDE.md to carry them:
- additive only, new files with a prefix, no commits;
- fictional names only;
- the test panels (reading94/94b, the 208 natural panel) are off-limits;
- never write to the repo-root notebook/;
- no secrets.

I still verify every report myself (seal, post-seal edits, recount, my own held-out probe). Run independent agents in parallel. Don't spin up a fleet; spend Ben's Claude usage on high-value jobs. Related: [[director-role]], [[mimo-skill]], [[parallel-opus-build-20260921]], [[minimize-usage]].

**2026-09-22 15:08 update:** Ben: "You should use opus subagents now". New dispatches of every kind go to Opus 5.5 subagents (opus-medium, model opus), including routine single-change builds and the verification legwork (recount, held-out probes). Muse runs already in flight finish and still get verified. The main session keeps synthesis, decisions, seal spot-checks and the board. Keep watching Mac load, because Opus agents still run Python suites locally.

**2026-09-22 ~19:50 SUPERSEDED:** every Opus subagent died at ~18:25 on "You've hit your weekly limit · resets Sep 26 at 7am (America/New_York)". Ben: "Use muse spark 1.3 agents now from opencode". All delegated work (builds, finishing dead runs, graders, judges, panel writers) goes back to Muse via `mimo/rungo4.sh` ([[mimo-skill]]) until Ben says otherwise. Muse over-claims and slips on grading, so verify harder: recount every mark myself.

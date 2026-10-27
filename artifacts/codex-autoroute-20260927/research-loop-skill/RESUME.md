# Resume the registered work

State recorded during skill adoption on 2026-09-27. This is a snapshot, not live
progress. Read the current driver outputs for status rather than launching again.

- Worktree: `/Users/ben-hannan/.codex/worktrees/retention-isolation/beautiful-model`.
- AR1 is complete, independently recounted and fully published: FAIL (not proved
  wrong). Read `../RESULTS.md`; do not rerun or pool it with AR2.
- AR2 folder: `../hard_replay/`. Marks commit:
  `542f61b8c63e505ed02b881eb2216d57001ed1c7`.
- Frozen scientific HEAD: `b5a1dd133327c9c335781f25ac7859e06a50ba31`.
- Existing sequential driver PID 71079, executor session 36630, started
  2026-09-27 14:59:06 UTC. Twelve trajectories: two arms, seeds 61–66.
- At 15:19 UTC the first baseline was complete and candidate seed 61 was in C.
  This is progress only; no AR2 final verdict exists at this snapshot.
- Follow-up automation: `finish-registered-retention-experiment`. It already
  checks usage and progress, then performs the full recount, grading and report.
- First check account usage. Below 20% remaining, create only AR2's `STOP` file
  for its cooperative checkpoint/stop, report incomplete and remove follow-up.
- While healthy and unfinished: no duplicate driver, extra experiment, source
  edit or HEAD change. Other processes and the watcher are out of scope.
- After all twelve runs: record a new UTC/machine/PID RUN-NOTE, run the registered
  full recount once, require all raw scores and 7,200 checkpoint requests to match,
  then run the mechanical grader. Preserve any failure; do not revise thresholds.
- Publish AR2 and these new skill-integration files only after recount. Text first,
  checkpoint seed-pair commits next, with pull --rebase and normal push to main.
  Never change the uploaded skill, pushed marks or old evidence.
- Report in plain language with shown/suggested/untested distinctions; finish the
  follow-up. A later experiment needs a new registration before any run.

Read [APPLICATION.md](APPLICATION.md) for how the skill is adapted and
[HYPOTHESES.md](HYPOTHESES.md) for the research queue. Do not execute the bundled
`scripts/loop.py` against this repository: its default mutation policy conflicts
with the explicit project rules.

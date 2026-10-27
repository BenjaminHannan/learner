# Chat prompt: blank-count grid replay pilot (written 2026-09-27 21:43 UTC by the Thread manager)

Ben pastes the block below into a fresh cloud chat on BenjaminHannan/learner.

---

Goal: implement and run the two-arm pilot in reviews/handoff-blank-replay-2026-09-27.md (random versus blank-count grid replay), and return its registered verdict.

Read that file first. It holds Ben's instruction and the full handoff, word for word. Follow it exactly: smallest change, checks, freeze the protocol and decision rules, then the two-seed pilot. No new methods, no model change, no review round.

Repo facts:
- The handoff's code paths are artifacts/codex-autoroute-20260927/ (run_experiment.py, auto_model.py, RESULTS.md, hard_replay/) and scripts/claude_rsn358a_envs.py. scripts/claude_mirreview_grid_forgetting.py is NOT on main. Find where the blank-count forgetting numbers came from, or say they could not be traced.
- Compute: this container's CPU only, $0. Do not rent anything.
- Put everything in a new directory artifacts/claude-blankreplay-YYYYMMDD/ (date from `date -u`). Keep checkpoints outside the repo and commit only small files.

Project rules:
- Commit straight to main after `git pull --rebase`. No PRs, never force-push. Only add files; never edit or delete earlier experiments. Never touch the repo-root notebook/.
- Write every time in a file from `date -u`. Seal PROTOCOL.md and PASSMARKS.md, with their hashes, in a commit before any score exists.
- Stop processes by exact PID only. Never read or print keys or secrets.
- Don't edit the handoff. If something in it can't be done as written, write the problem into a dated ADDENDUM before training.

Report when done, plain words first:
- the verdict (ADVANCE, DEPRIORITIZE, INCONCLUSIVE or INVALID);
- the per-seed table from section 9 of the handoff;
- which old grids were lost;
- whether addition and maze learning suffered;
- the commit and file locations.

# Chat prompt: sleep that also matches the reasoner's own earlier answers (Thread manager, 2026-09-28T15:40:06Z)

Ben proposed at 15:29 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEWKNP4p4YPN7jpvkcSA9dnha) fake replays and distilling from the model
itself, possibly replacing stored replays. He chose "Distill in sleep" on the TM's card at 15:37 UTC. The TM checked on main:
on the equal-practice ruler, 2,048 maze updates with no replay drop the practised loop's old kinds to 0 of 200, and the
unchanged sleep (512 updates; each step 4 stored sums, 4 stored grids and 8 branch mazes, weights .25/.25/.5, CE on the true
answers; store 128 + 128) brings them back only to sums 149/155 and grids 99/86 after k = 64, and sums 76/83 and grids 90/100
after k = 16,384 (eq-runs/loop-s{0,1}-pre/adapt.json; scripts/claude_fewex_bench.py:208-226, claude_fewex_data.py:43-46).
Each sleep took 121-197 s. The harness saves every rung's net (claude_fewex_eq_bench.py:109 and :119, `k0.pt` and `k{k}.pt`); the files are local to
the chat that ran the ruler. The teacher (that chat's `k0.pt`, the practised source) scores 200 and 199 of 200 before mazes,
so matching only its final answers would be almost the same as the true-answer loss; the prompt therefore matches its answers
at every thinking round. Paste into the SAME chat that ran the equal-practice ruler. Everything below the line is the prompt.

---

Effort: high (Opus 5.5)

# Goal: test whether sleep keeps old kinds better when the loop also matches its own earlier answers, round by round, on the replayed puzzles

**Why (read this first)**
- Your equal-practice ruler showed that learning mazes wipes sums and grids to 0 of 200, and today's sleep brings the practised loop back only part way (RESULTS-EQ.md, cad73c0c3).
- Ben's idea: during sleep, the model should learn from its own earlier self, not only from stored answers. If that works well, it could replace most of the stored puzzles.
- Background (check before relying on it): Learning without Forgetting (Li and Hoiem, 2016) and Dark Experience Replay (Buzzega et al., NeurIPS 2020) report that matching a model's own earlier outputs protects old tasks, and that storing those outputs with replayed examples beats plain replay in their benchmarks (shown there, untested here).
- The teacher must be the model **before** the day's maze practice, your `k0.pt`. After maze practice, the model scores 0 of 200 on old kinds, so copying it would copy the forgetting.
- The teacher gets 200 and 199 of 200 on the old kinds, so matching only its final answers would add almost nothing beyond the true answers. So the student matches the teacher's answer at **every thinking round**, where the teacher is still unsure in early rounds (suggested).

**Start points (reuse, don't retrain)**
- The practised loop's saved nets from `eq-runs/loop-s{0,1}-pre/`: `k64.pt` and `k16384.pt` (after maze practice) and `k0.pt` (the teacher).
- If any file is missing, first re-run that ladder with the unchanged harness up to the needed rung. Check that its rung scores equal adapt.json exactly, and say so.

**Arms (each sleep: 512 updates, the harness's sleep otherwise unchanged)**
- **R128:** today's sleep, the control.
- **D128:** today's sleep, plus a teacher term on the stored sums and grids only.
  - For the rounds the student is trained on in that step, the frozen teacher runs the same puzzle for the same number of rounds.
  - The added loss is 1.0 × the mean KL(teacher ‖ student) over answer cells and over those rounds, at temperature 1.
  - The true-answer loss, the maze part and the .25/.25/.5 weights don't change. The weight 1.0 is fixed now; don't tune it.
- **W128:** today's sleep with the stored sums and grids losses doubled. This checks whether any gain comes from the teacher, or only from more weight on old puzzles.
- **R16 and D16:** R128 and D128 using only the first 16 stored sums and the first 16 stored grids. This asks whether the teacher lets a much smaller store work.
- Run each arm from both saved nets (after k = 64 and after k = 16,384), both seeds, and 3 sleep draws: the harness's own seed and two more fixed now. That's 60 sleeps of about 2 to 3 minutes each.
- No maze example is stored beyond what the harness already gives sleep. The teacher adds one frozen copy of the net during sleep only; disclose it.

**Marks (write artifacts/claude-distill-YYYYMMDD/PASSMARKS.md and commit it before any sleep runs)**
- A **cell** is one seed × branch: 4 cells in all. A cell's score is the mean over its 3 draws on the ruler's fixed old panel (200 sums4, 200 grids5) at the learned stop.
- **Validity:** R128 with the harness's own draw reproduces adapt.json's recorded sleep scores exactly. If not, report the difference and use your re-run as the control.
- **Pass:** M1, M1b and M2 all hold.
  - **M1:** on each old kind, D128 beats R128 by at least 20 of 200 on the mean of the 4 cells, and is higher in at least 3 of the 4.
  - **M1b:** on each old kind, D128 beats W128 by at least 10 of 200 on the mean of the 4 cells. If M1 holds but M1b fails, the verdict is "helps only as extra weight".
  - **M2:** in every cell, D128's 9x9 maze dev score after sleep is no more than 6 of 300 below R128's.
- **Smaller store (its own verdict):** D16 beats R16 by at least 20 of 200 on each kind, by the M1 rule. Report whether D16 comes within 6 of 200 of R128 on each kind in at least 3 of 4 cells, meaning a store 8 times smaller plus the teacher matches today's sleep.
- **Proved wrong:** D128 beats R128 by less than 5 of 200 on the 4-cell mean for both kinds. Then matching its old self adds nothing to replay with true answers, at this size.
- **Report only:**
  - The spread across the 3 draws.
  - The teacher's own scores.
  - The mean KL before and after sleep.
  - Rounds used.
  - The 7x7 and 11x11 maze panels.
  - A fresh old-kind panel (200 + 200, a new seed fixed now, checked for no overlap with the store) for every arm.

**Rules**
- New files only: scripts/claude_fewex_distill_*.py and artifacts/claude-distill-YYYYMMDD/. Import the harness and never edit it, the ruler's sealed files or the repo-root notebook/.
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push.
- fp32 on CPU, $0, no rentals. Run jobs in the background and don't poll.
- Training data stays code-made. The teacher's outputs come from the model itself, which is allowed.
- Times in files come from `date -u`. Stop processes by exact PID. Never touch secrets.
- Label claims shown, suggested or untested. Give counts as "x of 200" or "x of 300".
- A separate subagent does a blind recount from the raw JSON and the marks only.

**Done means**
- Marks, code, all 60 sleep records, RESULTS.md with the verdicts and the recount, all pushed to main.
- Final report for Ben, 10 lines at most, plain words, result first:
  - Did matching its old self keep more sums and grids?
  - Was it the teacher, or just more weight on old puzzles?
  - Did a store 8 times smaller still work?
  - Did it cost any maze skill?
  - Time and money.
  - Commit hashes.

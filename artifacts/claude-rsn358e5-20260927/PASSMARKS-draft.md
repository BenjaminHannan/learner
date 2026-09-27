# rsn-358e5 marks, DRAFT for the Thread manager (written 2026-09-27 02:50:05 UTC; not sealed; nothing run)

**One change from rsn-358e4's eq-replayall: warm routing** (scripts/claude_rsn358e5_warm.py; selftest passes). For the first 10% of phases B and C, each new-kind batch picks its top-1 expert from the newest group only (225 of 2,500 sums steps and 135 of 1,500 maze steps). The gate value is still the full softmax share. Replay batches, later steps and all evaluations route as in 358e4. It uses the training batch's kind, like a curriculum, and never uses it at test time.

**Controls:** rsn-358e4's own eq-replayall and dense-replayall runs on the same seeds, 3-8. They are not rerun. CPU, 1 thread, torch 2.14, as in 358e4. It runs only after 358e4 has finished (the container has 4 cores). /bin/bash.

**Marks**, where N = sums4 after B + maze7 after C (of 400, dev seed 48000, already read in 358e/e3/e4, so this is not a held-out test):
- **REPRO (else INCONCLUSIVE, stop):** on every seed, every after-A dev score equals rsn-358e4 eq-replayall's. Phase A is untouched.
- **M, the routing took (else INCONCLUSIVE, "warm routing did not route"):** on at least 5 of 6 seeds, the new group gets at least 5% of the sums4 cells after B in at least one block, AND at least 5% of the maze7 cells after C in at least one block. The same measure as 358e4 ADDENDUM-3.
- **PASS:** mean N_warm >= mean N_eq + 50, AND N_warm > N_eq on at least 5 of 6 seeds.
- **Proved wrong:** M holds, mean N_warm <= mean N_eq + 10, AND N_warm <= N_eq + 10 on at least 5 of 6 seeds. Meaning: the new experts got the new kind and still did not learn it, so routing was not the limit. Capacity would then be suggested, not shown.
- Anything else, with REPRO and M met, is FAIL.
- **Report only, never graded:** T = grids5 + sums4 + maze7 after C against dense-replayall, with 358e4's bars (+40, 5 of 6) shown as a row; grids5 after B and after C; forced_batches; expert_share.
- **Predictions:** M 85%; PASS 30%; proved wrong 45%. Why low: in 7 of 8 earlier freeze-and-grow runs the new group already got at least half of the new kind in one block and still learned little (DIAG-new-group-share.md in rsn-358e4).

**Brain link (a guess):** in the adult dentate gyrus, young adult-born neurons are more excitable and more plastic than mature ones, so they tend to win the competition to encode new experiences instead of starting from nothing. Warm routing is the machine version of that head start. I have not checked this against papers in this session.

## Change after the Thread manager's review (02:52 UTC), added 2026-09-27 02:54:03 UTC
- **Disclosed stand-in:** warm routing is given each training batch's kind by the code, a hand-given task label. It is a task oracle, used for 10% of the new-kind batches in phases B and C (225 and 135 batches) and never at test time. A PASS would show that a head start works *given* that label. It would not show that the net finds its own new experts.
- The marks are otherwise unchanged. The Thread manager asked for both 358e5 and 358e6 to be sealed after it sees 358e6's draft (artifacts/claude-rsn358e6-20260927/PASSMARKS-draft.md).

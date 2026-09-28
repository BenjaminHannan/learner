# Chat prompt: the sparse thinker (looped net with experts) as Test D in the few-example race (Thread manager, 2026-09-28T01:30Z)

Ben shared arXiv 2605.09165 ("Sparse Layers are Critical to Scaling Looped Language Models") at 01:25 UTC and asked
whether the thinker should be a sparse reasoning model. The Thread manager advised entering it as a fourth design in the
few-example race under the same budget and marks, not a switch. Ben: "I say yes for the sparse thinker" at 01:29:56 UTC
(cmsg_01FuvegZXjMmeUzStiEFVnEWBig7FpFm3NGExej63Aa9hW). Everything below the line is the prompt.

---

Effort: high (Opus 5.5)

# Goal: test whether a sparse thinker (the loop with a mixture of experts in each block) learns a new kind of puzzle from fewer examples than the plain loop, as Test D in the few-example race

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first.
- Ben (a high-school senior) reads your final report.
- Ben's main measure is how few examples the thinker needs to learn a new kind of puzzle. The few-example race measures it. Practice is on sums and Latin grids, then the thinker adapts to mazes from k = 1, 4, 16 and 64 examples and from a stream of up to 65,536. Mazes are only the test's stand-in for "a new kind": nothing in the design may be built for mazes.
- Ben's idea, from arXiv 2605.09165 (Lee, Biloki, Hu, May): in a looped net, swap each block's feed-forward layer for a mixture of experts with a learned router. Each pass through the shared layers can then pick different experts. In language models up to 305M, a looped net with experts scored 39.6 against 38.7 for a normal net, while a plain looped net fell behind at 37.4. Treat these as the paper's claims. It did not test learning from few examples or forgetting.
- Our earlier expert tests are not the same thing. rsn-358e froze old experts and grew new ones, keeping old skills but learning new ones badly. Here every weight trains and nothing is frozen or grown.
- Other chats are running: the few-example baseline, the relation net (Test C), clip-on patches (Test A), the sleep test and the reader tests. Don't edit their files, don't touch their jobs, and never stop another agent's rental.

**Read first**
- artifacts/claude-fewex-20260927/: PROTOCOL.md (its plug-in contract), PASSMARKS.md, RACE-PASSMARKS.md, ADDENDUM-1..3, and RESULTS.md if it exists yet.
- scripts/claude_fewex_bench.py, claude_fewex_net.py and claude_fewex_data.py.
- An existing plug-in to copy the shape from: scripts/claude_patch_plugin.py. The relation net's files show how a race entry was gated: scripts/claude_relnet_*.py and artifacts/claude-relnet-20260927/.

**The one change: the sparse loop**
- Start from the race's loop exactly (2 shared blocks at width 256, 8 heads, learned stop, 48-round cap, the same attention and the same input re-added every round). Change only each block's feed-forward layer, which becomes 8 experts with a learned router picking the top 2 for each cell on each round, as in the paper (Mixtral style).
- The router sees only the cell's hidden state. It gets no kind label, no round number and no hand-written rule.
- Budget: the race counts every stored weight, so the sparse loop must be within 2% of the loop's 1,645,726. Size the experts to fit. This is stricter than the paper, which matched active compute and let the expert net store more weights. Report the active weights per cell per round beside the stored count.
- One load-balancing loss, the standard Switch/Mixtral auxiliary loss at coefficient 0.01, used in practice, in maze adaptation and in sleep alike. It is fixed now and never tuned on any maze score.
- Everything else comes from the harness unchanged: practice data and steps (including ADDENDUM-3's source qualification), the maze recipe, sleep, panels, seeds 0 and 1, fp32 and scoring. Use `--plugin`; never edit the harness. If you need a Learner, it must do exactly what the baseline learner does.

**Order**
1. Build the plug-in and its selftest. Run the harness's one-step gradient check (every 2-D weight matrix, every expert and the router, gets a nonzero gradient) and a CPU smoke run.
2. Write artifacts/claude-sparse-YYYYMMDD/PASSMARKS-D.md and commit it before any maze run:
   - **Test D:** the common gates in RACE-PASSMARKS.md, word for word, in both seeds, plus F_all at least 10 points above the loop in both seeds.
   - **Proved wrong:** F_all no higher than the loop in both seeds, or a maze gain only by breaking an old-kind gate. Either rejects this design at this budget.
   - **Report only, the paper's mechanism:** for each round pair, the share of cells whose two experts differ from the previous round (none, one or both), expert use per block, and any expert that gets under 1% of cells.
3. Practice, then the source guard (V1's 190 of 200 on sums and grids, each seed). If it fails, report that and stop.
4. Wait until the few-example baseline has passed V1-V3 on main. The race marks apply only after that. Then run the dev branches, and then the holdout once. Compare against the baseline's own loop numbers from the same seeds and panels, the way the relation net's race does. Don't retrain the loop.
- The protocol says fp32 on CPU. If that's too slow, add an addendum like the relation net's (strict fp32 on a GPU, shown equal to the CPU on a smoke run) and commit it before any maze score. Then use at most one rental job, capped at $4.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push. New files only: scripts/claude_sparse_*.py and artifacts/claude-sparse-YYYYMMDD/. Never touch the repo-root notebook/.
- Times in files come from `date -u`.
- Money: Ben's standing rule lets you rent. At most $4 per job. Destroy an instance only after a checked copy-back, otherwise stop it. Never read or print the vast key or any auth file.
- Never look at a dev or holdout maze score before PASSMARKS-D.md is committed, and change no mark after.
- Stop processes by exact PID.
- Label claims shown, suggested or untested. Give counts as "x of N".
- Save usage: run long jobs in the background, don't poll, skip status chatter, and use subagents only when needed.
- A separate subagent does a blind recount of the key numbers from the raw JSON and the marks only.

**Done means**
- Plug-in, marks, both seeds' dev and holdout results, RESULTS.md with the verdict and the recount, all pushed to main.
- Final report for Ben, 12 lines at most, plain words, result first:
  - Does the sparse thinker learn mazes from fewer examples than the plain loop (k = 1 to 64, and the stream)?
  - Did it keep sums and grids, before and after sleep?
  - Did different rounds actually use different experts?
  - Size, active weights, speed and money.
  - The single next step.
  - Commit hashes.

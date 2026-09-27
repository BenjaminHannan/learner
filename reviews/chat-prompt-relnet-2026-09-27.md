# Chat prompt: build the relation-network reasoner and race it on the few-example test (Thread manager, 2026-09-27T20:27Z)

Ben asked at 20:25 UTC for a prompt for a separate chat that builds the first reasoner design, running alongside the few-example test chat (reviews/chat-prompt-fewex-ruler-2026-09-27.md). Everything below the line is the prompt.

---

# Goal: build the relation-network reasoner, check it, and race it against the looped transformer on the few-example test

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first.
- Ben (a high-school senior) reads your final report.
- The reasoner is the heart of Ben's model: a small net trained from scratch on code-made puzzles. Today it's a looped transformer, which is published work, not new. Ben wants a brain-inspired design that beats it.
- His main measure (design/v3/30-modes/ben-goals-2026-09-26.md:24-26) is how few examples it needs to learn a new kind of puzzle, while keeping the old kinds.
- You build GPT-6 Pro's design 3, the **persistent relation-state network**. It's the one design that replaces the transformer instead of adding to it.
- Another chat is building the test at the same time: artifacts/claude-fewex-*/ and scripts/claude_fewex_*.py. Don't edit its files.
- This is a test. Nothing joins Ben's main build without his yes.

**Read first**
- reviews/gpt6pro-brain-reasoner-contenders-REPLY-2026-09-27.md: the notes at the top; section 1 (size accounting, stop rule); section 2, design 3 (the equations); section 3 (common protocol and Test C).
- scripts/claude_rsn358e_moe.py: the small dense loop you must match in size (2 blocks x width 256, 8 heads, 1,646,750 weights, learned stop, at most 48 rounds, 1-16 training rounds with gradient through the last 1-6).
- scripts/claude_rsn358a_envs.py (sums and grids), scripts/claude_xfer1_bench.py (maze carver) and scripts/claude_xfer1_net.py (practice recipe).
- The test chat's PROTOCOL.md and RACE-PASSMARKS.md, once they are on main.

**Build the net (follow GPT's equations)**
- Each cell has a state h_i. Each directed pair of cells has a relation state r_ij, all pairs, width q = 64.
- Update r_ij with a GRU from [h_i, h_j, the input-symbol difference, generic relative position]. Cells gather messages from their relations, then update with a GRU plus a residual MLP.
- Relation states carry across thinking rounds and reset between puzzles.
- Inputs are only the cell tokens and generic positions (row and column offsets). No puzzle-specific structure: no Sudoku constraint graph, no maze adjacency, no carry rules, no puzzle-kind label.
- Use a learned stop head on pooled cell states, with the same stop training and 48-round cap as the loop.
- Match total weights to the loop within 2%, counting everything: embeddings, heads, stop head and every persistent coefficient. GPT's sizing is a starting point: the residual MLP hidden width is about 1,576 at width 256.
- Use the same round truncation as the loop (1-16 rounds, gradient through the last 1-6).

**Checks before any race run**
- Weight table: relation net vs loop, part by part.
- Gradient check: every weight matrix gets a nonzero gradient in one step. Use fp32 with no autocast; an old autocast bug silently froze 8 of 12 matrices.
- Cost: time per training step and memory at 9x9 and 11x11 (121 cells means 14,641 pairs), compared with the loop. If all-pairs is too slow on CPU, shrink the batch or the round window and disclose it. Don't cut pairs with hand rules. A learned sparse version would be a separate variant, not the main arm.
- Practice: train on sums and grids with the same source recipe as the loop. It must reach 95% on 200 fresh 4-digit sums and on 200 fresh 5x5 grids, and be within 3 points of the loop on each (a race gate). A small learning-rate sweep on source dev is allowed and must be disclosed. If it can't reach the guard, that is a finding: report it.

**The race (Test C)**
- Wait until the test chat has committed RACE-PASSMARKS.md to main. Never edit it.
- If your net is ready first, commit the net and the checks, send Ben a short report, and stop. He'll tell you to go.
- Then run Test C through the locked harness: 2 seeds of the source-trained relation net, plus a fresh relation net as its own control.
- Use the test chat's loop and plain baseline runs. Rerun them only if the harness needs pairings they don't have.
- The verdict follows RACE-PASSMARKS.md exactly: PASS, FAIL, or the registered negative result. Also report training operations and inference time. A matched-compute comparison is report-only.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push.
- New files only: scripts/claude_relnet_*.py and artifacts/claude-relnet-YYYYMMDD/. Don't edit other tests' sealed files or repo-root notebook/.
- Times in files come from `date -u`.
- CPU only, $0. No rentals or downloads. Code-made data only; no LLM-written training data.
- Stop processes by exact PID. Never touch secrets.
- Label claims shown, suggested or untested. Give counts as "x of 300".
- Save usage: run long jobs in the background, don't poll, skip status chatter, and use subagents only when needed.
- A separate subagent does a blind recount of the key numbers from the raw files and the marks only.

**Done means**
- The net is built, checked and practised, and the checks are committed.
- If the marks were sealed: the race has run, RESULTS.md has the verdict against RACE-PASSMARKS.md, the curves per seed and the blind recount, all pushed to main.
- Final report for Ben, 15 lines at most, plain words, result first:
  - Does the relation network learn mazes from fewer examples than the loop and the plain net?
  - Does it keep sums and grids?
  - How much slower or bigger is it to run?
  - Is it worth keeping, and what's the single next test?
  - Commit hashes.

# Chat prompt: build the clip-on patch reasoner (fast path) and race it on the few-example test, with wider practice (Thread manager, 2026-09-27T22:04Z)

Ben chose this prompt at 22:01 UTC ("do the patches chat"). At 22:01:40 he asked for more practice kinds than sums and grids ("since there are only two today, can you add more?"). Everything below the line is the prompt.

---

# Goal: build the clip-on patch reasoner, check it, and race it against the looped transformer on the few-example test, with every arm practising a wider set of kinds

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first.
- Ben (a high-school senior) reads your final report.
- The reasoner is the heart of Ben's model: a small net trained from scratch on code-made puzzles. Today it's a looped transformer. Ben's main measure (design/v3/30-modes/ben-goals-2026-09-26.md:24-26) is how few examples it needs to learn a new kind, while keeping the old kinds.
- Why this design: in the brain, a fast learner (the hippocampus) lets you use a new experience right away, and sleep later teaches it to the slow learner. Our reasoner has no fast path. It can only learn by changing its weights over thousands of examples. You build GPT-6 Pro's design 1, **feedback-written method patches**, as that fast path.
- The design must be general. It gets no puzzle-kind label and no puzzle-specific structure. Mazes are only the test's stand-in "new kind", used because code can grade them.
- Other chats are running: the test chat (artifacts/claude-fewex-*/, scripts/claude_fewex_*.py) and the relation-network chat (artifacts/claude-relnet-*/, scripts/claude_relnet_*.py). Don't edit their files.
- This is a test. Nothing joins Ben's main build without his yes.

**Read first**
- reviews/gpt6pro-brain-reasoner-contenders-REPLY-2026-09-27.md: the notes at the top; section 1 (size accounting, stop rule); section 2, design 1 (the equations); section 3 (common protocol and Test A).
- scripts/claude_rsn358e_moe.py: the small dense loop you must match in size (2 blocks x width 256, 8 heads, 1,646,750 weights, learned stop, at most 48 rounds, 1-16 training rounds with gradient through the last 1-6).
- scripts/claude_rsn358a_envs.py (sums, grids, numbers), scripts/claude_xfer1_bench.py (maze carver) and scripts/claude_xfer1_net.py (practice recipe; xfer-1 kept deep supervision and no stop loss while learning mazes).
- The test chat's PROTOCOL.md and RACE-PASSMARKS.md, once they are on main.

**Build the net (follow GPT's design 1)**
- Keep the looped core. Add a low-rank patch inside the repeated step: h_next = F(h, x) + g(x, h) * B A h.
  - Rank r = 8 at width 256.
  - g is a learned gate that sees the puzzle and the current state, never a kind label.
- After a support example gets its feedback (the correct answer against the net's own answer), a small writer turns the support's activations and that error into a patch update.
  - The patch updates as A <- rho*A + (1-rho)*A_new, and the same for B.
  - Keep the writer's outputs and the patch's effect bounded.
- The patch persists across puzzles. It is not reset when the kind changes; only a puzzle's working state resets.
- Query answers never reach the writer.
- Ordinary weights stay fixed while supports are being written. Nights (sleep) update the ordinary weights, with replay.
- Match total weights to the loop within 2%, counting everything: writer, gates, stop head, embeddings, and the persistent A and B coefficients. GPT's sizing is a starting point: MLP hidden width 3.5 x 256 instead of 4 x 256, and a shared writer of about 2 x 256^2.
- Use the same round truncation and stop training as the loop.

**Wider practice (Ben's request)**
- Practice uses sums, grids and at least 4 more code-made, code-checked kinds. You pick them from the repo's generators or write new ones.
  - Examples: number puzzles, sorting, reversing, counting, bracket matching.
  - Use the same token format and no kind label.
- **Banned because they are too close to mazes:** anything about paths, reachability, walls, flood fill, connectivity or routes. No maze example may appear anywhere in practice.
- Seal the kind list, the generators and a hash of each before any training.
- A kind stays only if the plain loop reaches at least 90% on its fresh dev panel in the practice budget. Drop a kind that misses before sealing, and say so. Sums and grids keep the test's 95% gate.
- **Every arm practises the same kinds:** the patch net, the loop, the plain net, and the loop's learning-to-learn training (below). So you train your own loop and plain rivals, 2 seeds each. You can't reuse the test chat's baselines.
- Learning-to-learn training (GPT's Test A):
  - Build support-then-query episodes from the practice kinds, with no family IDs.
  - The writer gets credit only for doing better on *different* examples after the support, plus keeping old examples.
  - Differentiate through the last 2 writes.
  - The loop control gets the same episodic training with ordinary gradient adaptation, as RACE-PASSMARKS requires.
  - Write and seal the episode recipe before training.

**Checks before any race run**
- Weight table: patch net vs loop, part by part.
- Gradient check: every weight matrix gets a nonzero gradient in one step. Use fp32 with no autocast; an old autocast bug silently froze 8 of 12 matrices.
- Stability: 48 rounds with the patch at its largest allowed size, no blow-up.
- Zero patch: with A = B = 0, the net runs as an ordinary loop.
- Practice gate: each practice kind at its mark, and the patch net within 3 points of your loop on each.

**The race**
- Wait until the test chat has committed RACE-PASSMARKS.md to main. Never edit it.
- If your net is ready first, commit the net and the checks, send Ben a short report, and stop. He'll tell you to go.
- Before any race run, write ADDENDUM-wide-practice.md in your own artifact folder.
  - It says the only change from RACE-PASSMARKS is the wider practice, given to every arm.
  - It keeps Test A's bars unchanged, applied to your own loop and plain runs.
  - Commit it.
- Adaptation, as the default unless the protocol says otherwise; write it into your addendum:
  - Ladder rungs k = 1, 4, 16, 64: writer only, with ordinary weights frozen.
  - Stream rungs (256 to 64k): the loop's ordinary training with the writer still on.
  - Sleep: GPT's fixed sleep, updating ordinary weights with replay.
- Arms: 2 seeds of the patch net, your loop and plain rivals, plus a fresh patch net. The fresh net learns its supports by ordinary gradient updates, not through an untrained writer.
- The verdict follows RACE-PASSMARKS Test A exactly, as amended only by your addendum. That covers F_all at least 10 points above the loop on both seeds, the common gates, and the registered negative result.
- Report only:
  - old kinds and mazes right after the supports, before any sleep;
  - after sleep with the patch removed, which shows whether the nights absorbed it;
  - training operations and inference time.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push.
- New files only: scripts/claude_patch_*.py and artifacts/claude-patch-YYYYMMDD/. Don't edit other tests' sealed files or the repo-root notebook/.
- Times in files come from `date -u`.
- Use this chat's own machine, $0. If it has a GPU, use it in fp32 with no autocast, and record the torch version. No rentals or downloads.
- Code-made data only; no LLM-written training data.
- Stop processes by exact PID. Never touch secrets.
- Label claims shown, suggested or untested. Give counts as "x of 300".
- Save usage: run long jobs in the background, don't poll, skip status chatter, and use subagents only when needed.
- A separate subagent does a blind recount of the key numbers, working from the raw files and the marks only.

**Done means**
- The net is built, checked and practised, and the checks and the sealed practice kinds are committed.
- If the marks were sealed: the race has run, and RESULTS.md has the verdict, the curves per seed, the report-only rows and the blind recount, all pushed to main.
- Final report for Ben, 15 lines at most, plain words, result first:
  - Does the patch net learn mazes from fewer examples than the loop and the plain net?
  - Does it keep the old kinds, and do nights absorb the patch?
  - Did the wider practice help the loop too?
  - How much slower or bigger is it?
  - Is it worth keeping, and what's the single next test?
  - Commit hashes.

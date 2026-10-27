# Chat prompt: build the few-example test and measure the loop and plain baselines (Thread manager, 2026-09-27T20:20Z)

Ben asked at 20:15 UTC for a prompt to start a cloud chat on this. Everything below the line is the prompt.

---

# Goal: build the few-example learning test ("the ruler") and measure the baselines

You are working in the repo BenjaminHannan/learner (Ben's "Premonition" project). Read CLAUDE.md first. Ben is a high-school senior; he will read your final report.

## Why this matters

Ben's main measure (design/v3/30-modes/ben-goals-2026-09-26.md:24-26) is **how few examples the reasoner needs to learn a new kind of puzzle**, given what it already knows. The reasoner is a small net trained from scratch on code-made puzzles. Three brain-inspired designs will soon race the current looped transformer on this measure, each in its own chat. Your job is to build the test they will all be judged on, seal its pass marks, and measure the two rivals every design must beat. **Do not build any of the three designs.**

## Read these first

- reviews/gpt6pro-brain-reasoner-contenders-REPLY-2026-09-27.md: section 1 (accounting and stop rules) and section 3 (the proposed protocol, Tests A-C, run counts). The Thread manager's notes at the top say which parts we changed.
- artifacts/claude-xfer1-20260927/: RESULTS.md, program.md, the trial diffs 0001-0004. This is an earlier version of the same test on 430k-weight nets. Its harness is scripts/claude_xfer1_bench.py, claude_xfer1_net.py and claude_xfer1_adapt.py if they are on main; if not, rebuild what you need from program.md and the diffs.
- scripts/claude_rsn358e_moe.py: the small dense loop (2 blocks x width 256, 8 heads, about 1,646,750 weights, learned stop head, at most 48 rounds).
- scripts/claude_rsn358a_envs.py (sums and Latin grids) and scripts/claude_rsn358m_maze.py (maze format and checker). Its maze carver makes very few distinct layouts (about 14 at 7x7, 322 at 9x9 in 100k draws), so use the uniform spanning-tree (Wilson) carver that xfer-1 used.

## The test to build (defaults are chosen; follow them unless something is impossible, and say why)

1. **Source training:** sums and Latin grids only. No maze ever appears in source training, tuning or validation. No puzzle-kind label or kind-specific switch anywhere. Guard: every source-trained net scores at least 95% on 200 fresh 4-digit sums and on 200 fresh 5x5 grids.
2. **New kind:** mazes. The main test panel is 300 unseen 9x9 mazes. Also report 7x7 and 11x11 panels. Every panel layout is excluded, by hash, from every support set and stream. Count distinct layouts per size before relying on a size. Keep a dev panel for building and debugging, and a holdout panel that runs once, at the end.
3. **The ladder (Ben chose this):**
   - Few rungs, GPT's way: k = 1, 4, 16, 64 unique mazes, nested and sealed, 8 shuffled passes, each from a clean copy of the source-trained net.
   - Stream rungs, xfer-1's way: one run from a clean copy, fresh mazes in batches of 32, evaluated after 256, 1k, 4k, 16k and 64k mazes.
   - Also record k = 0 (cold).
4. **Scores:** the primary score F_all is the mean panel accuracy over all nine rungs, in percentage points. Also report F_few (mean of k = 1, 4, 16, 64), F_few minus cold, and the full curve per seed. GPT's "50% after 64 examples" is report-only.
5. **Old kinds:** score sums and grids before adaptation, after k = 64, after 64k, and after sleep. Report each kind separately.
6. **Sleep:** after the k = 64 branch and after the 64k stream, run GPT's fixed sleep: 512 updates x 16 examples, 8 old plus 8 drawn from that branch's own maze examples, from a stored replay allowance of 128 grids and 128 sums that every arm gets. Report D = old accuracy before adaptation minus after sleep, per kind.
7. **Rivals, 2 paired seeds each** (same supports, streams and panels across arms):
   - source-trained loop, about 1.65M weights;
   - source-trained plain transformer of the same total size (within 2%), one pass, no looping;
   - fresh loop and fresh plain (no source training), learning mazes by ordinary gradient updates.
   - The loop adapts with xfer-1's kept recipe (deep supervision with 4 updates per maze batch, and no stop-head loss while learning mazes). Plain gets the same number of updates per example, plus a small learning-rate sweep on source dev only, never on a maze panel.
8. **Stopping:** keep the learned stop head (48-round cap). Report mean rounds, how often it hits the cap, and a "stop failure" if learned stopping scores more than 2 points below the best fixed depth chosen on source dev.
9. **Size and compute:** count every weight and every persistent coefficient. Report weights, training time per arm, and inference rounds.
10. **Plug-in interface:** any new net must drop in without touching the locked harness. For example, a class with forward(tokens, positions) returning per-round cell logits and stop logits, plus a weight counter. Document it in PROTOCOL.md so the design chats can use it.

## Sealing, in this order

1. Write PROTOCOL.md, the harness, and PASSMARKS.md for this baseline run. Its validity checks are:
   - V1: the source guard is met by every net.
   - V2: every weight matrix gets a nonzero gradient in a one-step check. An earlier autocast/cache bug silently froze 8 of 12 block matrices, so use fp32 on CPU with no autocast.
   - V3: the ladder has signal, meaning at least one arm is between 10% and 90% on at least three rungs. If V3 fails, report INCONCLUSIVE and stop; don't retune after seeing panel results.
2. Write RACE-PASSMARKS.md for the three coming design races, adapted from GPT's Tests A-C:
   - primary F_all;
   - Tests A (correction patches) and C (relation network): F_all at least 10 points above the loop on both seeds;
   - Test B (branch neurons): at least 5 points above, plus a forgetting cut of at least max(3 points, half the loop's D);
   - common gates: source score within 3 points of the loop on each old kind; F_all at least 5 points above both the plain net and the design's own fresh copy on both seeds; post-sleep old kinds within 3 points of the loop;
   - GPT's registered negative results, and 50% at k = 64 as report-only;
   - if a design needs episodic learning-to-learn source training (Test A), the loop control gets the same training in that race.
3. Commit both files to main **before any run**, and record the commit hash in RESULTS.md.

## Rules

- Commit to main, no pull requests. `git pull --rebase` before every push; never force-push. Add new files only; never edit another test's sealed files. Never touch the repo-root notebook/ folder.
- New files go in artifacts/claude-fewex-YYYYMMDD/ and scripts/claude_fewex_*.py. Timestamps in files come from `date -u`.
- CPU only, $0. No rentals, no model or dataset downloads. All data is made by code; no LLM-written training data.
- No hand-written puzzle rules inside the nets, and no kind labels.
- Stop processes only by exact PID. Never read or print secrets.
- Label every claim shown, suggested or untested. Don't claim beyond the evidence. Give counts as "x of 300".
- Ben judges results per unit of usage. Launch long runs in the background and wait for them to finish instead of polling. Skip status chatter. Use subagents only when a step needs one.
- A separate subagent does a blind recount of the key numbers from the raw result files, with the marks as its only other input. Put its output in the artifact folder.

## Done means

Harness and marks sealed and committed. All baseline runs finished. RESULTS.md has one table per arm, per rung and per seed, plus the old-kind, sleep and rounds rows, the verdicts on V1-V3, and the blind recount. Everything is pushed to main.

Then end with a short report for Ben (15 lines at most, plain words, result first):
- does practice help the loop learn mazes with fewer examples?
- is the loop ahead of or behind the same-size plain net?
- at what number of examples does learning really start?
- is the test ready for the three designs, and what should a design chat read first?

Close with the commit hashes.

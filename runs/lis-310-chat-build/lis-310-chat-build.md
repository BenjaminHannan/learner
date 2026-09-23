COMMON RULES (the listener thread, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (the listener spec: design/v3/60-listener/frame-spec.md). Builder outputs are on origin/builder-outbox (git show origin/builder-outbox:<path>). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
INDEPENDENCE: never open or read items of any TEST-ONLY panel. New files only. Never check out branches in the worktree; get a copy of the code for the GPU machine with `git archive origin/main` and `git archive origin/builder-outbox <path>`.

YOUR TASK: builder for lis-310, which PLUGS THE LISTENER INTO THE CHAT AGENT. It's a CPU build. Unit tests use a stub reader, and the real weights come later from lis-300. Artifacts go in artifacts/claude-lis310-20260923/. New files only: scripts/claude_lis310_agent.py, scripts/claude_lis310_test.py and scripts/claude_lis310_demo.py.

CONTEXT. The chat page (scripts/claude_chatdemo_server.py) still reads with hand-written rules. The current base is 291: build_agent291(cfg) in scripts/claude_loop291_agent.py, plus DEFAULT_CONFIG291 and scripts/claude_fix291_glue.py (on origin/builder-outbox). It is a stack of rule layers; read its docstring. The listener is the fine-tuned MiniCPM5-1B from lis-300:
- scripts/claude_lis300_read.py: Reader(model_dir).read(turn, prev_reply) -> (frame, confs, raw, ms);
- scripts/claude_lis300_compiler.py: compile_frame(frame, turn, prev, conf, threshold) -> {write, ask_whose, ask_back, held, question, act}.
The frame format is design/v3/60-listener/frame-spec.md.

BUILD build_agent310(cfg), which is 291 plus the listener. Install it by subclassing or wrapping, as 291 installs 260; never edit a frozen file. Behaviour on each user turn:
1. Run the reader on the turn, with prev_reply = the assistant's previous reply. Compile with the threshold from cfg (lis-300's THRESHOLD.txt; default 0.99 until then).
2. If `write` is non-empty: save exactly those facts through the notebook's normal teach/correct doorway, the same path structured teaches take in fable_loop90_agent.Loop90AgentLoop._act. Map owner "me" to the user subject exactly as the base stores "my" facts (find out how and document it). The base's own screens (209/252b value screen, 228 source guard) must still apply. Reply with the base mouth's normal save confirmation.
3. If `ask_whose` is non-empty, save nothing. Reply "Whose <rel> is <value>, yours or someone else's?", naming the first such fact.
4. If `ask_back` is non-empty, save nothing. Reply "Just to check: is <owner>'s <rel> <value>?", using "your" for me. A plain "yes" on the next turn saves exactly that fact. Any other answer drops it.
5. If the act is NEGATE, SUPPOSE, PLAN or CHAT, or every fact is held (REPORTED, UNCLEAR, CHECK), nothing is saved by anyone, the base's rule chain included.
   - For NEGATE, SUPPOSE, PLAN and REPORTED, pass the turn to the base with TEACH/CORRECT writes blocked. Use the base's reply if it doesn't write; otherwise reply "Okay, I won't save that since it isn't a plain fact."
   - For CHAT, let the base handle small talk with writes blocked.
6. If the act is ASK or CHECK, pass the turn through to the base's question chain unchanged (n-hop, reverse, yes/no), with TEACH/CORRECT writes blocked on that turn.
7. If the reader output does not parse, save nothing and reply "Sorry, I didn't catch that. Could you say it another way?"
RULE: while lis-310 is on, the base's rule chain may NEVER write. Every write comes from step 2 or 4. Log every turn (reader frame, confs, decision, ms) to state_dir/lis310_log.jsonl.

TESTS (scripts/claude_lis310_test.py). Use a StubReader that returns fixed frames, so no weights are needed. Cover:
- 2 facts in one turn save 2;
- our -> whose-ask, nothing saved;
- low confidence -> ask-back, then "yes" saves 1 and "no" saves 0;
- a negation saves 0;
- "so X is Y" (CHECK) is answered by the base and saves 0;
- a question is answered from the notebook;
- the base chain's writes are blocked on 5 rule-chain-teachable turns;
- an unparsed frame saves 0.
Also put in a test that `scripts/claude_chatdemo_server.py` could load this agent. Do NOT edit the server: write scripts/claude_lis310_demo.py, a copy of how the server builds its agent, pointed at build_agent310 and a model dir argument.
Seal the tests and PASSMARKS.md (P310.1: all tests pass; P310.2: 0 base-chain writes in the blocked-write test) BEFORE the registered test run. RESULTS.md must list the hook point you chose and how "me" facts are stored.
If ~/premonition-models/lis300-merged/ exists when you finish, ALSO run 20 turns of your own casual dev chat through the real model on the Mac. Report the median/p90 ms per turn and each frame (fictional names, your own turns). Otherwise skip that and say so.
PUSH: artifacts/claude-lis310-20260923 scripts/claude_lis310_agent.py scripts/claude_lis310_test.py scripts/claude_lis310_demo.py artifacts/fable-predictions-ledger.md

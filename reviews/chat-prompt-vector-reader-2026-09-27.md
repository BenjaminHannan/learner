# Chat prompt: the thinker as fact reader, reading the 1B's vectors and writing pointer fact cards (Thread manager, 2026-09-27T22:27Z)

Ben's idea, 22:21-22:24 UTC: "the reasoning model should be the clean fact reader"; "what if we gave the reasoning model pointers? Or vector representations of things?"; "the reasoning model can transcribe the vectors to a fact card somehow". He answered "yes" at 22:24:42 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEW8QPqTDEcQSywnq1McWJHQy) to a first try of this architecture change. Everything below the line is the prompt.

---

# Goal: test whether the thinker can be the fact reader, reading a frozen 1B's vectors and writing fact cards that point at the message's words, against a normal LoRA reader trained on the same chats

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first.
- Ben (a high-school senior) reads your final report.
- Ben's design is reader, then thinker, then talker. Today the reader is its own 1B model, fine-tuned to write facts as text. Ben wants the thinker, a small looped net, to do the reading instead. Ben approved this first try of that architecture change (22:24 UTC). Nothing joins the build without his yes on the result.
- The thinker can't read English: it has only seen puzzle grids. So a **frozen** 1B reads the message and hands over its internal vectors. The thinker loops on them and writes fact cards.
- **Pointers:** a card's names and values are pointers to exact word spans in the message (or earlier turns), never newly written words. The thinker needs no vocabulary, and every card can be checked against the line it points to.
- Other chats are running: the lis-320 reader chat is finishing the Luna practice chats and will train the normal reader, and the relation-net and patch chats are working on the thinker. Don't edit their files, and don't queue or touch any lis-320 chunk jobs.

**Read first**
- artifacts/claude-lis320-20260926/PASSMARKS.md: what a fact is, the families (corrections, backref, former, lookalike, long turns), the save bar T = 0.995, and the scoring ideas.
- scripts/claude_lis320_check_we3.py and scripts/claude_lis320_build.py (code checks and code-written labels; train/dev split by dialog hash), scripts/claude_lis319_common.py (prompt and history format), scripts/claude_lis300_compiler.py and scripts/claude_lis300_score.py (frame spec, relation table, dev scorer).
- The Luna chats: origin/builder-outbox, artifacts/claude-lis320-20260926/full-luna/chunk1..10/raw.new.jsonl.gz (2,028 dialogs, seed 324), joined and cleaned the way ADDENDUM-11 does (scripts/claude_lis320_resume_clean.py). Read-only.
- scripts/claude_rsn358u_run.py and artifacts/claude-rsn358u-20260927/RESULTS.md (the kind-blind thinker: loop of 2 blocks at width 512, about 6.4M weights, learned stop).

**Data (fixed and sealed before any training)**
- Use chunks 1-10 only (2,028 dialogs). Pin their hashes. Build the kept rows with the unchanged code checks and code labels.
- Split by dialog hash: hold out about 10% of dialogs as the practice test (dev). Whole dialogs go to one side only. Both arms use the same split.
- Turn each code label into a card target: owner span, relation (from the existing relation table), value span, and state (current, former, correction), or "no fact". Report how many labels can't be mapped to exact spans, and drop them from both arms alike.
- Training data is Luna-worded with code labels only. Never Claude-written. Never read or use readpanel320 or any other sealed test panel.

**The two arms (one change: how the reading is done)**
- **Vector reader (new):** MiniCPM5-1B frozen, the same base as the reader. For each turn it encodes the turn with the same history window as lis-319, and one chosen layer's token vectors go through a small learned adapter into the thinker (2 blocks x width 512, looping, learned stop). Heads read out the cards: pointer heads for the owner and value spans, a relation head, a state head, and a confidence per card.
  - Pick the 1B layer and the save threshold on a slice of train, never on the dev set. Disclose both.
  - Count and report all trainable weights (adapter, thinker, heads). The 1B stays frozen and is not counted as thinker size.
- **LoRA reader (rival):** the lis-320 recipe unchanged (MiniCPM5-1B + LoRA, the sealed training settings, the same compiler and T = 0.995), trained on the same train rows.

**Checks before training**
- Gradient check: every trainable matrix gets a nonzero gradient in one step (fp32, no autocast; an old autocast bug silently froze matrices).
- Pointer check: on 50 train rows, the gold spans rebuild the gold card exactly.
- Leak check: no dev dialog id appears in train.

**Marks (write PASSMARKS.md and commit it before any training)**
- On the dev dialogs, both arms scored once by the same code scorer, cards compared field by field (owner, relation, value, state):
  - V1: vector reader's right saves at least 95% of the LoRA reader's.
  - V2: vector reader's turns with a wrong save at most the LoRA reader's + 2.
  - V3: on each hard family (corrections, backref, former, lookalike), the vector reader is no more than 5 points below the LoRA reader, as a share of that family's gold facts. Lookalikes count saves, where fewer is better.
  - PASS = V1-V3. Proved wrong: right saves below 80% of the LoRA reader's.
- Report only: right and wrong saves for both arms at their own save bars; cards whose pointers land on the wrong words; mean thinking rounds; time per turn; trainable weights for each arm.
- This is a practice-test result. If it passes, the next step is Ben's call: a fresh sealed panel, not readpanel320.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push. New files only: scripts/claude_vread_*.py and artifacts/claude-vread-YYYYMMDD/. Never touch the repo-root notebook/.
- Times in files come from `date -u`.
- Compute: this chat's own GPU if it has one. Otherwise at most one rental job, capped at $4; Ben's standing rule lets you rent. Destroy an instance only after a checked copy-back, otherwise stop it. Never stop another agent's rental. The MiniCPM5-1B download is already approved; no other new model.
- Never read keys or auth files. Stop processes by exact PID.
- Label claims shown, suggested or untested. Give counts as "x of N".
- Save usage: run long jobs in the background, don't poll, skip status chatter, and use subagents only when needed.
- A separate subagent does a blind recount of the key numbers from the score files and the marks only.

**Done means**
- Data sealed, marks sealed, both arms trained and scored once, RESULTS.md with the verdict and the recount, all pushed to main.
- Final report for Ben, 15 lines at most, plain words, result first:
  - Can the thinker read facts through the 1B's vectors about as well as a normal reader?
  - Right and wrong saves for both, and the hard families.
  - Do the pointers land on the right words?
  - How big and how fast is each?
  - Is it worth a sealed test, and what's the single next step?
  - Commit hashes.

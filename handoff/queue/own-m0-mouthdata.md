COMMON RULES (the director, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (the plan: design/v3/50-own-model/01-own-ear-mouth-plan.md). Builder outputs are on origin/builder-outbox (git show origin/builder-outbox:<path>). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (plan: design/v3/50-own-model/01-own-ear-mouth-plan.md §3.3; talking line plan: design/v3/30-modes/talk-fluency-plan.md). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
INDEPENDENCE: never open any TEST-ONLY panel, any artifacts/claude-*panel* folder, artifacts/claude-own-bench-20260923, or ANY file of the conversation benchmark convbench-f0 (the talk-f0-bench output). They grade this mouth later. New files only. Fictional names only. SEAL (shasum -a 256 > SEAL.sha256.txt, run from the repo root) your scripts + PASSMARKS.md BEFORE the registered run, and push the SEAL file. An unsealed run, or a sealed file changed after sealing, is a registered FAIL.

YOUR TASK: builder for own-M0, the TRAINING PAIRS for Premonition's conversational mouth. This is CPU only, no model training and no downloads, 60 minutes. Artifacts go in artifacts/claude-own-m0-20260923/.
Ben (17:55 UTC): "I only want to talk to it when it's able to speak fluent english in a conversational tone". The mouth turns a checked reply record into one or two warm, natural, conversational sentences. It must never add, drop or change a fact.
Input schema: reuse the record format of artifacts/fable-talker120-20260922/data/train.jsonl, with statuses OK, UNKNOWN, ABSTAIN, CLARIFY, SAVED and FORGOT, and fields name, relations, answer, subject, relation, hop and source. Read artifacts/claude-mouth241b-20260922/say_forms.json for relation nouns, plurals and person/place kinds. Add two input fields:
- "user_turn": the user's last message that led to the record. Write it yourself, and vary it: questions, statements, casual typing, lowercase, typos.
- "tag": one of ANSWER, ACK_SAVE, ABSTAIN, CLARIFY, FORGOT_ACK, WHOSE (our/we → ask whose; Ben's rule in design/v3/30-modes/our-policy-decision-20260923.md).
Output: "reply", written with slot tokens <S1> (owner name), <V1> (value), <R1> (relation phrase) wherever those strings go. The printer fills them in later, so the reply text contains NO literal names.
Build scripts/claude_own_m0_build.py:
- Write at least 20,000 train pairs and 1,000 dev pairs. Use a name pool disjoint from talker120's test names. Dev uses its own name pool and its own record combos.
- Each record gets several different good replies, in a conversational tone: acknowledgements ("Got it", "Nice, noted"), natural hedges on UNKNOWN, a light follow-up question where it fits ("Want me to remember anything else about <S1>?"), and contractions. No filler that claims anything new.
- Faithfulness filter (scripts/claude_own_m0_check.py, code only):
  - every slot the status needs is present exactly once or more;
  - no slot appears that the record lacks;
  - no capitalised word that could be a name appears outside slots;
  - negation and status wording match (UNKNOWN never states a value; FORGOT never restates the old value as current; SAVED never claims to have inferred anything).
  Drop failing rows and count them.
Marks (write in PASSMARKS.md BEFORE the run):
- Pm0.1: after the filter, 0 rows fail a fresh re-run of the check on every row.
- Pm0.2: no single reply string is more than 3% of any status's rows.
- Pm0.3: at least 40 distinct reply templates per status, measured with slots kept.
- Pm0.4: dev name pool ∩ train name pool = 0.
- Pm0.5: 0 crashes.
Report also, with integer counts: rows per status, per tag, how many were dropped by each filter rule, and 10 random train rows quoted (dev material, not a panel).
PUSH: artifacts/claude-own-m0-20260923 scripts/claude_own_m0_build.py scripts/claude_own_m0_check.py

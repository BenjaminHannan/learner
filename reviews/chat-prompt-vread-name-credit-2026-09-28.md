# Chat prompt: vector reader, credit the owner pointer by name (Thread manager, 2026-09-28T01:54:47Z)

Astra's read-only diagnosis of the vread backref gap (pasted by Ben at 01:39 UTC) proposed this test. The TM checked its code
claims: owner labels point at the newest copy (scripts/claude_vread_data.py:16, search order turn, previous reply, history newest
first), card confidence is the lowest of 7 probabilities (scripts/claude_vread_model.py:163), card cells get no position link to
tokens and token offsets clip at ±4 (claude_vread_model.py:76-83), the stop target is "every card right" at every round
(:275-276), the vector checkpoint on main is 0 bytes, and Luna chunks 11-13 exist on origin/builder-outbox. Ben asked at 01:53 UTC
for prompts that can run overnight. Everything below the line is the prompt.

---

Effort: high (Opus 5.5)

# Goal: test one fix for the vector reader's backref gap: give the owner pointer credit for any copy of the right name

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first. Ben (a high-school senior) reads your final report.
- vread (artifacts/claude-vread-20260927/, RESULTS.md at ffd6950be) tested a small thinker that reads a frozen MiniCPM5-1B's layer-12 vectors and points at words to write fact cards, against a LoRA reader. It failed narrowly on backref, where a fact's owner was named in an earlier turn: 81 vs 88 of 136 at each reader's own bar.
- A read-only diagnosis found two separate problems:
  1. **Split confidence.** When the owner's name appears 3 or more times, the reader usually points at the right person but with low confidence: 19 of 30 right-owner cards fall below 0.97, against 1 of 31 for LoRA. The owner label is the newest copy of the name, a card's confidence is the lowest of its 7 probabilities, and the start and end heads are softmaxes over the whole prompt, so probability likely splits across identical copies (suggested).
  2. **Wrong person.** It picks another person, usually one named more recently, in 16 vs 4 cases. This test does not try to fix that.

**The one change (arm B)**
- In training, the owner-start loss becomes −log of the total start probability over every whole-word copy of the labelled owner name in the prompt. The owner-end loss does the same over those copies' ends.
- At read time, the owner's start and end confidence is the total over copies whose text equals the chosen span.
- Nothing else changes: layer 12, the loop scheme, 4,000 steps, the sealed chunk 1-10 training rows, the calibration slice and the rule that picks each arm's bar.
- **Arm A** is the vread vector reader retrained exactly as it was run. The LoRA reader is not needed.
- Two seeds per arm. Save all 7 probabilities per card, and copy every checkpoint back and check it (the old checkpoint came back empty).

**Fresh data**
- All kept rows of Luna chunks 11, 12 and 13 from origin/builder-outbox (artifacts/claude-lis320-20260926/full-luna/chunkK/raw.new.jsonl.gz), built with the unchanged vread data code. Never train on them, and score them once.
- Never open readpanel320 or any other blind panel.

**Marks (write artifacts/claude-vread2-YYYYMMDD/PASSMARKS.md and commit it before any training)**
- **Validity:** at least 200 backref cards, with at least 60 whose owner name appears 3 or more times. Arm A must repeat the dev pattern in both seeds: its below-0.97 share for names appearing 3+ times is at least 25 points above its share for names appearing once. Otherwise the result is INCONCLUSIVE.
- **Pass (B against A, same seed, both seeds):**
  - **M1:** among B's right-owner backref cards, the below-0.97 share for names appearing 3+ times is at most 10 points above its share for names appearing once.
  - **M2:** B's backref right saves at 0.97 (history rule) are at least A's plus 5% of the backref cards.
  - **M3:** B's wrong turns on the whole fresh set (main rule, own bar) are at most A's plus 2, and its backref wrong saves at 0.97 are at most A's plus 2.
- **Proved wrong:** A repeats the pattern, but B's below-0.97 share for names appearing 3+ times stays within 10 points of A's in both seeds. Then splitting across copies of a name is not the cause.
- **Report only:** the wrong-person rate when a rival person is named (this change should not move it), and which of the 7 probabilities is lowest on low-confidence cards.

**Compute and money**
- One rental job at most, capped at $4, on a card like the RTX 4090 vread used (about 11 minutes per training run there). Ben's standing rule lets you rent.
- Destroy an instance only after a checked copy-back, otherwise stop it. Never read or print the vast key or any auth file. Never stop another agent's rental.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push.
- New files only: scripts/claude_vread2_*.py and artifacts/claude-vread2-YYYYMMDD/. Don't edit vread's files, and never touch the repo-root notebook/.
- Training data is never Claude-written. These rows are Luna-worded with code labels, so they are fine.
- Times in files come from `date -u`. Stop processes by exact PID.
- Label claims shown, suggested or untested. Give counts as "x of N".
- Save usage: run long jobs in the background, don't poll, and skip status chatter.
- A separate subagent does a blind recount from the score files and the marks only.

**Done means**
- Marks, code, both arms' fresh-set scores, RESULTS.md with the verdict and the recount, all pushed to main.
- Final report for Ben, 10 lines at most, plain words, result first:
  - Did crediting any copy of the name fix the low confidence?
  - Did right saves go up without new wrong saves?
  - What is left of the wrong-person problem?
  - Time and money.
  - Commit hashes.

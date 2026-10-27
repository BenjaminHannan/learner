---
name: grammar-line
description: Grammar thread (gram-360+): 360 finisher PASS (kept); 361, 362, 364 FAIL; Ben stopped chat grammar at ~90%; no registered next step
metadata:
  type: project
  modified: 2026-09-25T02:32:50.195Z
---
Grammar thread cmsg_01FuvegZXjMmeUzStiEFVnEWFAqAGfT6esf2DshxxdXLo5 (started 2026-09-25 00:31 UTC, Ben: "fix each of these"). Numbers 360-369.
Roadmap: design/v3/30-modes/360-grammar-roadmap.md.

- gram-360 = VERIFIED PASS 4/4 (02:55 UTC 09-25, artifacts/claude-gram360-20260925/VERIFY-360.md). Rule-based slot finisher (scripts/claude_gram360.py; arm scripts/claude_e2e360.py:build_360) renders only rule-agent parts. Fresh blind bank G (artifacts/claude-gram360-bankG-20260925, names E-J, now spent). Fill-in lines 60% -> 91%; 0 score changes; whole replies 89%/88%. It is arm G of the month-end thread's 336b.
- Grading method: scripts/claude_gram360_gradeprep.py (336's canaries, seeds 3601/3602) + two blind Opus Agent graders with the neutral question; scorer claude_gram360_score.py. Keys never in the graders' folder.
- Finding: MiniCPM5-1B is a poor judge of sentence quality (AUC 0.56-0.71; log-prob worse than chance). Don't build gates on it.
- gram-361 = registered FAIL (temperature 0.3: 1B chat 82% -> 90% clean, bar 97%; artifacts/claude-gram361-20260925/VERIFY-361.md).
- gram-362 = registered FAIL (08:45 UTC 09-25; artifacts/claude-gram362-20260925/VERIFY-362.md): learned critic on the 1B's token probabilities orders 338's 4 drafts. Gain +1.8/+4.4 (bar +5); judge prefers today's 49 vs 29; replies 40 -> 28 words; picked bare "I'm not sure." 8x. LESSON: a grammar picker learns "shorter is safer"; any picker needs a keep-the-answer term. Training set (1,280 drafts, two-grader labels) in artifacts/claude-gram362-20260925/train/.
- gram-364 = registered FAIL (19:15 UTC 09-25, VERIFY-364.md): v2 fill-in lines 95.9%/94.5% but only +2.7/+1.3 over gram-360 (93.2% on bank H; bar +3); 'your note about O' wording flipped 2 harness confirm answers (any wording must not add you/your). gram-360 stays; v2 not joined. Thread has no registered next step.
- Length-free self critic (20:00 UTC 09-25, report only, artifacts/claude-gram362-20260925/NOTE-lengthfree-critic-2026-09-25.md): with length regressed out, the 1B's own signals (word probabilities, hidden state) pick the clean draft of a same-length pair 51-59% (near coin flip). So NO self-signal critic as a night reward for chat (it rewards short, empty replies). Told Fix sleep; offered a day-labelled chat set (blind graders on 1B drafts from 1B-written prompts) if they want one.
- Remaining misses: the 1B's replies (~14% flagged by strict graders; DEV: garbled/unnatural phrases most), reader nonsense frames, unknown lowercase place names, "ex wife" hyphen.
- CPU prototyping works in the cloud container: MiniCPM5-1B snapshot 87179e5c downloads in ~20 s; torch CPU via pip.

- BEN (10:57 UTC 09-25): "grammar should come from a better single model, not adding checker models". So no chat-time checkers or pickers; graders may label training data. gram-364 (template renderer for rule lines) is not a checker and stays. Then 11:02 UTC Ben picked "Stop at 90%" on the card: chat grammar stays as it is; this thread only fixes fill-in lines. gram-365 (train the 1B on its clean drafts) NOT started; do not start it unless Ben asks.

**Why:** Ben's 99%+ grammar target; one change per experiment.
**How to apply:** the 1B's own chat sentences look capped near 90% by strict graders; Ben chose to stop chat-grammar work at ~90% (09-25 11:02). Next steps go one at a time on DEV first; offer passes to the month-end thread via the coordinator. Related: [[month-end-results]], [[mac-disk-watcher-hold]].

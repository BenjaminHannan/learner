# 333e: the 1B calls a write_creative tool; the writer sees the conversation. Marks fixed 2026-09-24, before 333e runs

Written by the creative research thread (Ben, 19:13 UTC: "It shouldn't be keyword. The worker model should be able to
call the creative model as a tool ... can't you give it the conversation? And why monday, not today?"). The month-end
thread agreed this thread builds it (19:14 UTC). Code: scripts/claude_cre333e_agent.py (tests 2/2),
scripts/claude_cre333e_wrap.py, head artifacts/claude-cre333e-20260924/head333e.json (scripts/claude_cre333e_train.py).
Background: design/v3/30-modes/research-creative-2026-09-24.md.

## The two changes, as two arms (each one change)
- **e1 = 333d with the router replaced.** Every turn is first shown to MiniCPM5-1B in its own tool-calling format
  (one tool, write_creative; thinking off; the last 3 earlier user messages). Its decision to call the tool is read
  from its layer-12 hidden state at the answer position by a trained logistic tool-call head (threshold 0.7). No
  keyword list. A called turn goes to 333d's writer unchanged; any other turn goes to 292t unchanged.
- **e2 = e1 with the writer given the chat so far** (user turns and the replies the agent actually sent, last 24
  messages), as twin b and 338 do. Router, prompt, sampling, guards and fallback identical to e1.

## Dev evidence (not the panel)
Head trained only on artifacts/claude-cre333e-train-20260924 (640 + 560 blind-written lines, names N-R) plus DEV-bank
lives 01-05. Why the call is trained: zero-shot the 1B wrote about calling the tool instead of calling it, and its
call probability ranked "any idea what X likes?" above real requests (CPU probe, this thread).
Held out (CPU, bf16):
| Set | 333c regex | 333e head |
|---|---|---|
| New DEV set artifacts/claude-cre333e-dev-20260924 (written blind, names S-Z): creative requests routed | 13/40 | 39/40 |
| same: look-alike controls routed (10 teach, 20 ask) | 1/30 | 2/30 |
| DEV bank lives 06-10: creative turns routed | - | 4/5 |
| DEV bank lives 06-10: other turns routed (teach, ask, smalltalk, nosave, correct) | - | 2/91 |
A first head trained on the tidy 640 lines alone routed 104/174 ordinary DEV-bank turns; the realistic 560 lines and
bank lives 01-05 were added for that reason. Threshold 0.7 was chosen on out-of-fold training probabilities.
DEV writer rehearsal (e1 vs e2, oracle notebook, placeholder agent replies): see DEV-333e.md.

## Arms and data
Panel creativepanel333 (TEST-ONLY; run 5th time; nobody reads it). P_e1 and P_e2 = 292t + 333e (wrap, CRE333E_ARM).
B = 333's registered run/arm_B.jsonl; T = twin b, run-b/arm_T.jsonl (both unchanged, sha256 checked).
Judge: design/v3/30-modes/333-judge-prompt.md, one fresh blind Opus agent per run (run-e1, run-e2), key applied by
script.

## Marks (each arm)
P333.1-P333.5 exactly as in PASSMARKS.md (0 events; controls equal to B ≥ 29/30; useful ≥ 32/40; invented ≤ 2/40;
preferred or tied vs T ≥ 20/40).

## One-change marks
| Mark | Bar |
|---|---|
| E.1 routing (e1): creative items routed | ≥ 34/40 |
| E.1b routing (e1): control items routed | ≤ 2/30 |
| E.2 conversation: useful(e2) − useful(e1) | ≥ +4 (+1 to +3 = inconclusive) |
| E.2b invented person facts (e2) | ≤ 2/40 |
Headline, report only: useful(e2) vs useful(T) in the same judging; "beats the plain 1B" is claimed only at
useful(e2) ≥ useful(T) + 3. Judge noise: T's useful count in the two judgings is reported side by side.

**Proved wrong if:** E.1 routes 25/40 or fewer (no better than 333c) or routes more than 4/30 controls (worse than
333c); E.2 if useful(e2) ≤ useful(e1), or invented(e2) is above T's.
Report only: fallbacks, guard counts, routed counts, ms per creative turn. Teach turns routed away inside creative
items are not recorded by the runner (it keeps stats for the last turn only); P333.2 covers routing damage to controls.

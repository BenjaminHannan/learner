# 0.2d gates, ADDENDUM-24: hand-written decision audit and what 0.2d does with each. Written 2026-09-26 17:45 UTC, before any code

The Thread manager asked for this at 17:33 UTC. A read-only audit agent listed 74 decision points: 36 mechanical and 35 stand-ins
for thinking or routing. The full table, with file:line, is in design/v3/30-modes/02d-audit-2026-09-26.md. Month-end checked the key lines
itself: claude_e2e02c.py:73 installs think299b; claude_y1w_answer.py:100-104 fires only when the rule reply abstains;
claude_cre333b_agent.py:45-59 is a regex; chat338 still sets 1-4 sentences and 90 words (claude_chat338_agent.py:37-44).

## Main finding: 0.2d cannot be the 0.2c build with parts switched off
k1a and y1w are reachable only through claude_e2e02c.build_02c, which installs the whole 0.2c rule stack. Decision:
0.2d is a **new, minimal build script** (scripts/claude_e2e02d.py, owner Month-end) that imports none of build_02c's
layers. The path is:
- reader: lis-320 (compiler + threshold only);
- notebook: store v4 plus raw turns;
- reasoner: the 358b3 loop net, through the disclosed grid reader;
- talker: plain MiniCPM5-1B on every turn, given the notebook and raw chat through the W input;
- sleep: night pool with dl-6's settings and a GLM-written frame.
Not installed: the 19 layers the addenda already dropped (stock lines, templates, the 292t question reader, lookup
"reasoner", declines, think299/299b, chat338/338b and its length rules, vary330c, gram360's rewriter, confirm rows,
lis-313b/314b/315/316).

## Stand-ins still on the path, and what 0.2d does
| Item | Decision | Row it touches |
|---|---|---|
| P1 grid reader (read_latin) | disclosed scaffolding; gr-1 (learned reader) owed | row A: the claim is "reasoner beats rivals given the grid", said in those words |
| P3 loop-net stop rule (3 steady rounds) | disclosed scaffolding; learned stop head owed | row A |
| Z1 sleep practises code-made puzzles, not the day's work | disclosed; a learned choice of practice from the day is owed | row B is reported as "number-puzzle practice", not "the day's work" |
| Z2 constrained decoding in sleep practice | disclosed (legal-expression filter, like a grammar) | H-B |
| S1 BM25 + frozen MiniLM rank fusion; v4 pointer step; note "when" string | mechanical plumbing, disclosed | memory |
| B5, B6 lis-300 compiler owner/value rules | disclosed inside the reader; lis-320's gate is scored on exactly this path | memory, S1 |
| B10, B20 value screens, lis-316 guards | removed; lis-320's gate is scored without them | memory (small, suggested) |
| W1 y1w trigger (fires only after a rule reply abstains) | removed; the W input runs on every turn, as ADDENDUM-12 meant | memory up; H3/H1 at risk (shown on DEV: the plain 1B answered 8-9 of 10 never-told asks) |
| I1/W5/I2 "I don't know" | y1t (trained doubt, learned) is the only way the S1/H3 win row is **claimed**; until it has a verified PASS, y1g's agreement check runs as disclosed scaffolding and S1/H3 are **reported, not claimed** | S1/H3, H1 |
| D1 creative regex, D2 context_facts, D3 k1a guards | recommended removed, pending Ben (the Thread manager's batch): one talker path on every turn | K1 about 28 to 24 of 60 on the k1a panel (shown); K1 no-harm against plain MiniCPM is then the plain talker by construction |

The lis-320 gate (H-R) must score the same save path the build runs (compiler + threshold, no screens or guards).
Reading facts is told this. No bar changes.

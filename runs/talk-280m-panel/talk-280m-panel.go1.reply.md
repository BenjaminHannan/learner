Writing your blind test panel — fetching specs and building fresh items.
Spec captured. Now I'll create the panel directory and the three files.
Validating the panel file, then sealing.
All counts check out. Sealing.
VERDICT: DONE — blind panel joinpanel280m written, validated, and sealed. 90 turns, all counts match the spec exactly.

Marks table (integer counts):

| category | turns | gold breakdown |
|---|---|---|
| ability | 25 | 25 × ability_list |
| teach | 8 | 8 × stored triple |
| called | 12 | 12 × exact expected value |
| smalltalk | 25 | 25 × smalltalk |
| mixed | 10 | 5 × ability_list, 5 × abstain |
| control | 10 | 5 × triple (teaches), 5 × exact value (questions) |
| TOTAL | 90 | 73 dialogs |

Every move: created 4 new files under artifacts/claude-joinpanel280m-20260923/ (panel.jsonl, SPEC-COPY.md, README.md, SEAL.sha256.txt). Nothing else touched.

Misses: 0. Post-seal recheck confirms 90 valid JSON lines with exactly the five required keys, and every called question sits in the same dialog after its teach turn.

Deviations (2):
1. PUSH not executed as a git push: OPUS-RULES hard rule 9 forbids commits and pushes, and the brief says OPUS-RULES applies in full. The files are in place in the worktree for the director to collect.
2. Mixed-gold judgment call: mixed turns blending small talk with an ability question are labeled ability_list; mixed turns asking about names never taught anywhere in the panel are labeled abstain. Mixed items are owned by 260 for M1 agreement, so these golds are writer labels only.

What it means (plain English): the 280m builder now has a fresh 90-question test that checks whether the joined agent handles ability questions, taught facts, chit-chat, mixed messages, and control questions correctly — without ever having seen these exact items before.

What it doesn't mean: this says nothing about whether 280m actually passes. I only wrote the test; I never ran any agent or any code, and per the blind-panel rule I can't say how any arm will score on it.

# 333: creative v1 on 292t. Marks fixed 2026-09-24 05:20 UTC, before the panel exists

Written by the month-end thread. Code: scripts/claude_cre333_agent.py (install_creative333, Gen333).
Plan: design/v3/30-modes/330-month-end-plan.md §5. One change on 292t: a turn that asks for ideas or a short piece
of writing becomes a WORK job with a creative phase (fixed N = 11 candidates from the base MiniCPM5-1B, grounded in
read-only notebook facts, candidates naming unknown people dropped, most-grounded kept). It never reaches listening.

Dev evidence before sealing (DEV bank, artifacts/claude-e2e331-dev-20260924): cue detector 10/10 creative turns,
0/184 false triggers (one cue tightened on dev: "recommend" -> "recommend (me|us) a/an/some/something").
Cloud smoke with a stub generator: grounded pick chosen, invented name dropped, 0 notebook events on the creative
turn, the next ordinary question answered as before.

## Panel
creativepanel333 (TEST-ONLY, written blind from design/v3/30-modes/333-creative-panel-spec.md, key audited blind):
40 creative items (a short teaching chat, then a request) and 30 control items (ordinary teach/ask turns that use
words like plan, gift, idea, write, recommend but do not ask for ideas).

## Arms
- P = 292t + install_creative333 (base MiniCPM5-1B generator).
- B = 292t alone (controls only).
- T = the plain twin (scripts/claude_e2e336_twin.py) given the same chat, then the request.

## Marks
| Mark | Bar |
|---|---|
| P333.1 notebook events on creative turns (P) | 0 |
| P333.2 controls where P's reply and stored triples equal B's | ≥ 29/30 |
| P333.3 creative items a blind judge rates "on topic and useful" (P) | ≥ 32/40 |
| P333.4 P replies stating a fact about a named person that the chat never gave (blind judge) | ≤ 2/40 |
| P333.5 blind pairwise judge: P preferred or tied vs T | ≥ 20/40 |

Report only: T's useful count and invented-fact count, fallbacks, ms per creative turn, context facts used.
**Proved wrong if** P's useful count is below T's, or P333.4 is worse than T's count (grounding made it worse).
Judges are blind Opus agents that see only the chat, the request and the replies (arm order randomised per item).

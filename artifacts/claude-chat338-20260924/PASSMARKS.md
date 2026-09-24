# 338: open conversation on the joined agent. Marks fixed 2026-09-24 ~11:50 UTC, before the panel is seen

Written by the month-end thread. Plan: design/v3/30-modes/330r-rebalance-2026-09-24.md (item 1).
Code: scripts/claude_chat338_agent.py (install_chat338, Gen338), runner scripts/claude_chat338_run.py,
unit tests scripts/claude_chat338_test.py (6/6 on the cloud CPU with a stub reader and a stub generator).

One change: a turn the joined agent gives up on (a CLARIFY line from the 336 scorer's fixed list, or one of the two
canned instruction lines) AND that changed nothing (no notebook event, same pending store, no confirm open) is
answered by the shared base MiniCPM5-1B as ordinary conversation (4 samples, first one passing guards G1 no memory
claims, G2 no invented people, G3 no unsupported names or numbers when the user asks about their own life,
G4 length). If none passes, the old reply stays. Last 12 chat messages kept in <state_dir>/chat338.json.

## Panel
chatpanel338 (TEST-ONLY, written blind from design/v3/30-modes/338-chat-panel-spec.md, key audited blind, escrowed
in /mnt/project-files/escrow-338/): 60 everyday conversations of 4 to 7 turns (small talk, advice, explanations,
feelings, follow-ups, a few facts in passing, a few questions about them, 10 questions about untold things).

## Arms (BensPC, one fresh agent per conversation)
- P = 330a + 334 + 333 + 338 (claude_chat338_run:build_P).
- B = 330a + 334 + 333 (the same without 338).
- T = the plain twin (same MiniCPM5-1B, whole chat in the prompt, the fair 211-style prompt).

## Marks (P)
| Mark | Bar |
|---|---|
| P338.1 grammar of P's distinct replies, by two blind graders that each catch ≥ 36/40 planted errors | ≥ 99% |
| P338.2 turns where P gives up or uses a canned instruction line (mechanical, `gave_up`) | ≤ 10% of turns |
| P338.3 turns a blind judge rates "natural and helpful" | ≥ 80% of turns |
| P338.4 blind pairwise judge, whole conversations: P preferred or tied vs T | ≥ 30/60 |
| P338.5 P replies that state a fact about the user or their people that the chat never gave (blind judge) | 0 |
| P338.6 notebook events on turns that are not `teach` (mechanical) | 0 |

Report only: P vs B pairwise (expected large), ask_known right (P, B, T), ask_unknown "don't know" (P, B, T),
T's invented-fact count, distinct replies and most common reply, guard counts, ms median and p90 on BensPC.
**Proved wrong if** P338.4 fails (the plain 1B holds a conversation better than Premonition does) or P338.2 fails
(the agent still gives up on everyday chat). Judges are blind Opus agents that see only the conversations (arm
order randomised per conversation with seed 338); never Ben.

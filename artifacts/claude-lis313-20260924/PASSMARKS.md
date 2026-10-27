# lis-313: answer questions from the reader's own question reading (arm D of lis-312)

Written by the listener thread (Opus) on 2026-09-24, before any F0 run. No training.

## Why
lis-301's reader reads questions right 77 of 81 times on dev. The lis-310 wrapper throws that reading away and hands every question to the old rule chain. On F0 the rule chain misread 12 of the 84 asks (for example "what's X's dog called"). This was checked in code: ASK/CHECK frames go to `_base_pass_blocked310`.

## The one change
`scripts/claude_lis313_agent.py` adds one wrapper (turn313) outside turn310.
- When the reader's frame is an ASK, turn313 looks that question up in the notebook, read-only.
- It replaces the reply only when the rule chain gave no answer (abstain or clarify) and the lookup found a stored value.
- Otherwise the rule chain's reply stays. That covers the cases where the two agree, disagree, the lookup misses, the question is inverse, or the turn is a CHECK.
- The wrapper never writes. The notebook event count is asserted unchanged.

Everything else is identical to arm C: base 292t, the lis-301 reader, T = 0.995, and turn310. The reader is still called once per turn.

## Run
`scripts/claude_lis313_f0.py` is a copy of `claude_lis312_f0.py`: arms A/B/C are unchanged, and arm D is added. It runs all four arms on the sealed F0 benchmark (40 dialogs, 286 turns, 84 asks) with a fresh agent per dialog. P312.1 to P312.4 (artifacts/claude-lis312-20260923/PASSMARKS.md) are scored from the same run.

## Marks (arm D vs arm C, same reader and T)
| Mark | Bar |
|---|---|
| P313.1 ask turns where the wrapper's own answer is wrong (`lis313_reader_answered_wrong`) | 0 |
| P313.2 asks right when the gold value is already stored (`ask_gold_stored_right / ask_gold_stored`) | ≥ 90% |
| P313.3 unexpected-save turns | D ≤ C |
| P313.4 asks answered right | D ≥ C + 3 |

Report only: every lis313_* counter, D's asks right/wrong/abstain, and ms.

**Proved wrong if** P313.1 ≥ 1 (the reader's question reading gives a wrong answer that the rule chain would not have given), or D asks right ≤ C asks right (the reading adds nothing on real dialogs).

The live confirm-at-use wording ("I think you told me X, is that right?") is NOT part of this test. It needs Ben's ruling first.

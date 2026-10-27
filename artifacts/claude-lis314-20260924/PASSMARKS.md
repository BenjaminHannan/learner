# lis-314, lis-315 and lis-316: confirm-at-use, per-fact release and code guards, as three separate wrappers

Written by the listener thread (Opus) on 2026-09-24, before any run. No training. Reader = lis-301 merged (sha b4fd93a2…), T = 0.995, base 292t.

## Why
lis-301 is safe at T 0.995 but saves too little (panel recall 35%). The lis-302 dev rescore (artifacts/claude-lis302-20260924/RESULTS.md) projects that:
- per-fact release saves 534/771 facts instead of 462, with the same 2 wrong turns;
- holding unsure facts and confirming them when they are needed keeps 743/771 (96%).

## The two changes (each its own file, each scored against arm C)
- **lis-315** (scripts/claude_lis315_agent.py): when a turn's confident facts were blocked only because another fact in the same turn was blocked, save the confident ones anyway through turn310's doorway. Then ask about the first remaining one, as turn310 does. Nothing else changes.
- **lis-314** (scripts/claude_lis314_agent.py): a fact that passes every check but is below T goes to a pending store instead of being asked back. The store never answers. When the user asks about that owner and relation and the notebook has no answer, the agent says "I think you told me X, is that right?" (Ben approved this wording at 02:07 UTC). "yes" saves it and "no" drops it.

- **lis-316** (scripts/claude_lis316_agent.py and claude_lis316_guards.py): 4 code guards, called me_prev, prev_owner, comma and mixed_case. A fact that trips one becomes unsure: it goes pending under lis-314, or is asked back without it. Dev counts (lis-301 dev, 753 writable facts): 0 catches, 1 false hold. The guards target error families that this dev set barely contains, so they are registered as a safety layer. The bars only check that they cost little.

Stack helper: scripts/claude_lis_stack.py (one reader call per turn). CPU tests: scripts/claude_lis314_test.py, 13/13.

## Test
- Panel: artifacts/claude-lispanel314-20260924/. It is TEST-ONLY: 40 invented dialogs and 354 turns, written blind, with the key checked by a blind second labeller and adjudicated. The listener thread has never read its items.
- Runner: scripts/claude_lis314_run.py, with arms A (292t alone), C (+310), P (+310+315), K (+310+314), S (+310+313+315+314) and G (S + 316).
- A mechanical user answers every question the agent asks ("Just to check…?" or "I think you told me…?") with yes if the fact is true at that point of the dialog, and no otherwise. Each such question counts as one question to the user.

## Marks
| Mark | Bar |
|---|---|
| P315.1 wrong-save turns | P ≤ C + 1 |
| P315.2 taught facts saved at dialog end | P ≥ C + 5 points |
| P315.3 questions to the user | P ≤ C |
| P314.1 wrong-save turns | K ≤ C + 1 and K ≤ 2 |
| P314.2 taught facts saved or correctly pending at dialog end | K ≥ 85% |
| P314.3 turns per question to the user | K ≥ 8 |
| P314.4 asks answered right (asks whose answer was taught) | K ≥ C + 5 asks |
| P314.5 never-told asks answered with a value | K ≤ C |
| P316.1 wrong-save turns | G ≤ S |
| P316.2 taught facts saved or correctly pending | G ≥ S − 2 points |
| P316.3 questions to the user | G ≤ S + 3 |

Report only:
- every summary.json count for all six arms, including saved-only facts, questions by kind and answer, and ms;
- the stacks S and G against the P314 bars. G is the deliverable for the month-end join.

**Proved wrong if:**
- lis-314: P314.1 fails, or P314.2 < 75%, or P314.4 < C. Then confirm-at-use does not turn unsure readings into safe, useful facts in real dialogs.
- lis-315: P315.1 fails, or P < C + 2 points on P315.2.

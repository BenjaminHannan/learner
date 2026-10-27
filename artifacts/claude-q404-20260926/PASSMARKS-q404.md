# PASSMARKS q-404 — math asked with "you" reaches the thinking step (registered 2026-09-26 ~14:15 UTC)

Owner: Month-end (problem #3, refuses too much). Registered while 383 (007b) runs, so the next step is ready either way.
Marks, arms and test data fixed now; code and the blind panel come after. Sealed; never edited.

## Why (shown in code)
claude_think299_agent.is_reasoning() refuses every turn that contains "you", "your" or "yourself" (SELF, line 29),
meant to keep questions about the assistant out of the think path. It also blocks ordinary math asked the way people
ask it ("Can you work out ...", "If you buy 3 ... how much do you pay?"). Those turns fall to the chat fallback, which
answers with one unchecked reply or an "I'm not sure" line. Fix sleep's chat-gap check (08ca12cb3) and the Mac
agent's doorway diagnosis both found this gate on 0.2c's puzzle wording. Untested: how many everyday math asks it blocks.

## One change
think299's "you" test is narrowed from "any you/your" to "a question about the assistant itself": the turn is
refused only if it asks about the assistant (who/what are you, your name/age/opinion/feelings/memory, do/can/will
you remember/like/think/feel/know me, about yourself), written as a short rule list on dev wordings only. Every other
think299 condition (question form, number signal, no notebook name) is unchanged. New wrapper builder; the sealed
builders stay untouched.

## Arms
Base B = the best joined build at run time, fixed now: X' (build_02c + lis-319 via claude_readersha_wrap + adapter
a33211dc…) with ROUTE02C on if and only if 383 is a verified PASS. Arm Q = B + q-404. Same machine, same seeds.

## Test data (written blind before the code; TEST-ONLY)
- math panel: 100 fresh everyday word problems with one integer answer (code-checked), written by blind agents:
  60 phrased with "you"/"your" as people naturally do, 40 without.
- self panel: 60 questions about the assistant or about the user that contain 2+ numbers (e.g. about the assistant's
  own abilities, or "how many of the 3 kids I told you about ..."), which must NOT go to the think path.
Never opened by me; only the runner and scorer read them.

## Marks
| Row | Test | Bar |
|---|---|---|
| M1 | math panel right (script, integer in the reply's answer line), Q − B | ≥ +10 |
| M2 | the 60 "you" items, Q − B | ≥ +8 |
| M3 | self panel: turns sent to the think path by Q | ≤ 3 of 60 |
| M4 | the 40 no-"you" items: Q's reply byte-identical to B's (the gate decision cannot change there) | 40/40 |
| M5 | math panel replies that state a wrong number as the answer, Q − B | ≤ +5 |

q-404 PASSES only if every row passes. A FAIL stays a FAIL.
Report only: gate decisions per wording; think vote splits ("worked it out a few times"); ms per turn.

## What would prove it wrong (fixed now)
- M2 < +3: the "you" gate is not what costs the math; look next at the vote-split rate (17 of 33 think turns split in
  0.2c's chat panel, Everyday chat's count) or at the fallback.
- M3 > 3: the narrowed rule lets questions about the user/assistant into the calculator; the rule needs the notebook.

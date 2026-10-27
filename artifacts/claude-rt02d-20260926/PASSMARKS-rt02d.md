# PASSMARKS rt-02d — chat route to the slept puzzle skill (registered 2026-09-26 ~13:40 UTC)

Owner: Month-end (fix A). Agreed with Fix sleep 12:50 UTC 09-26 under Ben's 12:48 rule on integrations.
Marks written and committed BEFORE the route code, the test panel or any run. Sealed at registration; never edited.

## Why (shown, Fix sleep's diagnosis main 08ca12cb3, plain 1B, CPU, the 0.2c 40 chat puzzles)
In 0.2c sleep passed all 6 marks inside the assistant (puzzle format: lucky 74 -> 192, greedy 5 -> 12 of 100), but the
same puzzles typed in chat were solved 0 of 40 before and after. The plain 1B given chat wording explains instead of
writing an expression (0/40, cut off mid-explanation); given the puzzle prompt with the rule-keeper it writes
expressions (2/40). The adapter-on column is pending (006m-chatgap on BensPC); it informs nothing below.

## One change
Arm B1 = arm B0 + route A. Arm B0 = X' of 0.2d-r: claude_e2e02c:build_02c, lis-319 reader (READER_SHA e688e1b2…6a76,
via scripts/claude_readersha_wrap.py), the 0.2c sleep adapter (sha256 a33211dc…36f5, sidecar-checked, 3 nights).
Route A: when a user turn is a number puzzle (a target and the numbers to use), the turn goes to the 1B's puzzle
prompt with the rule-keeper (claude_blurt2.Solver prompt + constrained decoding, the doorway the nights train), the
answer is checked with the exact checker (claude_blurt1.check), and the reply gives the checked expression. If no
checked expression is found, the reply says it could not find one (it never states an unchecked answer).
Nothing else changes: no new training, no new nights, the adapter stays installed exactly as in 0.2c.
Arm B1off (report + R2 only) = B1 with every LoRA scale at 0 for the route's call (the plain 1B behind the same route).

## Test data (written blind, sealed before the route code exists)
A blind agent writes, without seeing the route code or this repo's chat templates:
- chat puzzle panel: 100 fresh puzzles from claude_blurt2.puzzles(seed 4797), excluding every day, TEST and chat puzzle
  of 0.2c (seeds 4700-4702, 4790, 4795), each phrased by one of 10 held-out wordings the agent writes (none equal to
  claude_sleep02c.CHAT_ASK), 10 puzzles per wording.
- negatives: 100 ordinary chat messages that contain numbers but are not puzzles (ages, prices, dates, counts,
  recipes, "I need 3 more for 10" style near-misses), fictional names only.
Stored in artifacts/claude-panel-rt02d-20260926 (TEST-ONLY: never opened, printed or quoted by me or any builder;
only the runner and scorer read it). Route code is written after the seal, on dev wordings only.

## Marks
| Row | Test | Bar |
|---|---|---|
| R1 | chat puzzle panel, solved (claude_panel382_run.puzzle_solved on the reply), B1 | ≥ 8/100 AND B1 − B0 ≥ +6 |
| R2 | sleep reaches chat: B1 − B1off on the same panel | ≥ +4 |
| R3 | false triggers: route fires on the 100 negatives | ≤ 2 |
| R4 | no harm: on the 300 general items of dl-1 and the chat dev panel (artifacts/claude-panel382-dev-20260925/chat), B1's reply is byte-identical to B0's on every turn the route did not fire; route fires on ≤ 3 of the 300 | both |
| R5 | honesty: route replies that present an expression failing the exact checker | 0 |

rt-02d PASSES only if every row passes. A FAIL stays a FAIL.
Report only: per-wording solved counts; triggers per wording (missed puzzles); B1off solved; ms per routed turn;
greedy vs retry counts inside the route.

## What would prove it wrong (fixed now)
- B1 ≤ 3/100: the route does not carry the skill into chat.
- B1 ≥ 8 but B1 − B1off ≤ 1: the gain is the rule-keeper, not sleep; the learning loop still does not reach chat
  (then Fix sleep's B, chat-worded practice, is next).
- R3 > 2 or R4 broken: the trigger is too loose to ship even if R1 passes.

## Run
BensPC, $0, after 0.2d-r (007r). Job file written after the route code is sealed. DISK: 1.

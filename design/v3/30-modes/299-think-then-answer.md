# rsn-299: think, then answer (deep reasoning row for Sept 30)

Reasoning line, 2026-09-24. Assigned by the month-end rebalance (330r-rebalance-2026-09-24.md, item 4).

## The one change
The plain MiniCPM5-1B already writes its steps when prompted. The change: an exact calculator (scripts/claude_rsn299_tool.py) does the arithmetic. Whenever the 1B has written a calculation followed by "=", generation stops and the calculator writes the exact result, then the 1B continues. It handles:
- sums with + - * / and brackets;
- ceil/floor/round;
- clock times ("19:40 + 75", "17:10 - 9:30");
- weekdays ("Monday + 9").

Both arms get the identical prompt, word for word, with 10 worked examples, and the same greedy decoding and token budget. The only difference is who does the sums. This is "better than a brain" in the plain sense: people reason, then slip on the arithmetic, and this never slips on the arithmetic.

## How the design got here (dev only; 28 dev items written by me, not blind; the panel was never used)
1. **dev2:** the model wrote every sum as <<expr>> in a special format. Plain got 8/16 and calculator 7/16. The model broke the special format on clock times and weekdays.
2. **dev3:** the calculator learned bare clock times and weekdays. Plain and calculator tied at 14/28. The special format made its planning worse.
3. **dev4 (this design):** identical prompt, and the calculator fills in each "=". Plain got 13/28 and calculator 18/28, with 0 items worse. The 5 gains were all clock, weekday or arithmetic.
   - What's left is planning mistakes (a wrong sum set up) and missing-fact questions: 0/4 on both arms. The 1B never says "I'm not sure" here.

## Joining the agent
scripts/claude_think299_agent.py: install_think299(loop, model) wraps loop.turn. A turn goes to the think path only if all of these hold:
- it is a question;
- it has 2+ numbers, a clock time, a weekday with a number, or "how many" with a list;
- it names no one the notebook knows;
- it is not about "you".

Its behaviour:
- Read-only: it is checked to never write the notebook.
- If the 1B gives no answer line, it falls back to the inner loop.
- On the DEV bank of the end-to-end test it routes 0/194 turns, so fact answers can't change.

## Test
Blind thinkpanel299: 60 items written by a fresh Opus agent, sealed, with a blind Opus key audit (0/60 mismatches). Pass marks: artifacts/claude-rsn299-20260924/PASSMARKS.md.

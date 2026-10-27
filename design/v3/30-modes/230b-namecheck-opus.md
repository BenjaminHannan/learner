# 230b — a name check must compare the name (Opus)

**Problem.** 219's grounded D8 reply answers "Yes. Your name is <stored>." without looking at the name the user
asked about. So "Is my name Quenby?" after "My name is Ottilie." got a false "Yes." 230 kept that behaviour
on yes/no turns.

**Change.** scripts/claude_loop230b_agent.py wraps loop230. Only on a reply line that already starts
"Yes. Your name is ", asked_name() pulls a specific name out of the turn, using a few patterns: "Is my name
[really] X", "Is X my name", "Am I [called|named] X", "Did/Have I say/tell you my name is/was X", "Do you
know/remember my name is X", "Do you have me down as X". The name must be 1-3 words, contain no stop-words
and no "or", and be capitalised unless the whole turn is lower case. The name is compared with
N173.current_name, case-insensitive, on the whole name. If they differ, the reply is "No. Your name is
<stored>.". Routing is not widened and nothing is written. The 228 guard is installed and SrcGuardMixin228
comes first.

**Result.** Sealed verdict FAIL, on one sub-bar only (M1(c) 10/11). The miss is n230b-027 "My name's
Sorrel, right?": 230 already answered it without "Yes.", and 230b leaves it unchanged. All other marks
passed: 0 false yes, 10/10 NO fixes, 0 writes, 0 suite moves, smoke identical, +0.035 ms.
See artifacts/claude-namecheck230b-20260922/RESULTS.md.

**Open.** Tag questions and statement-questions ("My name's X, right?", "I'm X, aren't I?", "So my name
is X?") do not reach the name path. They get 230's "Your name is X." or a refusal. Handling them means
widening the route, so it needs its own experiment. "X or Y" choice questions are also not handled.

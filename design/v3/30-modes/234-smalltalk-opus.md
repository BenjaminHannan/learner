# 234 — One honest small-talk reply (Opus)

## Problem
The family demo opens with "Hi, how are you?". On loop138i that kind of turn
gets either the self router's mode-status line ("Right now I am back in
LISTENING mode, waiting for your next turn.", 24 of 40 dev phrasings) or the
generic decline (16 of 40). Both are confusing answers to a greeting.
Greeting-only turns ("Hi") already get 156b's fixed reply
"Hi! Teach me like ... Ask me like ...".

## Design (one change, reply-only)
scripts/claude_loop234_agent.py wraps loop138i read-only. The 138i turn runs
verbatim first (all logs/state are 138i's); then, only if the WHOLE turn
matches a closed grammar and the turn wrote no fact, the reply is replaced by

    I'm here and ready to learn. Tell me something, or ask me about what you've told me.

with 138i's greeting opener "Hi! " in front when the turn began with a
greeting (hi/hey/hello/hiya/howdy/yo/good morning/afternoon/evening, optional
"there", optional address "Premonition"). The grammar: optional greeting,
then one or more wellbeing cores about "you" (how are you / how r u / how
are you doing|feeling / how you doing / how have you been / how's it going /
how are things / how's everything|life|your day / how was your day / how do
you do / how do you feel / are you ok|okay|alright|well|good / you good ...),
each with optional time tails (today, lately, this morning, these days, now,
then). Any leftover token (a person's name, "that", "different", a second
real question) means no match, so "How is Kim?", "How are you, Kim?",
"How are you doing that?", "Hi! Where does Kim live?", status questions and
greeting-only turns keep 138i's reply byte-for-byte.

The reply claims no feelings (CANNOT sheet: cannot feel feelings). It says
only true things: the assistant is running and learns from what it is told.

## Not changed / not collided with
227/227b/227c identity sheet (name, maker, age, home) is untouched; no
identity template is a wellbeing core. "What's up" / "sup" are deliberately
NOT included (closer to a status question). Other bugs seen in passing
(e.g. "How many people do you know?" -> "I know 0 people: ." on an empty
notebook; "Hey there" alone not greeted) are out of scope.

## Evidence
See artifacts/claude-smalltalk234-20260922/RESULTS.md.

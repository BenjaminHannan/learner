# SPEC-COPY for exp 282 (copied from design/v3/30-modes/280-282-chat-fixes.md on origin/main)

Source document title (line 1):

# 280, 281, 282: three chat fixes from the chat-demo probe. Director's note, 2026-09-23 04:30 UTC

The "282" section, copied verbatim:

## 282: casual greetings and closings get small talk, not an error

Problem: "hey whats up" (t07-t0) gets "I didn't understand that question"; "Thanks, that's all!" (t01-t7) gets
"I didn't understand that well enough to save it". Bare "Thanks!" and "cool thanks!" already work.
The one change: the small-talk recogniser also accepts greetings and closings that are lowercase, lack
apostrophes or end marks, or carry a short closing tail ("that's all", "that's it", "bye for now", "see ya").
Only whole turns that are pure small talk; a turn with any fact or question content keeps its old route.
Marks: M1 smallpanel282: at least 90% of small-talk items get a fitting small-talk reply (260 arm shown);
0 writes on small-talk items; mixed items (small talk + a fact or question) keep 260's route and result exactly.
M2 frozen suites as in 280. M3 smalltalkpanel234 re-run once: every figure equal or better than 260.

Panel spec (smallpanel282, 60 turns): 20 greetings (casual, lowercase, slang, no punctuation), 15 thanks and
closings with tails, 15 mixed turns (a greeting or thanks plus a real teach or question, e.g. "hey, whats Ana's
city"), 10 controls. Fictional names only.

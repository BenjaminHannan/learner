# 0.2d gates, ADDENDUM-18: reader gate H-R (lis-320); training-data rule. Written 2026-09-26 16:47 UTC, before any run

Ben 16:39 UTC chose "Use GLM" (goals page 5f38f110e): nothing a model trains on, whether inputs, labels or targets,
is written or judged by Claude. At 16:46 UTC he chose "Retrain first" on the card "Retrain the chat reader without
Claude-written text before the first demo?" (cmsg_01FuvegZXjMmeUzStiEFVnEWPUML5zbDHC1nUneKzr3h9V).

## H-R: the reader gate (third headline gate, beside H-A and H-B)
- 0.2d's reader is lis-320 (owner: Reading facts). It is trained on GLM-written chats, with labels written and checked by code.
- PASS = it matches lis-319f on a fresh test that Reading facts seals before lis-320 trains, with marks fixed in that seal.
- lis-319f is not a fallback. If lis-320 falls short, 0.2d waits. ADDENDUM-12's reader line ("lis-319f") is replaced.
- Gate order: H-A (358b3 reasoner), H-B (sleep retention), H-R (reader). All three must be verified PASS before any
  0.2d code is sealed.

## Sleep data (H-B), checked by Fix sleep at 16:47 UTC
- dl-6: every trained row is a code-made number puzzle plus the 1B's own answer, kept only if code checks it right.
  That is 0 GLM rows, 0 Claude-judged rows and 0 Claude-written targets.
- The one Claude-written piece is the one-sentence instruction frame around every input (claude_blurt1.puzzle_prompt).
  It is the same in both arms. dl-6 runs as sealed.
- 0.2d's own sleep uses a GLM-written frame in place of that sentence.
- Whether dl-6's PASS can stand as H-B despite the shared frame is the Thread manager's ruling. If not, Fix sleep
  runs dl-6c with a GLM frame and that decides H-B.
- Creative's blurt data is asked separately and is registered when it answers.

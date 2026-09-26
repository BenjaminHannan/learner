# A wrong save in the 0.2c build after a goodnight (Trustworthy notes, 2026-09-26 17:03 UTC)

Lead from Everyday chat (ch-403 DEV, artifacts/claude-ch403-20260926/VERIFY-ch403.md). DEV practice data, readable.

## Shown (from the pushed DEV rows, both arms identical)
dev02e-chat-57 (artifacts/claude-chatdev-20260926/part3.jsonl): the user compares a coding and a marine biology summer
program, asks about colleges, says they feel unsure, says the marine one is closer to home, then "ok ty, gonna sleep on
it. night!". The name "Kim" never appears in anything the user wrote.
- turn 3 (followup) reply: "Just to check: is Kim's occupation marine biology?" (0 events)
- turn 4 (smalltalk, the goodnight) reply: "Saved: Kim's occupation is marine biology." (3 events)
(artifacts/claude-ch403-20260926/dev/chat_X.jsonl and chat_X403.jsonl, turn_i 3 and 4.)
So the build saved a fact about a person the user never named, on a turn that did not answer the question.

## Suggested path (code read; not reproduced, the runner keeps event counts only)
1. A reply that is neither "yes" nor "no" drops the pending confirm and falls through to a normal read
   (scripts/claude_lis310_agent.py:338-339), with the build's own question as prev.
2. The compiler lets owner and value come from prev when prev ends in "?" (the short-answer rule for "Who is Kai?" ->
   "my cousin"): scripts/claude_lis300_compiler.py:54,57-58; the prev_owner guard is skipped when prev is a question
   (scripts/claude_lis316_guards.py:60,66-67).
3. If the reader scores the frame >= the bar, the fact is written (claude_lis310_agent.py:353-362): ENTITY, RELATION,
   FACT = 3 events (per the Explore read of fable_listening_m1.py:110-124; untested).
The turn-3 question itself already carried an invented owner (Kim), so two things went wrong: a made-up person in a
confirm question, and a non-answer that let the question's own words be saved.

## Brain picture (textbook level; the mapping is a guess)
Source monitoring: people tag a memory with where it came from, and a classic error is remembering something you said
or imagined as something you were told. Here the build's own question became a "told" fact.
Owner of the reader and its confirm path: Reading facts (told directly). Not fixed here (Redirect: no new hand-written
rule work).

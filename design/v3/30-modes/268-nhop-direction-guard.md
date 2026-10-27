# 268: the n-hop reader answers backwards questions the wrong way ("Whose spouse is Dana?")

Director (Opus, reasoning line), 2026-09-23 ~05:20 UTC. New file; nothing edited. Diagnosis by the Muse builder rsn-nhopdiag (artifacts/claude-nhopdiag-20260923/DIAG.md on builder-outbox), checked against the code by me.

## Result first
A backwards question about a value V ("Whose spouse is V?", "Who is married to V?", "What has V written?", "What did V found?") gets a wrong answer when V itself has an outgoing fact of a relation the n-hop reader knows (a "chain"): the reply is V's own forward fact ("V's spouse is W."). Stored facts are never damaged (0 of 66 teaches wrong); only the reply is wrong. Builder's count: 12 of 12 such dev dialogs wrong, 0 wrong on controls.

## Cause (checked in code)
- scripts/fable_bench92_english_arm.py `compose_n_hop` (lines ~214-242): takes the single entity named in the question as `start` and walks only forward (`if s == cur`). The coverage gate checks that each walked relation is mentioned in the question, never its direction. So in "Whose spouse is V?", `start` = V and the walk follows V's own spouse edge.
- scripts/fable_loop138_agent.py `_hear_question` (lines ~122-131): the nhop frame is tried before everything below it, so the correct reverse path (190 reverse / 221 table inverse) never sees the turn.
- Relations without an n-hop cue word (boss, mother, friend) are not affected (8/8 right): the reader returns None and 190 answers.

## The one change
268 = base + one question-side direction guard around the nhop frame: when the question is backwards-shaped about `start` (the value slot: "Whose R is V?", "Who is/was R'd to V?", "Who is married to V?", "What has/did V <verb>?" where the verb is the relation's own verb, "Who has V as their R?"), the nhop frame is not used and the turn falls through unchanged to the layers below (190 reverse, 221/237 table inverse). Forward n-hop questions are untouched. No writes.

## Also found, NOT in 268 (logged)
With a same-relation chain ("X's author is P. P's author is M."), the forward one-hop question "Who wrote X?" over-walks to "X's author's author is M." (the walk goes to the sink). It needs a nonsense-looking chain to trigger. A separate follow-up if it shows up in real chats.

## Base, marks, falsifier
Base 138m (accepted; the guard is a wrapper that carries over to 138n/138p at the next merge). Built in parallel.
- M1 blind panel nhoppanel268 (spec-only writer): reverse_chain >= 22/24 right (all gold subjects named), 0 wrong over all items, uncued_reverse / forward_* / abstain byte-identical to 138m, 0 question writes.
- M2 frozen suites vs 138m's saved rows: moves exactly predicted; 0 new WRONG/WRONG-WRITE/lost OK (rt136 and bench have n-hop items; any forward n-hop move is a failure).
- M3 138m's restart + verifier dialogs: 0 ghost answers, 0 write changes, every reply change predicted. M4 latency <= +5 ms.
What would prove it wrong: any reverse_chain item still answered with V's own forward fact, any forward n-hop reply change, or any new wrong value.

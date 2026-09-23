# 266: two-step questions whose subject is a chain ("Where does Ana's boss live?")

Director (Opus, reasoning line), 2026-09-23 ~04:30 UTC. New file; nothing edited. Found by the chat-demo probe of 90 fresh turns (runs/chat-weakspots on builder-outbox). Those chats are dev material only.

## Result first: the question reader fails, not the reasoner

I ran 22 probes on 138n (the cloud copy, CPU). Each question was asked twice, once with a plain name ("Tovi") and once with a chain ("Ana's boss", after "Ana's boss is Tovi."):

| Question form | plain name | chain subject |
|---|---|---|
| "What is X's city/job?", "Who is X's mother?" | right | **right** (reasoner walks the chain) |
| "Who is the boss of X?", "What town does X live in?" | right | **right** (174 chain-of, 158c wh-city) |
| "Where does X live?" | right | "I didn't understand that question" |
| "Where was X born?" | right (221 rekey) | didn't understand |
| "Where does X work?" | right (138 n-hop verb) | didn't understand |
| "When is X's birthday?" | right (221 table) | didn't understand |
| "When was X born?", "Who does X work for?" | honest "I don't know" | didn't understand |
| "What does X do?" | didn't understand | didn't understand |

So the notebook and the chain reasoner already answer "Ana's boss's city" (stage `fake`, the base reasoner: "Ana's boss's city is Oslo."). The question readers that turn a verb or "when" question into a relation (the 221/237 table stages, the 138 n-hop verb reader and the base "where does X live" reader) only accept a **single name** as the subject. A possessive chain in that slot makes every one of them miss, and the turn falls through to "I didn't understand that question."

## The one change

**266 = base + one outermost ears stage, "chain-subject lift", for questions only.** When a question ending in "?" has a possessive chain as its subject ("A's R1", "A's R1's R2", "my R1", "my R1's R2"):
1. Swap the chain for one placeholder name that is not in the notebook, and hear that rewritten question through the whole existing stack in a dry, write-free way (the 221c pattern: only when it gives exactly one one-hop ask frame, with relation R and the placeholder as subject, and no write).
2. Then hear the canonical possessive question "What is <chain>'s R?" (for a person-valued R: "Who is <chain>'s R?") through the whole stack, and serve that reply. The base reasoner already answers it ("Ana's boss's city is Oslo."), gives "I don't know …" when a link is missing, and never writes.
3. In every other case the turn passes through byte-identical.

Why this option (director decision, logged; clearly better for the model):
- It reuses every verb and "when" phrasing the readers already know, instead of adding a new list of phrasings.
- The answer comes from the chain reasoner, which respects corrections and abstains when a link is missing.
- It is a question-only stage, so it can never write.

It does not add new verb phrasings: "What does X do?" fails for plain names too and stays out of 266.

## Base

The base is 138m, the newest accepted base. 138n and 138p are not accepted yet, and 266 is an outermost stage, so it carries over to them unchanged at the next merge. It is built in parallel and not ordered after 138nb and 138p, because nothing it needs depends on them.

## Marks (fixed before any build)

- M1, blind panel chainpanel266 (written from a spec only; run once after both seals):
  - chain_verb ≥ 90% right;
  - 0 wrong values over all items;
  - broken_chain: 100% honest abstain (a missing link must never be filled with a guess);
  - 0 question writes;
  - plain_control byte-identical to the base.
- M2, frozen suites (rt136, rt143 no-gate, sessions152, bench, marks123) vs 138m's saved rows: moves exactly the predicted list; 0 new WRONG, WRONG-WRITE or lost OK.
- M3, 138m's restart and verifier dialogs: 0 ghost answers, 0 write changes, and every reply change predicted.
- M4, latency: median added time ≤ +5 ms per turn.

## What would prove it wrong

- Any wrong value on a chain question: for example, the lift answering about "Ana" instead of "Ana's boss".
- Any answer given when a link is missing.
- Any reply change on a turn with no chain subject.

# 221b -- stored-relation fallback for questions (Opus)

Status: built 2026-09-22. Results: artifacts/claude-storedrel221b-20260922/RESULTS.md.

## The one change
StoredRel221bMixin (scripts/claude_loop221b_agent.py) sits outermost on the 221 ears.
It acts only on turns that end in "?", and it only produces an ordinary one-hop ask.
It fires in two cases:
- (A) the whole 221 stack understood nothing, or
- (B) 221 made a single one-hop ask on a known subject, and that key has no answering row.

When it fires, it reads the question against the relation keys the subject already holds
as active **taught** facts. Inferred, sleep-derived, web, proposed and forgotten rows are
never read. If exactly one key matches, the loop answers from that key, and the reply names
the key ("Tova Renn's landlord is Ada Wren."). With 0 matches, or 2 or more, the 221 reply
stays exactly as it was.

## Matching (sealed)
- The question must start with a question word (who, whom, what, which, when, where).
  "Do you know" / "can you tell me" in front is allowed. "Whose" is refused, and so are
  yes/no questions and any other "you" word.
- Exactly one subject: one known name, or the user ("my", "me", "I").
- Backward readings are refused:
  - the subject comes right after "by";
  - the question has "of" but the subject does not follow it;
  - "Who/What does SUBJECT ...".
- Every content word of the question must match a word of the key after a small suffix
  rule: founded~founding, graduate~graduation, coaches~coach, owns~owner.
- Key words the question leaves out must be generic (date, year, day, time, name, place,
  city, town, country, location).
- The question word must fit the key:
  - "when" needs a time word;
  - "where" needs a place word;
  - "who" needs neither.
- There are no synonym lists (doctor ≠ physician, boss ≠ supervisor).

## Why this and not more table rows
The old 221 misses came from keys that were not in the table. This change reads the keys
the notebook already holds, so it needs no new rows. It can only repeat something Ben
taught, word for word, under that exact key.

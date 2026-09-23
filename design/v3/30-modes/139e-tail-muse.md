# 139e — relation-gated unknown-tail clarify (design)

Follow-up to the registered FAIL of 139d. 139d's clarify ("Kim's city is
Rome honestly" -> `Did you mean "Rome"? Please say it again without the
extra words.`, 0 writes) worked on chat, but its trigger was too broad:
bench values "Gaelic football", "American football", "Wa language" end
in a lowercase word, the guard clarified mid-chain, and G1 got 20 new
wrong (RESULTS.md in `artifacts/fable-tail139d-20260922/`).

## THE ONE CHANGE vs 139d

The same trigger and reply, but ONLY when the teach/correct action's
relation is in the closed listed set below. Everything else is
byte-identical to loop139c (base agent: `scripts/fable_loop139c_agent.py`,
config `artifacts/fable-tailwords139c-20260922/loop139c-config.json`;
139d/139c code reused by import, no 139d/139c file edited).

Closed listed set (fixed here and in `scripts/fable_fix139e_tail.py`
before any panel read; normalised exactly as FakeEars._relation does —
lowercase, spaces to "_"):

- person-valued: mother, father, sister, brother, sibling, spouse,
  husband, wife, boss, friend, teacher, coach, pet, dog
- place-valued: city, town, hometown (home_town spelling too), country,
  birthplace (place_of_birth spelling too), school

NOT listed (byte-identical to loop139c whatever the value shape): sport,
language, genre, occupation, food, drink, color, instrument, and every
other relation, including all declarative bench73 template keys
(capital, continent, country_of_citizenship, manufacturer, notable_work,
religion, author, founder/founded, director, performer, educated_at,
headquarters, head_of_state/government, place_of_death, position_played,
creator, developer, employer and the rest) and the chat relations motto,
song, band, film, book, hero, lunch. Derived from the relation table
loop139c's probe uses (boss, city, coach, pet, school, teacher, town)
extended to the closed person/place set in the 139e brief; the
unlisted side is exactly where 139d's killers live (sport, language).

Trigger (copied verbatim from 139d, never redefined): after 139c's
strip, value's FIRST word starts A-Z and its trailing RUN of words is
all `[a-z]+`, none a name connector (of, the, and, de, da, del, della,
di, du, des, van, von, der, den, la, le, les, y, e, al, el, bin, ibn,
upon, on, in, at, for, a, an, to, with). Fires -> clarify, 0 writes,
exact reply `Did you mean "<clean>"? Please say it again without the
extra words.` Missing/empty relation never fires (safe default).

## Where it sits in loop139c

Step 1 locations (read before building): 139c's strip
`scripts/fable_fix139c_tail.py:46`, applied at
`scripts/fable_loop139c_agent.py:66` (ears hear) and `:82` (loop _act);
value extraction `scripts/fable_agent_loop.py:136`; 139b guard
`scripts/fable_fix139b_valueguard.py:99`. The 139e mixin
(`scripts/fable_fix139e_tail.py:RelationGatedTailMixin`, wired in
`scripts/fable_loop139e_agent.py:Loop139eEars.hear` and
`Loop139eAgentLoop._act`) checks at the same two levels after the full
139c chain. `turn()` inherited verbatim.

## Known edges (accepted before the run)

"maybe"/"probably" never reach any guard: base ears split-clarify first
(byte-identical both arms, locked as O19/O20). Lowercase-start values
keep loop139c's exact behaviour including dirty correction prompts
("black honestly", locked as O21). Listed-relation connector-ending
names ("Salt Lake City", "Joan of Arc") never fire. A listed-relation
value shaped like Capitalised + common noun (e.g. a city really called
"Green Valley") IS questioned — accepted, reported honestly.

## What the run taught (load-bearing)

The gate landed exactly on 139d's diagnosis: bench killers teach
sport/language (unlisted), so all 5375 bench triples scan 0 hits and G1
passes 0 moves / 0 new wrong; the 9 static chat-suite hits were
over-matches (base hearsay/multi-fact/question paths fire first, all
verified byte-identical pre-seal), so G2/G3 pass with 0 moves. Chat
behaviour kept: 27/27 listed-relation tails clarify exactly, 0 writes.

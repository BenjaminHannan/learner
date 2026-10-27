# 139d — unknown trailing chat words get a clarify (design)

Director probe 05:16 on loop139c (which strips a closed list): "Kim's
city is Rome honestly" saves "Rome honestly"; "Kim's mother is Rose tbh"
saves "Rose tbh". A closed list will always miss words.

## The one change

After 139c's strip, if a teach/correct value's FIRST word starts with
A-Z and its trailing RUN of words is all all-lowercase letters
(`[a-z]+`), none a name connector, the turn does not write and replies
exactly: `Did you mean "<clean>"? Please say it again without the extra
words.` The connector list is closed, fixed in
`scripts/fable_fix139d_tail.py` before any panel read: of, the, and, de,
da, del, della, di, du, des, van, von, der, den, la, le, les, y, e, al,
el, bin, ibn, upon, on, in, at, for, a, an, to, with.

Lowercase-start values ("black", "pizza", "green tea") and
all-Capitalised or connector-ending names ("Salt Lake City", "Take
That", "Lord of the Rings", "Leonardo da Vinci", "House of Wax") never
trigger and stay byte-identical to loop139c.

## Where it sits in loop139c

Step 1 locations. 139c's strip: `scripts/fable_fix139c_tail.py:46`
(`strip_chat_tail`), applied at `scripts/fable_loop139c_agent.py:66`
(ears `hear`) and `:82` (loop `_act`). Value extraction:
`scripts/fable_agent_loop.py:136`. 139b guard:
`scripts/fable_fix139b_valueguard.py:99`. The 139d mixin subclasses
loop139c and checks at the same two levels: ears `hear()` turns
unknown-tail teach/correct actions into clarify actions after the full
139c chain, and loop `_act()` 139c-sanitizes first, then returns
`{"kind": "clarify", ...}` with no write (covers the inner-chain path).
`turn()` is inherited verbatim; no loop139c file is edited.

## Known edges (accepted before the run)

A real value shaped like Capitalised + common noun IS questioned
("Pad thai" -> `Did you mean "Pad"?`, reported honestly). "maybe" /
"probably" never reach the guard: base ears split-clarify first
(byte-identical both arms). Lowercase-start values keep loop139c's
exact behaviour, including dirty correction prompts ("black honestly").

## What the run taught (load-bearing)

Bench sentences carry real Capitalised + common-noun values ("Gaelic
football", "American football", "Wa language") that the sealed rule
cannot tell from chat tails: the guard clarifies, the chain breaks, the
answer goes wrong (G1 20 new wrong, G2 bench detail 11 + 2). The rule as
sealed is too broad for declarative bench prose; a follow-up needs a
common-noun allowlist or a narrower trigger. Names, titles, and suite
prose are unaffected (probe 65/65, G3 0 moves).

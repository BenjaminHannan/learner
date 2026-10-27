# corrpanel401: a correction-heavy conversation bank (spec for the blind writer)

Wrong-as-fact thread, 2026-09-26, for sf-401 (plan: design/v3/30-modes/401-stale-fact-guard.md). This file is the
whole brief the blind writer gets. The bank is TEST-ONLY: never trained on, tuned on, quoted or read by builders.
It is written into the project's shared folder (escrow-401/), audited there by a second blind agent, and copied
unread into artifacts/claude-sf401-20260926/panel/ with its SEAL hashes before the registered run.

The format is exactly the 331 end-to-end bank format (month-end/331-e2e-bank-spec.md, "Files a writer produces"),
so the 336 runner and scorer read it unchanged. What differs is the mix: many corrections, questions after them,
and ordinary questions about facts that were never corrected.

## What a "life" is

One fictional person (the "user") chatting with a personal assistant that keeps a notebook of facts about the
user and the people and pets in the user's life. A life is 3 days of chat. Between days the assistant sleeps and
restarts. Each day has 5 to 9 user turns. The user writes casually, like texting a helpful friend: contractions,
lowercase, the odd typo, several facts in one message, facts mentioned in passing.

## Size and names

- 24 lives, ids `sf-t-01`..`sf-t-24`.
- All names (people, pets, towns, companies, schools, clinics) are freshly invented and fictional. Never use a real
  public figure. No two lives share a person or pet name. Real countries and big real cities are allowed as places.
- Keep people's first names ordinary-looking but invented or uncommon (not the most common English names).

## Turn kinds (whole bank of 24 lives)

| kind | minimum | notes |
|---|---:|---|
| `teach` | 120 | one fact (50), 2-3 facts in one message (40), fact in passing or in an aside (30) |
| `correct` | 60 | 2 or 3 per life, on day 2 (at most 12 on day 3 before that life's asks); see "Corrections" |
| `nosave` | 15 | hypotheticals, plans and wishes, jokes, "we"/"our" facts where who "we" is stays unclear |
| decoy turns | 30 | ordinary `teach`, `nosave` or `smalltalk` turns that look near a correction but are not one; see "Decoys" |
| `ask` edit | 60 | asks whose right answer depends on a corrected fact; see "Questions after a correction" |
| `ask` one-hop | 60 | about facts that were never corrected |
| `ask` two-hop | 20 | two never-corrected facts joined ("where does my sister's boyfriend work?") |
| `ask` reversal | 12 | taught one way, asked the other; never-corrected facts |
| `ask` yes/no | 20 | about never-corrected facts; gold `yes` or `no` |
| `ask` never-told | 12 | never taught, about people or things that exist in the life; right answer is "I don't know" |
| `smalltalk` | 30 | greetings, thanks, venting a bit |

At least 40 of the `ask` turns are on day 3 about facts taught on day 1 and never corrected.

## Corrections

A correction changes a fact the user taught earlier in the same life (usually day 1). Every corrected fact must
be a fact with ONE current value: where someone lives (city), where they work (employer), their job, their age,
their school or what they study, a pet's kind of animal, a partner or boss, and so on. Never correct a relation
where several values are normal (a sister, a friend, a child, a pet) by adding a second one; that is a decoy (below).

Spread the wording across these styles, each used at least 8 times in the bank:
1. the user's own mistake, old value named: "wait i said kelvey works at Brasswick, it's Morrow & Tull actually"
2. the user's own mistake, old value not named: "oh i told you wrong about dov's job, he's a welder"
3. a real change, old value named: "Isra isn't in Leeds anymore, she moved to York in june"
4. a real change, old value not named: "update: my brother got a new job at Pellam Dairy"
5. a negation plus the new value: "ok correction: Moss is NOT a rabbit, he's a guinea pig"
6. a correction said in passing inside another message: "anyway since ottilie moved to Galway she's been so happy"
The correction turn's `facts` holds the new fact; truth.jsonl closes the old fact (`valid_until_turn` = this turn)
and adds the new one.

## Questions after a correction (`ask` edit, 60)

- Per life 2 or 3, after that life's corrections, most on day 3.
- At least 25 are one-hop about the corrected fact ("where does Isra live now?" gold York).
- At least 20 are two-hop through the corrected fact, either hop ("what city is my brother's work in?" where the
  employer was corrected, or "where does my boss live?" where the boss was corrected).
- At least 10 are yes/no about the corrected fact, with gold `no` for the old value ("is Isra still in Leeds?") or
  `yes` for the new value; use `gold.type` "yes" or "no" with `ask_type` "edit".
- Some questions should not reveal that anything changed ("where does Isra live?"), some should hint at it
  ("where does isra live these days?").

## Decoys (30 turns, listed in decoys.jsonl)

Ordinary turns that look close to a correction but change nothing already taught. Each one sits near a taught
fact (same person, same town, or the same relation) and must NOT change it. Mix these:
- a second value where several are normal: "my other sister Ione is visiting" (the first sister stays);
- someone else with the same town or employer: "funny, my dentist also lives in Leeds";
- a visit or trip, not a move: "Isra is in York for the weekend" (she still lives in Leeds);
- a past fact said as past, when the current value is unchanged: "Dov used to be a welder before he trained as a
  nurse, years ago" only if the nurse job was already taught as current;
- a question the user asks themselves or a plan: "should my brother move to Pellam? he keeps talking about it".
After each decoy, at least one later `ask` (one-hop, two-hop, reversal or yes/no, not `edit`) checks the fact the
decoy sat near, with the unchanged value as gold.

## Files the writer produces (JSON Lines, UTF-8), in /mnt/project-files/escrow-401/

- `turns.jsonl` and `truth.jsonl`: exactly the keys and rules of the 331 spec (month-end/331-e2e-bank-spec.md,
  "Files a writer produces"): `life_id`, `day`, `turn_index` (0-based within the life, across days), `user_text`,
  `kind`, `ask_type`, `facts`, `gold` (`values`, `type`, `uses_facts`), `creative_seed_facts` ([] throughout; no
  creative turns in this bank); truth rows `fact_id`, `life_id`, `owner`, `relation`, `value`, `taught_turn`,
  `valid_until_turn`. `owner` is `USER` for the user. For `edit` asks, `gold.uses_facts` includes the NEW fact.
- `decoys.jsonl`: one object per decoy turn: `life_id`, `turn_index`, `near_fact` (the fact_id it sits near),
  `style` (one of: second_value, same_value_other_person, visit_not_move, past_said_as_past, plan_or_question),
  `checked_by` (turn_index of the later ask that checks it).
- `corrections.jsonl`: one object per `correct` turn: `life_id`, `turn_index`, `old_fact`, `new_fact`, `style` (1-6
  as numbered above).
- `README.md`: counts per kind, ask_type, day, correction style and decoy style, with no items quoted.

## Checks the writer runs before finishing (reported as counts only)

1. Every line parses and has exactly the keys above.
2. Every `gold.uses_facts` id exists in truth.jsonl, was taught before the ask's turn and is not closed before it.
3. Every value in `gold.values` equals the value of the fact it comes from, as it stands at the ask's turn.
4. Every corrected fact is closed at its correction turn and its replacement starts there; no fact is closed
   anywhere else.
5. No `ask` other than `edit` depends on a corrected fact; every `edit` ask depends on one.
6. No name repeats across lives; minimums above are met.
7. Each decoy's `near_fact` is still valid after the decoy and its `checked_by` ask uses it.

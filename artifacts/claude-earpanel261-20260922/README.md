# Ear panel 261 (blind reader panel), 2026-09-22 — TEST-ONLY

This is a fresh test panel for the "reader": the part that turns one chat
turn into the facts it states (TEACH) or the question it asks (ASK). It was
written blind. The author read only the task spec, the shared rules file, and
the schema and judgement-call sections of the panel-235 README. No code,
relation tables, training data, design notes, results, other briefs, other
panels, or builder folders were read. All person, place, company, pet, and
language names are invented for this panel. Category-level report only: this
file never quotes an item.

Files:
- `panel.jsonl`: 150 items, one JSON object per line.
- `make_panel.py`: generator. It holds the items by hand and writes the file
  deterministically. Run it from the repo root with
  `/usr/bin/python3 -B artifacts/claude-earpanel261-20260922/make_panel.py`.
  It checks family counts, block order, duplicate turns, verbatim
  subject/value presence, every R1–R12 quota, the lowercase/typo and no-"?"
  counts, schema exactness (including chain_aliases), multiword names in the
  full-name family, and a forbidden-name screen.
- `SEAL.sha256.txt`: SHA-256 of `panel.jsonl` and `make_panel.py`.

## Families

| family | items | clear: false |
|---|---|---|
| plain_teach | 25 | 0 |
| varied_teach | 30 | 0 |
| full_names | 15 | 0 |
| questions | 25 | 2 |
| chain_questions | 15 | 1 |
| no_save | 25 | 13 |
| corrections | 15 | 0 |
| **total** | **150** | **16** |

## Item format

- Each line is exactly {id, family, turn, gold, clear, notes}.
  ids run e261-001 … e261-150 in family-block order.
- TEACH frame: exactly {act, subject, relation, relation_aliases, value}.
  subject and value are the exact words from the turn in the same case.
  `me` stands for the speaker and covers plural owners.
- ASK frame: exactly {act, subject, relation, chain, relation_aliases,
  chain_aliases}. chain is null for one hop; for two hops it is
  [first relation, second relation], relation is the second one, subject is
  the start person, and chain_aliases is [aliases of hop 1, aliases of hop 2]
  with the second list equal to relation_aliases.
- Every relation carries one fixed alias list everywhere it appears.
- notes holds comma-separated risk tags (R1–R12, lower, typo, noq) plus the
  word "correction" in the corrections family.

## Judgement calls

- Pronouns spanning two clauses resolve to the named person; the later
  frame's subject is that resolved name.
- The verb decides school-vs-workplace: teaching or coaching at a named
  School, College, or Club is workplace; studying there is school.
- A move described as completed counts as current city.
- Statement-shaped confirmation checks save nothing, even without a
  question mark; they are flagged unclear because a question reading is
  also defensible.
- Declarative turns that merely mention a question word state their fact.
- Plans, goals, and wishes save nothing on their own; when a turn pairs a
  plan clause with a separate current fact, only the fact is gold.
- Pretend and hypothetical turns save nothing.
- Plural-relative turns carry one frame per named person for the relation
  plus each person's other stated fact.
- Appositive-relative turns carry the relative frame plus the other fact.
- After a named introduction of B, a following pronoun is read as B.
- Plural-owner turns (plural pronoun plus a relative, pet, home, workplace,
  or neighbour) belong to the speaker.
- A do-for-work question is job (flagged unclear: workplace is also fair);
  a yes/no existence question keeps its ASK gold (flagged unclear).
- Hearsay, opinion, news, past-habit, suggestion, and vague turns save
  nothing; hearsay, opinion, and suggestion are clear, the rest unclear.
- Corrections keep only the new value; negated old values are never gold.

## Risk quotas (counts only)

| tag | count | bar |
|---|---|---|
| R1 (varied_teach + full_names) | 13 | >= 8 |
| R2 no_save, empty gold | 9 | >= 8 |
| R2 no_save without "?" | 5 | >= 5 |
| R2 varied_teach with fact gold | 3 | >= 3 |
| R3 | 6 | >= 6 |
| R4 | 7 | >= 6 |
| R5 | 9 | >= 8 |
| R6 (in chain_questions) | 9 | >= 5 |
| R7 (teach families) | 7 | >= 6 |
| R8 total / varied fact / no_save empty | 6 / 3 / 3 | >= 6 / 3 / 3 |
| R9 (no_save, empty gold) | 5 | >= 5 |
| R10 | 4 | >= 4 |
| R11 | 6 | >= 6 |
| R12 | 5 | >= 4 |
| lower or typo turns | 17 | >= 15 |
| questions + chain lower/noq | 6 | >= 5 |

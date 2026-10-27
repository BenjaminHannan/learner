# rp371 reader panel (TEST-ONLY)

> **TEST-ONLY. Never read, train or tune on this panel. Runners read it; scorers print counts only; never quote turns, names or facts.**
> It is used once, to compare two ways of deciding which of the reader's facts are safe to save. Do not open the rows to "have a look", do not copy their style into training data, and do not report individual rows in any log, review or chat.

Built 2026-09-25 by Claude for exp 371. Every turn was written fresh for this panel. None of it was copied or adapted from training data, the dev set, LoCoMo or LongMemEval.

## Files

| file | what it is |
|---|---|
| `panel.jsonl` | 240 rows with the answer key. Keys, in order: `id`, `prev_reply`, `turn`, `kind`, `facts`, `nosave_reason` |
| `blind_input.jsonl` | the same 240 rows in the same order, with keys `id`, `prev_reply`, `turn` only. This is the only file the reader should see |
| `README.md` | this file |
| `label_B.jsonl` | a separate blind labeller's labels, used for the audit |
| `label_B2.jsonl` | a fresh blind labeller's labels for the 28 changed rows |
| `AUDIT.md` | audit of the key against labels B and B2 (counts only) |
| `changed_ids.txt` | ids of the 28 rows changed by the audit, one per line |
| `changed_blind.jsonl` | blind input (id, prev_reply, turn) for those 28 rows only |
| `SEAL.sha256.txt` | sha256 of every file above except itself; check with `sha256sum -c SEAL.sha256.txt` inside this folder |

The ids run from `rp371-001` to `rp371-240`. Rows are shuffled with a fixed seed, so kinds are mixed.

SHA-256 of the final version, after the label-B and label-B2 audits (see `AUDIT.md`). `SEAL.sha256.txt` seals every file:
- `panel.jsonl` 79305fbc2b7c3960fc98a1f735a3b50daeb2a65a9044835f1ff5c82845e7af51
- `blind_input.jsonl` 835236b81ea6ce5f35cc38dd619b6f55c1c1f75809bab825b8e56baad5cd119d

## Counts

| kind | rows | facts | what it tests |
|---|---:|---:|---|
| long_multi | 60 | 202 | long, messy turns (25 to 70 words) with 2 to 5 facts buried in filler. 32 of them carry an easy-to-drop second fact (where someone lives or comes from, an age in an aside, a job in brackets) |
| trap | 50 | 155 | role swaps and wrong attachment: made/built/designed/wrote/painted (active and passive), a pet named beside its owner with both ages, chains like "A's daughter B and B's son C", languages, place of death vs birthplace, dates next to places |
| teach_single | 30 | 30 | one fact in a short casual turn |
| correct | 20 | 22 | the user fixes an earlier value, sometimes without the word "actually". Only the new value is in the key. Two rows also restate a relation that is plainly true |
| short_answer | 15 | 17 | prev_reply asks a question and the turn is a short answer |
| nosave | 45 | 0 | nothing should be saved |
| smalltalk | 20 | 0 | chat with names or feelings but nothing to save |
| **total** | **240** | **426** | |

`nosave_reason` counts: negation 7, plan 7, hypothetical 7, reported 7, question 6 (including "so X is Y" checks), our_we 6, sarcasm 5, smalltalk 20. The reason is null on all 175 fact rows.

Fact owners: 219 facts are owned by `USER` and 207 by a named person, pet or thing.

`prev_reply` is empty on 80 rows (one third) and set on the other 160. Some set replies are specific to the turn. Others are generic neutral openers that carry no names or facts.

## Key conventions

- **owner**: `USER` for the speaker (I / me / my). Otherwise it is the person's or pet's name written exactly as in the turn. A pronoun is resolved to the named person only when this turn or `prev_reply` makes it clear. A pet's own facts (age, breed) are owned by the pet's name. "my dog X" is `USER / dog / X`.
- **Made things** (trap rows): the owner is the thing's name as written, the relation is `creator` (or a narrower word such as `writer`, `director`, `restorer`, `logo_creator`), and the value is the maker.
- **relation**: a short plain lowercase word or snake_case phrase, e.g. sister, city, hometown, birthplace, place_of_death, year_of_death, job, employer, school, studies, age, breed, dog, language, nationality, hobby, creator. The key does not use a fixed relation list. A scorer that needs one should map synonyms (for example flatmate/roommate/housemate, colleague/coworker, partner/girlfriend) before comparing, or score owner and value only.
- **value**: the exact words from the turn, with the user's spelling. There is one exception. On a short answer that points to one of the options offered in the question, the value is taken from `prev_reply`. Every value appears as a whole-word span of the turn, or of `prev_reply` on those short-answer rows (case-insensitive). A single row may contain several facts with the same value, for example two relatives who share an age.
- **Corrections**: only the new value.
- **Plurals**: one fact per value.
- **Nothing is saved** for negations, plans, hopes, hypotheticals, reported claims, questions or checks, our/we ownership, sarcasm or small talk. Fact rows can also contain these as distractors next to real facts, and those distractors are not in the key.
- **Stated, not inferred**: a fact is in the key only when the turn clearly states it. A workplace mentioned in passing does not teach a job. An unnamed relative ("my dad", "my in-laws") owns no facts.
- **Past and side facts**: a past fact that is clearly stated (a former boss, where someone used to live) is in the key, with a relation that marks it as past. A stated side fact, such as the app someone uses or the course they started, is also in the key.
- **Titles**: no value or owner in the key carries a title (Dr, Mr and so on). Turns that had one were rewritten during the audit to use a plain name.
- Typos appear only in ordinary words, never in names or values.

## Checks (all passed at build time)

- 240 rows with unique ids in sequence, and the exact count for each kind and each nosave reason.
- Keys exact and in order, for both the rows and the facts.
- Every nosave and smalltalk row has `facts: []` and a reason. Every other row has at least one fact and a null reason.
- Every long_multi turn is 25 to 70 words and has 2 to 5 facts. Every teach_single row has exactly 1 fact. Every short_answer row has a `prev_reply` ending in a question mark.
- Every value appears in its turn (or in `prev_reply` on short-answer option rows). Every non-USER owner appears in the turn or in `prev_reply`. There are no duplicate facts within a row.
- `blind_input.jsonl` matches `panel.jsonl` for id, prev_reply and turn, in the same order.
- **Name check against the dev set**: a script pulled every capitalised word out of the dev set's turns (194 rows, 129 distinct words) and never printed them. It then compared every capitalised word in this panel (451 distinct) with that list, leaving out real countries, big cities and language names. The first pass found 11 invented names that also appear in the dev set, and all 11 were replaced. The final pass found 0 name overlaps. The only remaining matches are 6 ordinary words.

The build and check scripts are in the build session's scratchpad (`rp371/build.py`, `rp371/check.py`). They are not part of this panel.

# Ear panel 235b (blind reader panel), 2026-09-22

**TEST-ONLY.** This panel scores the ear, which turns one chat turn into the facts it states or the question it asks. Do not train on it, tune on it, or print its items. Builders must not open `panel.jsonl` or `make_panel.py`. They may read only this README.

The writer worked blind. The only inputs were the 235b spec, the Opus rules, and the schema and judgement-call sections of the 235 README. Every name is made up. No name or place comes from the 235 README's examples.

Files: `panel.jsonl` (150 lines), `make_panel.py` (the items were written by hand; the script writes the panel deterministically and runs the self-checks), and `SEAL.sha256.txt` (covers those two files).

## Schema

Each line is exactly `{id, family, turn, gold, clear, notes}`. The ids run from `e235b-001` to `e235b-150` in family-block order. Frames follow the 235b spec exactly:
- TEACH frame: `{act, subject, relation, relation_aliases, value}`.
- ASK frame: `{act, subject, relation, chain, relation_aliases}`. `chain` is null for one hop. For two hops, `chain` is [first, second] and `relation` is the second one.

`subject` and `value` are the exact words from the turn, in the same case. `me` stands for the speaker. A relation always carries the same `relation_aliases`, taken from one fixed table in the generator.

## Families and counts

| family | items | clear: false |
|---|---|---|
| plain_teach | 25 | 1 |
| varied_teach | 30 | 2 |
| full_names | 15 | 0 |
| questions | 25 | 1 |
| chain_questions | 15 | 0 |
| no_save | 25 | 15 |
| corrections | 15 | 0 |
| **total** | **150** | **19** |

## Diagnosed-risk items (tagged in `notes`)

- **R1**, pronoun reference across clauses: 12 items (9 in varied_teach, 3 in full_names). In 3 of them the pronoun refers to the speaker's relative and the turn also has a first-person clause.
- **R2**, questions shaped like statements: 12 items in no_save, all with gold []. They include tag questions, rising "so ...?" questions, a double "??", and lowercase questions with no "?". There are also 4 items in varied_teach that contain a question word but state a fact. Their gold is TEACH.
- **R3**, the verb decides the relation: 10 items (6 in varied_teach, 4 in full_names). They cover teaches, studies, coaches, works and lectures at a named place, plus research done at one. 1 of them is clear: false.
- Questions: 14 of the 40 one-hop and two-hop questions are lowercase or have no "?".

## Relations used (27)

best_friend, boss, brother, city, colleague, cousin, daughter, employer, father, favorite_food, grandmother, hometown, instrument, job, language, neighbor, partner, pet, place_of_birth, roommate, school, sister, sister_in_law, spouse, stepfather, uncle, workplace. `mother` appears only as the first hop of a chain.

## Judgement calls (rules)

- **Pronouns**: when a second clause uses a pronoun for a named person, that frame's subject is the resolved name as it appears in the turn. A pronoun that points to an unnamed person (for example, "my new boss ... her name is") is not tagged R1. That frame then has subject `me`, with the relation named in the turn.
- **Possessive pronouns** ("her wife", "his daughter") link the relation to the named owner.
- **A shared fact** ("X and her wife Y live in Z", "my wife X and i both speak Z") gives one frame for each person it covers.
- **The verb decides the relation**: teaches, coaches and lectures at a place give `workplace`. Studies at gives `school`. Works at, works for, started at and got a job at give `employer`. `employer` and `workplace` list each other as aliases, so either is accepted. A school, library or hospital noun inside the value never changes the relation. Doing research at a university gives `workplace`, clear: false, because a student reading (`school`) is also defensible. `school` is not in workplace's fixed alias list.
- **A job title plus a place** ("is the head chef at X", "a welder at X") gives two frames: `job` and `workplace` or `employer`.
- **Where someone is from**: "grew up in" and "originally from" give `hometown`, clear: false, because place of birth is also defensible. "born in" gives `place_of_birth`. When a turn states both birth and upbringing, each gets its own frame and the item is clear.
- **Current city**: "moved to", "been living in" and "lives in ... now" all give `city`.
- **Statement-shaped questions** (tag, rising, "??", no "?") have gold [] and clear: false, because an ASK is also a reasonable reading.
- **Question words inside statements** ("I know who ...", "guess where ...", "that's why ...") state a fact. Their gold is TEACH, clear: true.
- **Nothing is saved** for hearsay introduced by "says", pretend or hypothetical framing, opinions that name no link, future plans, beliefs attributed to someone else, a past-only city, a negation with no new value, news items, greetings or thanks. Hearsay introduced by "apparently", a past-only city and news items are clear: false.
- **Corrections** hold only the new value. A negated or "old" value is never in gold. If a correction moves an old name to a different relation instead of negating it, both frames are gold. Every correction's notes say "correction".
- **Typos are kept verbatim** in subject and value, including a misspelled job title. A lowercase subject in a question keeps its lowercase form.
- **Yes/no "have a" questions** ("Does X have a brother?") are ASK for that relation, clear: false.
- **Imperatives** ("tell me where ...") are ASK.
- **Verb-form questions** ("report to", "employs", "teach") map to boss, employer and workplace.
- **Two-hop questions** start from the named person, or from `me`. There are no three-hop items.
- **Reused names**: some names appear in more than one family on purpose. Every item is scored on its own turn only.

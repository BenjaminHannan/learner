# Our panel 265 (blind group-owner panel), 2026-09-23 — TEST-ONLY

Do not read this panel item by item, tune on it, or quote it. Category-level
counts only. Written blind: the author read only the task brief, the shared
rules file, the field/frame format section of the sibling panel spec, and the
schema/judgement sections of the panel-235 notes. No code, relation tables,
results, other panels, or builder folders were read. All names of people,
towns, companies, pets, languages, and cars in the panel are fictional.

Files:

- `panel.jsonl`: 80 items, one JSON object per line.
- `make_panel.py`: generator. Holds the items by hand, writes the file
  deterministically, and runs the self-checks. Run from the repo root with
  the uv prefix (see the script header). Checks: family counts, id order,
  no duplicate turn, exact key sets, ask_whose consistency with the group
  pronouns in the turn, TEACH frame shape, one fixed alias list per
  relation, species word present for pet frames, subject/value spans present
  word for word, and a forbidden-names screen.
- `SEAL.sha256.txt`: SHA-256 of `panel.jsonl` and `make_panel.py`, made from
  the repo root with `shasum -a 256 <both paths>`.

## Families

| family | items | ask_whose | gold | clear: false |
|---|---|---|---|---|
| group_owner | 30 | true | [] throughout | 2 |
| mixed | 15 | true | the non-group fact only | 0 |
| first_person | 20 | false | one speaker fact, subject "me" | 0 |
| named | 15 | false | one third-person fact | 0 |
| **total** | **80** | true: 45 / false: 35 | | **2** |

Topic spread in the group set covers pets, home/city, relatives, workplace,
cars, and languages, with lowercase turns and predicate-ownership forms
included. The mixed set pairs a group-owned clause with a speaker fact or a
named-person fact; gold keeps only the latter.

## Item format

- Each line: `{id, family, turn, gold, clear, notes, ask_whose}` and no other
  keys. ids run `o265-001` … `o265-080` in family-block order.
- `ask_whose` is true exactly when the turn carries a group owner or subject
  (first-person-plural or reflexive forms). Gold for such a turn holds only
  facts not owned by the group, so it is usually empty.
- TEACH frame: `{act: "TEACH", subject, relation, relation_aliases, value}`.
  `subject`/`value` repeat the turn's exact words and case; `me` stands for
  the speaker. `relation` is a plain snake_case name with one fixed alias
  list per relation in the generator. The pet alias list covers every species
  word used in the panel.
- `clear` is false where a second reading is defensible. `notes` holds short
  category tags only.

## Judgement calls

- Group-owned facts (shared pet, home, relative, workplace, car, language)
  save nothing: gold is empty and the turn must ask whose.
- Teaching, studying, or coaching at a school, college, or club reads as the
  institution relation; the implied occupation alone is never gold.
- "Moved to" and "born in" read as current city and birthplace
  respectively; "grew up" style wordings were not used.
- Corrections were not used in this panel; every gold frame states a current
  fact from its own turn only.
- Two items are marked unclear: one opinion-style turn with no concrete
  fact, and one turn whose group wording states no standard frameable fact.
  Both carry empty gold either way.

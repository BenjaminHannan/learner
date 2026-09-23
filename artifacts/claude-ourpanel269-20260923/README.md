# Our panel 269 (blind group-word panel), 2026-09-23

TEST-ONLY. Never read item by item, never tune on it, never quote it.
Run once per arm after both seals, through the strict schema check first.

Follow-up to panel 265. Written blind: the author read only the 265 spec
(plus the 264 spec for field/frame format, OPUS-RULES.txt, and the schema +
judgement sections of the 235 README). No builder code, no relation table,
no other panel's items, no results were read. All names, places, languages,
workplaces, pets and wordings are new and fictional. No name or place from
any README read appears here.

Files:
- `panel.jsonl`: 100 items, one JSON object per line, ids o269-001..o269-100
  in family-block order.
- `make_panel.py`: holds the items by hand, writes panel.jsonl
  deterministically, and runs the self-checks. Run from the repo root with
  `/usr/bin/python3 -B artifacts/claude-ourpanel269-20260923/make_panel.py`.
- `SEAL.sha256.txt`: SHA-256 of `panel.jsonl` + `make_panel.py`, made from
  the repo root.

## Families (exact counts)

| family | items | gold rule | ask_whose | clear: false |
|---|---|---|---|---|
| group_owner | 30 | [] always (group-owned facts; agent must ask whose) | true | 0 |
| mixed | 15 | the other (first-person/named) fact only | true | 1 |
| first_person | 20 | I/me/my facts, subject "me" | false | 0 |
| named | 15 | third-person facts (controls) | false | 0 |
| non_owner_we | 20 | the other fact(s); every turn has >= 1 to save | false | 1 |
| **total** | **100** | | | **2** |

## Design notes (category level only)

- group_owner covers pet, home, city, relative, workplace, car, school,
  language and boss facts owned by we/us/our/ours. 14 of the 30 put the
  owner word away from turn start (spec asked >= 10), including mid-sentence
  owners, shared-group subjects, and predicate ours. 3 turns are typed
  all-lowercase; 4 use ours.
- mixed pairs one group-owner clause with one first-person or named-person
  fact in the same turn; gold holds the other fact only. Clause order varies.
- first_person spans city, job, pet, language, school, hometown,
  place_of_birth, workplace, employer, boss, car and relative facts
  (1 lowercase turn). named spans the same range as controls.
- non_owner_we: the group word owns nothing saveable (meeting at an hour,
  met somewhere, told-us reports, quoted signs/speech, us-groups doing
  something, between/with-us phrases, generic-we knowledge, fixed phrases).
  Each turn carries one named-person or first-person TEACH fact that must
  still save. ask_whose is false here by construction: nothing is owned, so
  there is nothing to ask whose about.
- Pet frames carry the species word in relation_aliases (same convention as
  the 264 spec). One fixed alias list per relation lives in the generator.
- The two clear:false items mark turns where a second reading is defensible
  (an office move that could read as a saveable fact under a group rule; a
  generic-we knowledge claim).

## Self-checks (in make_panel.py)

Family counts; ids o269-001..o269-100 in order; no duplicate turn; exact
line/frame key sets; subject/value spans word-for-word in the turn (except
"me"); fixed alias list per relation; ask_whose true exactly for
group_owner+mixed; group word present exactly in
group_owner+mixed+non_owner_we; group_owner gold always []; non_owner_we
gold never []; owner-mid count >= 10 with a mechanical first-word
cross-check.

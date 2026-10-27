# Ear panel 257 (blind reader panel), 2026-09-22

**TEST-ONLY.** This is a held-out test panel. Do not train on it, tune on it, copy its wording into practice data, or print its items. Report results at category level only.

The panel was written blind from the director's spec (earpanel257-spec.txt), the general rules file, and the schema and judgement-call sections of the ear panel 235 README. The writer read no code, relation tables, training data, results, other panels, design notes or builders' folders. All names and places are fictional.

## Files

- `panel.jsonl`: 150 items, one JSON object per line, fields exactly `id, family, turn, gold, clear, notes`.
- `make_panel.py`: holds every item by hand, writes `panel.jsonl` deterministically, and runs the self-checks. Run from the repo root with `python3 -B artifacts/claude-earpanel257-20260922/make_panel.py`.
- `SEAL.sha256.txt`: SHA-256 of `panel.jsonl` and `make_panel.py`.

## Families

| family | items |
|---|---|
| plain_teach | 25 |
| varied_teach | 30 |
| full_names | 15 |
| questions | 25 |
| chain_questions | 15 |
| no_save | 25 |
| corrections | 15 |
| total | 150 |

## Risk quotas (counted by the generator)

| quota | count | required |
|---|---|---|
| R1 pronoun turns (varied_teach + full_names) | 17 | >= 10 |
| R1 with a relative and a first-person clause | 5 | >= 3 |
| R2 statement-shaped questions in no_save (gold []) | 11 | >= 10 |
| R2 of those with no "?" | 7 | >= 6 |
| R2 fact statements with a question word (varied_teach) | 4 | >= 3 |
| R3 verb decides the relation | 12 | >= 8 |
| R4 compound family relations (teach families + questions) | 17 | >= 8 |
| R5 everyday relations (all families) | 26 | >= 10 |
| R6 two-hop questions with a relative first hop | 9 | >= 6 |
| lowercase or typo'd turns | 23 | >= 15 |
| lowercase or no-"?" questions (questions + chain_questions) | 7 | >= 5 |

R2 includes at least one tag question, one "so ...", and one doubled "??".

## Notes field tags

Space-separated tags: `R1`, `R1rel`, `R2`, `R2tag`, `R2so`, `R2dq`, `R2f`, `R3`, `R4`, `R5`, `R6`, `lower` (turn has no capitals), `typo`, `noq` (question with no "?"), `correction`, and `unclear why=<reason>` on every `clear: false` item (19 items). Other words are loose category labels.

## Judgement calls (category level)

- Relations use one fixed alias list each (in the generator). Compound family relations (step-, half-, -in-law, grand-, great-, second cousin) keep the full relation and carry no plain-relative alias.
- Teaching or coaching at a School, College, Club or Academy is `workplace`; studying at one is `school`. A bare "is at" such a place is `school` with `clear: false`.
- "grew up in" and "is from" are `hometown` with `clear: false` (birthplace is also defensible).
- A girlfriend/boyfriend is `partner`, not `spouse`.
- Statement-shaped questions, past residence and "did you know" news are gold `[]` with `clear: false`. Negated, hypothetical, pretend, uncertain, hearsay, opinion and small-talk turns are gold `[]`.
- A "used to be X but now Y" turn saves only the current value. Corrections hold only the new value; the generator checks that each negated old value is in the turn but never in gold.
- A job question about a neighbour's work ("what does X do") is `job` with `clear: false` (workplace also fair). A yes/no "does X have a Y" question is ASK with `clear: false`.
- Chain questions use exactly two hops; `chain_aliases[1]` equals `relation_aliases`.
- Names repeat across families on purpose. Every item is scored on its own turn only.

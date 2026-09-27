# Table panel 221b (question panel, blind)

Written 2026-09-22 by a Claude Opus agent working only from its brief. It did not read any code, relation tables, design docs, earlier panels or results.

File: `panel.jsonl`, 120 items. Fields: id, family, setup (1-4 teach sentences), question, expect (answer/abstain), gold (value, "yes"/"no", or null), clear, notes.
Seal: `SEAL.sha256.txt` (sha256 of panel.jsonl). Any edit after sealing voids the panel.

## Families (15 items each)
| family | what it tests | expect |
|---|---|---|
| named | question uses the stored relation words | 15 answer |
| word_form | verb or other form (coaches, founded, graduate, owns, born, live, married to, rent from, work for) | 15 answer |
| contractions_fillers | who's / what's / when's, fillers (um, hey, quick q, btw, again), one lowercase question with no "?", one first-name-only question | 15 answer |
| of_form | "the R of Y" questions | 15 answer |
| synonyms | doctor/physician, boss/supervisor, residence/city, mother tongue/native language, lawyer/attorney, vet/veterinarian, mobile/cell, GP/family doctor, etc. | 15 answer |
| traps | relation not stored, two partial matches (head/assistant coach, senior/project manager, home/work phone), unknown or near-miss person, fact stored for someone else, ex-wife vs wife, birth city vs current home | 15 abstain |
| user_facts | "My ... is ..." then a question with "my" | 14 answer, 1 abstain (dentist stored, doctor asked) |
| yes_no | yes/no questions, gold "yes" (9) or "no" (6) | 15 answer |

Totals: 104 answer, 16 abstain. 113 clear=true, 7 clear=false.

## Rules followed
- Setup sentences use only "<Name>'s <relation> is <Value>." or "My <relation> is <Value>." (checked by the generator script).
- All names, places, companies, pets, languages (Vellish, Dunnish) are invented. Phone numbers use 555-01xx; the email uses a .test domain.
- Some items add distractor facts (same person other relation, or same relation other person).

## Ambiguities (clear=false items)
- synonyms: residence asked as "What city" (might be a town); spouse asked as "husband" (assumes gender); "company" asked as "employer" (might be a company he owns).
- traps: the three two-partial-match items. The right behaviour is to not give one answer; listing both or asking which is also reasonable, so they are marked not clear.
- yes_no: "Does Nora Pardew own Kestrel Books?" with only Hal Pardew stored as owner: gold "no", but a co-owner is not ruled out.
- Also note: "Is Kurt Adler Hugo Brill's dentist?" assumes one dentist (marked clear). "When is Leo Marchetti's birthday?" stores a full date of birth, so "July 14" alone also counts as correct.
- Possessives such as "Brisko Games's" / "Northgate Rovers's" are kept in the strict setup form on purpose.

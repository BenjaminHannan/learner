# Panel 232: multi-word names in verb sentences (blind)

Written blind from the brief only (no code, relation tables, design docs or other panels read).
Generator: `make_panel232.py` (in this folder; deterministic, run from repo root). All names, towns, companies and languages are invented.

## Families (84 items)
| family | items | pairs | expect |
|---|---|---|---|
| lives_in | 18 | 9 | answer |
| works_at | 18 | 9 | answer |
| speaks | 18 | 9 | answer |
| mixed | 18 | 9 | answer |
| traps | 12 | none | 7 abstain (with question), 5 null (no question, write check only) |

Expect split: 72 answer, 7 abstain, 5 null. name_words: 36 one-word, 32 two-word, 16 three-word. All items `clear: true`.

Each pair = the same setup and question with (a) a one-word name and (b) a multi-word name in the same slot. 14 pairs use 3-word, particle or hyphen names (e.g. "Iris Mae Colter", "Tobin de Grey", "Mara Ellis-Vane", "Bram van Oster", "Aldo ten Brink").

## Judgement calls
- `name_words` counts space-separated words; a hyphenated surname counts as one word ("Mara Ellis-Vane" = 2); particles count ("Tobin de Grey" = 3). For the lower-case trap subjects ("the old baker") it counts the whole phrase (3).
- In some pairs (e.g. "Corvin" vs "Iris Mae Colter") the multi-word name does not share the control's first name; this is flagged in notes.
- Four answer pairs add a possessive distractor ("<Name>'s sister is Pella."). `expect_writes` lists only the lives in / works at / speaks writes; the possessive write is allowed but not listed or scored.
- Mixed family: the multi-word variant shares a first name, surname, hyphenated surname, first name + particle, or first + middle name with the other person; the one-word variant uses two different one-word names. Both writes are expected; the other person's value must not be the answer.
- Traps: 3 hedges (I think / Maybe), 2 hearsay (Tom says / Garrick told me), 3 negations, 2 statement-shaped questions ending in "?", 2 lower-case common-noun subjects. All expect no write; where a question is given the answer must be an abstain.
- Some values reuse names across items (e.g. Tarnby) but each item is meant to run in a fresh notebook.

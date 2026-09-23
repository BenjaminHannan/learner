# calledpanel281 (exp 281 blind panel)

60 turns, 10 dialogs (D01-D10), 6 turns each. Fictional names only, freshly invented.
Each dialog starts with 1 teach then only questions. Notebook state is per-dialog (fresh at each dialog start).

## Counts per category (turns)

| category | turns | meaning |
|---|---|---|
| teach_setup | 10 | control teach; states 1 fact; gold is the expected stored triple |
| stored_called | 25 | called/named/name-of question about a fact taught in the same dialog; gold is the exact expected value |
| nostore_called | 10 | same called-wording but the fact was never taught in that dialog; gold is `abstain` |
| ambiguous_called | 10 | `called` belongs to the value/name itself (`Who is X's <other-relation> called <Name>?`); gold is `abstain` |
| control_plain | 5 | plain possessive question without called/named about a taught fact; gold is the exact expected value |
| total | 60 | — |
| controls (teach_setup + control_plain) | 15 | — |

## panel.jsonl schema

One JSON object per line, keys:

- `dialog_id`: e.g. `D01`
- `turn_index`: 0-based index within the dialog
- `user_text`: the user turn text
- `category`: one of `teach_setup`, `stored_called`, `nostore_called`, `ambiguous_called`, `control_plain`
- `gold`: expected result:
  - teach turns: stored triple as `Subject|relation|Object` (e.g. `Lena|cat|Biscuit`)
  - answer turns with a stored fact: the exact expected value string (e.g. `Biscuit`)
  - items that must abstain: the literal `abstain`

Write expectations (for the scorer; not a separate field): every question turn (`stored_called`, `nostore_called`, `ambiguous_called`, `control_plain`) expects zero notebook writes. Only `teach_setup` turns expect a write, identical to the base behavior.

## Relations covered

Stored facts span pets (cat, dog), boats, bands, streets, teachers: Lena/cat, Marco/boat, Priya/band, Tomas/street, Ines/teacher, Kira/dog, Dario/boat, Sana/band, Joren/street, Mira/teacher.

Called-wording variants used: `What is X's R called?`, `What is X's R named?`, `Who is X's R named?`, `What's the name of X's R?`, `what's the name of X's R?`, `what do you call X's R?`, `What do you call X's R?`, `What's X's R called?`, `what's X's R's name?`, casual lowercase/no-punctuation forms (e.g. `what is Sana's band called`, `what do you call Tomas's street`).

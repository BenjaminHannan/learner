# creativepanel333

Test-only panel. Counts only.

| kind | items |
|---|---|
| creative | 40 |
| control_teach | 15 |
| control_ask | 15 |
| total | 70 |

Creative subtypes (not stored in items.jsonl):

| subtype | items |
|---|---|
| gift ideas | 10 |
| plans for a day or trip | 8 |
| short poems, toasts or cards | 8 |
| what to cook or bring | 6 |
| help wording a message | 4 |
| other | 4 |

Creative items with `about_untaught_person: true`: 10

Checks passed: keys exact; counts as specified; every control_ask gold appears in an earlier turn of its item; all person names start with A to M and no name repeats across items.

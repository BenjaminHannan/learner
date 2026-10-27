# sf-401 after the verdict: missed correction questions, reader or answer step? (report only, $0)

Written 2026-09-26 17:16 UTC (`date -u`) by the wrong-as-fact thread, for the Thread manager's round-4 question.
Counts only. Scripts: scripts/claude_sf401_blame.py (output in blame_out.json beside this) and claude_sf401_relcheck.py, both written after the verdict.
It changes no mark and no verdict.

Method: at each of the 74 edit asks, the notebook is the stored_triples snapshot of the last run row before the ask.
The new value (the corrected fact the ask's gold uses) and the old value (the fact that correction closed) count as
held when a stored triple matches the owner (the 336 scorer's owner_match) and the value, as the scorer's
facts_saved does. Values lis-314 parked as pending are not in the snapshot.

| Notebook at the ask | asks | B right | B not right (don't know / confirm other / wrong candidate) | whose miss |
|---|---|---|---|---|
| new value only | 23 | 10 | 13 (10 / 2 / 1) | answer step |
| old and new | 1 | 0 | 1 (1 / 0 / 0) | answer step |
| old value only | 24 | 12 | 12 (7 / 4 / 1) | reader or save |
| neither | 26 | 10 | 16 (10 / 5 / 1) | reader or save |
| all edit asks | 74 | 32 | 42 | |

- Of B's 42 missed correction questions, 28 are the reader's or the save's (the new value never reached the notebook)
  and 14 are the answer step's (the notebook held it).
- Of the 13 new-value-only misses, 8 have the stored triple under the same relation name as the truth sheet and 5 under a different one;
  relation names differ on 116 of the 282 right owner-and-value triples in B's final notebooks, so those 5 are undecided, not reader errors.
- The notebook held the new value at only 24 of 74 edit asks, and both values at only 1 (inferred, not checked: it keeps
  one value per relation). A test where recall sees both the old and the new value has to get them from the raw chat, not from
  the notebook.
- A has the same count in every notebook class at the edit asks (23, 1, 24, 26). The guard turned 11 of the 24
  old-value-only asks from missed to right (A 1, B 12), through confirm questions.

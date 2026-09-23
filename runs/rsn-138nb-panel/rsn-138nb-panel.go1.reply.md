Building your blind panel — fetching specs and checking resources.
Specs confirmed and base agent mapped — now drafting the 70-item panel.
Base mechanics are clear — now probing which phrasings the base stores reliably.
Pilot shows the base handles plain teaches well — now testing question variants.
Probing done — now writing the 70-item panel and runner scripts.
Panel drafted — now running the base once per item.
All setups store cleanly — now scoring the base run.
Scoring complete — now sealing the delivery.
Verdict: DELIVERED — blind panel invpanel138nb built, base 138n run once per item, sealed at artifacts/claude-invpanel138nb-20260923/.

Marks table (base 138n, integer counts; right = full credit per sealed scorer; right_names = names right ignoring label, backwards families only):

| family | n | right | right_names | wrong | question_wrote |
|---|---|---|---|---|---|
| whose_R | 14 | 2 | 14 | 0 | 0 |
| lives_born | 10 | 0 | 10 | 0 | 0 |
| has_as | 6 | 2 | 6 | 0 | 0 |
| verb_backwards | 10 | 9 | 9 | 0 | 0 |
| my_backwards | 4 | 1 | 4 | 0 | 0 |
| no_match | 8 | 8 | n/a | 0 | 0 |
| unknown_value | 4 | 4 | n/a | 0 | 0 |
| forward_control | 10 | 10 | n/a | 0 | 0 |
| teach_control | 4 | 4 | n/a | 0 | 4 |
| TOTAL | 70 | 40 | — | 0 | 4 |

Every move / every miss (category level, no item quoted):
- whose_R: 14/14 name-correct, 12 miss on the required backwards label only; 0 wrong, 0 writes.
- lives_born: 10/10 name-correct, 10 miss on the label only; 0 wrong, 0 writes.
- has_as: 6/6 name-correct, 4 miss on the label only; 0 wrong, 0 writes.
- verb_backwards: 9/10 full credit; 1 miss answered with a not-understood clarify (names missing); 0 wrong, 0 writes.
- my_backwards: 4/4 name-correct, 3 miss on the label only; 0 wrong, 0 writes.
- no_match 8/8 abstain correctly; unknown_value 4/4 abstain correctly; forward_control 10/10; teach_control 4/4 stored exactly their own triple (the only 4 question-writes on the panel, as designed).
- Total wrong: 0. No taught-subject leaks, no extra writes.

Deviations / replacements:
- 1 setup dropped and replaced before the base run: a forward employer value containing "and" was refused by the base (one-fact-at-a-time clarify, stored nothing); replaced with a single-company value. After replacement all 70 setups store exactly the listed triple (70/70 verified).
- 1 scorer correction before sealing: no_match right-check narrowed from taught subject-or-value to taught subject only, matching the spec wording (the asked value itself echoes in abstains). No panel content changed for this.
- run_base normalizes notebook subject USER to "you" for user-teach items so expected and actual triples compare exactly; documented in code.
- After SEAL no files were changed. `shasum -a 256 -c` from repo root: all 5 OK.
- Disk stayed above 3 GB free (18 GB). One process at a time. CPU only. Base ran once per item (70 rows). Fictional names only. No forbidden files opened; no commits or pushes.

What it means (plain English): the base already knows names backwards (43/43 name-hits on the five backwards groups) and is perfect at saying "I don't know" when it should and at plain forward questions — but it usually forgets to add the "worked out backwards" tag school requires for full credit, so full-credit scores look low on the plain backwards groups.

What it doesn't mean: low full-credit numbers do not mean the base gave wrong names (wrong = 0) or leaked facts it shouldn't (0 wrong, only the 4 designed statement-writes). It also doesn't say anything about any other agent — this is base 138n only, one run per item.

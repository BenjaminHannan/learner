Blind panel writer for exp 264 — fetching rules and spec.
Spec read. Disk has 19 GB free (above the 3 GB floor). Now I'll set up a todo list and build the panel generator.
Spec digested. Now writing the panel generator with all 150 hand-built items and self-checks.
Cleaning up a leftover dead-code fragment in the R17 check before running.
Checker bug: for ASK items the compound relation sits in `chain[0]`, not `relation`. Fixing the check.
Self-checks pass. Now the required careful reread of every item as a reader.
VERDICT: PASS — blind panel for exp 264 is built, self-checked, reread item by item, sealed, and verified. Folder: `artifacts/claude-earpanel264-20260923/` (panel.jsonl 150 lines, make_panel.py, README.md, SEAL.sha256.txt).

Marks table (integer counts; minimums in brackets):

| category | count (min) |
|---|---|
| plain_teach | 25 (25) |
| varied_teach | 30 (30) |
| full_names | 15 (15) |
| questions | 25 (25) |
| chain_questions | 15 (15) |
| no_save | 25 (25) |
| corrections | 15 (15) |
| total | 150 (150) |
| R1 pronoun across clauses | 10 (8) |
| R2 statement-questions, no_save, gold [] | 9 (8) |
| R2 of those with no question mark | 5 (5) |
| R2 question-word statements, TEACH gold | 3 (3) |
| R3 verb decides relation | 6 (6) |
| R4 compound family relations | 8 (6) |
| R5 everyday relations | 11 (8) |
| R6 relative first hop | 7 (5) |
| R8 varied (plan excluded) / no_save (whole-turn plan) | 4 / 4 (3 / 3) |
| R9 pretend/hypothetical, no_save | 6 (5) |
| R10 plural relatives, frame per person | 4 (4) |
| R11 appositives, both frames | 10 (6) |
| R12 pronoun refers to B | 4 (4) |
| R13 typo next to a name | 8 (8) |
| R14 all-lowercase names | 6 (6) |
| R15 name particles | 6 (6) |
| R16 wrong-relation traps | 8 (8) |
| R17 stale values outside "not X" | 6 (6) |
| lowercase/typo turns overall | 25 (15) |
| lowercase/no-"?" in questions + chain | 6 (5) |
| clear:false | 13 |

Every move: wrote make_panel.py (items by hand, fixed alias list per relation, self-checks for family counts, duplicate turns, word-for-word subjects/values, every quota, schema exactness incl. chain_aliases); ran it — first run failed on my own checker (R4 check missed ASK chain hops), fixed the checker, reran — all self-checks passed; reread all 150 items once as a careful reader and fixed 3 plural-relative golds to include one kin frame per person plus each person's other fact; wrote category-only README; sealed from repo root; `shasum -c` output: both files OK. Every quota met or exceeded. Misses: zero. No TEST-ONLY panel was opened. Disk stayed at 19 GB free; one process at a time throughout.

Deviations: two, both reported. (1) The task line says PUSH, but OPUS-RULES hard-forbids commits/pushes, so the folder is sealed on disk and NOT pushed or committed. (2) I edited my own unsealed make_panel.py twice before sealing (one checker bug fix, one gold fix from the reread); no existing, sealed, or other-agent file was touched — additive-only held.

SEAL lines:
e90deeaaa616fdcabcb417c2b9d53782d39bd5237b28c1cb699ddf4fefd30a6e panel.jsonl
1d1002cdb0c7204dded489918650f8ceb6a0f2721ae6c2e616e0e6369b944a38 make_panel.py
-c output: panel.jsonl OK, make_panel.py OK.

What it means (plain high-school English): there is now a sealed 150-question answer key that tests whether the reader program saves the right facts and asks the right questions, including tricky cases like typos, pronouns, plans, and look-alike relations.
What it doesn't mean: it does not say the reader program is good or bad — no program has been tested against this panel yet, and I never saw the builder's code.

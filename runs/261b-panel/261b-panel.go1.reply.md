Building your blind panel — fetching specs and verifying rules.
Spec and rules reviewed. Now building the 150-item panel by hand.
Self-check caught a substring bug in my own checker ("Studio" matched "stud"). Fixing the checker.
All self-checks pass. Now the required careful reread of every item before sealing.
Panel regenerated clean. Writing the category-level README, then sealing.
VERDICT: PASS — earpanel261b is built, self-checked, reread, sealed, and verified (150/150 items, all quotas met).

Marks table (integer counts):

| check | bar | got |
|---|---|---|
| total items | 150 | 150 |
| plain_teach | 25 | 25 |
| varied_teach | 30 | 30 |
| full_names | 15 | 15 |
| questions | 25 | 25 |
| chain_questions | 15 | 15 |
| no_save | 25 | 25 |
| corrections | 15 | 15 |
| R1 (varied+full pronoun items) | ≥8 | 12 |
| R2 no_save statement-questions, gold [] | ≥8 | 9 |
| R2 of those with NO question mark | ≥5 | 5 |
| R2 varied_teach question-word statements, TEACH gold | ≥3 | 3 |
| R3 verb-decides-relation | ≥6 | 8 |
| R4 compound family relations | ≥6 | 8 |
| R5 everyday relations | ≥8 | 16 |
| R6 chain first hop is a relative | ≥5 | 9 |
| R7 plural owners, subject me | ≥6 | 7 |
| R8 total / varied-with-fact / no_save plans | ≥6 / ≥3 / ≥3 | 7 / 3 / 4 |
| R9 pretend/hypothetical no_save | ≥5 | 6 |
| R10 plural relatives | ≥4 | 5 |
| R11 appositives | ≥6 | 7 |
| R12 pronoun refers to B | ≥4 | 5 |
| R13 typo next to a name | ≥8 | 8 |
| R14 all-lowercase names | ≥6 | 7 |
| lowercase-or-typo turns overall | ≥15 | 26 |
| questions+chain lowercase or no-"?" | ≥5 | 6 |
| noq tags total | — | 11 |
| clear:false items | — | 19 |
| duplicate turns | 0 | 0 |
| span failures (subject/value not in turn) | 0 | 0 |
| schema failures | 0 | 0 |

Every move (3, all before the seal, none after):
1. Self-checker bug fix: my R3 word check matched "stud" inside "Studio" and wrongly failed one item; fixed the checker to match whole words ("study"/"studies"). Panel items unchanged.
2. Reworded one plain_teach job item that also named a workplace, so the gold (job only) is everything the turn states and nothing more.
3. Flipped one full_names doctor item from clear:true to clear:false, since the attached clinic name makes a second (workplace) reading defensible.

Every miss: none. Every quota met or exceeded on the first sealed generation.

Deviations from the spec: none. Blindness kept: besides the spec and OPUS-RULES.txt I opened only the schema/format and judgement-call sections of the earpanel235 README (via a branch copy in /tmp, never checked out); no code, data, design notes, results, other briefs, or other panels (including 257/261) were read. All names/places are invented and none come from the 235 README.

SEAL (2 lines):
1adf2ac76b8128ec897bb025bfa21e21d74dfcb7c20aef5f608a5f58aacaf99f artifacts/claude-earpanel261b-20260923/panel.jsonl
d8904668ed153dead2a72f9a820e8faf1c3a51aff03cb620b6015a76a0e788af artifacts/claude-earpanel261b-20260923/make_panel.py
`shasum -a 256 -c` output: panel.jsonl OK, make_panel.py OK.

What it means (plain high-school English): there is now a finished 150-question test, locked with checksums, that checks whether a reader program pulls exactly the right facts out of chat messages — including tricky cases like pronouns, typos, lowercase chat, plans vs. real facts, and two-step questions.

What it doesn't mean: it says nothing about how good any reader program is — no program was run against this panel here (TEST-ONLY panels are never tuned on or quoted). A builder still has to score against it separately, and this panel alone can't prove a reader is good, only exactly these 150 cases.

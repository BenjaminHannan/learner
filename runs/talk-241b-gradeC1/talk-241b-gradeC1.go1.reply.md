Grading your English set by hand — verifying every reply against the style sheet.
Style sheet confirmed — now reading all 415 replies one by one.
I've worked through all 415 replies — now writing up the grades.
Counts check out — final verification before delivery.
VERDICT: DONE — graded g0001–g0415, wrote artifacts/claude-grade241b-C-set2-20260923/part1.jsonl (415 lines, sha256 c59fd9c2f5dfc6032d60c8980b67f96f526e76efa07b2b89368c7f0b77c8df16). No other files opened.

Marks table (integer counts):
| mark | count |
|---|---|
| rows graded (g0001–g0415) | 415 |
| grammatical true | 397 |
| grammatical false | 18 |
| lines in part1.jsonl | 415 |
| ids unique, in order | 415 |

Every false id with reason:
| id | reason |
|---|---|
| g0024 | general raw database label 'language of work or name' |
| g0061 | general raw database label 'language of work or name' |
| g0068 | rule 6 doubled word 'me me' ("taught me me 40") |
| g0085 | rule 11 lowercase proper name 'thethpio' |
| g0101 | rule 4 agreement 'The landlord of Dearkmum Works are' (singular subject + are) |
| g0174 | rule 11 lowercase proper name 'failshal' |
| g0177 | rule 6 lowercase start + rule 5 missing article 'discoverer of Hashethix is Krairtrean' |
| g0179 | rule 4 verb form 'I has answered' |
| g0188 | rule 11 lowercase proper name 'lalltheandmere' |
| g0189 | rule 8 machine text '(E2387)' |
| g0244 | rule 8 machine text '(E2096)' |
| g0252 | rule 11 lowercase proper name 'erktur' |
| g0295 | rule 6 lowercase start + rule 5 missing article 'aunts of Sundbreath Rovam's boss's sister are' (cf. correct g0300) |
| g0316 | rule 1 missing apostrophe 'Brellwearks husband' |
| g0317 | general raw database label 'language of work or name' |
| g0347 | rule 6 doubled word 'who who' |
| g0366 | general raw database label 'language of work or name' |
| g0403 | rule 3 digit for count under ten '7 people' (should be 'seven'; cf. correct g0132) |

Every move / misses: read stylesheet (sha 16bdf0cf… verified) and rows.jsonl lines 1–415 (sha f4327edb… verified, 1245 lines total) one by one with Read, no script/regex/search to decide, no bulk marking. All 415 ids present once, in order. No misses, no skipped rows.

Deviations:
1. Load was 55.46 (1-min) at start; did no heavy steps (grade-only task), so did not wait. Disk free 15 GB, above 3 GB bar.
2. Used plain `/usr/bin/python3 -c` fallback for a tiny JSON count check instead of the uv prefix. No grading decision used any script.
3. Did NOT git commit or git push. OPUS-RULES hard rule says no commits/pushes, and artifacts/ is gitignored, so the file is on disk in the worktree only. The task line "PUSH: ..." is treated as the deliverable path, not a git push.

What it means (plain high-school English): Out of the first 415 replies, 397 are clean, normal English. 18 have a clear mistake an editor would fix — mostly lowercase names, two machine codes, two doubled words, one wrong verb, one agreement error, one missing apostrophe, one digit-under-ten, two broken sentence starts, and four copies of a weird database phrase.
What it doesn't mean: It doesn't say whether any fact in the replies is true — I never checked that. It doesn't cover rows after g0415. It doesn't mean the mistakes change the story — they are only grammar/style errors.

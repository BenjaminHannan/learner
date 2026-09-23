Grading 415 replies by hand — verifying files and reading every row myself.
First hundred rows checked — continuing through the set one by one.
Spotted several clear errors so far — reading the next batch.
I've graded all 415 rows by hand — now writing the verdict file.
Verdict: DONE — graded rows 1–415 (g0001–g0415), wrote artifacts/claude-grade241b-D-set2-20260923/part1.jsonl. No git commit/push made (see deviations).

Marks table (integer counts):
- rows graded: 415
- marked true (grammatical): 398
- marked false (ungrammatical): 17

Every false move (id + reason):
- g0024: false — general: raw database label "language of work or name" ("No, your language of work or name is Binwamese.")
- g0061: false — general: raw database label "language of work or name"
- g0068: false — rule 6: doubled word "me me" ("taught me me 40 facts")
- g0101: false — rule 4: subject-verb agreement "The landlord of Dearkmum Works are"
- g0174: false — rule 11: lowercase proper name "failshal" (a creator, i.e. a person)
- g0177: false — rule 5 and 6: missing article and lowercase start "discoverer of Hashethix is Krairtrean."
- g0179: false — rule 4: wrong verb form "I has answered"
- g0188: false — rule 11: lowercase proper name "lalltheandmere" (country of origin, i.e. a place)
- g0189: false — rule 8: internal entity code "(E2387)"
- g0244: false — rule 8: internal entity code "(E2096)"
- g0252: false — rule 11: lowercase proper name "erktur" (a parent, i.e. a person)
- g0295: false — rule 5 and 6: missing article and lowercase start "aunts of Sundbreath Rovam's boss's sister are" (compare g0300 with "The aunts..." = ok)
- g0316: false — rule 1: missing apostrophe "Brellwearks husband" (should be possessive)
- g0317: false — general: raw database label "language of work or name"
- g0347: false — rule 6: doubled word "who who"
- g0366: false — general: raw database label "language of work or name"
- g0403: false — rule 3: digit for count under ten "7 people" (should be "seven")

Every miss: none known. Borderline calls I marked TRUE and why: g0085 "thethpio" (a cat — rule 11 covers person/place/organisation/title only, so not judged); g0128/g0213 "religion or worldview" (reads as natural English, unlike "language of work or name"); g0346 "Ember Ember" (a strange invented name, not a list, and strange names are not errors); "no web rows" (standard English for things, not a bare-zero error).

Deviations:
- I accidentally read 5 rows past my range (g0416–g0420) in one chunked read (lines 361–420 of rows.jsonl). I graded and wrote only lines 1–415; the extra rows were seen, not graded or recorded.
- Task says PUSH the file; OPUS-RULES forbids git commits/pushes, so I left the file written in the worktree, uncommitted, unpushed.
- Verification only: line count/JSON/ids checked with wc + an offline uv python check (415 lines, 415 unique ids, g0001 first, g0415 last, in order, 17 false). No script, regex or search was used to decide grades; each row was read and judged one by one.
- Environment: uptime load ~41.9 (1-min) but this was a read-only grading task with no heavy runs; df showed ~14 GB free on /, above the 3 GB stop line.

What it means (plain English): out of your 415 replies, 398 are clean, natural sentences and 17 have a clear grammar mistake a careful editor would fix — mostly the weird phrase "language of work or name," small codes like "(E2387)," repeated words, one wrong verb ("I has"), one singular/plural mismatch, one digit that should be a word, and a few names left lowercase.

What it doesn't mean: it doesn't say any fact is wrong or any story detail is bad — I only graded grammar. It also doesn't say the whole batch is good or bad beyond these 415 rows; other rows were not mine to grade.

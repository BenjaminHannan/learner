Grading 228 replies for M1 — verifying the seal and reading every row.
Seal OK (`fixedtext.jsonl: OK`). I've read all 228 rows. Now an exhaustive locate-only sweep for digits/placeholders (judgment remains my own) to make sure I miss no candidate:
My output directory doesn't exist yet — creating it (additive, allowed), then writing my grades:
Verifying the file's shape only (counts/validity — the judgments are already mine):
Grading done. File verified and in place.

**VERDICT: 219 of 228 replies fully grammatical natural English; 9 fail, all for the same defect (bare digits for small counts).**

Marks table (integer counts):

| Mark | Count |
|---|---|
| Rows graded | 228 |
| grammatical = true | 219 |
| grammatical = false | 9 |
| Rows skipped / unread | 0 |
| Duplicate / missing ids | 0 |

Every move (all 9 false rows, id + exact problem):
- r024 — "I have saved facts 11 times so far." Bare digits "11" for a small count; sibling rows spell it out ("four times", "seven times").
- r050 — "There are 11 guesses waiting for your approval." Bare digits "11"; siblings use "Six", "Four", "One", "No".
- r072 — "The count is 14." Bare digits "14"; siblings use "None", "One", "Five", "Two".
- r090 — "I know 11 facts you taught me." Bare digits "11"; siblings use "three", "eight".
- r093 — "Of my facts, 10 are sleep-derived." Bare digits "10"; siblings use "Seven", "Nine", "One", "Six".
- r117 — "I know 13 facts you taught me." Bare digits "13"; siblings use words.
- r149 — "Of my facts, 12 came from rules." Bare digits "12"; siblings use "Four", "Nine", "Two", "One".
- r162 — "I hold 11 quarantined web rows." Bare digits "11"; siblings use "one", "four", "two", "six".
- r198 — "I know 14 facts you taught me." Bare digits "14"; siblings use words.

Misses / deviations:
- Misses: none. I read all 228 rows myself; judgments are mine, no script decided any grade (a script only located digit candidates and validated my output file's shape).
- Other defect classes checked and absent: zero "zero"/"0" counts, zero USER-style placeholders (grep for USER in reply texts hit only template_ids, not reply text), zero code fragments, zero broken punctuation.
- Judgment calls (kept as true): "in turn N" digits (r031, r032, r053, r073, r075, r082, r104, r132, r138, r155, r174, r224) are turn labels like "page 5", not counts, so they are natural. Terse confirmations ("Saved:", "Updated:", "Forgotten:", "None.", "You did.", "Bye!") are normal conversational ellipsis, not machine text. Example names in quotes (Kim/Lee, Tom/Ann, Mira/Lisbon) are illustrative, not placeholders.
- Deviation on PUSH: the file is written at artifacts/claude-grade255b-B-20260923/m1-grades.jsonl (228 lines, every id r001–r228 exactly once, valid JSON), but I did NOT git commit or git push it — OPUS-RULES hard rule 9 ("No git commits, PRs or pushes") applies in full and overrides the brief's PUSH line. The director can collect the file from the worktree.
- Environment: seal check `shasum -a 256 -c artifacts/claude-fixedtext255b-20260923/SEAL2.sha256.txt` said OK. Free disk 16 GB (above the 3 GB floor). Load was high (~30) but I ran no heavy compute, only reads plus one tiny format check.

What it means (plain English): about 96% of the fixed replies read like something a careful person would actually say — full sentences, normal words for numbers, clean punctuation. The only recurring slip is writing small numbers as digits (11, 14) instead of words (eleven, fourteen), which looks computer-generated next to the sibling replies that spell them out.

What it doesn't mean: this says nothing about whether any reply is true, correct, or consistent with the notebook — I graded English only, per the brief. It also doesn't mean the 9 flagged rows are broken beyond repair; each needs only its digits spelled out.

Grading 449 replies for clean English — verifying rules and loading the batch.
Rules check out — now pulling the 449 replies to grade.
First hundred look mostly clean — continuing through the next set.
I've read all 449 rows. Now I'll create the output directory and writer script.
File written. Verifying line count, id uniqueness/order, and the false rows.
VERDICT: DONE — graded all 449 rows (h0001–h0449). 426 grammatical, 23 ungrammatical. File written to artifacts/claude-gradef1-B-20260923/part1.jsonl (449 lines, every id exactly once, verified).

MARKS TABLE (integer counts):
| Measure | Count |
|---|---|
| Rows graded | 449 |
| grammatical = true | 426 |
| grammatical = false | 23 |
| — misspelled "Origianl"/"origianl" (general spelling) | 11 |
| — missing article "the" before Kingdom names (rule 5) | 9 |
| — sentence starts lowercase (rule 6) | 2 |
| — doubled word "say say" (rule 6) | 1 |
| Rows skipped / unread | 0 |
| Misses (rows I could not judge) | 0 |

EVERY FALSE ROW (id + reason):
- h0016: general — "Origianl" (should be "Original")
- h0117: rule 5 — missing "the" in "change it to United Kingdom of Great Britain and Ireland?"
- h0118: rule 5 — missing "the" in "a citizen of Kingdom of the Netherlands"
- h0126: general — "origianl"
- h0187: general — "origianl"
- h0194: rule 6 — doubled word "say say"
- h0199: rule 5 — missing "the" in "The capital of Kingdom of the Netherlands is Nässjö"
- h0205: general — "Origianl"
- h0226: general — "origianl"
- h0230: general — "origianl"
- h0233: rule 5 — missing "the" in "a citizen of United Kingdom of Great Britain and Ireland"
- h0234: rule 5 — same as h0233
- h0244: rule 5 — same as h0233
- h0263: general — "origianl"
- h0266: general — "Origianl" (also "Nbc", not separately counted)
- h0314: rule 6 — sentence starts lowercase "capital of …"
- h0369: rule 5 — missing "the" in "The capital of Kingdom of the Two Sicilies is Naples"
- h0370: rule 5 — same UKGBI wording as h0233
- h0386: rule 6 — sentence starts lowercase "continent of …"
- h0397: general — "origianl"
- h0398: general — "Origianl"
- h0409: rule 5 — missing "the" in "a citizen of Kingdom of England"
- h0433: general — "Origianl"

EVERY MOVE: read the style sheet (sha256 matched 16bdf0…dad8ef), read sweep rows 1–449 myself via git show, judged each reply by hand against the sheet, created exactly one new file (part1.jsonl), verified 449 lines / ids h0001–h0449 unique and in order / 23 false. No scripts were used to decide; a formatter script only wrote out my hand grades. Never opened any other folder file, grader output, f1-20260923 files, or configs. No scorer run. No TEST-only panels involved.

DEVIATIONS:
1. The /private/tmp/…/OPUS-RULES.txt path did not exist; I read the same rules via git show origin/main:handoff/kit/briefs/OPUS-RULES.txt instead.
2. "PUSH": I did not git commit or push (hard rules forbid it). The deliverable sits uncommitted in the worktree for the director to collect.
3. The Grep tool's `rg` binary is broken on this Mac (EBADARCH); verification used file read + line counts instead. Nothing else was touched: part2.jsonl and all other files left alone.

WHAT IT MEANS (plain English): F1's talking line is mostly clean — about 95 in 100 replies (426 of 449) are fully correct English sentences. The 23 bad ones fall into three small buckets: a repeated "origianl" typo, a dropped "the" before Kingdom-style country names, and 3 one-off slips (a doubled "say say" and two lowercase sentence starts). Odd names, strange facts, and weird values were ignored as instructed.

WHAT IT DOESN'T MEAN: This says nothing about whether the replies are true, sensible, or on-task — I graded grammar only. It covers only rows 1–449, not the rest of the sweep, and my 9 article calls (the "the"-before-Kingdom rows) are strict-standard-English judgments the director may want to double-check against the gold answers.

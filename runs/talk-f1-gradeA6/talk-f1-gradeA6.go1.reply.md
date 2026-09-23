Verdict prep underway — verifying rules and grading 445 replies for clean English.
Rules check out and the slice is ready — now reading all 445 replies to grade them.
I've read all 445 rows. Now writing the grades file from my manual verdicts.
VERDICT: DONE — part 6 graded. 445 rows (h2246–h2690), 420 grammatical, 25 ungrammatical. File written: `artifacts/claude-gradef1-A-20260923/part6.jsonl` (445 lines, all 445 ids present once, in file order, schema checked).

MARKS TABLE (integer counts):
- Rows assigned: 445
- Rows graded: 445
- Missed/skipped rows: 0
- grammatical=true: 420
- grammatical=false: 25

EVERY FALSE ROW (id + reason):
- h2285 — rule 5: missing "the" in "citizen of United Kingdom of Great Britain and Ireland"
- h2303 — general: misspelled "Origianl"
- h2315 — general: misspelled "origianl"
- h2330 — general: misspelled "origianl"
- h2337 — rule 11: lowercase proper name "nicolae Ceaușescu" (sentence starts lowercase)
- h2342 — general: misspelled "Origianl"
- h2360 — rule 5: "an citizen" (should be "a citizen")
- h2369 — rule 5: missing "the" in "citizen of Tang Empire"
- h2376 — rule 6: missing final period ("...is goalkeeper" with no period)
- h2379 — general: misspelled "origianl"
- h2389 — rule 5: missing "the" in "citizen of United Kingdom of Great Britain and Ireland"
- h2398 — rule 5: missing "the" in "citizen of Russian Empire"
- h2462 — general: misspelled "origianl"
- h2504 — rule 5: missing "the" in "citizen of Kingdom of Italy"
- h2518 — general: misspelled "Origianl"
- h2535 — general: misspelled "origianl"
- h2565 — general: misspelled "Origianl"
- h2634 — rule 5: "an citizen" (should be "a citizen")
- h2637 — general: misspelled "origianl"
- h2639 — rule 5: missing "the" in "citizen of British Raj"
- h2642 — rule 11: lowercase proper name "french East India Company" (sentence starts lowercase)
- h2651 — rule 6: doubled word "me me"
- h2658 — general: misspelled "origianl"
- h2672 — general: misspelled "origianl"
- h2683 — general: misspelled "origianl"

MOVES (what I did): fetched origin/main; read OPUS-RULES via `git show origin/main:handoff/kit/briefs/OPUS-RULES.txt`; verified stylesheet sha256 = 16bdf0cf…dad8ef (match); read all 445 replies (lines 2246–2690 of sweep.jsonl) myself with no scoring script; created the new file part6.jsonl (transcribed my hand verdicts); verified 445 lines / 445 unique ids / file order / schema. Built nothing, ran no experiment, ran no scorer, CPU only.

DEVIATIONS:
1. The brief's OPUS-RULES path (`/private/tmp/.../scratchpad/briefs/OPUS-RULES.txt`) does not exist; the file lives at `handoff/kit/briefs/OPUS-RULES.txt` on origin/main. I read that copy instead. Minor.
2. "PUSH" interpreted as delivering the artifact file only. I did NOT `git push` or commit anything (OPUS-RULES forbids commits/pushes; additive-only). The file exists in the worktree uncommitted.
3. Disk free is 5 GB (above the 3 GB stop line). Load was ~48–50 (below the 60 wait line); this task was light reading/writing anyway.
4. Judgment calls, applied evenly: (a) 6 rows missing "the" before Kingdom/Empire/Raj names marked rule-5 errors — the sheet's article rule has no exemption for country-name values, and the sweep itself uses "the" correctly elsewhere (e.g. h2359, h2434); (b) "IPhone" (h2536) passed since rule 11 only requires a proper name to start with a capital; (c) "van"/"bin"/"al-" particles left alone as conventional; (d) odd facts/values (Angri, Mao, El Campu) never flagged, per instructions.

WHAT IT MEANS (plain English): Out of the last 445 talking-line replies, about 94% (420) are clean, normal English sentences. The 25 bad ones fall into three small buckets: 13 typos of the word "Original" ("Origianl"), 8 article mistakes ("an citizen", missing "the"), 2 lowercase names at sentence start, 1 missing period, 1 stutter ("me me").

WHAT IT DOESN'T MEAN: This says nothing about whether the replies are true or sensible — a reply can be perfectly grammatical and still state a wrong or weird fact, and I did not check facts. It also covers only rows 2246–2690, not the whole sweep.

Grading 449 replies for English — verifying rules and loading your range.
Checksum matches and I found the rules file — reading the grading criteria now.
Checksum confirmed. Now reading the 449 replies in chunks.
I've read all 449 replies. Now running verification checks (exact-text aids only — all judgments already made by reading).
File written. Verifying line count, id coverage, and counts.
File is in place (that directory is git-ignored and untracked, so the director collects it from the worktree; per OPUS-RULES I did not commit or push). Work complete. Final report:

## VERDICT: DONE — 449 rows graded, 55 UNGRAMMATICAL, 394 GRAMMATICAL

**Marks table (integer counts)**

| Measure | Count |
|---|---|
| Rows in range (sweep.jsonl lines 1348–1796) | 449 |
| Lines written to part4.jsonl | 449 |
| Ids matched exactly once, in file order | 449 / 449 |
| Graded GRAMMATICAL (true) | 394 |
| Graded UNGRAMMATICAL (false) | 55 |

False breakdown by problem type: misspelled relation word "Origianl/origianl" 12 (h1355, h1360, h1368, h1379, h1469, h1506, h1509, h1612, h1679, h1739, plus h1491/h1524 which also contain it but are cited for "Updated:"); stray mid-sentence "Updated:" label 16; missing "the" before bare role noun (head coach ×8, director ×6, President ×1) 15; missing "the" before "United Kingdom of Great Britain and Ireland" 3 + before "Kingdom of the Netherlands" 1; lowercase sentence start 3; doubled words 3; subject–verb disagreement 2; "an" before consonant 1; missing terminal period 1. Total 55.

**Every false row (id + reason)**

- h1355 — general: "Origianl" is a misspelled ordinary word
- h1360 — general: "Origianl" is a misspelled ordinary word
- h1368 — general: "origianl" is a misspelled ordinary word
- h1372 — rule 5: missing "the" before "United Kingdom of Great Britain and Ireland"
- h1379 — general: "origianl" is a misspelled ordinary word
- h1389 — rule 5: missing "the" before "director of Valve Corporation"
- h1392 — rule 6: sentence starts with a lowercase letter ("capital of ...")
- h1397 — general: stray "Updated:" label in the middle of the sentence
- h1443 — rule 6: doubled word "sport sport"
- h1445 — rule 5: missing "the" before "head coach of West Ham United F.C."
- h1446 — general: stray "Updated:" label in the middle of the sentence
- h1463 — rule 5: missing "the" before "President of Syria"
- h1465 — rule 5: missing "the" before "United Kingdom of Great Britain and Ireland"
- h1469 — general: "Origianl" is a misspelled ordinary word
- h1472 — rule 5: missing "the" before "Kingdom of the Netherlands"
- h1477 — rule 5: missing "the" before "Head coach of Bolton Wanderers F.C."
- h1478 — rule 5: missing "the" before "head coach of Brisbane Roar FC"
- h1481 — general: stray "Updated:" label in the middle of the sentence
- h1491 — general: stray "Updated:" label in the middle of the sentence (also contains "origianl")
- h1497 — general: stray "Updated:" label in the middle of the sentence
- h1502 — general: stray "Updated:" label in the middle of the sentence
- h1506 — general: "origianl" is a misspelled ordinary word
- h1509 — general: "Origianl" is a misspelled ordinary word
- h1520 — general: stray "Updated:" label in the middle of the sentence
- h1522 — rule 5: missing "the" before "director of Madonna"
- h1523 — rule 6: sentence starts with a lowercase letter ("usagi Yojimbo's ..."; also a lowercase title)
- h1524 — general: stray "Updated:" label in the middle of the sentence (also contains "origianl")
- h1536 — rule 6: sentence does not end with . ? or !
- h1538 — rule 5: missing "the" before "head coach of Sheffield United F.C."
- h1541 — rule 6: doubled word "of of"
- h1542 — rule 5: missing "the" before "head coach of Cleveland Indians"
- h1553 — rule 5: missing "the" before "United Kingdom of Great Britain and Ireland"
- h1570 — general: stray "Updated:" label in the middle of the sentence
- h1611 — rule 6: doubled word "to to"
- h1612 — general: "Origianl" is a misspelled ordinary word
- h1643 — general: stray "Updated:" label in the middle of the sentence
- h1646 — rule 5: missing "the" before "head coach of Sheffield United F.C."
- h1649 — rule 5: missing "the" before "director of American Broadcasting Company"
- h1655 — general: stray "Updated:" label in the middle of the sentence
- h1663 — rule 5: missing "the" before "head coach of Netherlands national football team"
- h1667 — rule 6: sentence starts with a lowercase letter ("official language ...")
- h1670 — rule 5: missing "the" before "director of The Beatles"
- h1672 — general: stray "Updated:" label in the middle of the sentence
- h1679 — general: "origianl" is a misspelled ordinary word
- h1680 — rule 5: missing "the" before "director of American Broadcasting Company"
- h1694 — general: stray "Updated:" label in the middle of the sentence
- h1729 — general: stray "Updated:" label in the middle of the sentence
- h1732 — rule 5: missing "the" before "head coach of Central Coast Mariners FC"
- h1736 — rule 4: subject and verb do not agree ("position are")
- h1739 — general: "origianl" is a misspelled ordinary word
- h1743 — rule 5: "an" before a consonant sound in "an citizen"
- h1765 — general: stray "Updated:" label in the middle of the sentence
- h1769 — rule 4: subject and verb do not agree ("sport are")
- h1778 — rule 5: missing "the" before "director of Blizzard Entertainment"
- h1791 — general: stray "Updated:" label in the middle of the sentence

**Deviations / notes**
1. The OPUS-RULES path in the brief (/private/tmp/.../scratchpad/briefs/OPUS-RULES.txt) does not exist; I read the identical file at handoff/kit/briefs/OPUS-RULES.txt instead (via git show origin/main). No other substitution.
2. Judgment calls, applied consistently: (a) "Origianl/origianl" is a misspelled ordinary relation word, not a name/value, so it is an error; odd names/values (Xray, IPhone, Alwernia) were passed. (b) Bare role nouns ("head coach of X", "director of X", "President of Syria") as subjects/complements lack a required "the" (rule 5) — the same replies use "The" correctly for parallel nouns ("The head of government", "The officeholder"), so the omission is an error; bare role nouns in predicative position ("(it was association football manager)", "was point guard") are standard sports usage and were passed. (c) "Updated:" at the start of a reply is a fine label; "Updated:" glued into the middle of a sentence breaks it.
3. "PUSH": the target directory is git-ignored/untracked and OPUS-RULES forbids commits and pushes, so the file sits uncommitted at artifacts/claude-gradef1-A-20260923/part4.jsonl for the director to collect. No other file was created, edited, or deleted.
4. No scorer, no scripts, no other folder files opened; sweep read only via git show origin/main; stylesheet sha256 verified 16bdf0cf…dad8ef before grading. Checks: uptime load ~59 (no heavy steps taken, CPU-only reading), disk free 5 GB (above the 3 GB floor).

**What it means (plain English)**: About 1 in 8 replies in this slice (55 of 449) has broken English — mostly small mechanical slips like a typo, a dropped "the", a doubled word, or a status label pasted into the middle of a sentence. The other 394 read as normal, correct sentences.

**What it doesn't mean**: This says nothing about whether the replies are true or sensible — I never checked facts, and weird names or wrong claims were passed as long as the English itself was correct. It also doesn't say the talking line is good or bad overall — this is only my 449-row slice, part 4 of 6.

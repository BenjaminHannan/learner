# own-M0b: natural conversational mouth replies, Opus-written and blind-reviewed (2026-09-23 18:45 UTC)

- Records: 3,000 records sampled from own-M0 train (seed 2024; the tag mix is set below). Six Opus writers each wrote 2 free-form replies per record under one brief. Replies use the slot tokens <S1> <R1> <V1>, fictional names only.
- Code filter (scripts/claude_own_m1_common.py slot_check, plus literal-value, user-name-leak and source-wording checks): 5,980 of 6,000 kept. The 20 dropped were all from my deliberately strict source-wording rule.
- Blind review: four Opus reviewers read all 5,980 rows, with no code deciding verdicts. Codes: F1 unsupported claim, F2 wrong status, F3 grammar, F4 unnatural, F5 doesn't fit. Result: 5,663 GOOD, 317 BAD, and 0 F2 in every part.
- Second opinion: an independent reviewer read 600 random rows and agreed on 575/600. Table: GOOD/GOOD 549, BAD/BAD 26, primary GOOD vs second BAD 18, primary BAD vs second GOOD 7.
- Kept: primary GOOD, and not BAD by the second opinion. Also dropped: rows whose record value has a digit (own-M0 junk values like "Borto2"; 43 rows).
- Result: train.jsonl has 5,602 rows and 2,479 distinct replies; the top reply is 120 rows = 2.1%.
  Tags: ANSWER 1,784, ABSTAIN 1,169, ACK_SAVE 1,165, FORGOT_ACK 582, CLARIFY 507, WHOSE 395.
- dev.jsonl = own-M0 dev (byte-identical to builder-outbox artifacts/claude-own-m0-20260923/dev.jsonl), so v1 and v2 are measured on the same records.
- Known reviewer patterns removed: value said twice, CLARIFY replies that don't ask which same-named person, "where does X live" answered with another relation, "a few" for two, unsupported timing.

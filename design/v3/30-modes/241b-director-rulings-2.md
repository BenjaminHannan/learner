# 241b: director's rulings, part 2 (2026-09-23 05:55 UTC, before any new grade exists)

**The first two graders' M1 grades are invalid.** Graders A and B each marked all 1205/1205 replies grammatical
with the single reason "ok". The sealed scorer would PASS M1 on both, but my own read of a 132-row stratified
sample found at least one clear error (s0875, a raw relation label: "... is the language of work or name of ...")
and 241's grader found 42 errors on the same kind of sweep. A grade that never says no is not evidence. So M1 is
NOT scored from grades A/B, and 241b's M1 stays open.

**New M1 method: canary-checked graders (fixed now).**
- Grading file artifacts/claude-grade241b-set2-20260923/rows.jsonl (sha256 f4327edb…43d5): the 1205 sealed sweep
  rows plus 40 rows with planted errors (8 kinds x 5: agreement, missing "the", lowercase name, doubled word,
  entity code, digit for a small count, missing apostrophe, "I doesn't"/"I has"), shuffled, new ids. The key
  (which id is which) stays with the director until the grades are in; its sha256 is
  1333f9a11c386df3a86d131132be3bba06fff41a18354f1785f252be43958321.
- Two new graders, C and D, each grade all 1245 rows (3 parts each), blind to each other and to the key.
- A grader counts only if it flags at least 36 of the 40 canaries. A grader that fails this is discarded, not re-run
  in the same form.
- M1 is then scored with the sealed scorer on the 1205 sweep ids, from each valid grader. M1 passes only if every
  valid grader passes and at least one grader is valid.
- M4 (judge) is valid: 61 distinct notes, mixed picks. M4 = 97 wins, 9 losses, 14 ties: 91.5% of non-ties, 7.5%
  losses. PASS.

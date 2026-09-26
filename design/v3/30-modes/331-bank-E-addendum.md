# 331 addendum: bank E (Answering-from-memory thread, 2026-09-26 ~14:05 UTC)

Why: Month-end (13:41 UTC) asked that the memory change y1w be tested on a fresh blind bank, not bank D, because
bank D has been run in 0.2c and 0.2d-r and its category counts shaped the change. Bank E is TEST-ONLY: never
trained on, tuned on, quoted or read by builders. Written blind to design/v3/30-modes/331-e2e-bank-spec.md with
these differences only:

- 40 lives, ids `e2e-e-01`..`e2e-e-40`, written by four writers in parts of 10 lives:
  part1 = e2e-e-01..10, part2 = 11..20, part3 = 21..30, part4 = 31..40.
- Names: every person and pet first name is an invented Welsh-, Irish- or Scottish-sounding name (the style of
  "Eluned", "Tadhg", "Morven"); invented towns, companies, schools and clinics. Real countries and big real cities
  are allowed as places. No real public figures. To keep the four parts apart, person and pet first names start
  with A-F in part1, G-L in part2, M-R in part3, S-Z in part4. No name repeats across lives.
- Fact ids: `eNN-fMM` (NN = the life's number, MM a label local to the life).
- Each part meets the spec's minimums divided by 4, rounded up (teach 35: one fact 18, 2-3 facts 10, in passing 8;
  correct 7; nosave 7; one_hop 15; two_hop 9; reversal 7; edit 7 with at least 3 two-hop through the corrected
  fact; yesno 4; never_told 8; partial 3; smalltalk 13; creative 8; at least 15 asks on day 3 whose facts were all
  taught on day 1).
- Conventions as bank DEV's README states them: `gold.values` empty for yesno and never_told; for reversal the gold
  value is the fact's owner; for partial the known first-hop value; for two-hop and two-hop edit asks only the
  final answer, with both hops in `uses_facts`; a correction may change the relation as well as the value, and
  the old fact is closed at the correcting turn.
- Files: /mnt/project-files/escrow-y1e/partN/turns.jsonl, truth.jsonl, README.md. Checker (counts and ids only):
  `python3 -B scripts/claude_y1e_bankcheck.py /mnt/project-files/escrow-y1e/partN --lives 10 --prefix e2e-e-`.
- Then one blind auditor (a different agent) checks all 40 lives against the spec and writes fixes as
  turns_v2.jsonl / truth_v2.jsonl with audit.jsonl; the merged v2 files are sealed (SEAL.sha256.txt) and only the
  hashes go on main before the registered run.

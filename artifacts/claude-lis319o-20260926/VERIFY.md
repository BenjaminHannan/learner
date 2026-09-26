# lis-319o verify: FAIL (O2, O4)

Written 2026-09-26 16:54 UTC by the reading thread. Counts only; no panel text. Read: lis319o-panel-mac (lis-319f, read once, seals OK;
RESULTS-read.md on builder-outbox). 50 pairs, two blind Opus judges (JUDGE_SAME.md), both said same on all 50 (0 disagreements).
Judges' own notes: every saved owner matched the gold owner; 5-6 relation calls were broader or narrower synonyms.

| Mark | OLD (current compiler) | NEW (owner may come from earlier turns) | Bar | Result |
|---|---|---|---|---|
| O1 whole-claim right saves | 78 | 102 | >= OLD + 8 | pass (+24) |
| O2 wrong saves | 2 | 5 | <= OLD + 2 | FAIL (+3) |
| O3 lookalike saves (60 rows) | 0 | 0 | <= OLD + 1 | pass |
| O4 newly admitted saves not credited | - | 3 of 27 | <= 1 | FAIL |
Valid (86 facts need history; 240 rows read). Not proved wrong (gain 24 > 2).
Report: corrections saved right 0 -> 10 of 30; stale saves 0 -> 0; admitted saves on ambiguous rows 0; admitted wrong with a
gold fact of the same relation and value but another owner: 1; turns with a wrong save 2 -> 4.

## What it means
Letting the compiler accept owners named earlier finds many more right facts (+24, and corrections 0 -> 10), and the reader
never saved on the 10 ambiguous-pronoun rows. But 3 of the 27 newly admitted saves are wrong (1 of them the wrong person),
which is more than the bars allow. FAILs stay FAILs: the compiler is not changed.
Since Ben chose "Retrain first" (16:46), owners named earlier in the chat become code-labelled backref rows in lis-320's
GLM data, so the reader itself learns them. The compiler contract is re-tested only on lis-320, as its own single change.

## Correction (2026-09-26 17:03 UTC)
Line 19 says "1 of them the wrong person". That undercounts: all 3 of the wrong admitted saves were the wrong person.
The `admitted_wrong_owner` count in scripts/claude_lis319o_owner.py only matched when the relation name was identical;
two of the three used a synonym of the gold relation (employer vs works_at, occupation vs job), the third had the same
relation (allergy) with a different owner. The FAIL verdict and the O2/O4 counts do not change. lis-320 will score
wrong-person saves on backref rows as their own mark, on the owner only, whatever the relation is called.

# lis-320 ADDENDUM-3: a correction improvement mark (written before any lis-320 training row or reader read exists)

Written 2026-09-26 19:25 UTC by the reading thread. At this time no opencode-route row exists, no lis-320 reader exists, and no reader has
read the sealed panel (claude-readpanel320).

## Why
PASSMARKS R3 only asks that corrections not get worse (NEW >= OLD - 2). lis-320 is the plain, well-known fix for the
correction misses (lis-319k VERIFY.md: of 60 corrections lis-319f saved 4; 19 were compiler-rejected, mostly because the
owner was named in an earlier turn; 12 were read right but under the 0.995 bar). That fix is to train the reader on the
missing case: GLM-worded corrections (correct weight 3.0, update and fix kinds, dc2b7f7f7) and owners named earlier (backref).
The two rule-side tries failed: lowering the bar (lis-319k) and letting the compiler take earlier owners (lis-319o).
This mark says in advance whether the fix fixes corrections.

## Mark (from claude_lis320_score.py counts already computed; no code change)
- C1: NEW correction_right >= OLD correction_right + 10 on the sealed panel (52 gold corrections).
- Proved wrong: NEW correction_right <= OLD + 2.
- Valid only if OLD misses at least 20 of the correction facts; otherwise INCONCLUSIVE.
- C1 is reported as its own verdict ("training on corrections fixes corrections"). The lis-320 PASS/FAIL verdict stays
  R1-R7 as sealed; C1 does not change it either way.

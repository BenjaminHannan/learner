# Exp 259 value boundary: RESULTS

**Verdict: FAIL.** M1 (blind corrtail258 panel) fails 5 of its 10 bars. M3 (corrpanel252) fails on its sealed
mechanical rule, because of a scorer mismatch I made (details below). M2, M4, M5, M6 and M7 pass.
Seal: SEAL.sha256.txt (sha256 71f658233289f5a3...), sealed 17:55 and verified OK after the runs. Ledger P259.1-5.
Each registered run was done once. Panel seal OK; schema OK.

## Marks (259 vs 252b)
| Mark | Bar | 259 | 252b | Pass |
|---|---|---|---|---|
| M1 that_denial | >= 10/12 | 3/12 | 0/12 | no |
| M1 other_tail_denial | >= 8/10 | 2/10 | 1/10 | no |
| M1 false claims (all 80) | 0 | 1 (t258-003) | 5 (002, 003, 010, 011, 035) | no |
| M1 junk writes | 0, except same-as-252b in that_correction / pure_denial_that | 2: t258-009 (that_denial, same as 252b, not allowed), t258-026 (allowed, same as 252b) | 2 (009, 026) | no |
| M1 wrong values (that_denial + other_tail_denial) | 0 | 17 | 21 | no |
| M1 other families newly wrong | 0 | 0 | - | yes |
| M1 question_tail | 6/6 | 6/6 | 6/6 | yes |
| M1 unstored_tail | 6/6 | 6/6 | 6/6 | yes |
| M1 keep | 8/8, byte-identical to base252b | 8/8 | 8/8 | yes |
| M1 control | 16/16, byte-identical | 16/16 | 16/16 | yes |
| M1 that_correction / pure_denial_that (info) | - | 0/12, 2/10 | 0/12, 2/10 | - |
| M2 dev252b false replies | gone | 0 | 6 (001, 003, 010, 013, 014, 015) | yes |
| M2 wrong removals / question writes | 0 / 0 | 0 / 0 | 0 / 0 | yes |
| M2 junk | only b252-035 | only b252-035 | only b252-035 | yes |
| M2 controls / moves | identical / as predicted | 0 diffs; moves = exactly the 6 predicted | - | yes |
| M3 corrpanel252 | moves as predicted; 0 new wrong or junk | 1 move (c252-022), outside the sealed rule; 0 new wrong, 0 new junk | - | no |
| M4 suites | moves = 252b's; 0 new bad | rt136 4, sessions152 1, rt143 0, bench 0 (= 252b); 0 new bad; rows equal except seconds | same | yes |
| M5 sleep smoke | identical | identical | - | yes |
| M6 restart dialogs | 0 ghosts, 0 dup fails, 0 moves | 0, 0, 0 (18 rows) | 0, 0 | yes |
| M7 latency | <= +5 ms/turn | -0.06 ms (2.71 vs 2.77 ms median) | - | yes |

(The 252b scorer's own M2_pass prints false because its bar demands 0 junk. 259's bar allows b252-035, which is the only junk.)

## Every move
- M1, newly right vs 252b: t258-002, t258-010, t258-011, t258-035. Newly wrong: none.
- M2: b252-001, 003, 010, 013, 014, 015 each change from "I don't have <V, tail> as ..." (while V is stored)
  to "OK, I removed <V> as <S>'s <R>.", and the follow-up becomes "I don't know <S>'s <R>."
- M3: c252-022. 252b said "I don't have Tobin anymore, that's outdated as Quenby's manager, ..." while Tobin was
  stored. 259 says "OK, I removed Tobin as Quenby's manager." The sealed rule allows only the removal of
  head(V) = "Tobin anymore". The scorer's head() does not drop 252's clause-end word "anymore", although the fix
  does (I added that just before the seal and did not update the scorer). By the sealed rule this is a move
  outside prediction, so M3 = FAIL. No re-scoring was done.
- M4 / M5 / M6: no moves vs 252b.
- dev259 (information): 259 matches every sealed prediction. tail_denial 16/22 (252b 2/22), near_miss 9/9,
  unstored_tail 7/7, question_tail 6/6, keep 15/15 (identical to 252b), pronoun 2/2, restart 5/5.
  False claims: 0 on 259, 20 on 252b.

## Diagnosis (one note)
Almost all remaining M1 misses (t258-001, 004-008, 012, 036-042, 044) are sentences the base ears cannot read at
all. Both arms reply "I couldn't save that as a fact." 259 only acts after the ears have read the denial, so it
cannot help there. The panel uses two-word names such as "Tobiah Rusk" and other shapes the old ears reject.
t258-003 ("I don't have true as ...") and the t258-009 junk ("Saved: ... cat isn't Pumice, this is an old
record.") are 252b behaviour that 259 leaves unchanged.

## Deviations
- The fix went beyond the literal rule 1 in three places, all declared in PASSMARKS before the seal:
  3a (the tail lands in the relation words); 3b (154f-owned "X's R is not V, tail"); and the wording
  "I have S's R as V, not V W" for heads that extend a stored value with extra words.
- The M3 scorer rule and the fix disagree on "anymore"-type clause-end words (see above). This is a scorer bug
  sealed with the code. Reported, not fixed.
- M3 ids could not be listed before the seal (test-only panel); a mechanical rule stood in for them.
- The brief says 5 false replies in dev252b; there are 6 (b252-014 is the 154f-routed one).
- Scorers ran with /usr/bin/python3 (3.9), because python3 in bash is a broken binary on this Mac.
- After the runs I read the 259 replies for the wrong M1 rows and for c252-022, for the diagnosis only.

## What it means
When the model can read a denial with a trailing comment ("Nell doesn't work at Garrow, that's old news"),
259 now removes the right fact instead of wrongly saying it doesn't have it. On the development sets this
removed every false "I don't have X" reply. Nothing else changed: suites, sleep, restarts and speed all stayed
the same.

## What it doesn't mean
It does not make the model understand more kinds of sentences. On the blind panel most denials were not even
readable by the model's ears, so 259 could not act, and it scored 3/12 and 2/10 against bars of 10 and 8.
The real bottleneck on this panel is the ears (reading two-word names and new shapes), not the value boundary.
This is a toy test on fictional names, not a natural-conversation result.

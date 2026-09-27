# Exp 252b — value-screen fix on 252 — RESULTS

## Result: registered FAIL (M2, one item, as predicted)

- The fix removes the bad write behind c252-022. On the panel nothing else changed.
- It also removes 5 of the 6 junk writes that 252 makes on the new held-out safety dev.
- The one left is b252-035: "That's wrong, that's old news." still stores Kasia's employer as "old news". That write comes from the "that's Z" correction pattern, not from the value screen. It is exp 258's job, as ruled.
- M1, M3, M4 and M6 pass.
- Every prediction in PASSMARKS came true, including the FAIL.

## Marks

| Mark | Bar | 252 | 252b | Verdict |
|---|---|---|---|---|
| M1 panel rows differing from 252 (besides ms_per_turn) | c252-022 only | — | c252-022 only (0 other of 99) | pass |
| M1 c252-022 writes nothing, followup has no junk value | yes | stored "that's outdated" | store unchanged; followup "Quenby's manager is Tobin." | pass |
| M2 junk writes (56 items) | 0 | 6 | 1 (b252-035) | FAIL |
| M2 wrong removals | 0 | 0 | 0 | pass |
| M2 question writes (6 question items) | 0 | 0 | 0 | pass |
| M2 controls identical to 252 | 12/12 | — | 12/12 | pass |
| M3 moves equal 252's (rt136 4, sessions152 1, rt143 0, bench 0) | equal | 5 | 5, identical lists | pass |
| M3 new WRONG / WRONG-WRITE / junk / lost OK | 0 | — | 0 / 0 / 0 / 0 | pass |
| M4 sleep smoke fields that differ (besides agent / config / label / seconds) | 0 | — | 0 | pass |
| M6 ghost answers / failed duplicate checks / moves vs 252 (18 dialogs) | 0 / 0 / 0 | 0 / 0 | 0 / 0 / 0 | pass |

## Every difference

- **Panel c252-022.**
  - Turn reply: 252 said "Updated: Quenby's manager is that's outdated (it was Tobin)."; 252b says "I don't have Tobin anymore, that's outdated as Quenby's manager, so I didn't change anything."
  - Store: unchanged. Followup: "Quenby's manager is Tobin."

  The reply wording is clumsy, but nothing is written. Tobin staying is the same safe result as 138k.
- **Held-out dev, junk writes 252 made and 252b no longer makes:**
  - b252-001 "…, that's outdated" (employer)
  - b252-006 "…, thats outdated" (city)
  - b252-008 "… - that's changed" (boss)
  - b252-013 "…, that's outdated" (manager)
  - b252-018 "…, thats outdated" (place of birth)

  Each now writes nothing. The reply is either "I don't have …, so I didn't change anything." or the base's "I couldn't save that as a fact." The denied fact stays, so these denials are not carried out either, which is a safe miss.
- **Still wrong: b252-035.** "That's wrong, that's old news." after "Where does Kasia work?" gives "Updated: Kasia's employer is old news (it was Norbeck)."
- **Suites, smoke, restart dialogs:** no differences from 252.

## Reference column (no mark): 138k on the same dev, run once before the seal

- 138k has 1 junk write: b252-051 "Correction: Amos's teacher is Calloway." stores a fake person "Correction: Amos". This was already fixed by 252.
- It has 0 wrong removals and 0 question writes.
- All 6 of 252's junk writes on this dev (001, 006, 008, 013, 018, 035) were **introduced by 252**; 138k writes none of them. After 252b, only b252-035 is left.

## Screen word list (from PASSMARKS)

**Added:** thats hes shes theres heres whats whos wheres whens isnt wasnt arent werent doesnt didnt dont theyre youre theyll youll itll thatll therell wholl hed theyd youd itd thatd whod theyve youve weve whove.

**Excluded, because they are real words or names:** its hell shell well ill wed id shed were lets whys hows ive im cant wont.

## Deviations

- **M1 timing column.** M1 compares rows on every field except `ms_per_turn`. That is wall time, so it can never match byte for byte; this was stated in PASSMARKS before the seal.
- **252 comparison rows.** The 252 rows for M2 were made in the same registered session. The M3, M4 and M6 comparisons use 252's registered outputs from `artifacts/claude-correct252-20260922/run/`.
- **Load.** Load reached about 42 during the runs, under the limit of 60. The M1–M6 runs took under 3 minutes in total.
- Nothing was re-run.

## What it means

- The assistant no longer saves bits of chatter like "that's outdated" or "thats changed" as if they were a real place or boss, when you add them to the end of a correction.
- The change didn't alter anything else: the same answers on the blind test (except the fixed one), the old suites, sleep and restart checks.

## What it doesn't mean

- It is still not fully safe. "That's wrong, that's old news." still makes it save "old news" as a workplace. That is the next fix (258).
- It doesn't understand more sentences than before. In the fixed cases it now does nothing, rather than doing the right thing (removing the old fact).
- The word list only covers contractions written without their apostrophe. A new kind of chatter ("old news", "whatever") could still slip through the screen.

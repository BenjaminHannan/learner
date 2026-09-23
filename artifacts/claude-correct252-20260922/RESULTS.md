# Exp 252 — corrections and denials on 138k — RESULTS

## Result: registered FAIL

The fix passes every non-panel mark: dev, suites, sleep smoke, restart probe and latency.

On the blind panel, M1a, M1b and M1c fail. **M1a:** all five correction families fall short of their bars. **M1b:** 12 wrong values on my arm (the bar is 0; 138k has 52). **M1c:** 1 junk write. M1d (controls) passes.

My arm got 83/100 panel items right; 138k got 40/100. On the five correction families that is 45/62 against 2/62. There were 0 wrong removals on either arm, but 1 junk replacement on mine.

## Marks

| Mark | Bar | 138k | 252 (mine) | Verdict |
|---|---|---|---|---|
| M1a verb_denial | ≥ 13/14 | 0/14 | 9/14 | FAIL |
| M1a possessive_denial | ≥ 9/10 | 2/10 | 7/10 | FAIL |
| M1a contextual_denial | ≥ 11/12 | 0/12 | 10/12 | FAIL |
| M1a contextual_correction | ≥ 13/14 | 0/14 | 10/14 | FAIL |
| M1a explicit_correction | ≥ 11/12 | 0/12 | 9/12 | FAIL |
| M1b wrong values | 0 | 52 | 12 | FAIL |
| M1c junk writes | 0 | 3 | 1 | FAIL |
| M1c followup writes | 0 | 0 | 0 | pass |
| M1c question_trap (store unchanged) | 12/12 | 12/12 | 12/12 | pass |
| M1c ambiguous (store unchanged) | 6/6 | 6/6 | 6/6 | pass |
| M1c unstored_denial (store unchanged) | 8/8 | 8/8 | 8/8 | pass |
| M1d control, byte-identical to base138k.jsonl | 12/12 | 12/12 | 12/12 | pass |
| M2 dev right | 81/81 | 35/81 | 81/81 | pass |
| M2 dev junk writes / trap writes | 0 / 0 | — | 0 / 0 | pass |
| M2 dev restart items | 5/5 | 0/5 | 5/5 | pass |
| M3 new WRONG / WRONG-WRITE / junk / lost OK | 0 | — | 0 / 0 / 0 / 0 | pass |
| M3 moves equal the predicted list | 5 predicted | — | 5 (the same 5 ids) | pass |
| M4 sleep smoke fields that differ (besides agent / config / label / seconds) | 0 | — | 0 | pass |
| M5 added median time per turn | ≤ +5 ms | 2.84 ms | 2.90 ms (+0.06 ms) | pass |
| M6 ghost answers | 0 | 0 | 0 | pass |
| M6 failed duplicate checks | 0 | 0 | 0 | pass |
| M6 reply or store moves vs 138k (18 dialogs) | 0 predicted | — | 0 | pass |

**Harness checks:**
- The panel schema check passed (`run/schema-check.txt`).
- The panel hashes match the director's values, and `shasum -a 256 -c` on the panel seal passed.
- My re-score of the writer's base rows agrees with their `base_right` and `base_wrong_value` on 100/100 items.
- My own 138k run gave replies identical to the writer's base138k.jsonl on 100/100 items.

## Every move

**M3.** All five are reply-only. Verdicts and stored facts are unchanged, and these are exactly the predicted ids and texts.
- rt136 C071, C072, C073 and C075 (negations about people the notebook has never heard of). The reply is now "I don't have anything saved about Tom / Mira / Tom / Peru, so I didn't change anything."
- sessions152 S3-teachers-correction#6 ("no wait, it's denver", said after a two-hop answer). The reply is now "I worked that out from: Nadia's teacher is Rao and Rao's city is seattle. Which of those facts is wrong?" The verdict stays UNHELPFUL.
- rt143: none. bench (800 items): none.

**M4 and M6.** No moves.

**Panel: the 17 items my arm got wrong.** Nothing was wrongly removed. 16 of the 17 left the store as it was; the 17th is the junk write.
- **The junk write (c252-022).** The turn was "Quenby's manager is not Tobin anymore, that's outdated." My two-clause path read "that's outdated" as the new value and replaced the fact: "Updated: Quenby's manager is that's outdated". The cause is my stopword screen: it splits on spaces only, so "that's" does not match the stopword "that". This is a real safety bug in my code.
- **Missing apostrophes, not understood** (c252-005 "doesnt", c252-012 "cant", c252-021 "liesls coach isnt"). These three are among the wrong values: the followup still gave the old fact.
- **Wordings my reader does not handle.** Nothing was changed for any of these:
  - "isn't living in" (c252-009);
  - a trailing "that's old info" (c252-006);
  - ", not anymore" (c252-013);
  - "That's old info." as a denial (c252-030);
  - "They speak Suldari." with no correction word (c252-046);
  - "that's old info, she's at X now" (c252-048);
  - "it changed, it's delcot now" (c252-050).
- **Lowercase names, refused by the base teach reader** (c252-055 "elspet lives in ostrand now, not tessbury", c252-060 "quenby no longer works at kellin yard, she works at …"). My fix only replaces when the base teach path accepts the new fact, as the brief requires.
- **My own safety rules asked instead of acting:**
  - "no, oswin's not corwin's brother" (c252-019);
  - "no she doesnt" (c252-033);
  - "nope, velsic" (c252-041): a bare value after "no" asks, a rule I added before the seal after "No, Kira." looked like it could be a name said to me;
  - "Not Tobin, Garrow's teacher is Ysolde." (c252-062).

  Nothing was written in any of these. Where the followup then stated the old value, it counts as a wrong value.

M1b counts wrong values in: 005, 012, 019, 021, 030, 041, 046, 048, 050, 055, 060 and 062.

## Deviations

1. **Rows 138k had no usable base rows for.** 138k's saved suite rows for rt136, rt143 and sessions152 use names that `fable_suitediff` cannot find. As the director asked, I ran the four suites on 138k in this session before the seal (0 moves against 138j, GATE clean) and copied the rows under names it finds (`run/base138k-rows/`). The copies and the base run are sealed. A pilot of 138k against those rows gave 0 moves.
2. **Checker failure in the registered driver.** The M6 and M5 checker calls failed ("Bad CPU type": bash picked a broken `/usr/local/bin/python3`). The probe and latency runs themselves completed, once each. I then ran the same sealed checker (`scripts/claude_corr252_m6check.py`) on those saved outputs with the working `python3`. Nothing was re-run.
3. **Ledger time is wrong.** P252.1 says "sealed … 17:20"; the seal was actually made at about 17:01, before any registered run (M2 started at 17:02:16).
4. **Dev set changed before the seal.** Two pilot dev cases were rewritten before the seal:
   - d252-010: the followup "Whose employer is Ashgrove?" names the removed value, so the schema's wrong-value rule would always flag it;
   - d252-039: the lowercase verb sentence is refused by the base teach path.

   I also added two items (a bare name after "No," and "It's Tuesday." as a control). All of this happened before the seal.
5. **M1a thresholds are per family.** No family was re-run, and no item was run more than once.

## What it means

- The new layer lets the assistant take back a fact when you say it is wrong in the common shapes: "X doesn't work at Y", "Y isn't X's boss", "That's wrong" right after it told you something, "No, it's Z", and "Actually X lives in Z, not Y".
- Before, it removed almost nothing: 2 of 62 correction items right. Now it gets 45 of 62.
- It never removed the wrong fact.
- It never wrote on questions ("Doesn't X live in Y?"), on unclear turns, or on denials of things it didn't have.
- It left the controls exactly as before.
- It didn't break any old test suite, the sleep check or the restart check, and it adds almost no time.

## What it doesn't mean

- **It is not ready.** It failed the blind test in every correction family.
- **It made one bad write.** It saved "that's outdated" as someone's manager, because a word check missed "that's". That kind of mistake is exactly what the test is meant to catch.
- **Casual typing isn't handled.** Messages with no apostrophes ("doesnt", "cant"), all-lowercase names, and phrases like "that's old info" or "it changed" are mostly not understood.
- **In 12 cases the old value was still there.** The assistant would still repeat it afterwards.
- The dev set passing 81/81 only shows it handles the wordings I thought of myself. The panel shows that real wordings are wider than that.

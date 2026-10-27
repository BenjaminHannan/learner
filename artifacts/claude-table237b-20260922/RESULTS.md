# Exp 237b -- relation table v1.2 -- RESULTS

**Result: FAIL (registered).** M1 misses two family bars: synonym **21/30 (70 %)**, bar 85 %; new_relation **9/20 (45 %)**, bar 80 %.
Every other mark passes: date 8/10; traps 0 new value-giving; controls 10/10 byte-identical; 0 new wrong values; 0 question writes; M2 83/83; M3 GATE clean with only the predicted move; M4 sleep smoke clean; M5 -0.03 ms.
The table added **0 wrong answers and 0 writes**. It fixed 15 panel items (base221 -> 237b: synonym 14 -> 21, new_relation 6 -> 9, date 3 -> 8).
**Main cause of the misses:** 15 of the 22 misses are asked with a verb or a phrase ("Who mentors X?", "Who does X's hair?", "What bicycle does X ride?", "What does X go by?"), not with a relation noun. v1.2 was enumerated noun-first, so it lists relation names and their synonyms, but very few verb wordings.

## Marks
| Mark | Bar | Result | Pass |
|---|---|---|---|
| M1 synonym | >= 85 % | 21/30 (70 %) | **FAIL** |
| M1 new_relation | >= 80 % | 9/20 (45 %) | **FAIL** |
| M1 date | >= 80 % | 8/10 | pass |
| M1 trap NEW value-giving vs base221 | 0 | 0 (traps 10/10 abstain) | pass |
| M1 control byte-identical to base221 | 10/10 | 10/10 | pass |
| M1 new wrong values | 0 | 0 | pass |
| M1 question writes | 0 | 0 | pass |
| M2 dev cases | all right, 0 writes | 83/83 (syn 38/38, new 18/18, date 9/9, trap 14/14, control 4/4), 0 writes | pass |
| M3 suitediff vs 237's base221 rows | 0 bad, predicted moves only | rt136 0, rt143 1 (L3 reply-only, predicted), sessions152 0, bench 0; GATE clean | pass |
| M4 sleep smoke | as 237 | sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, ow 0, 82.6 s | pass |
| M5 median added ms vs loop221 | <= +5 | -0.03 | pass |

Schema check: SCHEMA OK. Both seals (mine, 12 files; panel, director hashes) were verified before and after the runs. The 221 arm reproduced base221 80/80.

## Every move vs base221 (16)
- Right after being wrong (15):
  - synonym 015 physician, 016 GP, 017 telephone number, 018 cell number, 019 email address, 021 last name, 022 family name;
  - new_relation 031 "the landlord for X", 034 "Who tutors X?", 041 "Who coaches X?";
  - date 056 graduate, 057 "first open" (the capture fix), 058 founded, 059 "open its doors", 060 birthday -> date of birth (the reply names "date of birth").
- Abstain -> different abstain (1): 055 "When did Elsbeth get married?" now gives "I don't know Elsbeth's wedding date." (the stored relation is wedding_anniversary, which is not linked). Run alone 5 times: identical all 5, no write. The 228 guard was installed. This is not a flip away from a right answer.
- Suites: rt143 L3 reply-only ("I don't know Tomas Reed's team."), as predicted.

## Every miss (22), with a one-line diagnosis
Synonym (9):
- 014 "Which college does Zelbie attend?" (stored: university): the "Which R does X attend?" wording is not in the table.
- 020 "Where does Ilvessa live?" (stored: address): the wording maps to the city row, and address is not in its group, so the reply is an honest "don't know city".
- 023 "What does Brannoc go by?" (nickname): verb wording not listed.
- 024 "What vehicle does Dessary drive?" (car): vehicle was deliberately kept as its own row (broader than car), and the "What vehicle does X drive?" wording is missing.
- 025 "What bicycle does Keffin ride?" (bike): "ride" wording not listed.
- 026 "What motorcycle does Orlena ride?" (motorbike): "ride" wording not listed.
- 027 "What is the name of Pashko's puppy?" (dog): the base claims "the name of X" (known limit), and puppy is not an alias of dog.
- 028 "What's the name of Wendrel's kitty?" (cat): same cause as 027.
- 029 "Who is Calloway's closest friend?" (best friend): alias "closest friend" missing.

New_relation (11):
- 033 "Who is the vet for Corvath's pets?": the base captures "the vet for Corvath", and "'s pets" fits no template.
- 036 "Who lives next door to X?" (neighbour): verb wording missing.
- 037 "Who does X share a flat with?" (flatmate): verb wording missing.
- 038 "Who plays in a band with X?" (bandmate): verb wording missing.
- 040 "Who teaches Jorvel piano?" (piano teacher): verb wording missing; the base reads "Jorvel piano" as a name.
- 042 "Who does X's accounts?" (accountant): verb wording missing.
- 044 "Who does X's hair?" (hairdresser): verb wording missing.
- 045 "Who mentors X?" (mentor): verb wording missing.
- 047 "Who babysits X?" (babysitter): verb wording missing.
- 048 "Who is teaching X to drive?" (driving instructor): verb wording missing.
- 049 "Who's the plumber X uses?" (plumber): wording missing.

Date (2):
- 053 "What day was Cressida born on?" (birthday): wording missing.
- 055 "When did Elsbeth get married?" (wedding anniversary): the wording reaches wedding_date, and wedding_anniversary is not linked to it.

All 22 misses are abstains. None gives a wrong value.

## Predictions (ledger P237b.1-6)
- P237b.1 WRONG (synonym and new_relation bars missed).
- P237b.2 RIGHT.
- P237b.3 RIGHT.
- P237b.4 RIGHT.
- P237b.5: the mark passed, but the prediction range (+1 to +4) was WRONG. The panel median was -0.03 ms, because the 221 arm also reads its table on base misses. Dev showed +2.6.
- P237b.6 PARTLY right. It named the "name of" limit (027, 028) and the deliberate non-links (024 vehicle, 055). It missed the main cause: verb-phrase asks.

## Deviations
- Reused 237's sealed runner scripts/claude_table237_run.py (hash unchanged, included in my seal).
- The scorer drops a leading a/an/the when it matches values. This is declared in PASSMARKS before the seal.
- 3 dev cases were changed during the pilot, before the seal (d40, d45, d83; listed in PASSMARKS).
- The trailing-word fix ("first open") was done in table data only. No code was needed.
- There was a pilot-only shell slip (zsh variable-as-command), before the seal. There were no fixes of any kind after the seal and no re-runs, except the required 5x single-item run of 055.

## What it means
- Adding true synonyms to the table is safe. It fixed 15 questions and added no wrong answers, no writes, no trap leaks and no cost in speed.
- When people ask about a relation, they often use a verb ("Who mentors Orrin?") instead of the relation's noun. A noun-first table cannot catch those. The next table needs a verb-wording section per relation: mentors / babysits / coaches / teaches X Y / does X's hair / lives next door to / rides / goes by / attends.

## What it doesn't mean
- It does not mean the table gives wrong answers. Every miss was an honest "I don't know".
- It does not show that synonym coverage is complete. The pass is on my own dev cases only, and the blind panel says it is not.
- The fix is not proven. Adding verb wordings is a guess based on this one panel of 80 items, and it would need a new blind panel to test.

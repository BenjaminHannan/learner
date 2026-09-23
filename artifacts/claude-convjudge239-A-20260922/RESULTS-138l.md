# Exp 239 conversation panel — Judge A grades of merge 138l vs 138k vs 138i (TEST-ONLY)

**Result first:** 138l fixes storage for one sentence type and still sits far from Ben's targets. Correct rises
82 -> 86/244 and fully good turns 43 -> 47. Bad writes fall 5 -> 1. But grammatical falls 107 -> 97, because several
wrong-but-grammatical replies were replaced by the two ungrammatical fallback templates. Natural >= 4 stays at 51, and
conversations with zero simple mistakes stay at 0/30.

Method: the panel seal was checked (panel.jsonl OK); the 138l transcript and change file are outside that seal.
I diffed 138l against 138k myself. I found the same 15 changed replies and the same 43 changed turns (a reply or the
stored triples before or after changed) as the change file. I re-graded 67 turns blind: those 43, plus every later turn in
a conversation where an earlier reply changed (its visible context). All used the rubric and consistency rules in
RESULTS.md, plus the added rule for the rephrase template from RESULTS-138k.md. The other 177 turns carry their 138k grade
(`carried=true` in grades-138l.jsonl). No agent code, design notes or other judges' files were read.

## Rates, side by side

| measure | 138i | 138k | 138l |
|---|---|---|---|
| grammatical | 104/244 (42.6%) | 107/244 (43.9%) | 97/244 (39.8%) |
| correct | 81/244 (33.2%) | 82/244 (33.6%) | 86/244 (35.2%) |
| natural mean | 2.07 | 2.28 | 2.29 |
| natural >= 4 | 51 (20.9%) | 51 (20.9%) | 51 (20.9%) |
| fully good turns | 43 | 43 | 47 |
| conversations with 0 simple mistakes | 0/30 | 0/30 | 0/30 |
| bad writes | 5 | 5 | 1 |
| missing writes | 42 | 41 | 41 |

Per intent (138i / 138k / 138l):

| intent | turns | grammatical | correct | natural mean | natural >= 4 |
|---|---|---|---|---|---|
| ask | 83 | 25 / 25 / 19 | 14 / 14 / 14 | 1.60 / 1.60 / 1.59 | 8 / 8 / 8 |
| cannot | 11 | 0 / 0 / 0 | 4 / 4 / 4 | 1.36 / 1.36 / 1.36 | 0 / 0 / 0 |
| correct | 6 | 0 / 0 / 0 | 0 / 0 / 0 | 1.00 / 2.00 / 2.00 | 0 / 0 / 0 |
| greet | 27 | 22 / 22 / 22 | 21 / 21 / 21 | 2.59 / 2.59 / 2.59 | 0 / 0 / 0 |
| other | 1 | 1 / 1 / 1 | 1 / 1 / 1 | 5.00 / 5.00 / 5.00 | 1 / 1 / 1 |
| self | 18 | 5 / 7 / 7 | 2 / 2 / 2 | 1.33 / 1.83 / 1.83 | 1 / 1 / 1 |
| smalltalk | 5 | 3 / 3 / 3 | 0 / 0 / 0 | 1.60 / 1.60 / 1.60 | 0 / 0 / 0 |
| teach | 63 | 25 / 26 / 22 | 16 / 17 / 21 | 2.00 / 2.59 / 2.63 | 18 / 18 / 18 |
| thanks | 30 | 23 / 23 / 23 | 23 / 23 / 23 | 3.90 / 3.90 / 3.90 | 23 / 23 / 23 |

Simple-mistake counts:

| simple_mistake | 138i | 138k | 138l |
|---|---|---|---|
| none | 69 | 70 | 74 |
| missed_known_fact | 61 | 58 | 62 |
| missing_write | 42 | 41 | 41 |
| misread_request | 25 | 26 | 27 |
| odd_or_broken_sentence | 12 | 12 | 12 |
| unhelpful_decline | 12 | 12 | 12 |
| ignored_correction | 6 | 6 | 6 |
| wrong_subject | 8 | 6 | 1 |
| other | 4 | 5 | 5 |
| bad_write | 5 | 5 | 1 |
| wrong_value | 0 | 3 | 3 |
| false_yes | 0 | 0 | 0 |

Mistakes per conversation: 1 to 9, median 6 (unchanged).

## Grade changes vs 138k (67 re-graded turns)

| outcome | turns | by intent |
|---|---|---|
| better | 4 | teach 4 |
| worse | 7 | ask 6, teach 1 |
| mixed | 3 | teach 3 |
| same | 53 | ask 26, thanks 14, teach 9, correct 3, cannot 1 |

"Better" or "worse" compares correct first, then grammatical and natural. "Mixed" means grammatical went down and
natural went up.

By category:
- **Better (bad_write -> none, 4):** a "my <relation> is called/named <Name>" teach now stores the bare name and says
  so cleanly. This is the only storage fix, and it is the whole of the correct-count and bad-write gain.
- **Still a bad write (1, same grade):** the same sentence shape with a misspelled relation word now stores the right
  name, but under the misspelled relation, and the confirmation echoes the typo.
- **Worse (7):** 6 questions that used to get a grammatical-but-wrong reply (the name-question hijack, or the
  favourites misroute) now get either the glued fallback or the save-failure rephrase reply. Correctness is unchanged
  (still wrong), grammar is lost. wrong_subject becomes missed_known_fact 4, misread_request 2. One teach turn moved
  from the name hijack to the rephrase reply (missing_write both times; grammar lost).
- **Mixed (3):** teach turns that used to get the name hijack or the favourites misroute now get the honest
  rephrase reply: less confusing (natural 1 -> 2) but ungrammatical. Still missing_write.
- **Same (53):** mostly later turns in the affected conversations. Notably, questions about the relatives whose names
  are now stored cleanly still fail: the "anyone called my <relation>" reply and the fallback persist on 4 turns where the
  answer was in the notebook with the correct value. Clean storage alone did not fix recall.

## What it means

138l stores one common way of naming a relative or pet correctly, and the notebook is cleaner (1 bad write left).
The user still can't get those names back by asking, and removing the name-question hijack exposed the two
ungrammatical templates on more turns. The grammar rate went down.

## What it doesn't mean

The four extra correct turns are all confirmations of saves. No question became answerable, and recall, corrections,
self questions and social turns are unchanged. The better/worse split is one judge's rule (correct, then
grammar and naturalness), and 177 turns were carried rather than re-read.

## Where judgement was hard

- A misspelled relation stored with the right name: kept as a bad write (the notebook key won't match the correct
  spelling), unchanged from 138k.
- Replacing a wrong-but-grammatical reply with an ungrammatical one: counted as worse, although the new replies are
  arguably more honest.

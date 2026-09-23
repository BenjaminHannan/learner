# Exp 239 conversation panel — Judge A grades of agent 138k vs 138i (TEST-ONLY)

**Result first:** 138k is a small step up from 138i and nowhere near Ben's targets. Grammatical 107/244 (43.9%,
was 42.6%); correct 82/244 (33.6%, was 33.2%); natural mean 2.28 (was 2.07); natural >= 4 unchanged at 51;
fully good turns unchanged at 43; conversations with zero simple mistakes still 0/30. Almost all of the natural-score
gain comes from one thing: a failed teach now gets an honest "couldn't save that" reply instead of the glued
fallback. The facts are still not saved. One new kind of error appeared: 3 wrong values (138i had none).

Method: the panel seal was checked (panel.jsonl OK). I diffed the two transcripts myself and got the same
60 changed turns as the coordinator (a reply, the stored triples after, or the stored triples before differ).
I graded those 60 blind from the panel, the 138k transcript and the stored triples, using the rubric and
consistency rules in RESULTS.md. The other 184 turns carry their 138i grade (`carried=true` in grades-138k.jsonl).
No agent code, design notes or Judge B files were read. Note: the 138k transcript and the change file are not
covered by the panel seal (it covers panel.jsonl only).

One rule added for a reply template 138i never produced, a request to rephrase because the sentence
"shape" isn't known:
grammatical = no (an internal jargon word, and the rephrase request ends without a question mark). Natural = 2 on
statement turns (teach, correct), because there it truthfully says nothing was saved but asks the user to rephrase plain
English. Natural = 1 on questions, thanks and small talk, where it treats the turn as a fact to save.
This parallels rule 1 for the old fallback.

## Rates, 138i vs 138k

| measure | 138i | 138k |
|---|---|---|
| grammatical | 104/244 (42.6%) | 107/244 (43.9%) |
| correct | 81/244 (33.2%) | 82/244 (33.6%) |
| natural mean | 2.07 | 2.28 |
| natural >= 4 | 51 (20.9%) | 51 (20.9%) |
| fully good turns (grammatical, natural >= 4, correct) | 43 | 43 |
| conversations with 0 simple mistakes | 0/30 | 0/30 |
| bad writes | 5 | 5 |
| missing writes | 42 | 41 |

Per intent (138i / 138k):

| intent | turns | grammatical | correct | natural mean | natural >= 4 |
|---|---|---|---|---|---|
| ask | 83 | 25 / 25 | 14 / 14 | 1.60 / 1.60 | 8 / 8 |
| cannot | 11 | 0 / 0 | 4 / 4 | 1.36 / 1.36 | 0 / 0 |
| correct | 6 | 0 / 0 | 0 / 0 | 1.00 / 2.00 | 0 / 0 |
| greet | 27 | 22 / 22 | 21 / 21 | 2.59 / 2.59 | 0 / 0 |
| other | 1 | 1 / 1 | 1 / 1 | 5.00 / 5.00 | 1 / 1 |
| self | 18 | 5 / 7 | 2 / 2 | 1.33 / 1.83 | 1 / 1 |
| smalltalk | 5 | 3 / 3 | 0 / 0 | 1.60 / 1.60 | 0 / 0 |
| teach | 63 | 25 / 26 | 16 / 17 | 2.00 / 2.59 | 18 / 18 |
| thanks | 30 | 23 / 23 | 23 / 23 | 3.90 / 3.90 | 23 / 23 |

Simple-mistake counts (138i -> 138k): none 69 -> 70; missed_known_fact 61 -> 58; missing_write 42 -> 41;
misread_request 25 -> 26; odd_or_broken_sentence 12 -> 12; unhelpful_decline 12 -> 12; wrong_subject 8 -> 6;
ignored_correction 6 -> 6; bad_write 5 -> 5; other 4 -> 5; **wrong_value 0 -> 3**; false_yes 0 -> 0.
Mistakes per conversation: 1 to 9, median 6 (unchanged).

## Grade changes

Of the 60 changed turns, 50 changed grade and 10 kept an identical grade (7 thanks, 2 small talk, 1 ask).
By intent: teach 36, correct 6, self 5, ask 3. Most changes are natural score only: 42 of the 50 kept the
same mistake label, and 47 of the 50 changed natural score (net +52 points). Only 8 changed label:
missed_known_fact -> misread_request 2, missed_known_fact -> wrong_value 1, wrong_subject -> wrong_value 1,
unhelpful_decline -> wrong_value 1, wrong_subject -> other 1, misread_request -> unhelpful_decline 1,
missing_write -> none 1.

## Mistake classes that moved (general words)

1. **Failed teach turns now say so honestly, but still don't save.** The glued "don't know / didn't understand"
   block on teach and correction turns was replaced by a clear "I couldn't save that, please rephrase" reply (51 replies).
   It is better (natural 1 -> 2) but still not grammatical, it names an internal concept, and it pushes the work back
   onto the user. The same set of everyday sentence types still fails to store (see RESULTS.md class 2). Correction
   turns remain 0/6.
2. **The new rephrase reply leaks onto non-statement turns.** Questions typed casually or lower-case, thanks phrased
   in less common ways, and small talk now get "I couldn't save that as a fact". This is as confusing as before and
   reads as if the assistant misheard a question as a statement.
3. **"Works at" now stores, for one sentence shape.** A lower-case "<name> works at <place>" was saved (reply uses
   "employer", natural 3). This is the only teach turn to become correct.
4. **New: stale answers after a failed correction (wrong values).** Because the correction could not be saved, a
   follow-up question returned the old value confidently. This is the first wrong fact a user would see from this
   agent. The two-step question over that same stored fact still fell to the old fallback, a real recall failure.
5. **Self questions: new answers, still wrong.** Asked its name, it now says it has no name because nobody gave it one
   (a wrong value, since its name is Premonition). Asked who made it, it says nobody taught it that. Both add an
   internal description ("a notebook, a lookup loop, and fixed rules"). They are grammatical and less confusing
   (natural 3) but still incorrect. Self intent stays at 2/18 correct.
6. **Unchanged:** recall of stored facts, the "anyone called my <relation>" reply, the name-question hijack on
   non-self turns, greetings, out-of-scope requests, the favourites misroute, and all 5 bad writes.

## What it means

138k fixes the tone of failure more than the failures themselves. Users are now told plainly when a fact wasn't
saved, and the assistant describes itself instead of answering about the user. But almost everything that failed in
138i still fails. A few questions now get confident wrong answers where 138i said "don't know", and one of those
is its own name.

## What it doesn't mean

It does not mean storage or recall improved: only one extra teach turn stored, and only 1 correct-count point moved.
The natural-mean gain rests mostly on my added rule for the new template. A judge who scored that template at 1
would see almost no change. 184 turns were carried over, not re-read. The changed turns were graded blind, but the
same judge graded both runs.

## Where judgement was hard

- How to score the new rephrase reply (see the added rule above). It is honest on teach turns, which makes 2 rather than 1 defensible.
- "Who are you" answered with a self-description that omits its name: graded not correct (label other).
- The "no name" answers: wrong_value rather than unhelpful_decline, because it asserts something false about itself.
- The stale-value answer after a failed correction: wrong_value on the question turn, with the correction turn itself
  already counted as ignored_correction.

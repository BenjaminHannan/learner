# Exp 239 conversation panel — Judge A regrade of agent 138m vs 138l (TEST-ONLY)

**Result first:** 138m is better than 138l on grammar and on questions about the assistant itself, but no better at
answering taught facts. Grammatical replies went from 97 to 171 of 244. Fully good turns went from 47 to 61.
Correct went only from 86 to 89. Still **0 of 30 conversations had zero simple mistakes**.
Of the 84 changed turns, 72 were better, 11 worse and 1 the same. All 11 worse turns are cases where the right
answer was "I don't know" or "I can't do that". The old long fallback said it did not know. The new short reply
only says it did not understand the question.

Seal: `shasum -a 256 -c artifacts/claude-convpanel239-20260922/SEAL.sha256.txt` -> panel.jsonl OK.

Method: I regraded only the 84 turns whose reply changed. I followed the rubric and conventions 1–7 in RESULTS.md,
and used grades-138l.jsonl to keep similar replies graded alike. The other 160 rows are copied from grades-138l.jsonl
with carried=true. No stored triples changed, so no teach-turn write grades moved.
File: `artifacts/claude-convjudge239-A-20260922/grades-138m.jsonl`.

New convention 8, needed for the short fallbacks 138m introduces:
- The short "didn't understand the question, say it another way" reply is graded grammatical=yes and natural=2
  (readable but off-target). On a question whose fact the user had taught, it counts as missed_known_fact.
  On a question the assistant should handle about itself, it counts as unhelpful_decline.
  On an out-of-scope request or a question whose right answer is "I don't know", it is correct=no with the label
  misread_request. It never says it doesn't know or can't do the task, so rule 1/4's "right substance" credit does not apply.
- The short "didn't understand that well enough to save it" reply is grammatical. Natural is 1 on a plain
  greeting or thanks, where it is plainly wrong for the turn, and 2 when the turn really did contain a statement.
  On a teach turn with nothing stored it is labelled missing_write (rule 2).

## Totals

| measure | 138l | 138m |
|---|---|---|
| grammatical | 97/244 (39.8%) | 171/244 (70.1%) |
| correct | 86/244 (35.2%) | 89/244 (36.5%) |
| natural mean | 2.29 | 2.65 |
| natural >= 4 | 51 (20.9%) | 65 (26.6%) |
| fully good (grammatical, natural >= 4, correct) | 47 | 61 |
| conversations with zero simple mistakes | 0/30 | 0/30 |
| bad writes | 1 | 1 |
| missing writes | 41 | 41 |

Mistakes per conversation for 138m: 1 to 9, median 5.

## Per intent

Each cell shows 138l -> 138m.

| intent | turns | grammatical | correct | natural mean | natural >=4 | fully good |
|---|---|---|---|---|---|---|
| ask | 83 | 19 -> 65 | 14 -> 9 | 1.59 -> 2.14 | 8 -> 10 | 5 -> 7 |
| cannot | 11 | 0 -> 11 | 4 -> 0 | 1.36 -> 2.00 | 0 -> 0 | 0 -> 0 |
| correct | 6 | 0 -> 0 | 0 -> 0 | 2.00 -> 2.00 | 0 -> 0 | 0 -> 0 |
| greet | 27 | 22 -> 27 | 21 -> 21 | 2.59 -> 2.63 | 0 -> 0 | 0 -> 0 |
| other | 1 | 1 -> 1 | 1 -> 1 | 5.00 -> 5.00 | 1 -> 1 | 1 -> 1 |
| self | 18 | 7 -> 17 | 2 -> 11 | 1.83 -> 3.39 | 1 -> 10 | 1 -> 10 |
| smalltalk | 5 | 3 -> 3 | 0 -> 3 | 1.60 -> 2.80 | 0 -> 3 | 0 -> 3 |
| teach | 63 | 22 -> 23 | 21 -> 21 | 2.63 -> 2.65 | 18 -> 18 | 17 -> 17 |
| thanks | 30 | 23 -> 24 | 23 -> 23 | 3.90 -> 3.90 | 23 -> 23 | 23 -> 23 |

Ask "correct" dropped from 14 to 9. Two recall turns became correct (user's-name questions now answered). Seven
turns whose right answer was "I don't know" lost their credit (convention 8).

## Simple-mistake labels

| simple_mistake | 138l | 138m |
|---|---|---|
| none | 74 | 88 |
| missed_known_fact | 62 | 59 |
| missing_write | 41 | 41 |
| misread_request | 27 | 39 |
| odd_or_broken_sentence | 12 | 1 |
| unhelpful_decline | 12 | 5 |
| ignored_correction | 6 | 6 |
| other | 5 | 2 |
| wrong_value | 3 | 1 |
| wrong_subject | 1 | 1 |
| bad_write | 1 | 1 |
| false_yes | 0 | 0 |

## The 84 changed turns: better 72, worse 11, same 1

How I compared: a change in "correct" decides the verdict. When "correct" did not change, the turn is better or worse
depending on grammar and naturalness (no turn was mixed). Fully good among the changed turns went from 0 to 14.

What kinds of changes these were:
- **Better (72).**
  - 41 ask turns now get a short, grammatical "didn't understand, say it another way" instead of the long,
    self-contradicting fallback. They are still wrong: 39 still miss a taught fact. Two now return the user's
    stored name correctly.
  - 14 self turns got better. Its name, who built it, whether it is a person, what it is and how it learns are now
    answered in plain sentences. Nine of these became fully good. Five still get the short "didn't understand" reply
    (what it knows right now, what it can do, how it compares to a general chatbot, where it keeps facts, whether it
    can remember), but it is now grammatical.
  - 3 small-talk turns ("how are you" style) now get a friendly "ready to learn" line in place of an internal
    status line. They count as correct, but the line is a little stiff (natural 4).
  - 7 cannot turns (jokes, opinions, likes, advice, alarms, messages) and 6 greeting/thanks turns now get a
    grammatical short fallback. They are still misreads: none of them declines politely or greets back.
  - 1 teach turn with a leading greeting still stores nothing, but the reply is now grammatical.
- **Worse (11).**
  - 7 ask turns and 4 cannot turns (weather, time, general knowledge) had "I don't know" as the right answer.
    The old long fallback contained that substance and was credited as correct but ungrammatical. The new short
    reply says only that it did not understand the question, so it is now a misread.
- **Same (1).**
  - A question about a detail the user never gave now returns a different stored fact about the user instead of
    saying it doesn't know. Its natural and correct grades are unchanged; the label moves from missed_known_fact
    to misread_request.

## What it means

To a user, 138m reads as much cleaner English (70% grammatical against 40%). It now handles the common
"who/what are you" questions. It still saves and recalls the same small set of facts, since no writes changed. It
also still says "I didn't understand" to many ordinary questions it should answer, or should answer with a plain
"I don't know / I can't do that". The next gain is not in wording. It is in routing: recognising a known-fact
question, an honest don't-know, and an out-of-scope request.

## What it doesn't mean

This is one judge's hand regrade of 84 changed replies from one run. The 160 carried rows were not re-examined.
Convention 8 is a judgement call. If short "didn't understand" replies on don't-know turns were credited as correct,
correct would be 100/244 and the 11 worse turns would count as better.

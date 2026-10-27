# Exp 239 conversation panel — Judge A grades of agent 138i (TEST-ONLY)

**Result first:** by a user's eye, 138i is far from Ben's targets. Grammatical replies 104/244 (42.6%),
correct 81/244 (33.2%), natural mean 2.07/5 with 51/244 (20.9%) at 4 or better. Only 43/244 turns were
fully good (grammatical, natural >= 4 and correct). **0 of 30 conversations had zero simple mistakes**
(best conversation: 1 mistake). 5 bad writes, 42 missing writes. Target was 99%+ grammar and no simple mistakes.

Seal: `shasum -a 256 -c artifacts/claude-convpanel239-20260922/SEAL.sha256.txt` -> panel.jsonl OK.

## Rubric (written before grading, applied to all 244 replies by hand)

- **grammatical** (yes/no): would a careful copy-editor accept it as written English? Casual register is fine.
  "no" for: broken agreement, wrong article, empty list slots, run-on or glued sentences that contradict each other,
  raw code-like words, a doubled or garbled phrase, or an echoed misspelling in the assistant's own sentence.
- **natural** (1–5): 5 = a helpful person would say exactly this; 4 = fine, slightly stiff; 3 = understandable but robotic;
  2 = odd or off-target but readable; 1 = confusing or plainly wrong for the turn.
- **correct** (yes/no/na): does it do what the panel's expect note says, checked against the stored triples.
  A teach turn is correct only if the right facts were stored with the right values.
- **simple_mistake**: one primary label per turn: none, wrong_value, false_yes, missed_known_fact, misread_request,
  wrong_subject, bad_write, missing_write, ignored_correction, odd_or_broken_sentence, unhelpful_decline, other.
- **bad_write** (yes/no).
- **fix**: a one-line better reply whenever the turn is not (grammatical=yes, natural>=4, correct=yes).

Consistency rules I used:
1. The long three-sentence fallback (says "I don't know it from what you taught me", "I won't guess" and "I didn't
   understand, say it another way" all at once) is graded grammatical=no (glued, self-contradicting sentences with a
   comma splice). Natural = 2 when the right answer really was "I don't know" (then correct=yes, mistake =
   odd_or_broken_sentence); natural = 1 everywhere else.
2. Teach turn with nothing stored -> missing_write, whatever the reply says.
3. Ask turn where the user had taught the answer -> missed_known_fact, even when the fact never reached the notebook
   (the user can't see the notebook). I note below how many of these had the fact actually stored.
4. Out-of-scope lookups (weather, time, capital city): a "don't know" is the right substance -> correct=yes but
   ungrammatical. Out-of-scope actions/opinions (jokes, alarms, messages, advice, likes) answered with "not taught"
   -> correct=no, misread_request.
5. Questions about the assistant itself that it should handle -> unhelpful_decline when it gives the fallback,
   wrong_subject when it answers about the user instead.
6. Saying "you're welcome" to a thanks-plus-goodbye counts correct, natural 4.
7. A stored value that keeps a leftover naming word from the sentence ("called <Name>") is a bad_write.

## Rates

| group | turns | grammatical | correct | natural mean | natural >=4 |
|---|---|---|---|---|---|
| ALL | 244 | 104 (42.6%) | 81/244 (33.2%) | 2.07 | 51 (20.9%) |
| ask | 83 | 25 (30.1%) | 14/83 (16.9%) | 1.60 | 8 (9.6%) |
| cannot | 11 | 0 (0.0%) | 4/11 (36.4%) | 1.36 | 0 (0.0%) |
| correct | 6 | 0 (0.0%) | 0/6 (0.0%) | 1.00 | 0 (0.0%) |
| greet | 27 | 22 (81.5%) | 21/27 (77.8%) | 2.59 | 0 (0.0%) |
| other | 1 | 1 (100.0%) | 1/1 (100.0%) | 5.00 | 1 (100.0%) |
| self | 18 | 5 (27.8%) | 2/18 (11.1%) | 1.33 | 1 (5.6%) |
| smalltalk | 5 | 3 (60.0%) | 0/5 (0.0%) | 1.60 | 0 (0.0%) |
| teach | 63 | 25 (39.7%) | 16/63 (25.4%) | 2.00 | 18 (28.6%) |
| thanks | 30 | 23 (76.7%) | 23/30 (76.7%) | 3.90 | 23 (76.7%) |

No correct field was graded "na". Fully good turns (grammatical, natural >= 4, correct): 43/244.

## Simple mistakes (one primary label per turn)

| simple_mistake | turns |
|---|---|
| none | 69 |
| missed_known_fact | 61 |
| missing_write | 42 |
| misread_request | 25 |
| odd_or_broken_sentence | 12 |
| unhelpful_decline | 12 |
| wrong_subject | 8 |
| ignored_correction | 6 |
| bad_write | 5 |
| other | 4 |
| wrong_value | 0 |
| false_yes | 0 |

Of the 61 missed_known_fact turns, about 10 had the needed fact(s) actually in the notebook (a retrieval or
routing failure); the other ~51 are knock-on effects of a teach turn that stored nothing.
No false yes and no invented values were seen: when the agent fails, it fails toward "don't know", never toward a wrong fact.

## Bad writes: 5

All five are the same pattern: a "my <relation> is called/named <Name>" teach stored the value with the
naming word still attached (so the value is "called <Name>" instead of "<Name>"). One of the five also stored a
misspelled relation word exactly as the user typed it. The later questions about those people then failed.
No write stored a fact the user never said.

## 0-simple-mistake conversations: 0 / 30

Mistakes per conversation ranged from 1 to 9 (median 6).

## Top failure classes, ranked by how often a user would hit them

1. **The long all-purpose fallback.** 124/244 replies (51%), in 29/30 conversations. One fixed block glues
   "I don't know that from what you taught me", "I won't guess" and "I didn't understand, say it another way"
   together. It is ungrammatical, contradicts itself, and is used for greetings, thanks, facts being taught,
   questions it should answer, and out-of-scope requests alike. This single reply is most of the grammar failure.
2. **Everyday teach sentences are not stored** (42 missing writes, 26 conversations; only 16/63 teach turns correct).
   Stored reliably: "my <relation> is <Name>" and "<Name>'s <relation> is <Name>", plus "<Name> lives in <Place>".
   Not stored: first-person facts about the user (where I live, where I work, my job, my school), "I have / I've got a
   <pet> named X", pronoun follow-ups ("she/he/they ..."), ages, jobs of other people, "works at", "is from",
   "my <relation>'s name is X", sentences with two or three facts, lower-case names, a leading "remember that",
   and a leading greeting before a fact. One multi-fact sentence got a polite "one fact at a time" request instead.
3. **Taught facts are not recalled** (61 turns, 25 conversations). Mostly downstream of class 2, but about 10 are
   real recall failures: the user's own name when stored, relatives whose stored value carried "called",
   two-step chains where the first hop stored a full name and the second hop a short name, yes/no checks of a
   stored fact, and "who is <Name>?" reverse questions.
4. **Garbled "anyone called my <relation>" reply.** 14 replies in 13 conversations treat a possessive phrase as if
   it were a person's name. Ungrammatical, confusing, and it appears even when that relative was stored.
5. **Name-question hijack.** 14 replies in 10 conversations answer "you never told me your name" to anything
   mentioning a name or "called": the assistant's own name, who built it, a pet's or a parent's name, a gym, and even
   on teach turns. Twice it said this after the user's name had been stored, which is a false statement to the user.
6. **Questions about the assistant itself are not handled** (self intent: 2/18 correct). Its name, who built it,
   whether it is a person, how it learns, what it knows, whether it can remember, and how it compares to a general
   chatbot all failed; only the "what can you do / help with" wording worked, and that list uses internal jargon.
7. **Social turns misfire.** Greetings with an extra word, and thanks phrased as "cheers", "thanks anyway",
   "that's all", "thank you, dear", "nice one" got the fallback. "How's it going / what's up / how's your day" got an
   internal status line naming an all-caps mode. The standard greeting is a terse template instruction (natural 3),
   not a greeting. Plain "thanks" and "bye" work well.
8. **Out-of-scope requests are not politely declined.** Jokes, opinions, likes, advice, alarms and messages got the
   "not taught / didn't understand" fallback instead of "sorry, I can't do that". Weather/time/general-knowledge
   questions get the right substance but in the broken fallback.
9. **Corrections are ignored** (0/6). Every "actually / no wait / sorry, it's X not Y" turn got the fallback,
   and nothing changed in the notebook.
10. **"Favourites" misroute.** Any question or statement containing "favourite" or "colour" was answered as if asked
    about the assistant's own favourites, including when the user was teaching their own favourite.
11. **Robotic phrasing on the turns that work.** "Lives in" is echoed back as "<X>'s city is <Place>", "works at"
    as "employer", and the confirmation echoes typos and the leftover naming word.
12. **Other stray replies**: one question about who fills a role for the user got an unrelated answer about where
    facts come from, and one question asking whether it was guessing got an internal message about not handling negation.

## What it means

To a normal user, 138i mostly fails to understand ordinary chat. About half of all replies are the same broken
fallback, most everyday facts are not saved, and so most questions come back as "I don't know". The parts that do
work (simple "my X is Y" facts, "who is my X", plain thanks and bye) are correct and clean. The agent never invented
a fact or said a false yes.

## What it doesn't mean

This is one judge's hand grading of one run of 244 turns; a second judge may differ by a few points on the
natural scores. It does not measure the reasoner's accuracy on the formats it was built for. The failure
counts overlap (a missed write causes later misses), so the class counts are not independent problems.

## Where judgement was hard

- Whether the fallback is "correct" when the right answer truly was "I don't know" (I said yes, but ungrammatical).
- Whether to blame an unanswered question on recall (missed_known_fact) when the fact never got stored; I followed
  the brief's wording (user taught it -> missed_known_fact) and split out the ~10 true recall failures above.
- The template greeting: grammatical in casual register, correct, but natural 3.
- Replies that say "I don't know" correctly but wrongly claim the user never told their name, or treat a known
  relative as unknown: graded correct=no.

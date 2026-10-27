# 156c — wider small talk on loop138h (Muse)

Exp 156b taught the phone agent six no-write small-talk classes, and
loop138h carries them inside its 138f stack — so "Hi!", "Good
morning.", "Thanks!", "Bye!", "Hey you", "See you later." and "Good
night." already answer. The director's held-out probe still falls
through to "I didn't understand that": "Hello there.", "How are
you?", "Nice weather today." A person making ordinary chat keeps
being told they were not understood. This experiment adds exactly
one thing: wider small-talk classes for those everyday turns.

## The one change

New files only: `scripts/fable_fix156c_smalltalk.py`
(Smalltalk156cMixin + closed anchored phrase sets + normaliser +
guards, the whole change) and `scripts/fable_loop156c_agent.py`
(thin wrapper stacking the mixin outermost on loop138h, which is
imported read-only). Five classes, one fixed short reply each:

- trailing-word greetings ("Hello there", "Hey you", "Hiya" is base,
  "Hi friend", "Hello again") -> the 156b greeting reply verbatim;
- the how-are-you family ("How are you?", "How's it going?",
  "What's up?", "How are you doing today?", "How is your day
  going") -> "I'm just plain software, so I don't feel much, but
  I'm ready to help!";
- weather/idle chat ("Nice weather today.", "It's cold out.",
  "Lovely day", "What a beautiful day") -> "Sounds nice! I don't
  feel the weather - I'm just plain software.";
- first-person feelings about the user ("I'm tired.", "I'm happy
  today.", anchored `im + feeling-word + optional tail`) ->
  "Thanks for telling me. I'm just plain software with no
  feelings, but I'm here to help.";
- extra goodbyes ("See you soon", "Take care", "Talk soon", "Have a
  good day") -> "Bye!" verbatim.

The firing rule is 156b's: only when the notebook path returns
exactly the generic fallthrough AND the whole normalised message
matches one anchored phrase. Anything loop138h already answers —
156b classes, me/name/verb stages, the 168 feelings path — never
reaches the matcher, and overlapping inputs ("Hey you", "See you
later.", "Good night.") keep byte-identical replies by design.
Clarify acts never write (fable_agent_loop.py:337-339), so all 44
new turns write nothing; the how-are-you, weather and feelings
replies never claim the agent has feelings — it is plain software.

## Why anchored phrases, not a longer word list

156b's whole-message-must-be-vocabulary rule works for single words
but cannot hold a sentence: "How are you?" contains "are" and
"you", which must stay content words for the ask path. Anchored
full-message phrases solve this — the sentence matches only whole,
so "How are you, Tom?", "Nice weather, Tom.", "It is cold in
Oslo." and "How is Kim's city?" stay exactly as the base handles
them. Two extra guards close the remaining holes: a possessive
guard blocks every "'s" form except the contractions inside our own
phrases (how's/what's/it's) and "I'm", so "Kim's boss is Lee." and
"My sister is Ada." can never match; a question-word guard blocks
who/whose/whom/where/which/when/why, so questions about stored
facts can never match. "Happy is my dog." has no leading "im" and
stays on the base path, as do "I am hungry" and "I am from Lima"
(deliberately unlisted). Nothing is learned, so there is nothing
to drift.

## What it does not do

It does not remember greetings, learn names from chat, or answer
"who are you" (another experiment's router). "Are you happy?"
stays on the base path — only first-person "I'm …" statements are
chat. "Bye for now" stays a near-miss, keeping 156b's guards.

## Marks

S1 is a new 77-row panel (44 small talk, 5 classes; 33 near-misses
with teaches, questions, names and places): small-talk rows must
return the exact class reply with 0 writes (bar >= 90%), near-miss
rows must be byte-identical to loop138h in reply and stored
triples. S2 replays nothing old — the panel itself carries the
guards. S3 repeats the frozen guards with an empty exception list:
redteam136, redteam143, sessions152, bench (4 splits) and marks123
all per-case identical to the sealed 138h rows (marks123 modulo
predicted volatile metadata: sleep SKIP agent filename,
total_seconds timing, rt110 statuses-only log metadata).

# 156b — small-talk classes (Muse)

Exp 156 put a no-write small-talk stage on the phone agent: when the
notebook path did not understand a message and every word was in a
sealed 39-token list, it answered with a short fixed reply per class.
That passed its own panel, but everyday chat still fell through: "good
morning", "thanx", "thanks a lot", "goodnight", "gn", "see you",
"ttyl", "wow", bare emoji, "got it", "sorry" and "hmm" all got "I
didn't understand that." And laughing ("LOL") got "Got it!", which
sounds wrong.

## The one change

Replace the exact-word list with a small-talk classifier that is still
closed and rule-based: no learned weights, no panel tuning. Six
per-class lexicons written from general knowledge of English chat:

- greeting (old words + time-of-day: morning, afternoon, evening, good
  morning/afternoon/evening),
- thanks (old words + thanx/thnx + "so much"/"a lot" tails),
- laugh/reaction (lol, haha incl. longer runs, wow, nice, cool,
  emoji-only),
- ack (ok/okay/k/sure/got it/alright/okie + 156's yup/yep/yes/fine/
  great/awesome with the same reply),
- bye (old words + goodnight, gn, nite, later, ttyl, see you/ya),
- apology/hesitation (sorry, hmm, hm, um, uh, oops),

plus normalisation (lower-case, repeated-letter collapse, phrase
glueing, punctuation/emoji splitting). The firing rule is 156's: only
when the notebook path returns exactly the generic fallthrough AND the
whole message is small talk. Any content word ("Hi Tom", "Wow Records'
founder is Ann", "Sorry's singer is Justin Bieber") leaves the reply
untouched. Class replies stay short and fixed; laughter gets "Haha,
nice!" and apologies get "No worries!".

Two deliberate details. First, multi-word items are glued to phrase
tokens ("good morning", "see you", "got it", "a lot") so bare
good/see/got/it/a stay content words -- "good thanks" and "a lot of
people came" are still not small talk, exactly as in 156. Second, the
mixin wraps loop150 directly rather than loop156: 156's exact-word
stage would otherwise shadow the new classes (it already answers "lol"
with "Got it!"). Behaviourally this is still one change from 156.

## Why classes, not a longer list

A flat list cannot tell laughter from agreement, so one reply has to
cover both ("Got it!" for "LOL"). Classes keep replies natural while
staying fully auditable: every token is in a sealed set or matches the
(ha)+/(he)+ shape, and the priority order (thanks > bye > greeting >
apology > laugh > ack) resolves mixes like "cool thanks" or "k bye"
deterministically. Nothing is learned, so there is nothing to drift.

## What it does not do

It does not understand feelings, remember greetings, or handle "who are
you" (another experiment's router). Emoji mixed with content ("Rosa's
sister is Pia 🙂") still goes through the notebook path. Pure
punctuation (":)", "...") is not emoji and never fires.

## Marks

T1 is a new 116-message panel (84 small talk, 14 per class; 32
near-misses with content or names). T2 replays 156's sealed 68-case
panel: 59 rows identical, 8 laugh rows move to the laugh reply, and
"thanks a lot" moves from near-miss to thanks (all listed). G1/G2/G3
repeat 156's guards: bench and suite verdicts identical, sessions change
on exactly the same 23 turns (laugh turns now get the laugh reply).

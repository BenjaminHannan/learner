# 156 — Small talk without writes (Muse, exp 156)

## The problem in one paragraph

The exp-152 phone-session red team (artifacts/fable-session152-20260922/
RESULTS.md, class N1) found every greeting, thanks, laugh, ack and bye --
46 turns across the two targets ("hi", "lol", "thanks!", "ok cool",
"k bye", "heyyy", ...) -- gets the generic "I didn't understand that.
Could you say it another way?" A normal person saying hello and being
told they were not understood is stuck. The project allows fixed
small-talk replies as plain-software scaffolding, so this experiment
adds exactly one: a no-write small-talk stage.

## The code responsible (found before sealing, nothing edited)

- scripts/fable_loop90_agent.py:291 -- ChainEars.hear fallthrough:
  after every stage is tried and gated, an unmatched turn returns
  `[{"act": "clarify", "text": "I didn't understand that. Could you say
  it another way?"}]`. This is the "notebook path did not understand"
  signal the new stage keys on (exact string match).
- scripts/fable_agent_loop.py:148 -- the FakeEars template's identical
  fallthrough text at the bottom of the template chain.
- scripts/fable_agent_loop.py:337-339 -- AgentLoop._act handles
  `clarify` acts with no notebook write, which is why emitting a
  clarify reply guarantees 0 writes.

## THE ONE CHANGE

New files only: scripts/fable_fix156_smalltalk.py (Smalltalk156Mixin +
closed lists + normaliser, the whole change), scripts/
fable_loop156_agent.py (thin wrapper stacking the mixin outermost on
loop150, in the style of scripts/fable_loop140_agent.py and scripts/
fable_fix150_subjectguard.py), runners scripts/fable_fix156_probe.py /
fable_fix156_bench.py / fable_fix156_session.py, config artifacts/
fable-smalltalk156-20260922/loop156-config.json. loop150, loop139b and
every other file are imported read-only.

The mixin runs super().hear(turn) first, so the full loop150 chain (129
strip, 139b value screen, 150 subject guard) has already spoken. Only
when the base returns exactly the generic fallthrough is the message
tested: lower-cased, letter-runs collapsed ("hiii"->"hi",
"heyyy"->"hey", "thx!!"->"thx"), every non-alphanumeric (punctuation,
emoji) turned into a word split. If every token is in the closed
SMALLTALK_VOCAB (39 tokens after normalisation), one fixed short reply
per class is returned as a clarify act (never a write):

- greeting -> `Hi! Teach me like "Tom's boss is Ann." Ask me like "Who
  is Tom's boss?"` (one teach example, one ask example)
- thanks -> `You're welcome!`
- laugh/ack -> `Got it!`
- bye -> `Bye!`

Class priority thanks > bye > greeting > ack, so "cool thanks" is
thanks, "k bye" is bye, "ok cool" is ack. Empty and emoji-only input
has zero tokens and is never small talk.

## What is NOT small talk (unchanged by construction)

- Small talk mixed with content ("hi, Tom's boss is Bob", "ok so who
  is Tom's boss?"): content words are outside the closed list, so the
  all-words test fails and the base reply returns untouched. A separate
  experiment handles fillers.
- "who are you" / "what can you do" (and "heyy, what can you do?"):
  who/are/what/can/do are not in the list; they stay on the
  fallthrough for the exp-127 self router.
- Bare corrections ("no wait, it's Denver"), filler teaches ("btw
  marta's brother is kai"), name traps ("Kip", "Hi-Fi Records' founder
  is Ann"): "no"/"wait"/"btw"/names are not in the list.
- Anything the notebook path understood (teaches, asks, hearsay/SPLIT
  clarifies, "I wasn't waiting for an answer."): condition (a) fails,
  base actions return untouched.

## Sealed lists (exact; matched post-normalisation; reason per group)

Greeting (never a name/relation/question word): hi, hey, hello, yo,
hiya, howdy. Thanks: thanks, thank, thx, ty. Bye: bye, byebye,
goodbye, cya, night. Laugh/ack: lol, lmao, haha, hahaha, ha, hehe,
ok, okay, k, cool, nice, great, awesome, yup, yep, yes, fine, sure,
alright. Glue (only rides along inside thanks): you, very, much, so,
helpful. Deliberately excluded: no, wait, who, what, where, is, are,
can, do, you-are contexts, btw, also, oh, actually, my, and every
name and relation word.

## Evidence before sealing (dev only; the new loop never ran)

- Pure-function scan: 44/44 probe small-talk rows hit the right class;
  24/24 near-misses miss; 0 fires on 4,375 bench strings (600 teaches
  + questions), 174 redteam110 sends, 145 redteam136 cases, 57 cases150
  rows, 202 redteam98 sends except one bare "yes".
- That bare "yes" (redteam98, rt81 x2) is harmless: loop150 answers it
  with "I wasn't waiting for an answer." (answer path, verified on the
  base), not the fallthrough, so the stage cannot fire there.
- Base calibration: loop150 replays all 6 exp-152 sessions
  reply-identical and write-identical to the sealed T-T run (180/180),
  so G3's only predicted moves are the 23 small-talk turns.

## Marks (see PASSMARKS.md, sealed)

T1: 68-case probe (44 class replies with 0 writes; 24 near-misses
byte-identical to loop150). T2/G3: 152 sessions, only the 23 sealed
small-talk turns change. G1: bench per-item identical to loop150 rows,
0 moves. G2: marks123 per-case identical to marks150, 0 moves. G4:
every run < 1500 s Mac CPU; daemons take idle_seconds.

## What it means / does not mean

It means hello stops being a dead end while the notebook stays
untouched by chatter. It does not mean the assistant understands
feelings, remembers greetings, or answers identity questions -- those
are other experiments' jobs.

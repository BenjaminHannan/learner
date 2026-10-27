# ch-403 diagnosis: why everyday chat tied the plain 1B (0.2c row C1, 30 - 30)

Everyday-chat thread, 2026-09-26 ~13:50 UTC. Free, CPU only. Counts only for the TEST side: chatpanel02c's text, the
judges' reasons and the 0.2c replies were never printed or read; scripts classified them and printed counts.
Inputs: origin/builder-outbox artifacts/claude-e2e02c-20260926/run/chat_{X,T}.jsonl, score/chat_key_T.json;
origin/main artifacts/claude-e2e02c-20260926/judges/out/pair_b{1..4}.jsonl. Plain-language page for Ben:
https://claude.ai/artifact/2Xo7spiAFkWBph2dDYLxfK

## 1. Stock non-answers on turns that saved nothing (shown)
Each of X's 335 chat replies was matched by script against the fixed lines in the code.

| Stock line (code) | Turns | Kinds | Conversations |
|---|---|---|---|
| think299b vote split: "I'm not sure. I worked it out a few times and got different answers." | 18 | think 17 (of 33), followup 1 | 17 |
| 137c pretend rule: "OK, I'll treat that as pretend, so I won't save it." | 10 | followup 10 | 10 |
| 338b people guard, HONEST338B and its 7 vary330c rewordings | 18 | explain 8, followup 7, advice 3 | 14 |
| total on everyday turns | 46 | | 32 of 60 |

Every one of the 46 had 0 notebook events (none saved anything). Not counted: 4 honest lines on ask_known turns and
6 on ask_unknown turns (memory rows, not everyday chat).

## 2. Who won (blind pair judges, keys applied by script)
| Conversations | X won | T won |
|---|---|---|
| no stock line (28) | 18 | 10 |
| one or more stock lines (32) | 12 | 20 |
| all 60 | 30 | 30 |

In 19 of the 20 conversations T won where a stock line appeared, the judge's one-line reason contains a failure
word (fail, ignore, miss, non-answer, deflect, evade, refuse, off-topic, irrelevant, confuse, odd, nonsense,
incoherent, pretend, decline). Helpfulness words (help, useful, practical, specific, concrete, advice, suggest,
idea) appear in 16 of T's 30 winning reasons and 4 of X's 30.

Median words per reply, X vs T: advice 53 vs 118, explain 46 vs 120, followup 40 vs 116, feelings 48 vs 69,
think 14 vs 88, smalltalk 15 vs 16.

## 3. Mechanisms (checked in the code)
- **Think split** (scripts/claude_think299b_agent.py): 5 sampled calculator runs, an answer needs 3 of 5 votes,
  else the fixed line. Owner: month-end (problem "refuses too much", route 383, which hands abstains on questions not
  about the user to the 1B). Not touched by ch-403.
- **Pretend line** (scripts/fable_fix137c_hypo.py): a turn that opens with suppose / imagine / pretend / let's say /
  hypothetically / in theory / what if / say that stores nothing and replies HYPO_REPLY. 338 hands a turn to the 1B
  only on a clarify marker, a canned line or a topic miss (claude_chat338_agent.gave_up/topic_miss), so HYPO_REPLY
  goes out. A follow-up like "what if that doesn't work?" (the spec's own example, 338-chat-panel-spec.md) is an
  ordinary question.
- **People guard** (scripts/claude_chat338b_agent.py): when the wrapped turn gave up, any question with my/mine/our,
  he/she/him/her, a relation word (the list includes cat, dog, kid, friend), or "<word>'s", and no advice word, gets
  HONEST338B instead of the 1B. It was added after 338's DEV run, where the 1B guessed at 5 memory questions.

## 4. DEV practice chats (readable; artifacts/claude-chatdev-20260926, 60 conversations, 336 turns, written by three
separate writers from the 382 spec, names A-M, checker OK)
338b's people_question vs ch-403's recall403, per kind (notebook names as the loop would hold them):

| kind | turns | 338b fires | recall403 fires |
|---|---|---|---|
| smalltalk | 51 | 0 | 0 |
| advice | 78 | 6 | 0 |
| explain | 64 | 12 | 1 |
| followup | 49 | 5 | 0 |
| feelings | 32 | 0 | 0 |
| think | 33 | 8 | 0 |
| teach | 15 | 0 | 0 |
| ask_known | 8 | 7 | 8 |
| ask_unknown | 6 | 6 | 6 |

DEV memory bank (artifacts/claude-e2e331-dev-20260924, 71 memory asks): 338b fires on 70, recall403 on 70 (both
miss "how old is nan turning?"). recall403 was written while looking at these DEV sets, so the TEST panel is the
only fair check of it. The pretend rule fires on 2 DEV follow-ups (the DEV writers used "what if" less often).

## 5. What this does and doesn't say
- Shown: 46 stock lines on turns that saved nothing; where each comes from in the code; the 18-10 and 12-20 splits.
- Suggested, not tested: the stock lines caused most of X's losses (a pattern across conversations, not an
  experiment). Shorter, less detailed replies may cost some wins.
- Untested: removing every stock line reaches 40 of 60. At the no-stock-line rate (18 of 28 = 64%) it would be about
  39 of 60, so removing stock lines is probably needed but may not be enough on its own.

## 6. Split of the work (proposed to month-end by message, 2026-09-26 ~13:50 UTC)
- think split: month-end's route 383.
- pretend line and people-guard diverts on turns that saved nothing: this thread, ch-403 (one change, one test).
- replies too short or generic: a later, separate change if ch-403 is not enough.

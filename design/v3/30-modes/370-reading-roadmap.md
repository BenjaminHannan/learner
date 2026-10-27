# Reading facts from chat: road map (thread "Fix: reading facts from chat", 2026-09-25 02:25 UTC)

Ben, 00:31 UTC: fix reading facts from chat. 02:18 UTC: get as much done tonight as possible, with a road map.
Numbers for this line: lis-318 and lis-319 (end of the lis block), then rd-370 to rd-379.

## Where we are (shown)
- 336 end-to-end: 57% of taught facts saved, 22% of answerable asks right, 33 wrong saves after confirm "yes".
- lis-317 (DEV, 131 chat facts): the reader finds 89 before its safety gate. The gate (min token prob >= 0.995)
  keeps 20. The reader invents some facts on chatty turns, so the gate is doing real work.
- The hand-written save rules cap DEV at 103/131 even for a perfect reader: a closed list of 153 relation words,
  values copied word for word, and a reader that sees only the assistant's last reply (not earlier turns).
- A gate that samples the reader 8 times fails: the reader repeats its mistakes as confidently as its right reads.
- Asks: even when every needed fact was saved, the DEV run answered right 3 of 15.

## Steps, one change each, each with marks fixed before it runs
| # | Change | Why | Judged on | Pass mark (headline) |
|---|---|---|---|---|
| lis-318 (tonight, BensPC) | retrain the reader with ~2,500 chatty turns (Opus-written, blind-checked) | it misreads chat | sealed readpanel318 (240 turns) | reads >= 85% of facts before the gate, saves >= 40 more, <= 2 wrong turns |
| lis-319 | the reader sees the recent conversation (last ~6 turns), not just the last reply | "she's 84" points back to someone named earlier; sleep's night re-read needs the whole day | a fresh blind dialog panel | owner right on back-reference facts, no new wrong saves |
| lis-319b (after lis-319) | the save checker (claude_lis300_compiler) accepts an owner named in the earlier turns the reader saw, not just this turn or the last reply | with the plain checker, 0 of 223 agreed back-reference facts in the h1 training set would save (found 03:10 UTC 09-25) | the lis-319 panel, saves not reads | back-reference facts saved >= 60%; wrong turns <= 2 |
| rd-370 | open relations: keep the reader's own relation words; match questions to facts by meaning | 15/131 DEV facts have no word on the 153 list (species, breed, studies...) | DEV then a fresh panel | ceiling on DEV >= 120/131 |
| rd-371 | a learned "am I right?" checker trained on the reader's own mistakes, replacing the 0.995 gate | the gate throws away most right reads | held-out chat, then the panel | keeps >= 80% of right reads with <= 1% wrong saves |
| rd-372 | question side: the same reader parses the ask; answers matched by meaning | 3/15 right even with every fact saved | DEV asks, then a fresh panel | answerable asks right >= 70% when the facts are saved |
| rd-373 | confirm questions only for clean facts, in one fixed wording; a "yes" never saves a garbled fact | 33 wrong saves came right after "yes" | end-to-end DEV | 0 wrong saves after a confirm |
| rd-374 | end-to-end test on a fresh bank (the month-end thread's 336b style), then LoCoMo via the Benchmarks thread | the real goal | fresh sealed bank; LoCoMo | the 336 marks M1, M3, M4 |
| rd-375 (asked by Benchmarks, 03:00 UTC 09-25) | dates on saved facts: the reader marks when a fact became true ("last May", "yesterday") and the notebook keeps the turn's date plus that time | a FACT event has no time field (fable_notebook_contract.py:329-333 and _append:167 add only n/prev/v), so "when did..." questions can't be answered | its own fresh blind bank of dated chats (never LoCoMo or LongMemEval text) | time asks right >= 60% when the fact is saved; no change to other answers |
| rd-376 (asked by Benchmarks, 03:00 UTC 09-25) | updates without the word "correction": the reader tags a new value that replaces an old one ("I moved to X") so the notebook supersedes it | a taught new value for a one-value relation returns CONFLICT unless correction=True (fable_notebook_contract.py:335-341) | its own fresh blind bank of change-over-time chats | latest value right >= 80%; 0 old values lost on non-updates |
| rd-377 (from bm-390, 17:45 UTC 09-25) | overheard chat: read a conversation between two other people (speaker A about B, events, plans, dates), save as heard-not-taught facts with the speaker as source, no confirm question | on 10 LoCoMo chats 0.1 saved 18 facts from 5,882 turns and asked 2,334 unanswered "am I sure?" questions (artifacts/claude-bm390-20260925/VERIFY-bm390.md) | its own fresh blind bank of two-person chats written from scratch (never LoCoMo or LongMemEval text) | facts from the bank read >= 70%; wrong <= 2%; 0 confirm questions |

rd-375 and rd-376 change the notebook contract as well as the reader: check the Notebook line's history first, keep the change additive (new optional fields, old logs still load), one change per run.

## Direction change (Ben, 19:22 UTC 09-25): relation facts are ~1% of the work
The reader stays as a foundation, but this line stops growing the relation table. From now on:
- M1 memory notes (replaces rd-370 and rd-372): the reader writes short plain-sentence notes of anything worth remembering from
  a conversation (events, plans, opinions, feelings, preferences, what was discussed, who said it, when), not owner/relation/value.
  Questions are answered by finding notes by meaning. This is the same thing as the raw-turn episodic memory Benchmarks proposed
  for 0.2 (owned by Month-end): one shared design, not two.
- rd-371 (the verifier, queued) is general: "does this source support this statement?" works for any note, for sleep's
  self-check of what a night learned, and for any thread's checker. It stays.
- lis-319 (reading with earlier chat) stays: notes and sleep's night re-read both need the conversation, not one turn.
- rd-373 (confirm guard), rd-375 (dates) and rd-377 (overheard chat) fold into M1: every note carries its time and speaker, and
  overheard speech is saved as heard, with no confirm questions. rd-376 (silent updates) becomes "newer note wins".
- Overlaps worked directly with: Fix sleep (night re-read + verifier as self-check), Benchmarks (LoCoMo recall), Month-end (0.2
  episodic memory), Sleep research (wins checker).

Rules for all of them: DEV data only for building; blind panels sealed before a run and never trained or tuned on;
no LoCoMo or LongMemEval text (or anything built from them) in any training data; the notebook saves taught facts only;
registered FAILs stay FAIL, and each FAIL gets one diagnosis-driven follow-up.

## What does not move
Ben's standing rules: learned parts over hand rules, never guess, "I don't know" when unsure, one change per experiment.
The sleep thread's night re-read (job A) will call this reader offline with the whole day's chat; lis-319 is built for that.

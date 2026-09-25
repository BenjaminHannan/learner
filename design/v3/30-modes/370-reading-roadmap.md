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
| rd-370 | open relations: keep the reader's own relation words; match questions to facts by meaning | 15/131 DEV facts have no word on the 153 list (species, breed, studies...) | DEV then a fresh panel | ceiling on DEV >= 120/131 |
| rd-371 | a learned "am I right?" checker trained on the reader's own mistakes, replacing the 0.995 gate | the gate throws away most right reads | held-out chat, then the panel | keeps >= 80% of right reads with <= 1% wrong saves |
| rd-372 | question side: the same reader parses the ask; answers matched by meaning | 3/15 right even with every fact saved | DEV asks, then a fresh panel | answerable asks right >= 70% when the facts are saved |
| rd-373 | confirm questions only for clean facts, in one fixed wording; a "yes" never saves a garbled fact | 33 wrong saves came right after "yes" | end-to-end DEV | 0 wrong saves after a confirm |
| rd-374 | end-to-end test on a fresh bank (the month-end thread's 336b style), then LoCoMo via the Benchmarks thread | the real goal | fresh sealed bank; LoCoMo | the 336 marks M1, M3, M4 |

Rules for all of them: DEV data only for building; blind panels sealed before a run and never trained or tuned on;
no LoCoMo or LongMemEval text (or anything built from them) in any training data; the notebook saves taught facts only;
registered FAILs stay FAIL, and each FAIL gets one diagnosis-driven follow-up.

## What does not move
Ben's standing rules: learned parts over hand rules, never guess, "I don't know" when unsure, one change per experiment.
The sleep thread's night re-read (job A) will call this reader offline with the whole day's chat; lis-319 is built for that.

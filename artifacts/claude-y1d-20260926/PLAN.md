# y1d: where are memory answers lost? (Answering-from-memory thread, 2026-09-26 ~14:00 UTC)

Owner: the "Answering from memory" thread (row Y1 of 0.2c: answerable memory asks right, X 45 vs G 44 of 195;
registered FAIL, stays a FAIL). This is a DIAGNOSIS on DEV data, not a registered change. Decision rules are fixed
below before the GPU run; the one change they point to gets its own sealed marks afterwards.

## Part 1 (done, free, CPU): notebook arms on the DEV bank
Script: scripts/claude_y1d_savesplit.py over existing DEV runs (origin/builder-outbox). 56 answerable asks
(gold type value/yes/no). "Saved" = the 336 scorer's rule (same owner and value in stored_triples at the ask row).

| arm (DEV) | right (of 56) | asks with no cited fact saved | some saved | all saved | all saved but lost |
|---|---:|---:|---:|---:|---:|
| G (e2e330 dev arm_G, lis-301 stack) | 5 | 39 | 7 | 10 | 8 |
| X02c (0.2c dev, lis-319 code with lis-301 weights: same D1 error as bank D) | 5 | 30 | 13 | 13 | 11 |
| lisC (lis e2e dev) | 0 | 27 | 16 | 13 | 13 |

Losses on the question side when every fact was saved (G, read on DEV): the question itself is read as a failed teach
("I didn't understand that well enough to save it"), relation names differ (boss vs manager, partner vs fiance,
occupation vs job), reversal asks are not inverted, and a two-hop ask stops after one hop ("Your father is Vaughn.").
X02c also answers 17 of 56 answerable asks with a confirm question ("Just to check ..." / "I think you told me ...")
that does not name the answer.

Bank D (TEST-ONLY, counts only from origin/builder-outbox score/mechanical.json), answerable 195:
X right 45, abstain 84, confirm-other 50, wrong-candidate 16; G right 44, abstain 98, confirm-other 36, wrong 17.
ep-382's answer step (382b) only runs on an abstaining reply with no confirm open, so it can reach at most X's 84.
T (plain twin, whole chat as a conversation) is degenerate on bank D (312 distinct replies of 658, one reply 41
times) and on DEV (twin b answers "Hello! ... How can I assist you today?" to every ask), so T's 15 of 195 does not
measure the 1B's reading.

Shown: on DEV the notebook route loses answers both at the save (39 of 56 asks for G) and at the question
(8 of the 10 fully saved asks for G). Untested: how well the 1B answers from the user's own words.

## Part 2 (GPU, rental): the 1B reading raw turns (scripts/claude_y1d_readchat.py)
ep-382's exact answer step (SYSTEM382, rows block, 4 samples at T 0.7 / top-p 0.9, 338 strict guard + G5,
abstaining samples skipped, else "I don't know.") on every DEV ask (71), fed three row sets:
gold (only the turns that taught the cited facts), all (every earlier user turn, in order), k20 (store v2 recall
top 20 = what 382b's E arm sees). Plus one greedy answer per ask and condition with no guard. Scored by the 336
scorer's score_ask. Seed 4021. No reader weights, no notebook.

Let A_c = answerable right (of 56) with ep-382's step for condition c; G_nb = 5 (notebook G on DEV).

## Decision rules (fixed before the run)
- D1 reading: A_gold >= 28 -> the 1B can read these answers from the right turns. A_gold < 20 -> the 1B's reading
  is the bottleneck; the next change is reading (row format or trained reading on its own graded drafts), not routing.
- D2 finding: F = A_gold - A_all. F <= 5 -> finding costs little on bank-sized lives. F >= 10 -> finding is a loss
  even on short lives; the next change is what goes into the rows.
- D3 382b's input: A_k20 >= A_all - 3 -> the store's ranking costs nothing here.
- D4 guard cost (report): asks right greedy but not right with the guarded step, per condition.
- D5 honesty: never_told asks answered "don't know" under all and k20 (of 10), and answerable wrong-candidates.
- Routing: if A_all >= 25 and never_told under all >= 8 of 10, the next single change is the trigger: memory
  questions the notebook does not answer directly (an abstain OR a confirm question) go to ep-382's step over the
  heard turns. Marks for that change are written and sealed before its own run.

## Proved wrong
"Reading the user's own words beats the notebook on DEV" is wrong if A_all <= 10 (twice the notebook's 5 or less).

## Plain summary for Ben
The assistant keeps a notebook of facts. On practice chats it answered only 5 of 56 memory questions. Two things go
wrong: most facts never make it into the notebook, and even when a fact is there, the question often isn't
understood. This test asks a simpler thing: if the small model just reads what you actually said, can it answer?
We try it with only the right lines, with the whole chat, and with the 20 lines the memory search picks.

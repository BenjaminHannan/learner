# Domain mode: "learn how to do spreadsheets" (design and sealed marks, Fri Oct 9, 2026, 11:40 AM ET)

Asked by Ben, 10:57 AM ET 10-09: "Also add a mode where I can have it learn a bunch of skills in a domain", and 10:58 AM ET:
"Like if I said learn how to do spreadsheets". Funding bar, Ben 10:57 AM ET: "once you demonstrate all those [principles] as true,
I'll fund a larger training run or something. Keep demonstrating those principles in the model and iterating until they're found as the goal."
Thread "Domain-learning mode", run as ultracode (Opus plans and judges; every helper is Haiku 5.5).
Labels: **shown** = measured or read in code; **suggested** = reasoned; **untested** = never run. Times ET.

## 1. In one paragraph

Ben types one line, "learn how to do spreadsheets". The model opens the tool for that domain (a spreadsheet), reads its help page,
and then teaches itself: it makes its own practice problems by changing the help page's examples, asks the tool for the right answer
to each, tries each one itself, keeps what it got right, sleeps on it, checks that it has not forgotten its old skills, chooses what to
practise next by where it is improving fastest, and stops when its own quiz stops improving. Nobody picks data, settings or the
finish line while it runs. The tool is plain code (allowed: an outside tool the model calls, like its calculator). The only thing a
person gives is the sentence.

## 2. The seven steps (the finished model), who does each, and what exists today

| Step | What the model does | Done by | Exists today |
|---|---|---|---|
| 1. Open | Picks the tool that fits the sentence from its tool shelf and reads its help page (one worked example per function). Later also searches its own text library (FineWeb-Edu has spreadsheet tutorials) for more examples | model (tool choice); help page and library search are tools | **not built**: today's model has one tool (the calculator) and cannot read a sentence like this. Small test: the tool and its help page are handed over (sec. 5) |
| 2. Make practice | Writes new problems by changing the examples (new numbers, new cells), asks the tool for each answer, throws away any the tool cannot run | model; the tool checks | **not built** (closest: research-loop replay draws new inputs, `creative/rl/replay.py`, PR #48) |
| 3. Try | Answers each problem its own way (thinking + calculator) without the tool's answer, then checks against it. Right tries are kept as its own worked steps (ST1). For a miss it asks the tool to show its working, the way a spreadsheet's "evaluate formula" button does, and keeps that | model; tool shows working | **partly**: own-tries-checked exists for number rules (research loop, 71.3% first try, shown); never on a tool's working |
| 4. Choose | Keeps a score per kind of problem (grouped by which help example it came from). Next day's practice goes mostly to the kinds where its score moved most in the last 2 days (up or down), a tenth spread evenly, mastered kinds (>= 95%) only the even share | model's own scores + fixed rule | **never ran** (`sleep_sc`, `night7d.py:488`, held; an older batch-picker failed, `artifacts/claude-slp358lp-20260926`) |
| 5. Sleep | Trains at night on the day's kept tries (gentle rate 1e-4, every row new, the fast-sleep lessons) mixed half-and-half with replay of its own old questions answered by its pre-mode self | model; fixed constants | **partly**: lr 1e-4 nights keep skills (VL pass); fresh rows stop overfit (2x2); self-replay never tried here |
| 6. Check | Before and after each night answers the same 512 old questions; if it now disagrees with its pre-mode self on more than 3 points more of them, it undoes the night and halves the next one | model; fixed constants | **not built** (no paper found that tests an undo gate either) |
| 7. Stop | Keeps 256 of its own day-1 problems aside as its own quiz (never trained on). Stops when the quiz rises less than 1 point over 2 nights, or every kind is mastered, or after 12 nights. Then says what it learned (kinds and quiz scores) | model's own quiz + fixed rule | **not built** (H1 is the same idea for one question; built, never run) |

**Autonomy level.** Level 1 (this design): every choice comes from the model's own scores, through fixed rules written here and
the same for every domain, never tuned on a test (Ben's 10-07 deploy rule, as the project applies it: fixed design constants are
allowed). Disclosed: in the small test the loop calls the spreadsheet tool at fixed points on the model's behalf, because
today's model can only write calculator calls; the model choosing when to call a new tool needs sec. 4 item 1. Level 2 (later, its own mark): the model learns those choices itself, with a small head that predicts its own progress
(like MAGELLAN, 2025) and a learned stop (like H1).

## 3. Worked example: spreadsheets

Help page (10 kinds, one example each; the small test's version). Column-major text grid, row numbers implied by position:
`A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)` -> `13`.
Kinds: SUM, MAX, MIN, PRODUCT, cell arithmetic (`=A1+B2*2`), division (`=A1/B1`, exact or QUOTIENT per the calculator's
own division), MOD, ABS(A1-B1), COUNTIF(range, ">k"), IF(A1>B1, A2, B2).
The tool's working for `=SUM(A1:A3)` is `add 4 7 = 11 ; add 11 2 = 13`, the same call text the calculator already uses, so a
worked step the model keeps is a row in its normal training format.
At the test the spreadsheet tool is taken away and only the calculator is left, so the only way to pass is to have learned what
formulas mean.

## 4. What the finished model needs for the full version (from one sentence, real spreadsheets)

1. **Calls written fully as text, including the operation's name.** Today the operation is picked from a fixed list of 8 by an
   op head (`tool.py:7-8`, shown); a new tool's operations cannot be expressed. B3 group 2 (learned writing) should make the
   whole call letters. Needed for step 1 with a real tool; not needed for the small test.
2. Reading the sentence and choosing a tool (English reading through Gemma; tool choice learned).
3. Library search as a tool, and long reading (Ben's 2,000-letter answer, 10-09; carry-over for longer docs).
4. Writing formulas for word tasks ("total the East sales"): the open-English talker (Ben's separate session).
5. Level 2 choices (learned progress head, learned stop).
None of these block the small test below.

## 5. The small test (DM-S): spreadsheets on today's checked 3M model

- **Parent:** T1SDR 3M (calculator outside, confirmed over 6 seeds, Ben cleared 8:21 AM ET 10-09), seeds 200 and 201,
  checkpoints `/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s20{0,1}/` (shown). Kill-first: seed 200 first, seed 201 only
  if seed 200 is not proved wrong. Later the same test runs on B3 3M (when built) and the 30M rung (before the Oct 31 readout).
- **Machine:** the free cloud computer (CPU). No PC, no Mac, no money.
- **Given to the model:** the spreadsheet tool (plain code) and its help page (10 examples). Nothing else from us.
- **Fixed constants** (file `domain/constants.json`, hashed; identical for every domain): 1,024 made problems a day; the quiz is
  256 day-1 problems kept aside; explore share 0.10; mastered 0.95; progress window 2 days; night lr 1e-4, batch 64, each new
  row seen 16 times, half of every batch self-replay from a 4,096-question diary of its old training questions answered by its
  pre-mode self; forgetting check on 512 other diary questions, undo if agreement with the pre-mode self drops more than 3 points,
  next night half as many visits; stop when the quiz rises < 1 point over 2 nights, or all kinds >= 0.95, or 12 nights.
  Chosen once from the fast-sleep lessons and two papers (Self-Challenging: 200 self-made tasks hurt, 800 helped), before any
  spreadsheet result; never changed per domain.
- **Practice maker (the model's):** replace every digit run in a help example with a random digit run of the same length, ask the
  tool, keep it if the tool can run it and it fits the model's caps (prompt <= 208 letters, <= 16 numbers, answer <= 8 letters,
  <= 7 calls). It keeps the example's grid shape, so longer ranges and mixed formulas are never practised (the far split tests them).
- **Sealed panel (ours, for scoring only; the model never sees it):** 1,000 questions = 10 kinds x (60 near + 40 far), from a
  separate generator with its own seed, written and hashed before the run. Near = the help example's shape with new numbers and
  cells. Far = longer ranges (5-6 cells, near uses 2-4), the other column, and two kinds in one formula, all within 7 calls.
  Zero rows over any cap (no cut answers, Ben's rule).
- **Old skills panel:** the skills DEV in_dist file (34 families), scored with `harm_measure` (`creative/harm_look.py:22-40`, PR #48):
  fails if in_dist drops more than 1.5 or any family drops more than 5 with its 95% interval below 0.
- **Arms:** Before (the parent) and After (the parent after the mode). One change: the mode. The panel is also scored on every
  night's saved copy, for mark DM5 only.

### Marks (sealed with this file; change only by a dated addendum)

| Mark | Pass | Proved wrong |
|---|---|---|
| DM1 learns the domain | near split, After minus Before >= +30 points on each seed | < +10 on seed 200 (seed 201 not run) |
| DM2 goes past its practice | far split, After minus Before >= +10 on each seed | <= +2 on both seeds |
| DM3 keeps old skills | harm measure passes on each seed | in_dist drop > 5 on either seed |
| DM4 runs itself | audit: every training row traces to a made problem + the tool's reply + the model's own try or the tool's working; no row from our panels; constants file hash identical across domains; no person step in the log | any row from our panel, or any per-domain setting |
| DM5 knows when it is done | at its stop night, near score >= the best night's near score minus 3, and the near score is not rising more than 3 points a night | stops while rising > 5 a night, or runs >= 4 nights past its best with DM3 failing |
| DM6 second domain, same constants | RPN calculator notation (`3 4 + 2 *`), its own tool and sealed panel, constants file unchanged: DM1 and DM3 bars | as DM1 and DM3 |

Ben's hair-miss rule applies to this screen (a one-question miss counts as met). DM6 runs only after DM1-DM5 read.
Reported, not gated: which kinds it learned and which it gave up on (IF is the hardest, 5 calls); the self-check undo count.
A later single change (its own test): choosing vs no choosing (even practice mix, same nights), to show the choosing helps.

## 6. Ladder (how this joins the finished model)

1. DM-S on T1SDR 3M, cloud CPU, now (build Fri-Sat, run about a day per seed, untested speed; measured by the smoke run).
2. DM-S again on B3 3M when it exists (big-run plan 10-12 to 10-19), and on the 30M rung, so the Oct 31 readout can say
   "learned spreadsheets by itself" for the model we would ship.
3. Level 2 choices (learned), its own marks.
4. The full version from a sentence (sec. 4), after the English talker works.

## 7. Risks (from the papers, sec. 9)

- Cold start: STaR says a model with no right tries cannot bootstrap. Answer here: the tool shows its working on misses.
- Collapse on own outputs (Shumailov 2024): only tool-checked tries enter training.
- Forgetting: lr 1e-4, fresh rows, self-replay (SSR 2024, LwF 2016), undo gate. The undo gate and the stop rule have no
  precedent we found; they are the new, untested part.
- Too few problems (Self-Challenging 2025: 200 hurt, 800 helped): 1,024 a day.

## 8. Scorecard and queue (sent to the big-run thread through the coordinator)

- Scorecard: new row 9, "Learns a new domain by itself" (Ben 10:57-10:58 AM ET 10-09), marks DM1-DM6; it also feeds row 5
  (practice choice and when to stop) and row 1b (learns from one example per kind).
- Queue: cloud CPU only, now; no PC or Mac time. Later: one DM-S run on B3 3M and one on the 30M rung (CPU or a Mac gap).
- B3 build note: write the whole tool call as letters, including the operation name (sec. 4 item 1), in group 2.

## 9. Papers used (Haiku sweep 10-09; links in `/mnt/project-files/papers/domain-mode-papers.md`)

Absolute Zero (2025), Self-Challenging Agents (2025), Haluptzok et al. 2022, Kanitscheider et al. 2021 (Minecraft, learning
progress), Matiisen et al. 2017 (teacher-student curricula), MAGELLAN (2025), Voyager (2023), STaR (2022), Mind the Gap (2024),
Self-Evolving Curriculum (2025), ExIt (2025), Hsieh et al. 2023 (tool docs), Toolformer (2023), Gulwani 2011 (FlashFill),
SpreadsheetCoder (2021), FLAME (2024), SpreadsheetBench (2024), Self-Instruct (2023), Shumailov et al. 2024, SSR (2024),
LwF (2016), Lee et al. 2025 (self-improving transformers).

## Addenda (dated 2026-10-09, after the code review; the sealed text above changes only by these)

Status at the end of the review fixes: code, tests and the audit changed under domain/. **The shared RPN panel file is not replaced yet** (`/mnt/project-files/domain-mode/panel/rpn.jsonl`, sha256 140be650...): the write was refused in this session and needs Ben's approval. The candidate panel is built and checked outside the shared folder (below). No run has been made for any mark. Labels: **shown** = measured here, **suggested** = reasoned, **untested** = not run.

**A1. Sealed RPN panel overlaps practice (leak, DM4). Shown.** 12 days of the practice maker (1,024 a day, one shared context, as in `mode.main`) produced 41 prompts equal to rows of the sealed RPN panel: 35 `a b /`, 5 `a b %`, 1 `a b -`. Cause: practice keeps each help example's digit-run lengths, and the near rows drew 1-99 with no length rule, so they overlapped. Change: RPN near rows are redrawn until their digit-run lengths differ from the help example's (`domain/panel.py`, `rpn_draw`; main asserts it). The sheet panel is unchanged (sha256 b9574ab1..., the same bytes). Candidate RPN panel: sha256 `309890ce3809ed77a0c6af37ab9aa9c23fb76778ce7bbaf7f0ba260a3f93759f`, built in the scratchpad. Check: 0 overlaps with the same 12 days of practice (shown); the simulated training set (11,478 rows, tool path) audited against the old panel gives 36 overlaps and against the candidate 0 (shown, `domain/audit.py`). Install is pending approval; until then DM4 fails on the shared panel.

**A2. Deviation: no row form for `mod` and `cmp` (bug, DM1/DM6 scope). Shown.** progparse has no text form for `mod`. For `cmp`, `compare x y` becomes MIN or MAX when the answer is a digit (`custom_io/models/progparse.py:143-149`), so a 0/1 result has no faithful text form, and row_gold returns no program for it. `make_row` therefore refuses every call with op `mod` or `cmp` (`no_row_form_*`). Kinds affected: MOD (all rows), COUNTIF and IF (`cmp`), and `a b %` (`mod`). They get no trained rows in any run until progparse has a form for them (a change in `custom_io/`, outside `domain/`). Change: a `choice:` marker (`NO_ROW_FORM` in `mode.py`) and a `deviation` event (id A2) at the start of every run. **Suggested, for Ben and Opus before DM1 is read:** withdraw the DM1 and DM6 kind claims for MOD, COUNTIF, IF and `a b %`, or say in writing how the marks are scored without them.

**A3. Far split for COUNTIF and IF (spec mismatch). Shown.** Sec. 5 says far rows use 5-6 cell ranges. The sealed far rows use 2 cells for COUNTIF (40 of 40 rows) and no range longer than 2 cells for IF (34 with 2, 6 with none). Reason: COUNTIF costs 3n-1 steps (5 at 2 cells, 8 at 3) and the cap is 7 calls, so 5-6 cells cannot be asked (`panel.py:14-16`). Far SUM, MAX, MIN and PRODUCT keep 5-6 cells in every row (shown). So **far COUNTIF tests two cells only**; this is written here before DM2 is read. The sealed panel is not changed.

**A4. Undo gate, per night (spec mismatch). Shown in code and in a run.** Design step 6 reads "before and after each night ... disagrees ... on more than 3 points more of them". The code measured agreement once, after the night, against 100, so drift from nights already kept was counted again. Change (`mode.py`, step 7): the same 512 check prompts are answered before the night and after it, and the night is undone when before minus after is more than `undo_drop_points` (3). **Choice:** cumulative drift is not capped. A cumulative cap would need its own constant and mark; it is not added here. Run check (`mode.main` with three nights; agreement values fixed in advance at 100, 98, 98, 96.5, 96.5, 92.0; the real model was used, the values were scripted): night 1 kept (drop 2.0), night 2 kept (drop 1.5), night 3 undone (drop 4.5, 30 rows dropped). The old reading (100 minus agreement) gives 3.5 for night 2 and would have undone it.

**A5. Answer-only rows and single-cell ranges (spec mismatch). Shown.** Before the fix, rows with no worked steps trained: 92 of the 128 diary rows of the earlier smoke run had no calls (count checked here), and 86 of the 174 accepted SUM drafts in a 3,000-draw test had empty steps (single-cell ranges such as `A3:A3`). `make_row` skipped the tool check when there were no calls. Change: (a) `draft()` refuses a draft whose tool working is empty (`no_steps`); (b) `make_row()` refuses zero-step rows from every source (`zero_steps`), so diary rows need at least one call; (c) `build_diary` takes the check set first (the first 512 pool prompts, pre-mode answers) and the diary from the rest, so a stricter diary cannot leave the check set empty. An empty check set would read 0 agreement and undo every night (`main` asserts it is non-empty). Consequence (**suggested**): diary rows are fewer. In the sample smoke run 285 candidates were refused as `zero_steps`, and the diary still filled to 128 (the smoke size); with the full TRAIN file the diary may stay below the 4,096 constant, and the run log's `diary` event will say so. The constants file is unchanged (sha256 2198dc5d...).

**A6. Own tries kept on final answer alone (bug). Shown.** An own try was kept when its last call equalled the answer. Example: `A: 9 1 6 | B: 0 5 9 ; =ABS(A1-B3)` trained as `0 - 0 = 0`, while the tool's working is max 9 9, min 9 9, sub 9 9 = 0. Change (`try_day`): an own try is kept only when its calls equal the tool's working (op, operands and result, in order). Otherwise the tool's working is trained and the event is counted (`own_not_tool_working`). Consequence (**suggested**): own rows will be rare. Sec. 2 step 3 ("right tries are kept as its own worked steps") then holds only when the model writes the tool's working exactly. In the three-night sample smoke sheet run 2 own rows were kept and 41 correct tries were not the tool's working (counted in the `try` events). This needs a decision before DM1 is read.

**A7. DM4 audit line for diary rows (spec mismatch). Shown.** DM4 says every training row traces to a made problem and the tool's reply. Diary rows come from TRAIN prompts, which the tool cannot check, so self-replay could not pass DM4 as written (the earlier smoke run had 128 diary rows, none with a tool reply). Change: DM4 is read as two audit lines. (i) own and tool rows: a made problem, the tool's reply, and the model's own try or the tool's working (A6). (ii) diary rows (`source` diary): a TRAIN prompt, answered by the pre-mode self with at least one call (A5), and no sealed-panel prompt. Both are checked after each run by `python3 -m domain.audit RUN_DIR`, which reads the panels (`mode.py` cannot: `guard()`). Shown: the sample smoke sheet run passes (259 rows, 0 panel overlaps, 0 zero-step rows, 0 bad sources).

**Marks after these addenda.** DM4 passes only after the candidate RPN panel is installed and a real run passes `domain.audit`. DM1 and DM6 need the A2 and A6 decisions. Regression tests: `domain/tests/test_review_fixes.py` (6 tests) and the original `domain/tests/test_tools.py` (10 tests) both pass.

**Opus rulings on A1-A7 (12:37 PM ET 10-09, before any run).**
- A1 accepted. The candidate RPN panel replaces the first one (written by this thread at 11:51 AM ET, never used by any run); the first one is kept as `panel/rpn.v1-overlap.jsonl` for the record. DM4 is read on the candidate.
- A2 decided: no change to `custom_io/` for this test (one change at a time). **DM1, DM2 and DM6 are scored on the kinds the model can be trained on**: sheet SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS (7 of 10); RPN all kinds except `a b %` (7 of 8). Bars unchanged (+30 near, +10 far), computed over those kinds' rows. MOD, COUNTIF, IF and `a b %` stay in the practice mix (the model is not told they cannot be learned) and are reported. They double as a picking check: a good picker moves its practice away from kinds that never improve (reported share on the last day).
- A3 accepted (COUNTIF is unscored under A2 anyway).
- A4 accepted: the undo gate compares the 512 check answers before and after each night; drift from kept nights is not capped. Reported: cumulative agreement with the pre-mode self after the last night.
- A5 accepted (Ben's no-truncation rule: no zero-step rows from any source).
- A6 accepted as the conservative choice: an own try is kept only when its calls equal the tool's working, so a right answer reached by wrong steps is never trained. Disclosed: the model then learns mostly from the tool's working, and its own tries mainly feed its scores (quiz, progress, stop). Reported: own rows kept and right-but-different tries per night.
- A7 accepted (two audit lines).

**A8. Does a bigger model pick its skills better? Reported, not a gate (Ben, 12:32 PM ET 10-09: "Also when it's smarter (bigger) it will be better at picking its own skills").** Written before any run.
- R1, pick gain: near-split score after the mode with its own picks minus the same run with an even mix (explore share 1.0, same nights and row count; a control arm we set, not part of the deployed mode). Positive = its picks help.
- R2, self-knowledge: rank correlation across kinds (Spearman) between the model's own last quiz score per kind and the sealed near score per kind. Higher = it knows better what it can and cannot do, which is what its picks run on.
- R3, wasted practice: share of the last day's practice spent on kinds that never improved on its own quiz (includes the A2 kinds). Lower = better picking.
- Sizes: T1SDR 3M now (seed 200, after DM-S, one extra CPU run for R1's even-mix arm); then B3 3M vs B3 10M when the ladder builds them (big-run plan, 10-12 to 10-23), and the 30M rung. Same constants file at every size.
- Ben's idea reads as **supported** if R1 and R2 are higher at 10M than at 3M on both seeds and R3 lower; **not supported** if 10M is no better than 3M on any of the three on both seeds. Either way it is reported next to the size bar (scorecard row 3) as extra evidence, never as the bar itself.
- Note: at Level 1 the picking rule is fixed, so size can only help through better self-scores (R2). The Level 2 version, where the model learns to predict its own progress, is where size should matter most; that test gets its own marks when built.

**A9. Diary replay keeps the parent's call-free answers (Opus, 1:10 PM ET 10-09, before any result was read).** A5 also refused diary rows with no calls. In the first real start (12:40 PM ET) that threw away 8,813 of 13,824 scanned old questions (64%), so self-replay covered only questions the parent answers with the calculator, and every call-free family (word answers, lookups, rule-from-examples) got no replay. A self-replay row is the parent's whole own output, never a cut-down target, so A5's no-truncation reason does not apply to it. Change: `make_row(..., allow_zero=True)` for diary rows only; practice rows (own/tool) still need worked steps (A5 stands for them); `domain/audit.py` counts zero-step rows only outside the diary. Check (smoke, 20 updates, same seed): with the A5 diary the harm measure fired on `fewshot_number_rule` (in_dist drop 0.44); with this diary nothing fired (drop 0.22). Both are one tiny smoke and prove nothing alone. The 12:40 PM start was stopped at night 1 before any training finished; its folder is kept as `runs/sheet-s200-stopped-diary-a5`. The real seed-200 run restarts from scratch with this change.

**A10. Result of DM-S v1, sheet seed 200 (run 1:02-1:52 PM ET 10-09; scored 1:56 PM ET) and the ruling (Opus, 2:05 PM ET).** Shown, from `runs/sheet-s200/analysis/RESULT.md` and `log.jsonl`.
- The loop ran alone for 7 nights (night 1 undone, drop 3.71) and stopped on its own quiz (74.22, 75.78, 73.83). Its own quiz rose from 11.7 to about 74 pooled, and to 96-100% on all 7 trainable kinds.
- Sealed panel, scored kinds: near 3.33 -> 2.86 (DM1 -0.48, **proved wrong** on seed 200), far 1.07 -> 0.36 (DM2 fail). Old skills: in_dist 90.22 -> 88.16, `passage_qa` and `seq_next` fired (DM3 fail). DM4 pass (7,996 rows, 0 panel overlap). DM5 pass on its letter, but the panel never moved, so it says nothing. R2 (own quiz vs panel, Spearman) -0.02; R3 8%. Agreement with the pre-mode self fell from 100 to 93.2 over the kept nights (A4 does not cap the total).
- Cause (shown by a probe on the final night, 60 questions each): fresh one-digit, three-row grids of the help example's exact shape are 100% (`=SUM(A1:A3)`, `=SUM(A1:A2)`); the same with column B is 5%, with two-digit numbers 3%, with a four-row grid 20%. The practice maker only replaced digits with digits of the same length, so every practice problem kept the help example's column letters, grid size and one-digit numbers. The model learned that narrow shape (shortcuts such as "add the first numbers"), not what a cell reference means, and its own quiz came from the same narrow maker, so it could not see the gap.
- Ruling: kill-first, so seed 201 of v1 does not run. **v2 = one change: a wider practice maker**, the same for every domain. Each draft applies these text edits to a help example: every number gets a new random length from 1 to (the longest number in the domain's help page + 1); each run of two or more space-separated numbers has a 1 in 2 chance of one number inserted or deleted; with chance 1 in 2, the letter part of every letter-digit token (like `A1`) with one letter is renamed to another letter used in such tokens in that example; with chance 1 in 2, one symbol (not a letter, digit or space) is swapped for another symbol used in that example. The tool keeps only drafts it can run. The quiz comes from the same maker. These edits were chosen after seeing this failure and knowing the panel's dimensions (disclosed), so v2 is scored on a **fresh panel draw** (same generator, new seeds 91011 and 91012), and DM6 (RPN, where no result has been looked at) is the cleaner check of the edits. DM4 for v2: panel rows whose exact prompt also appears in training are dropped from scoring and counted; DM4 fails if more than 2% of panel rows are dropped. Marks DM1-DM5 otherwise unchanged. DM3's failure is left for its own change (a cap on total drift) if v2 still fails it.

**A11. Where the practice maker stands under Ben's rules (Opus, 2:15 PM ET 10-09; raised by the coordinator).** Said plainly: the practice maker (v1's digit swap and v2's four text edits) is hand-written code. Under Ben's no-hard-coding and deployable-autonomy rules, hand code is allowed only as an outside tool that the model chooses to call, by writing the call as text. In DM-S, the loop calls it at fixed points, as it does the spreadsheet tool, because today's model can write only calculator calls from a fixed list of 8 operations (sec. 4 item 1). So in DM-S the maker is a **fixed design constant**: one piece of code, the same for every subject, set before any run. It never reads our panels or any per-subject setting, and it is not tuned between subjects. This is the same status the project already gives the night's fixed constants and the search and executor tools that the sleep calls (deploy rule as applied, 10-07). It is **not** "the model widens its own practice". DM4 therefore certifies **Level 1** only: every choice comes from the model's own scores, and making practice and checking it are done by domain-free outside tools called on a fixed schedule. Scorecard row 9 stays "partly" until **Level 2**. In Level 2 the model writes the tool calls itself, both "vary this example" and "evaluate this", as letters, once B3 group 2 lets it write a call's operation name (O1). Then it decides when and how to vary from its own progress, with its own marks. No change to v2's code or marks.

**A12. Review of the v2 maker before its first run, and one fix to edit (c) (Opus, 8:30 AM ET 10-10).** Shown: all 48 domain tests pass and the v2 panel hashes match their .sha256 files. Found in review: under A10's wording, edit (c) renames a cell letter only to another letter already used in a cell reference of the same example. Five of the ten spreadsheet help examples (SUM, MAX, MIN, PRODUCT, COUNTIF) refer to one column only, so (c) could never fire on them and the column-B gap that sank v1 would stay for four of the seven scored kinds. Fix, the same for every domain: the new name may also be any capital letter that stands alone in the example (like the `B` in the label `B:`). Only letters in letter-digit tokens are ever renamed, as before. RPN examples have no such letters, so DM6 is unaffected and stays the clean check. Disclosed: found by reading the help page against A10's rule, and confirmed by counting the columns the v2 panel uses per kind (about half of the near SUM, MAX, MIN and PRODUCT rows use the other column, as the panel's sealed definition "new numbers and cells" already said). Smoke, one practice day on the real vocabulary: 1,024 problems from 175,458 tries in 16 s; every scored single-column kind now practises both columns; grids of 2-4 rows and one- and two-digit numbers. Marks unchanged.

**A13. Result of DM-S v2, sheet seed 200 (run 8:21-10:46 AM ET 10-10; scored 10:51 AM ET), and v3 (Opus, 11:05 AM ET 10-10).** Shown, from `runs/sheet-s200-v2/analysis/RESULT.md` and `log.jsonl`.
- The loop ran alone for 8 nights, none undone, and stopped on its own quiz (pooled 6.3 -> 62.5).
- Fresh sealed panel (`sheet.v2`), scored kinds: near 2.14 -> 69.05, **DM1 +66.9, PASS** on seed 200 (SUM 0 -> 70, MAX 2 -> 78, MIN 13 -> 90, PRODUCT 0 -> 70, cell arithmetic 0 -> 67, division 0 -> 57, ABS 0 -> 52). Far 1.07 -> 1.07, DM2 fail (far needs 5-6-cell ranges and two kinds in one formula; the maker's grids hold 2-4 numbers, so this is going past practice, and it did not). **DM3 FAIL**: in_dist 90.22 -> 86.03 (drop 4.19, under the proved-wrong bar of 5), seven families fired. Agreement with the pre-mode self fell 100 -> 90.82 over the nights (per-night drops 2.73, 2.15, 0.98, 1.37, 0.59, 0.98, 0.39, 0.00, never above the per-night gate). DM4 pass (10,804 rows, no panel row in training, 0 dropped). DM5 pass (stop night 69.05, best 69.76 on night 7). R2 0.89 (v1: -0.02): its own quiz now ranks the kinds the way the sealed panel does. R3 0%.
- Ruling: DM1 passes, so v2's maker stays. DM3 is the blocker. A10 named a cap on total drift as the next change; this addendum puts fresh replay first. Reason: the project's own 2x2 sleep screen (5329b2c6c) found that skills harm comes from overfitting small reused row sets and that fresh rows help, and the v2 nights drew about 11,500 replay rows a night, with replacement, from one 4,096-question diary (each question seen about 22 times over 8 nights). A cap stops training instead of removing that cause; it stays the next change if v3 fails DM3.
- **v3 = one change:** each night's replay half is fresh old questions (never used before in the run and never check prompts), answered by a frozen copy of the pre-mode self under the diary's rules (A9), each used once. Constant `replay_fresh: true` in the constants file (the same for every domain). Everything else as v2; scored on `sheet.v2`.
- **v3 marks, seed 200, fixed now:** pass = DM3 passes and DM1 stays >= +30. Proved wrong (fresh replay does not cut forgetting) = in_dist drop > 3.19 (not at least 1 point better than v2's 4.19). In between = fail, not proved wrong. DM2, DM4 and DM5 are reported on their usual bars. Next: on a pass, seed 201 of v3, then DM6 (RPN); if proved wrong, the total drift cap (v4).
- Smoke (shown): 640 fresh rows in 16.7 s; audit ok. Adds about 5 minutes a night on 4 CPUs.

**A14. Result of v3 (fresh replay), sheet seed 200 (run 10:58-11:31 AM ET 10-10), and v4 (Opus, 11:45 AM ET 10-10).** Shown, from `runs/sheet-s200-v3/log.jsonl`.
- Night 1 had the same practice rows as v2's night 1 (721 rows, same seed), with 11,552 fresh replay rows. It drifted more than v2's night 1: agreement 96.29 (drop 3.71) against v2's 97.27 (2.73), so the per-night gate undid it. Night 2 (half visits) dropped 3.91 and was undone too. The quiz never moved, and the loop stopped after 2 nights with the parent's weights. v3 therefore learns nothing (DM1 0); its DM3 "pass" is empty and is not claimed. Read: **fresh replay does not cut forgetting here** (one seed; one check prompt is 0.2 points, so the night-1 gap is 5 prompts). `replay_fresh` is set back to false; the code stays.
- Checked and ruled out (shown, no training): AdamW's weight decay pulling weights toward zero. Shrinking the parent's matrices as 2,900 updates of decay would (x0.971) leaves agreement at 99.61, so v2's drift comes from the updates themselves. Suggested, untested: replay answers are the model's own greedy answers, so their loss starts near zero and they push back only after drift has happened.
- **v4 = one change from v2** (the cap A10 and A13 named): the undo gate counts total drift from the pre-mode self. A night is undone when agreement on the 512 check prompts is below 100 - 3 = 97, instead of when that night alone drops more than 3 (A4). Constant `undo_total: true`. Everything else as v2; scored on `sheet.v2`.
- **v4 marks, seed 200, fixed now:** pass = DM3 passes and DM1 >= +30. Proved wrong = DM1 < +10 (the cap leaves too little learning) or in_dist drop > 3.19 (the cap does not protect). In between = fail, not proved wrong. Prediction, written before the run: v2's night 1 gave +24.8 near for 2.73 points of drift and later nights each add more drift, so DM1 near +25 with DM3 at or near pass, i.e. fail, not proved wrong. Either way it measures whether 3 points of drift keep old skills, which fixes the target for the next change (more learning per point of drift).

**A15. Result of v4 (total drift cap), sheet seed 200 (run 11:35 AM-12:20 PM ET 10-10; scored 12:25 PM ET), and v5 (Opus, 12:35 PM ET 10-10).** Shown, from `runs/sheet-s200-v4/analysis/RESULT.md`. As predicted in A14: night 1 kept (agreement 97.27), nights 2 and 3 undone (95.12, 94.73), stopped on its quiz after night 3. DM1 +24.8 (2.14 -> 26.90): fail, not proved wrong. DM3: in_dist drop 1.47 (inside 1.5), but `rule_apply` and `seq_next` fired: fail. DM5 pass, DM4 pass, R2 0.85. Read: one night at lr 1e-4 already harms two rule-from-examples families, so a drift budget alone cannot pass DM3. Next is a change that learns with less drift per night. An outside-opinion prompt for Astra is in `reviews/astra-domain-mode-forgetting-2026-10-10.md`.
- **v5 = one change from v4:** replay share 0.5 -> 0.875 (each batch of 64 = 8 new rows + 56 replay rows; each new row is still seen 16 times, so a night has 4x the updates). Constant `replay_share` (the same for every domain).
- **v5 marks, seed 200, fixed now:** pass = DM1 >= +30 and DM3 passes. Proved wrong (more replay does not cut drift) = night-1 agreement drop not below 2.0 (v4: 2.73). In between = fail, not proved wrong.

**A16. Result of v5 (replay share 0.875), sheet seed 200 (run 12:23-1:55 PM ET 10-10), and v6 (Opus, 2:20 PM ET 10-10).** Shown, from `runs/sheet-s200-v5/log.jsonl`. Night 1 (1,442 updates, 7 of 8 rows replay) dropped 4.30 points of agreement, more than v4's night 1 (361 updates, 2.73). It was undone, and so was night 2 (711 updates, 4.30). The loop stopped with the parent's weights. **v5 is proved wrong** on its fixed mark (night-1 drop not below 2.0). `replay_share` is back to 0.5. Read (suggested): drift grows with the number of updates whatever the replay share, because replay targets are the model's own answers and push back only after drift.
- The creative roadmap's sleep screens give the lead (coordinator relay, 12:24 PM ET; `creative/results/fastsleep/sleep7d/README.md` on branch claude/project-thread-2kevpk, Tests SC, SCL, SCM and SCM2). Model-picked replay is the first recipe there that kept old skills over two nights while learning: every 32 updates, draw replay rows, score each under the current model and under a frozen copy from before the night, and replay the ones whose loss rose most.
- **v6 = one change from v4:** the model picks its own review that way, from its diary (`replay_pick: true`; rounds every 32 updates; draw 512, pick the 128 with the largest loss rise). SC used 1,024 and 256; this run halves both to fit the CPU (per-row losses are about 70 ms each here) and keeps the top-quarter ratio and the 32-update rounds. Disclosed. The first 32 updates of a night replay uniformly, as in SC. lr stays 1e-4 (SCL, the clean SC run, was at 1e-4). The total-drift gate (A14) stays.
- **v6 marks, seed 200, fixed now:** pass = DM1 >= +30 and DM3 passes. Proved wrong (picking does not cut drift here) = night-1 agreement drop of 2.73 or more (v4's night 1, the same night without picking). In between = fail, not proved wrong.
- Smoke (shown): per-row losses match the batch loss (mean 0.0597 both); picking rounds run; picked rows' loss rise 0.43 vs -0.04 for all drawn rows on the first round.

**A17. Result of v6 (model-picked review), sheet seed 200 (night 1 only, 2:00-2:31 PM ET 10-10; then stopped by hand, kill-first).** Shown, from `runs/sheet-s200-v6/log.jsonl`. Picking ran as designed: picked rows' loss rise was 0.15-0.50 against 0.02-0.13 for all drawn rows. But night 1 dropped 3.52 points of agreement, more than v4's night 1 (2.73), so it was undone. **v6 is proved wrong** on its fixed mark, and the run was stopped after night 1. Pattern over four runs with the same night-1 new rows: plain diary replay 2.73, fresh replay 3.71, more replay 4.30, picked review 3.52. Suggested: replay content is not the lever on this 3M model; learning the new rows moves shared weights, and the rule-from-examples families feel it first. Options put to Ben (2:40 PM ET): a small add-on that holds what a domain teaches (used only with that tool, or always on), or waiting for the bigger model. The Astra prompt now carries v5 and v6.

**A18. v7: a per-tool add-on (Opus, 3:05 PM ET 10-10; run started 2:40 PM ET on the recommended option; Ben chose "Add-on per tool" on the card at 2:50 PM ET).** Change from v4: what the domain teaches goes into a small add-on. Each of the model's 28 Linear layers gets a low-rank pair: rank 8, alpha 16, 135,488 parameters, about 4% of the model; it starts at zero, so a new add-on changes nothing. The model's own weights are frozen. The add-on is on for this tool's work (practice tries, the quiz, the nights and the sealed panel) and off for old questions (the forgetting check and the old-skills panel). The add-on trains at lr 1e-3, custom_io's base training rate. The 1e-4 night rate existed to protect old weights, and here they are frozen. Disclosed: (1) in this test we switch the add-on by the question's subject, standing in for the finished model's own tool choice (Level 1, as A11); (2) DM3 then holds by construction. The analysis reports, but does not gate, the old-skills harm with the add-on left on. Constants `addon: per_tool`, `addon_rank: 8`, `addon_alpha: 16`, `addon_lr: 0.001`, `replay_pick: false` (the same for every domain); everything else as v4.
- **v7 marks, seed 200, fixed now:** pass = DM1 >= +30 (DM3 holds by construction; DM4 and DM5 on their usual bars). Proved wrong = DM1 < +10, meaning an add-on this size cannot hold the domain. Reported: DM2, the harm with the add-on left on, and the night count.
- Smoke (shown): the merged checkpoint reproduces the live add-on's loss exactly (0.10785 both). With the add-on off the model equals the parent (0.05838 both). The forgetting check reads 100 with the add-on off.

**A19. Result of v7 (per-tool add-on), sheet seed 200 (run 2:40-4:20 PM ET 10-10; scored 4:30 PM ET).** Shown, from `runs/sheet-s200-v7/analysis/RESULT.md`. The loop ran alone for 7 nights, none undone (the check reads 100 with the add-on off, as designed), and stopped on its own quiz (pooled 6.3 -> 45.3 at night 6, 42.2 at night 7). **DM1 +38.1, PASS** (near 2.14 -> 40.24; MAX 73, MIN 72, cell arithmetic 43, ABS 37, division 28, PRODUCT 17, SUM 12). **DM3 PASS by construction**: with the add-on off the model is the parent. DM4 pass (10,091 rows, no panel row in training). DM5 pass (stop 40.24, best 42.14 on night 6). R2 0.87. DM2 fail (far +0.7). Reported: with the add-on left on, old skills drop 6.18 and seven families fire. The add-on really is separate, and switching it by tool is what keeps old skills. The add-on learns less than v2's whole-model nights (+38 against +67), SUM and PRODUCT most of all; a bigger rank is the lever if needed (forgetting report, coordinator relay 3:27 PM ET). Next, per kill-first: seed 201 of v7, then DM6 (RPN, same constants).

**A20. Result of v7, sheet seed 201 (run 4:25-6:20 PM ET 10-10; scored 6:25 PM ET), and DM6 start.** Shown, from `runs/sheet-s201-v7/analysis/RESULT.md`. 8 nights, stopped on its own quiz. **DM1 +53.8, PASS** (near 0.95 -> 54.76). DM3 pass by construction; with the add-on left on, old skills drop 9.78 and eleven families fire. DM4 pass (10,830 rows, no panel row in training). DM5 pass (stop 54.76 = best). R2 0.91. Far +1.07. **Read across both seeds: DM1 PASS (+38.1, +53.8); DM2 PROVED WRONG (+0.71, +1.07, both <= +2): it does not go past its practice to longer ranges or mixed formulas; DM3, DM4 and DM5 pass.** DM6 now runs: RPN with its own tool and sealed panel (`rpn.v2`), seed 200, the constants file unchanged (the same hash as the two v7 sheet runs). DM6 bars: DM1 and DM3 as for sheets.

**A21. Result of DM6 (RPN, v7 constants unchanged), seed 200 (run 6:25-7:23 PM ET 10-10; scored 7:28 PM ET), and the read of DM-S.** Shown, from `runs/rpn-s200-v7/analysis/RESULT.md`. 4 nights, stopped on its own quiz. Near on scored kinds 6.54 -> 90.07 (**+83.5, DM1 bar PASS**). Every scored kind reached 83-100, except `a b /` at 55 (the calculator's exact division leaves few kept problems). DM3 pass by construction; with the add-on left on, old skills drop 4.12 and five families fire. DM4 pass: 7 of 800 panel rows (0.9%) were also training prompts and were dropped from scoring, under the 2% bar. DM5 pass (90.07, best 92.01). R2 0.73. Far -0.4. **DM6 PASS**: the same constants file learned a second subject.
- **DM-S read (v7, per-tool add-on, Level 1):**
  - DM1 PASS: sheet +38.1 and +53.8; RPN +83.5.
  - DM2 PROVED WRONG: it does not go past its practice.
  - DM3 PASS by construction.
  - DM4 PASS at Level 1.
  - DM5 PASS.
  - DM6 PASS.
- **Open:**
  - Going past practice (DM2). Far problems need shapes the maker never makes, such as longer ranges and two kinds in one formula, so the model would have to compose or extrapolate.
  - The add-on switch is ours in this test, standing in for the model's tool choice (Level 2).
  - Whole-model learning without forgetting: the forgetting report's "own checked tries" path.
  - A8 R1 (choosing vs even mix) and the bigger-model re-runs.

**A22. v8: the model switches its own add-on (Level 2 routing), measured on the three finished v7 runs (Opus, 7:45 PM ET 10-10; marks fixed before any routed result).** Change: v7's switch was ours (the question's subject). In v8 a small gate on the model's own reader decides. The gate takes the mean of the parent's reader features over the prompt (the add-on off, so the switch never depends on the add-on) and feeds a logistic unit (`domain/route.py`, fixed settings `GATE`, the same for every domain). The model trains it from its own records: positives are the prompts it practised with the tool, negatives are its diary of old questions. No panel or DEV row trains it. Then each sealed-panel question and each old-skills question is answered by the parent or by the add-on model, as the gate decides. Disclosed: the gate is trained after the run from the run's own log. That equals a last step of the mode that uses only what the mode itself recorded; it goes into `mode.py` if this passes.
- **v8 marks, fixed now, on each of sheet s200, sheet s201 and RPN s200:** pass = routed DM1 >= +30 and routed DM3 passes (harm measure on the old-skills answers the gate chose). Proved wrong = routed DM3 fails on any run (the gate turns the add-on on for old questions), or routed DM1 < +10 on any run (the gate misses the subject's own questions). Reported: the share of panel near, panel far and old-skills questions the gate switched on, and the gate's training accuracy.

**A23. Result of v8 (the model's own switch), 7:55 PM ET 10-10.** Shown, from `analysis/ROUTE.json` in each run.

| run | gate training (practice / diary prompts, accuracy) | switched on: panel near / far / old skills | routed DM1 | routed DM3 |
|---|---|---|---|---|
| sheet s200 | 5,995 / 4,096, 100% | 100% / 100% / 1 of 1,360 | +38.1 PASS | drop 0.00, none fired, PASS |
| sheet s201 | 6,734 / 4,096, 100% | 100% / 100% / 1 of 1,360 | +53.8 PASS | drop 0.00, none fired, PASS |
| RPN s200 | 3,534 / 4,096, 100% | 100% / 100% / 0 of 1,360 | +83.5 PASS | drop 0.00, none fired, PASS |

- **v8 PASSES on all three.** Its own switch keeps old skills, measured rather than by construction: the one old question switched on did not change its answer. The switch now lives in `mode.py`: at the end of a per-tool run the model trains it from its own records and saves `gate.pt` beside the final checkpoint (smoke shown). 
- Caveat (suggested): telling these subjects apart is easy, because spreadsheet and RPN prompts look nothing like the old-skills prompts. A harder check is two subjects with similar prompts, which needs a second add-on and a switch that chooses between add-ons.
- DM4 is now Level 1 for making and checking practice (fixed outside tools on a fixed schedule) and Level 2 for using what it learned (its own switch).

**A24. Ben's clarification and the third subject: reading code (Opus, 9:20 PM ET 10-10; marks fixed before the tool, panel or run exist).** Ben, 9:09 PM ET: "I think you took my learning spreadsheets thing too literally ... it could learn how to code very well. Or ... how to use computers very well. Or ... how to research in one specific area. I just meant like general skills it could learn." So the goal is broad skills. The loop (make practice from the help page's examples, check with the tool, sleep into a per-tool add-on, its own switch, stop on its own quiz) has nothing subject-specific in it. The limit is today's 3M model: it writes only calculator calls (a fixed list of 8 operations) and answers of 8 letters or fewer, so it cannot write programs, drive a computer, or write a report (sec. 4 items 1 and 4). The first step toward coding that today's model can take is **reading code**: given a small program, say what it prints.
- **Tool `py`:** a sandboxed runner for a small Python subset. It is parsed with `ast` against a whitelist, never `exec` or `eval`, and has a step cap. A prompt is one line, and `; ` ends a statement (it stands for a newline). Each `+ - * //` is one calculator call, `max`/`min` are calls, and `abs(a - b)` is a `sub` with the larger value first. Comparisons in `if` and `while` make no call: the model decides them itself, which avoids `cmp`, the operation with no row form (A2). Help page: 10 kinds, one example each: assignment with addition, an arithmetic chain, max/min, abs, list indexing, a for-loop sum, a for-loop repeat, if/else, a while loop, and a one-line function.
- **Sealed panel `py.jsonl`** (seed 91021, its own generator, separate from the maker, written and hashed before the run): 10 kinds x (60 near + 40 far). Near is the help example's shape with new numbers and new variable names. Far is longer loops or two kinds in one program. Every row fits the caps (prompt <= 208 letters, <= 16 numbers, answer <= 8 letters, <= 7 calls); no row is cut.
- **Constants unchanged** (the v7 file, the same hash as the sheet and RPN runs). Per-tool add-on with its own switch (A22/A23).
- **Marks, seed 200 (seed 201 runs only if 200 is not proved wrong):** DM1 = near, routed by its own switch, >= +30. DM3 = routed old-skills harm measure passes. DM4 = audit passes (panel collisions <= 2%). DM5 as before. DM2 (far >= +10) is reported. Proved wrong = routed near < +10.
- Next after this, when the model can write calls as letters and open text (B3 group 2, the talker): flip the direction to "task -> write the program", checked by running it in the same tool. That step is writing code.

**A25. The py tool is built, plus one maker edit found in review (Opus, 9:50 PM ET 10-10, before the run).** Shown:
- The tool (`domain/tools/py.py`) is an `ast` whitelist walker that never calls exec, eval or compile. It caps loops at 50 iterations, 400 AST nodes and call depth 6. `//` runs only when the division is exact (the calculator's own div).
- The help page has 10 kinds, 1-4 steps each.
- The sealed panel `py.jsonl` has 600 near and 400 far rows, sha256 `bdad2e23c07aa1f0...`. Its longest prompt is 98 letters, it uses at most 7 steps, no row is over a cap, and none equals a help prompt.
- All 56 tests pass, including 8 new ones for the tool and panel.
- Smoke: practice keeps about 40% of draws on py, against 0.6% on sheets.

Found in review: the maker's renames, edit (c), touch only capital cell letters, so practice programs would keep the help page's variable names. Near panel rows use new names (A24), the same kind of gap as v1's column B. **Edit (e), the same for every domain:** with chance vary_p, one letters-only word that occurs at least twice in the draft (a name the text reuses) is renamed everywhere to a new random word of 1-3 lowercase letters that the text does not already use. Checked: no sheet or RPN help example has a repeated word, so (e) never changes their drafts; the sheet and RPN results stand (their random draws would differ on a re-run). Disclosed: chosen knowing the panel's near rule. Marks unchanged.

**A26. py seed 200 result, and why three kinds learned little (Opus, 10:45 PM ET 10-10, after the run).** Shown:
- Run `py-s200-v8`, constants sha256 `4781b0be...` (the v7 file, the same as the sheet and RPN runs). 5 nights, stopped by the quiz rule, no night undone.
- **Marks.**
  - DM1 near: +46.50 (14.67 -> 61.17), PASS.
  - Routed by its own switch: +46.3, PASS. The switch is on for 99.8% of panel near rows and for 1 of 1,360 old questions.
  - DM3 routed drop: 0.00, PASS.
  - DM4: PASS (9,027 rows, 0 panel overlap, 0 dropped).
  - DM5: PASS (the stop night is the best night).
  - DM2 far: -0.5, fail. Proved wrong needs seed 201 at +2 or less as well.
  - R2: 0.836.
- **Per kind, near:** function 100, chain 98, assign add 97, max min 85, abs 80, if else 68, while 50, for repeat 33, list index 0, for sum 0.
- **Audit naming.** The py panel was built once, under the v2 rules (A24). `audit.py` now reads it as `py.v2.jsonl`, a byte-identical copy of `py.jsonl` (same sha256, `.sha256` file beside it). The content is unchanged.
- **List index got no practice.** Shown by re-drawing 600 drafts from its help example. Edit (a) gives every number a new random length of 1-3 digits, so positions such as `i = 1` and `v[2]` fall outside the 3-item list. The tool rightly answers "?" for 598 of 600 drafts. Day 1 kept 0 list-index rows. For repeat (528 of 600 drafts are "?": loop counts and products grow past the caps) and for sum (452 of 600) are thinned the same way.
- **For sum cannot be written as a training row.** The row format (custom_io progparse) points every operand at a number in the prompt, one of 4 constants (1, 2, 10, 100), or an earlier result. A loop counter's values (0, 1, 2, 3, ...) are not written in the prompt. So a loop-sum row exists only when the counter values happen to fall in that set: s starts at 0 and the range is 3 or less. Of the 58 re-drawn drafts the tool accepts, 56 are refused (`gold_ops`). Day 1 refused 38.
- **Both limits sit in the outside parts** (the maker's yield and the row format), not in the model's learning. Every kind with enough kept rows rose.
- **Next (default, nothing changed):** seed 201 with the same code and constants, per A24's marks. After that, a fix for the maker's yield, the same for every domain, written as A27 with its marks before any run. The row-format limit belongs to the shared format, which this mode does not own. It is recorded here and not changed.

**A27. Practice yield: edit (a) at chance p, the same for every domain (Opus, 11:10 PM ET 10-10, written before any run).**
- **Problem (shown in A26).** Edit (a) gives every number a new length. Numbers that must stay small (a list position, a loop count, a row inside the sheet's grid) almost always break, and the tool rejects the draft. Drafts kept out of 400 per help example (seed 7, real vocabulary, no model): py list index 3, for repeat 25, for sum 57; sheet kinds 0-7 each.
- **Change (one).** Edit (a) gives each digit run a new length with chance vary_p, like edits (b)-(e). Otherwise the run is kept as it is. This is set by the constant `relength_each_p: true`; false keeps the old rule, so old runs still replay. Nothing else changes.
- **Measured before any run (no model).**
  - py: list index 3 -> 50, for repeat 25 -> 94, for sum 57 -> 93.
  - sheet: the 0-7 kinds rise to 19-70.
  - RPN: kinds fall to about 60% of before (more duplicate drafts), but every kind still keeps 8 or more.
- **Risk.** Half the time, practice keeps the help page's numbers, so it is narrower. v1 showed that narrow practice teaches shortcuts. DM1 near rows use new numbers, so a shortcut would show as a lower DM1.
- **Marks, py seed 200** (against A26's `py-s200-v8`, same seed):
  - Pass: list index near >= +30, routed DM1 >= +43.3 (A26's +46.3 minus 3), and routed DM3 passes.
  - Proved wrong: list index near < +10, or routed DM1 < +36.3.
  - Expected and not counted: for sum stays near 0, because the row format refuses its rows (A26).
- **Marks, sheet seed 200.** The same rule must not break spreadsheets. Compared with `sheet-s200-v7` routed +38.1: pass needs routed DM1 >= +35.1 and DM3 passing; proved wrong is routed DM1 < +28.1.
- **Reported for both:** DM2 far, per-kind changes, and practice yields from the log.
- **Order.** These runs come after py seed 201, which uses A24's marks and the old code. The look-alikes thread's DM5 "keep the best night, picked by the model's own quiz" is a separate later change (A28) and is not part of this test. Disclosed: the stats panel's seed 91021 (look-alikes, PR #59) equals the py panel's seed. The generators differ, and no prompt is shared.

**A26, seed 201 (Opus, 12:05 AM ET 10-11; code and constants of A24-A26, run before A27 was switched on).** Shown:
- Run `py-s201-v8`: 4 nights, stopped by the quiz rule, no night undone.
- DM1 near: +46.83 (10.50 -> 57.33), PASS.
- Routed by its own switch: +46.83, PASS. The switch is on for 100% of panel near rows and for 1 of 1,360 old questions.
- DM3 routed drop: 0.00, PASS. DM4: PASS (8,101 rows). DM5: PASS (the stop night is the best night).
- DM2 far: +0.25. With seed 200's -0.5, both seeds are at +2 or less, so **DM2 is proved wrong for py**, as it was for sheets.
- R2: 0.872.
- Per kind, near: assign add 100, function 95, max min 93, chain 85, abs 70, if else 67, for repeat 35, while 22, list index 5, for sum 2. The same kinds are weak on both seeds, as A26's causes predict.
- **Code reading passes DM1 and DM3 on both seeds.**

**A8 result: R1 pick gain (Dopamine thread's control, its addendum B6; recorded 12:10 AM ET 10-11).** Shown, one seed:
- The control `/mnt/project-files/dopamine/r1/sheet-s200-even` ran v7 sheet s200 with an even practice mix every day (`--even-mix --fixed-nights 7`), at the same constants hash. Its night 1 matched v7.
- Near at night 7: even 50.00 against the rule's 40.24, so **R1 = -9.76**. Reported only; A8 never gated on it.
- The mean over nights 1-7 is close (35.14 against 34.25). Most of the gap is night 7, and the even run was still rising (+5.95 that night).
- Suggested cause (the Dopamine thread's reading): the rule follows the 2-night quiz change on about 26 quiz items per kind (1 item = 3.8 points). Kinds whose small quiz stalled lost practice: on the last day SUM got 5.3% and PRODUCT 1.0%. At night 7, even against rule: SUM 33.3 vs 11.7, PRODUCT 46.7 vs 16.7.
- The pick rule is what the Dopamine thread's race replaces (learned edge and progress motivators against the rule and the even mix). Any change to it (a practice floor per kind, bigger quizzes) waits for that race. It is not stacked on A27.

**A27 result: the practice-yield change fails, and is switched off (Opus, 3:05 AM ET 10-11).** Shown, seed 200, routed by the model's own switch:
- **py (`py-s200-v9`).**
  - List index near: 0 -> 20, FAIL. The pass mark was +30 and proved wrong was below +10.
  - Routed DM1: +46.33, within the +43.3 mark. DM3: drop 0.00.
  - Practice now reached the weak kinds. Day 1 kept 39 list-index rows (0 before) and 66 for-sum rows. For sum rose 1.7 -> 15.0, but day 1 still refused 45 for-sum rows (`gold_ops`, A26).
  - Other kinds fell: abs 80 -> 57, if else 68 -> 57.
- **sheet (`sheet-s200-v9`).**
  - Routed DM1: +29.3 against v7's +38.1, FAIL. The pass mark was +35.1 and proved wrong was below +28.1. DM3: drop 0.00.
  - SUM 12 -> 27 and PRODUCT 17 -> 38 rose. MAX 73 -> 25, cell arithmetic 43 -> 13 and ABS 37 -> 22 fell.
  - This matches A27's named risk: practice that keeps the help page's numbers half the time is narrower, and kinds that need new cell positions lose.
- **Decision.** `relength_each_p` is removed from `domain/constants.json`. The file is back to sha256 `4781b0be...`, the hash of every earlier v7/v8 run, so those runs re-analyse cleanly. The code path stays, off by default.
- **Reported:** DM2 far is still about 0 on both runs (py +0.0, sheet -0.7).

**A28 checked offline: "keep the night the model's own quiz rates best" does not help (Opus, 3:05 AM ET 10-11).** Shown, no training. On 10 finished runs, the stop night picked by the best own quiz scores, against the last kept night:

| run | change |
|---|---|
| sheet-s200-v7 | +1.9 |
| sheet-s201-v7 | -5.5 |
| rpn-s200-v7 | -0.5 |
| py-s200-v8 | -5.0 |
| py-s201-v8 | -1.3 |
| py-s200-v9 | -2.2 |
| sheet-s200-v9 | +0.7 |
| stats-s200-v8 | 0 |
| invoice-s200-v8 | +11.9 |
| sheet-s200-v2 | 0 |

The mean change is 0.0. The quiz (about 26 items per kind) is too noisy to choose a night, the same cause the Dopamine thread found for the pick rule (A8 R1). DM5 keeps the last kept night. No change is made.

**A29. Does the main brain's guarded whole-model recipe carry over to code reading? (Opus, 4:40 AM ET 10-11, marks written before the run.)**
- **Why.** The Main brain thread's arm N (PR #60, `mainbrain/constants-kf97n-lr3e4.json`) learned sheets at seed 200 with no add-on and no switch: near +42.1, in_dist drop 0.66, no family fired. It may replace the add-on, but it has been tried on one subject only. This run uses the same file, unchanged, on the third subject: the A24 py tool.
- **Run.** `python3 -m mainbrain.fullrun --constants mainbrain/constants-kf97n-lr3e4.json --parent <T1SDR s200> --tool py --seed 200 ...`, from a worktree of PR #60's head (`34b115fe`, which contains this branch up to `0eff9d05`). Output goes to `runs/py-s200-kf97n`. Cloud CPU, 4 threads.
- **Scoring.** domain.analyze on `py.v2.jsonl` and DEV in_dist. There is no switch: every question goes to the final checkpoint.
- **Marks, seed 200.**
  - DM1 near >= +30 is a pass; < +10 proves the carry-over wrong.
  - DM3, the plain harm measure on the whole model: an in_dist drop <= 1.5 with no family fired is a pass; a drop > 5 proves it wrong.
  - DM4: the audit is clean. The constants hash differs from `domain/constants.json` by design (the recipe's own file), and this is reported, not failed.
  - DM5 as before.
- **Reported:** the result next to the add-on's routed +46.3 (A26) on the same seed, per kind, and DM2.
- **Order.** The Main brain thread's seed 201 on sheets confirms or refutes the recipe itself. This run only asks whether the recipe needs per-subject settings.

**A29 result: the guarded whole-model recipe carries over to code reading, with no add-on, no switch and no per-subject setting (Opus, 6:15 AM ET 10-11).** Shown, seed 200, `runs/py-s200-kf97n`:
- **DM1 near:** +47.67 (14.67 -> 62.33), PASS. The add-on with its own switch scored +46.3 on the same seed (A26).
- **DM3, whole model:** in_dist 90.22 -> 89.78 (drop 0.44), no family fired, PASS.
- **DM4:** audit clean. The constants hash differs from `domain/constants.json` by design (the recipe's own file); this is reported, not failed. analyze's table prints "PROVED WRONG" for this cell only because it compares against the domain file.
- **DM5:** PASS. 4 nights; night 3 undone by the total-drift check.
- **DM2 far:** +3.75 (3.00 -> 6.75), the first far gain above +2 on any py run, but still below +10. It comes from assign add 22.5 -> 32.5 and chain 2.5 -> 27.5.
- **Per kind, near:** function 97, assign add 98, chain 98, max min 80, abs 80, if else 80, for repeat 62, while 20, list index 7, for sum 2. The weak kinds are the same as with the add-on (A26 causes).
- **What it means:** one seed. Together with the Main brain thread's sheet result, the same recipe file now passes two subjects. It may replace the add-on once its sheet seed 201 confirms. The Main brain thread reported NaN nights on sheet seed 201, a fault it is fixing. This run had no NaN night.

**A30. v10: does the add-on learn to join two things it knows, inside the real mode? (Sonnet, 2:20 AM ET 10-13, marks written before the run.)**

*Why.* Far transfer's lab (PR #61, L12) found that an add-on of rank 64, taught join-last joins (two whole pieces joined by one accepted symbol), joins *held-out* near-grid questions at 44.3 (hand-written layout) and 45 (held-out layout); far (`F5`) stayed 3.8 to 4.0. That was a lab run of 4,000 plain updates. This addendum asks whether the same lesson survives the mode's real nightly loop (16 visits per new row, half the batch replayed from the diary, undo gate, stop rule). The relay named the run: v10 = v9 + join-last joins as one more kind of `make_practice` + the rank-64 add-on.

*Pros / Cons verdict (written first, as asked).*
- Pros: (1) the lab shows the mechanism works, so this is the cheapest honest test of whether it survives the real loop; (2) the code already exists (`domain/far/joinlast.py`), merged here; (3) free (cloud CPU, about 2.5 to 3 hours, no GPU, no rental); (4) the panel is sealed before the run, with a join split made by a *different* generator (`sheet_probe.candidate`), so the maker cannot grade itself.
- Cons: (1) **starvation as written.** One more kind at normal weight gets about 2.5% of kept rows (about 26 rows a night, about 3K join visits in all) against 128K join visits in the lab (the L9 curve was 3.6 / 7.9 / 15.5 / 28.1 F4 at 500 / 1000 / 2000 / 4000 updates, so 3K visits predicts a flat curve); (2) a fixed share is a change from "one more kind"; it halves near practice, so DM1 may dip; (3) rank 64 and joins arrive together, so a near gain cannot be pinned on joins alone (answer below); (4) far is not expected to move, which can be misread as failure; (5) one seed.
- Verdict: **do it, changed.** The join kind gets a fixed 50% of each day's kept rows (`joinlast_share` 0.5, drawn first; the other kinds share the rest by the mode's usual mix). At natural weight the test would be predicted to fail for a dull reason (volume) and would say nothing about the idea. No separate rank-64 control: L8 rank 64 with no joins gave F4 4.3 and v9 rank 8 gave 1.4, so a join gain this size cannot come from the rank alone. Seed 200 first (kill-first); seed 201 only if seed 200 is not proved wrong; a natural-weight arm (no `joinlast_share`) only if the fed arm passes.

*What is run.* `python3 -m domain.mode --constants domain/constants-v10-sheet.json --parent <T1SDR s200> --tool sheet --seed 200 --data <skills 200K, seed 1> --out runs/sheet-s200-v10`. The constants file is v9's (`domain/constants.json`, widen `crossover`, 3 rings, 3,000 per ring) plus `joinlast: true`, `joinlast_share: 0.5`, `addon_rank: 64`, `addon_alpha: 128` (alpha = 2 x rank as in v7 and in the lab LA64). Nothing else differs from v9. Its sha256 is recorded in the run's start event and checked by analyze (`--constants`). The join kind: piece 1 drafted by `mode.draft` (A10 edits on a ring pick), piece 2 a whole piece of a help example with only its own text edited, joined by an accepted (form, symbol) pair (16 for the sheet); the model's own try is kept only when equal to the tool's working (A5), as for every kind.
- The mode's merge with Far's branch (v9 code) is the code path run here; it changed one thing that matters: A25's `word_edit` draws one random value per vary, which shifted every stream and lowered join-last yield from 0.138% to 0.113% of attempts. Not material (about 9K attempts a second, about 50 seconds a night for 512 join rows). Disclosed.

*Panel.* `sheet.v4.jsonl` in `/mnt/project-files/domain-mode/panel`, sealed before any v10 code ran on it, sha256 `f527a4872b5a2e74c71196b73a28ead88c5d5b07c58c1dcba4978baa531d0b79`. 1,420 rows: 600 near and 400 far (the A10 generator, seed 91031) and 420 join (60 for each of the 7 scored kinds: a near grid, two scored kinds joined by + or *, partner a different kind; generator `sheet_probe.candidate(kind, 'F4-two')`, seed 91032). Every row is checked against the help prompts, every older sealed panel, the lab probe and eval rows, and each other. Decontamination (DM4) is by exact prompt as for v2 and v3 (`.v4` added to `DECONTAM_SUFFIXES`). The mode never reads it.

*Marks (seed 200, sheet.v4, scored kinds, parent T1SDR s200 -> final).*
- **J (join split, final minus parent):** pass >= +20; proved wrong < +8. (Lab L12: 44.3; Far's own J4 pass was >= 20 and proved wrong < 12; the real loop is allowed less because it has 7 nights, not 4,000 updates of joins only.) Reported unrouted (add-on on for every question) and routed by the model's own switch (`ROUTE.json`).
- **DM1 near (sheet.v4 near):** the standing bar, pass >= +30, proved wrong < +10. Reference v9 sheet s200: +36.2. A near gain under +30 with J passing is reported as "joins cost near practice", not a pass.
- **DM2 far:** reported; prediction <= +5 (lab 3.8 to 4.0). Not a pass-or-kill mark for v10. The standing DM2 text still applies in the table.
- **DM3 harm:** routed (the product): in_dist drop <= 1.5 and no family fired, pass; drop > 5, proved wrong.
- **DM4:** audit clean (decontam <= 2%, no zero-step or bad-source row), constants hash = `domain/constants-v10-sheet.json`.
- **DM5:** as before, last kept night.
- **Reported, not gated:** join rows kept and visited per night, the share of join rows in the log, the join yield per attempt, per-kind join accuracy, and where the join gain lands (kinds and forms).
- **Proves the idea wrong:** J < +8 on seed 200 at a 50% join share. That would say the lab's lesson does not survive the real loop *even when fed*, and join-last drops out of the mode.
- **Does not decide:** a single seed (the one-seed caveat stays on every cell); far.

*Reference points on record before the run.* v9 sheet s200: near +36.2, far -0.7, F4 (lab probe) 1.4. L12 lab LA64: F4 44.3, held-out layout 45, F5 3.8 / 4.0.

*Constants files after the merge with Far's branch.* `domain/constants.json` now carries v9's widen keys (sha256 `a2f87dd1...`, the hash in Far's v9 runs). The v7 and v8 file (sha256 `4781b0be...`, the hash in every earlier run) is kept as `domain/constants-v7.json`: re-analyse an older run with `python3 -m domain.analyze ... --constants domain/constants-v7.json`. The v10 file is `domain/constants-v10-sheet.json`.

**A30 result, seed 200: near passes, joins land in the middle (+9.8, not +20), far does not move (Sonnet, 6:00 AM ET 10-13).** Shown, from `runs/sheet-s200-v10/analysis/RESULT.json` and `ROUTE.json` (run 2:34 to 5:36 AM ET, 8 nights, 10,921 s, stop rule: quiz rise below 1 over 2 nights, no night undone, panel `sheet.v4`, constants hash match):

| mark | value | verdict |
|---|---|---|
| J join split, add-on on (unrouted) | 0.24 -> 10.00 (+9.76, n 420) | **FAIL (not proved wrong: >= +8)** |
| J join split, routed by the model's own switch | 0.24 -> 10.00 (+9.76); the switch sent 100% of the join questions to the add-on | **FAIL (not proved wrong)** |
| DM1 near, unrouted and routed | 3.10 -> 50.95 (+47.86, n 420 scored) | PASS (v9 sheet s200 was +36.2) |
| DM2 far | 1.43 -> 0.36 (-1.07) | not moved, as predicted (<= +5) |
| DM3 harm, routed (the product) | in_dist 90.22 -> 90.22, drop 0.00, nothing fired | PASS (the switch sent 1 of 1,360 DEV questions to the add-on) |
| DM3 harm, add-on left on | 90.22 -> 73.46, harm.py fails | reported (the A19 pattern: harm is removed by the switch, not by the add-on) |
| DM4 | audit clean, 0 panel rows in training, 11,685 rows, constants hash = `constants-v10-sheet.json` | PASS |
| DM5 | last night 50.95 = best, rise +0.24 | PASS |

- **Join curve by night (add-on on):** 0.24, 0.71, 1.67, 3.57, 3.81, 6.43, 7.38, 6.43, 10.00. Still rising when the stop rule fired (+3.57 on the last night). The model's own join quiz (23 questions) read 4.35% at the end, so the quiz cannot see join progress and the stop rule ended the run on the other kinds' quiz rise.
- **Where the joins land:** by first piece, MAX 16.7, ABS 13.3, division 11.7, PRODUCT 10.0, SUM 10.0, MIN 5.0, cell arithmetic 3.3; by length of the working, 3 steps 12.6, 4 steps 9.2, 5 steps 10.8, 6 steps 3.0.
- **Join practice actually delivered:** 512 join rows a night (the 50% share held), 4,096 distinct join rows over 8 nights, 8 of them solved by the model itself and the rest taught by the tool's working; about 65K join-row visits in all (16 visits each), about half the lab's 128K.
- **Suggested (not shown):** the gap to the lab's 44.3 is mostly join volume: Far's L9 curve for the same add-on reads 15.5 at about 64K visits, so 10.0 is a little under the lab's own curve at this volume, not far under it. A second possible cause is that the join rows share their nights with replay and 10 other kinds.
- **Untested:** that more nights or more join visits would reach +20 here; that the stop rule is what limited the joins; why near rose more than v9's (+47.9 vs +36.2: rank 64 versus rank 8, or the new panel).
- **What the marks say:** the idea is **not proved wrong** (J >= +8) and **not shown to work** (J < +20). The lab's lesson survives the real nightly loop, weakly, when fed half the practice. Far stays flat, as the lab predicted.
- **Per A30's order:** seed 201 was started right away (6:00 AM ET, `runs/sheet-s201-v10`, parent T1SDR s201, same constants file and panel). The natural-weight arm is not run: it is only for a fed arm that passes. If seed 201 also lands between +8 and +20, the one change to try next is the stop rule only (12 fixed nights, so the join curve is not cut off), with J >= +20 a pass and J < +12 proved wrong, written before that run.

**A30 result, seed 201, and the verdict on v10: joins do not reach +20 in the real loop; join-last is not added to the mode (Sonnet, 8:35 AM ET 10-13).** Shown, from `runs/sheet-s201-v10/analysis` (run 5:54 to 8:27 AM ET, 7 nights, 9,201 s, same constants file and panel; parent T1SDR s201):

| mark | seed 201 | seed 200 |
|---|---|---|
| J join split, add-on on or routed (the switch sent 100% of join questions to the add-on) | 0.71 -> 7.62 (**+6.90, PROVED WRONG: below +8**) | 0.24 -> 10.00 (+9.76, FAIL, not proved wrong) |
| DM1 near | 0.24 -> 43.10 (+42.86, PASS) | 3.10 -> 50.95 (+47.86, PASS) |
| DM2 far | 0.00 -> 1.43 (+1.43) | 1.43 -> 0.36 (-1.07) |
| DM3 harm, routed | in_dist 90.88 -> 90.88, drop 0.00, nothing fired, PASS | 90.22 -> 90.22, PASS |
| DM3 harm, add-on left on | 90.88 -> 73.97 (harm.py fails) | 90.22 -> 73.46 |
| DM4 / DM5 | audit clean, 0 panel rows in training, hash match / PASS (last night 43.10, rise +1.19) | PASS / PASS |

- **Join curve, seed 201, by night:** 0.71, 1.67, 1.43, 3.57, 5.95, 3.33, 3.81, 7.62. Noisy, rising about +1 a night.
- **Two seeds together:** join gain +9.8 and +6.9 (mean +8.3) against the pass bar of +20 and the lab's 44.3. Both near passes, far flat, routed harm 0.
- **Verdict (the marks as written):** seed 200 lands in the middle band and seed 201 is under +8, so the fed 50% join share in the real nightly loop is **proved wrong for reaching +20 at this volume** (about 65K join visits a seed). It is not proved that joins cannot be learned: the curve rose on both seeds and was still rising when the stop rule fired.
- **Suggested, not shown:** the lab's 44.3 needed about twice the join volume and a join-only run of updates; the loop shares its updates with replay and ten other kinds. A dedicated join stage after the nights (Far's lab recipe, 4,000 updates) is where this belongs, not a fixed share inside the nights.
- **Untested:** 12 fixed nights, more visits per join row, or a join-only stage inside the mode. None is queued. The conditional "12 fixed nights" follow-up written above is void, because it applied only if seed 201 also landed between +8 and +20.
- **Decision:** join-last is not added to the default nightly loop. `joinlast` and `joinlast_share` stay in `domain/mode.py`, off by default (they are keys of `constants-v10-sheet.json` only), so the lab can reuse the kind. The near gain without a join share is already on record (v7, v9).

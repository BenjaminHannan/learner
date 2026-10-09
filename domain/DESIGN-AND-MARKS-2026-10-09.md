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

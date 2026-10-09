# Animation storyboards for the project (nothing built yet)

Asked by Ben, 10-09. He picks one, then it gets built with HyperFrames. This file is the "pick one" menu.
Every word, number and date comes from the repo or the project files. Where a number is mine (re-added from a raw file, or a plain subtraction), it says so.
Checked: six Haiku readers went through every number and claim against the sources (145 claims). 25 were flagged; all are fixed below or labelled.

## 1. The guide, and what it says

[Get started with Claude Motion](https://support.claude.com/en/articles/17454997-get-started-with-claude-motion) (the link in your message was cut off at "17...", this is the match; I read it by web fetch).
It says:
- Tell Claude **who will watch it, where it will play and roughly how long**.
- **Attach your own material** (report, data, images) so the animation is built from your content.
- The animation is **code**, so you can change one word, one number or one timing and the rest stays as it was.
- Export as **MP4**.

It says nothing about storyboards, scene seconds or checking frames. Those come from your message, so I used your format: who, where, how long, then scenes with seconds and on-screen words, numbers and pictures.

## 2. What this project has, and what it does not

This is a research model, not an app. So, plainly:

| Kind of source | Real thing here? |
|---|---|
| Landing page | **No.** There is no website for the project. The pages in the project folder are internal explainers and a status board. |
| Onboarding flow for a new user | **No.** Nobody "signs up". The README quick-start (`./run.sh audit`, `test`, `smoke`) describes the older September memory prototype (last edited Sep 30), not today's model, so I did not use it. The nearest real "step by step" is **how one question travels through the model** (idea 1). |
| Release notes | **No.** GitHub shows 0 releases and 0 tags. The nearest real things are the pull requests (titles and bodies) and the "wins" list on the progress board. I treated the newest work (Oct 8 to 9) as "the latest release". |
| Charts | **Yes.** Five explainer pages hold drawn charts (architecture, deep dive, whole-model roadmap, creative roadmap, leak check). The raw result files hold the real numbers. |
| Screenshots | **No app screenshots exist.** The "pictures" below are drawn shapes plus real text lines from the files (like `sub 12 5 = 7`). |

## 3. Defaults for all four (change any of them)

- **Who it is for:** you, and anyone you show the project to who has never seen it (a friend, a teacher, a teammate). No jargon.
- **Where it plays:** muted, on a phone or laptop, in a chat or on a shared page. So every word is on screen; no voice-over.
- **Size:** 1920x1080, 16:9, 30 frames a second, MP4.
- **Colors and labels:** green = tested, amber = built but never tested, grey = a placeholder. Every number gets a plain-words caption under it. Scores always say "out of 100".

## 4. The ranking (most useful to you first)

| Rank | Idea | Kind | Length | Why this place |
|---|---|---|---|---|
| 1 | One question's trip through the model | A flow one picture can't explain | 45 s | You asked today (9:07 AM) to clear up how the model works. This is the "how it works" video, and it shows the newest parts honestly. |
| 2 | What happens when you turn the thinking down | A number that falls flat alone (73.01) | 40 s | The cleanest real proof so far that the thinking part does the work. Fresh numbers, easy to update when the next run lands. |
| 3 | Sleep, new version vs old | A "new vs old" change | 40 s | Newest result with numbers (76.1 in 256 steps vs 71.3 in about 600). The sleep follow-ups are on hold, so it ranks below the main story. |
| 4 | The model decides when it is done | The newest feature | 35 s | Newest build (Oct 9), but it has never been tested, so it has no result to show. Fine as a plan video; weak as a "look what works" video. |

If you only want one: **1**. If you want one longer intro: **1 then 2** (45 + 40 = 85 seconds, same colors, they fit together).

---

## Idea 1. One question's trip through the model (flow, 45 s)

**For:** someone who has never seen the model. **Plays:** muted, phone or laptop. **Runs:** 45 s.
**Source:** `architecture/FINISHED-MODEL-2026-10-09.md` sections 1 to 3 and 5 (the step-by-step with Tom's apples). The example is made up: the deep-dive page `architecture/model-deep-dive.html` says of the same question "Made up for this page, in the style of the 200,000 practice questions. It is not a real row."
**Two things I invented for the picture, so you know:** the "done?" switch turning green after round 4 (no file records a stop round for this question; it is an illustration) and the wording of the captions (the facts are from the file, the sentences are mine).

| # | Time | Words / numbers / pictures on screen | Plain meaning |
|---|---|---|---|
| 1 | 0:00 to 0:04 (4 s) | Title: "How our model answers one question". Below it, typed out letter by letter: "Tom has 12 apples. He gives away 5, then buys 3. How many does he have?" Small tag: "example question, made up". | Today's question. |
| 2 | 0:04 to 0:10 (6 s) | Label "1. Read". The sentence lights up letter by letter and each letter gets a small colored dot. Caption: "A reader we borrowed (Gemma) reads it once. Every letter gets a meaning." Tag: "borrowed, not changed by our training". | Reading is done by a model we did not train. |
| 3 | 0:10 to 0:17 (7 s) | Label "2. Think, round 1". A small team of note cards glows over the sentence, arrows from every letter to the cards, cards pass notes to each other. Counter: "Round 1". Caption: "Our own thinking part looks at every letter and passes notes back and forth. One pass is one round." Tag: "ours, learned from nothing". | The thinking part is ours. |
| 4 | 0:17 to 0:25 (8 s) | After round 1 a small "call writer" types a request in computer-code style: `sub 12 5` (with a tiny note "sub = subtract"). The numbers 12 and 5 fly out of the sentence into it. A grey box "Calculator (an ordinary program, not AI)" returns `7`. The line `sub 12 5 = 7` drops into the thinking part's notes. Caption: "12 minus 5 = 7. It asks the calculator, then writes down the answer." | The model asks for a calculator; it does not do the arithmetic itself. |
| 5 | 0:25 to 0:32 (7 s) | Counter "Round 2". Next request: `add 7 3`, calculator returns `10`, line `add 7 3 = 10` joins the notes. Caption: "7 plus 3 = 10. Then the next step." | Two steps for a two-step question. |
| 6 | 0:32 to 0:38 (6 s) | Rounds 3 and 4 tick by with "nothing to calculate" tiles (illustration). A small "done?" switch flips to green. Caption: "It decides by itself when it is done: at least 1 round, at most 32." Amber tag: "the stop switch: built, never tested yet". | The 32 is a safety limit so it cannot think forever. |
| 7 | 0:38 to 0:45 (7 s) | Label "3. Write the answer". A box copies `10` from the last calculator line and shows a big **10** with the caption "Final answer: 10 apples". Then a legend: green "tested at the smallest size: Gemma in front (1 test), calculator as a separate helper (6 tests, one leak check cleared by Ben)", amber "built, never tested: requests in any round, the stop switch", grey "placeholder: the part that writes English answers does not exist yet". Last line: "Never tested all together yet. Open question: a few answers still come with zero thinking rounds." | Be honest about what is proven. |

**Real numbers used:** 12, 5, 3, 7, 10 (the example); 1 and 32 (rounds, FINISHED-MODEL sec. 3); "6 tests" (the calculator-as-helper model matched the old model over 6 seeds; its leak check missed as sealed and you cleared it at 8:21 AM, sec. 5 item 1 and 5 of 6 seeds for the swap check); "1 test" (G1 seed 400, sec. 5 item 2); the zero-rounds caveat (sec. 5 item 2).

---

## Idea 2. What happens when you turn the thinking down (a flat number, 40 s)

**For:** same audience. **Plays:** muted. **Runs:** 40 s.
**Source:** the raw result files `results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json` and `.../PT/RESULT.json` on branch `claude/8a-g-pc-results` (test G1, the 3M size, seed 400, run on your PC). The scores for 0, 1, 2 and 24 rounds are **my re-adding** of those files (saved as `animations/source-g1-3m-s400.json`); only 0 rounds (0.66) and the full score (73.01) were already written in `whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md` addendum G. "6,040 held-out questions" and "1,000 multi-step questions" are the deep-dive page's own words for the two test sets (pooled-5 and chain-5).

| # | Time | Words / numbers / pictures on screen | Plain meaning |
|---|---|---|---|
| 1 | 0:00 to 0:04 (4 s) | Big **73.01** fades in. Under it: "points out of 100, on 6,040 test questions kept aside (4,410 right)". | A score with no context. |
| 2 | 0:04 to 0:08 (4 s) | Text: "Is it the thinking doing the work? Let's turn the thinking down." A dial appears set to **12 rounds** with the note "what it used while learning. One round = one pass of look and pass notes." | We test the claim by breaking it. |
| 3 | 0:08 to 0:18 (10 s) | The dial turns 12, then 2, then 1, then 0. A tall bar shrinks with it: **73.01, 29.30, 20.00, 0.66** (caption "points out of 100"). Under each: "4,410 right, 1,770 right, 1,208 right, 40 right (of 6,040)". At 0 the bar nearly vanishes. Caption: "No thinking: 40 right out of 6,040." | Less thinking, worse answers, all the way to nothing. |
| 4 | 0:18 to 0:22 (4 s) | Dial turns up to **24**. Bar barely moves: **72.57** (a hair lower, 27 fewer right). Caption: "More rounds than it learned with: no gain." | Extra rounds do not help. |
| 5 | 0:22 to 0:29 (7 s) | New panel: "Multi-step questions" (1,000 of them; caption "score out of 100"). The same dial gives **0.0, 0.0, 1.1, 99.9** for 0, 1, 2, 12 rounds. Caption: "Questions with several steps need the rounds most." | Steps need rounds. |
| 6 | 0:29 to 0:36 (7 s) | Two columns, header "score out of 100". "Ours (with a thinking part; about 3.5 million settings it learned itself)": **73.01**, multi-step **99.9**, trains at **1.02** small steps a second, total training time **about 6.5 hours**. "Plain model of the same size (no thinking part; about 3.5 million)": **67.12**, multi-step **91.0**, **2.80** steps a second, total training time **about 2.4 hours**. Caption: "Both use the same borrowed reader. Ours scores 5.9 more points out of 100 but is about 2.7 times slower to train." | The honest trade: better, but slower to train. |
| 7 | 0:36 to 0:40 (4 s) | Amber card: "One test, at the smallest size. A second test and the bigger sizes are still to come on Ben's PC." | Do not claim more than the test shows. |

**Numbers I made up from the files:** 5.9 = 73.01 minus 67.12; "about 2.7 times" = 2.80 divided by 1.02. Both are plain subtraction or division.
**Careful with the re-cut:** seed 401 is estimated to finish about 8:30 PM ET tonight (spec addendum H, an estimate). The 10M runs are queued behind it with a late-Saturday readout estimated, and the spec lets the second 10M run be skipped. So a re-cut changes only numbers in the data file, but nobody can promise which numbers land when.
**Name warning:** the raw files also contain a different subset called "multistep" (480 rows per split). The "1,000 multi-step questions" here is chain-5. Keep them apart in the data file.

---

## Idea 3. Sleep, new version vs old (a "new vs old" change, 40 s)

**For:** same audience. **Plays:** muted. **Runs:** 40 s.
**Sources:** old sleep: `fast-sleep/RESEARCH-LOOP-2026-10-07-report.md` (71.3 +/- 2.5, from 41.6 at the start, six model copies). New sleep: pull request #53 "Consolidation sleep" (76.1% in 256 updates, six copies, per-copy 78.3, 77.9, 71.3, 75.8, 76.4, 77.0; the old sleep needs 558 to 610 updates "by its formula"). The puzzle picture: `creative-roadmap/creative-roadmap-page.html` (2 to 5, 4 to 9, 7 to 15, 10 to ?).
**What the test really is** (the report's own caveat): five kinds of rules, 65 rules in all, all seen in practice; the test is reading which rule a few new examples show and answering a new question of that kind on the first try. It is **not** inventing a rule it has never met. The captions say this.

| # | Time | Words / numbers / pictures on screen | Plain meaning |
|---|---|---|---|
| 1 | 0:00 to 0:05 (5 s) | Puzzle: "2 to 5, 4 to 9, 7 to 15, 10 to ?" Three possible rules slide in: "x + 3" (works for 1 of the 3 examples), "x times 2 + 1" (works for all 3), "x times 3 - 1" (works for 1 of 3). Caption: "A few examples show which rule is hiding. One guess, no trial and error." Small tag: "example in the style of the test". | The test: spot the rule, answer a new question. |
| 2 | 0:05 to 0:10 (5 s) | A bar at **41.6** with the label "where we started: about 42 right out of every 100". Under it: "Sleep = after a day of practice, the model studies what it found." | The starting point of the old sleep. |
| 3 | 0:10 to 0:17 (7 s) | Moon icon. The bar climbs to **71.3** (range of likely error: plus or minus 2.5). Label "Old sleep: 71.3 right out of 100". Counter: "about 558 to 610 practice steps (one step = one small adjustment)". | The old sleep works but is long. |
| 4 | 0:17 to 0:25 (8 s) | Six small bars appear, one per separate copy of the model (78.3, 77.9, 71.3, 75.8, 76.4, 77.0; caption "each copy's score, out of 100") and merge into one **76.1**. Label "New sleep: 76.1 right out of 100". Counter: "256 practice steps". Caption: "Higher, and less than half the practice." | New sleep: better and shorter. |
| 5 | 0:25 to 0:31 (6 s) | Two small pictures. "Half the practice is fresh made-up questions built from rules it found itself, so it never re-reads the same one." "Half is fresh questions on old skills." "Every 32 practice steps it tests itself and keeps its best version." | How the new sleep is built. |
| 6 | 0:31 to 0:40 (9 s) | Amber card, three lines: "Old skills: no drop compared with the model just before sleep, on all 6 copies (they moved +0.12 to +0.82 points)." "Not shown: that the sleep itself improves old skills (it scored 1.58 points lower than practice without sleep)." "Not a side-by-side test: 71.3 is the old sleep's saved number, on its own copies." | Say what is not proven. |

**Caution to show Ben:** the sleep follow-ups (SC, AP, lr 3e-4, the 71.3% re-check) are on hold, and the main sleep proof (job 9) is still running; `big-run/PLAN.md` line 191 says none of it feeds the pretraining run, and line 184 says a shipped model needs sleep. So this is a research result, not a part of the model yet.

---

## Idea 4. The model decides when it is done (newest feature, 35 s)

**For:** same audience. **Plays:** muted. **Runs:** 35 s.
**Sources:** pull request #56 (body), `architecture/B3-GROUP1-BUILD-2026-10-09.md`, the code `custom_io/models/b3.py` on branch `claude/project-thread-qtxfp4`, `architecture/FINISHED-MODEL-2026-10-09.md` sec. 3, `big-run/PLAN.md` row 5 (the stop's pass marks).
**Everything here is built, none of it has been tested.** So there is no result scene, only the plan and the marks.
**A correction I found in the checking:** the PR body and the spec say all four parts are switches that start off. The code (`b3.py`, lines 1 to 20) has two real switches for this group: Gemma + calculator together (`eg_embed`) and requests in any round (`any_round`). The stop switch is already built into the base model, and the 2,000-letter reading comes from the size settings file. So only two of the four can be flipped off to find a break. The storyboard uses the code's version.

| # | Time | Words / numbers / pictures on screen | Plain meaning |
|---|---|---|---|
| 1 | 0:00 to 0:04 (4 s) | Title: "New: it decides when it is done". Amber tag: "built Oct 9, never tested yet". | Be upfront first about what is not tested. |
| 2 | 0:04 to 0:11 (7 s) | Two question cards, "a 1-step question" and "a 12-step question". Under them, dashed empty bars for "rounds used". Caption: "One round = one pass of look and pass notes. Goal: the easy one uses at most half the rounds of the hard one." Tag: "target to pass, written before the test". | The target, shown as a target, not a result. |
| 3 | 0:11 to 0:18 (7 s) | After each round a tiny "done?" switch looks at the thinking part's notes. Label "The stop switch is 257 settings, a tiny share of the model." Caption: "It stops at the first round it decides is settled. At least 1 round, at most 32." | How small the stop part is. |
| 4 | 0:18 to 0:25 (7 s) | Before and after: "Before: calculator requests only in rounds 1 to 7." "Now: any round, up to 32. Up to 16 requests fit in its notes." | Requests can come whenever the model wants. |
| 5 | 0:25 to 0:31 (6 s) | Three items slide in: "Gemma and the calculator together" (a switch), "requests in any round" (a switch), "reads up to 2,000 letters (before: 280)" (set in the size file). Caption: "If the first test fails, we flip the two switches off one at a time to find which one broke it." | Why it is built this way. |
| 6 | 0:31 to 0:35 (4 s) | Card: "First test: the smallest size, after the current test (G1) passes. Needs Ben's OK." | When it will be tested. |

**If you want this one:** I would wait for the first test result and add it as a final scene. The data file would have an empty slot for it.

---

## 5. Considered and left out

- **Bigger model, does it help? (3 million to 10 million):** the only 10M numbers for our own design came from a run with a bug (`register-bug-8a-caps`; the plain models' 10M numbers are fine); the fixed re-run is still going. I would animate it then, not now.
- **Creative-roadmap bar charts** (for example "sleeping on tries that pass the check": 0.4 to 27.3 and 1.2 to 35.9, dated Oct 7): real, but idea 3 covers the same story with newer numbers.
- **How a job reaches the PC safely** (`REMOTE_RUN.md`: preflight, sync, test, time-boxed pilot): real, but it is a developer chore, not something the project shows anyone.
- **Talker gap (66.1 vs 92.6):** these numbers are in the roadmap notes (`architecture/redesign-ideas-2026-10-07.md` line 92), and your separate talker session owns the problem. PR #54 holds a different diagnosis with other numbers.

## 6. What happens after you pick (so you know what to expect)

1. I install HyperFrames (it installs from npm here; Chromium and ffmpeg are already on the machine, so no paid compute).
2. All the words, numbers and timings go in **one data file**. "Slow down the second scene" changes only that scene's seconds. "Change this number to 18%" changes only that number.
3. I render a draft, grab one frame a second, look through them, fix what looks wrong, then export a 1080p MP4.

# Exp 261b RESULTS: 261's arm A plus the mixed-case span guard (builder, 2026-09-23)

## Result: registered FAIL

Arm A (261's A + span guard, sealed theta 0.25, prompt B, scorer with Ruling 1)
on the blind panel (150 items, every arm run once after both seals): M1 pass,
M2 FAIL (9 wrong saves, bar 1), M3 FAIL (98/135 = 72.6%, bar 85%), M3b FAIL
(23/135 = 17.0%, bar 12%), M4 pass, M5 pass, M6 pass. Overall verdict FAIL.
Predictions P261b.1, .5, .6, .7, .9 right; P261b.2, .3, .4 ranges wrong; P261b.8
(~30% ALL) resolves to FAIL.

## Marks, arm A (integer counts)

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | no_save saves <= 1 | 1 | yes |
| M2 | wrong saves (statement fams + no_save) <= 1 | 9 | NO |
| M3 | exact TEACH recall >= 85% and >= B + 30 | 98/135 = 72.6% (B 0/135 = 0.0%, diff +72.6) | NO |
| M3b | UNSURE <= 12% of gold TEACH | 23/135 = 17.0% (15 checker + 8 guard on statement fams) | NO |
| M4 | exact ASK recall >= 90% | 38/40 = 95.0% | yes |
| M5 | median ear + checker + guard ms/turn <= 800 | median 367.5, p90 701.4, max 1065.5 | yes |
| M6 | every A frame byte-identical in A261 | 0 mismatches | yes |

Every arm's M1-M4 (each arm run once; B = 138i + 228 on statement items):

| Arm | M1 no_save saved | M2 wrong | M3 hit/gold (%) | M4 hit/gold (%) |
|---|---|---|---|---|
| A_raw (canon, no brake) | 6 | 57 | 99/135 (73.3) | 38/40 (95.0) |
| A_brake (canon + brake) | 4 | 34 | 99/135 (73.3) | 38/40 (95.0) |
| A_gate (canon + brake + margin gate 9.3) | 2 | 18 | 76/135 (56.3) | 38/40 (95.0) |
| A261 (canon + brake + checker 0.25) | 1 | 16 | 99/135 (73.3) | 38/40 (95.0) |
| A (registered: A261 + guard) | 1 | 9 | 98/135 (72.6) | 38/40 (95.0) |
| A_nocanon (brake + checker, no canon) | 1 | 19 | 95/135 (70.4) | 38/40 (95.0) |
| B (138i + 228) | 0 | 2 | 0/135 (0.0) | - |

A261 also: M3b 15/135 = 11.1% (pass). A vs A261: M1 1 = 1; M2 9 vs 16
(guard removed 7 wrong saves); M3 98 vs 99 (guard cost 1 hit: its single false
hold); M4 38 = 38; M3b 23 vs 15 (guard added 8 unsure on statement fams,
pushing M3b over the bar).

Question families: 0 stray TEACH saves on questions/chain_questions in every
ear arm.

## Per family, arm A

| Family | n | TEACH hit/gold | wrong | saved | ASK hit/gold | exact | unsure (checker+guard) |
|---|---|---|---|---|---|---|---|
| plain_teach | 25 | 24/34 | 4 | 28 | 0/0 | 16 | 8 (4 guard-held) |
| varied_teach | 30 | 35/53 | 3 | 38 | 0/0 | 18 | 11 (2 guard-held) |
| full_names | 15 | 25/31 | 1 | 26 | 0/0 | 12 | 1 |
| corrections | 15 | 14/17 | 0 | 14 | 0/0 | 12 | 3 (2 guard-held) |
| no_save | 25 | 0/0 | 1 | 1 | 0/0 | 24 | 0 |
| questions | 25 | 0/0 | 0 | 0 | 23/25 | 23 | 0 |
| chain_questions | 15 | 0/0 | 0 | 0 | 15/15 | 15 | 0 |

## Per risk tag, arm A (R1-R14; items carry several tags, so rows overlap)

| Tag | n items | TEACH hit/gold | wrong | ASK hit/gold | unsure (guard-held) |
|---|---|---|---|---|---|
| R1 pronoun across clauses (:stmt) | 12 | 22/24 | 0 | - | 1 (0) |
| R2 statement-questions (:stmt 3 / :no_save 9) | 12 | 1/3 | 2 | - | 1 (0) |
| R3 verb decides (:stmt) | 8 | 8/9 | 0 | - | 2 (1) |
| R4 compound relatives (:stmt 6, :questions 2) | 8 | 12/12 | 1 | 2/2 | 0 |
| R5 everyday relations (:stmt 8, :questions 8) | 16 | 10/12 | 0 | 6/8 | 2 (0) |
| R6 two-hop via relative (:chain_questions) | 9 | - | 0 | 9/9 | 0 |
| R7 plural owners (:stmt) | 7 | 4/7 | 0 | - | 3 (1) |
| R8 plans/goals (:stmt 3 / :no_save 4) | 7 | 2/3 | 0 | - | 4 (0) |
| R9 pretend (:no_save) | 6 | - | 0 | - | 0 |
| R10 plural relatives (:stmt) | 5 | 4/20 | 1 | - | 0 |
| R11 appositives (:stmt) | 7 | 13/14 | 0 | - | 0 |
| R12 pronoun-after-R (:stmt) | 5 | 7/10 | 0 | - | 3 (0) |
| R13 typo next to a name (:stmt) | 8 | 5/12 | 1 | - | 8 (6) |
| R14 all-lowercase names (:stmt) | 7 | 9/9 | 2 | - | 0 |

## Panel theta curves (recorded pYES, guard applied after checker for A)

A (guarded): recall flat at 72.6% from theta 0 to 0.7 while wrong falls
25 -> 5; no theta reaches both bars (at theta 0.95: recall 54.8%, wrong 2;
at 1.0: recall 0, wrong 0).
A261 (unguarded): recall flat at 73.3% from theta 0 to 0.7 while wrong falls
34 -> 10; no theta reaches both bars either.

## A's held-back and wrong frames (categories only, never quoted)

Guard held 8 frames: 7 good holds, 1 false hold.
- Good holds (7, all checker-approved at pYES 0.41-0.94): 4 typo-glued
  subject spans on R13 items, 2 typo-glued value spans on R13 items, 1
  possessive-phrase subject span on an R7 item. Every one matched no gold
  frame; each would have been a wrong save without the guard.
- False hold (1, pYES 0.95): an R3 employer value mixing a lowercase article
  into an otherwise-capitalised organisation span. It matched its gold frame,
  so the guard cost exactly 1 hit of recall (A 98 vs A261 99).
Wrong saves, all passed by the checker (9): 2 fine-grained job-title
confusions (pYES 0.80-0.96); 1 food-value confusion (pYES 0.80); 2
lowercase-name frames storing a relation word as the value on R14 items
(pYES 0.45-0.54); 1 home-relation misread (pYES 0.96); 1 appositive
location-relation misread (pYES 0.77); 1 plural-relative vehicle frame
(pYES 0.32); 1 no-save language save on a check-style turn (pYES 0.26,
no case mix, so the guard passed it by design).

## Ruling 1 contribution (diagnostic, no panel re-run)

Rescoring the panel with the sealed 261 scorer WITHOUT the narrower patch
gives byte-identical A261 marks (M2 16, M3 99/135): Ruling 1 converted zero
frames on this panel, because the 261b panel spec already lists the species
word in pet gold relation_aliases, so those frames already matched. The rule
is harmless but was redundant here.

## Arm B note (no bar)

Arm B saved 2 frames total across 110 statement items (both wrong, hence M2 2
and M3 0/135): the rule reader abstained almost everywhere on this panel, so
the ">= B + 30" half of M3 is trivially met and means nothing. 261's panel
gave B 13/122; this panel's turns (pronouns, appositives, typos, lowercase)
are outside what the rules parse.

## Latency

Ear GPU (both resident on the 5070 Ti): 150 turns, median 159.3 ms, p90
326.1 ms, max 503.8 ms; 84/150 beamed; ckpt sha ok; no VRAM spill.
Checker: 266 panel queries, 0 fallbacks, median 279.9 ms. Ear-greedy +
checker + guard per turn (sealed M5 definition; beam-decode time excluded):
median 367.5 ms, p90 701.4 ms, max 1065.5 ms.

## Deviations

- D1 (sealed, inherited from 261): checker question is prompt variant B,
  rewording the brief's literal text and adding two NO clauses.
- D2: the blind panel was never opened before this seal (no listing, no
  hashes, no counts). After the seal its SEAL verified 2/2 OK from the repo
  root, the strict schema check passed via the sealed loader, and every arm
  ran ONCE. earpanel257 and earpanel261 were never run.
- D3: llama-server handling. The first background launch (Start-Process) died
  silently with an empty log; relaunched fully detached via Win32_Process
  (PID 19652, 261's exact flags). After all runs it was stopped by its exact
  PID (taskkill, verified gone, GPU back to idle 271 MiB). pythonw 13036 and
  all other BensPC processes untouched; no stray python processes left.
- D4: M5 counts ear-greedy ms + checker ms + guard ms (sealed definition);
  beam decoding is extra (GPU full-turn medians above for context).
- D5: the no-Ruling-1 rescore above is a local recomputation from recorded
  preds/pYES, not a panel re-run. Sealed files unchanged (seal rechecked
  15/15 OK after all runs).

## What it means (plain English)

The guard works as designed but the experiment fails. The guard caught 7
typo-glued wrong saves the checker approved, at the cost of 1 wrongly held
true fact -- yet the run still fails on three marks. Two deeper problems: the
ear itself only writes down about 73 of every 100 facts before any checking
starts (when one turn names two relatives it records 4 of 20; on typo-adjacent
turns it misses half), and the checker confidently approves fine-grained
mistakes (near-identical job titles, a home fact that was only checked, not
told). Adding the guard also pushed unsure holds from 11% to 17%, failing a
mark 261's arm passed. A mechanical case rule fixes the typo leaks it was
built for, but it cannot fix missing facts or confident misreads.

## What it doesn't mean

It does not mean the guard is useless: 7 of its 8 holds were correct, M1, M4,
M5 and M6 all pass, and questions are untouched (38/40). It does not mean
Ruling 1 is wrong: it changed nothing here only because the new panel already
lists species words as aliases. It does not mean the ear got worse: the ear
alone read 99 of 135 here; this panel is harder than 261's (plural relatives,
typo and lowercase names). It does not mean a higher theta would have saved
the run: both theta curves are flat on recall while wrongs barely move, so no
cutoff passes M2 and M3 together.

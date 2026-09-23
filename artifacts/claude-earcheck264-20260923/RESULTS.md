# Exp 264 RESULTS: the question-answering checker (builder, 2026-09-23)

## Result: registered FAIL

Arm A (261b's A with the YES/NO checker replaced by the QA checker, sealed
prompts v5 + mapping v3, span guard kept, scorer with Ruling 1) on the blind
panel (150 items, every arm run once after both seals): M1 FAIL, M2 FAIL,
M3 FAIL, M3b FAIL, M4 pass, M5 FAIL, M6 pass. Overall verdict FAIL.
Predictions P264.2, .5, .6, .7, .8, .9 ranges right; P264.1 range right but
the bar missed (2 vs 1); P264.3 range missed by 0.2 (64.8 vs 65-78);
P264.4 range missed by 0.4 (30.4 vs 20-30).

## Marks, arm A (integer counts)

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | no_save saves <= 1 | 2 | NO |
| M2 | wrong saves (statement fams + no_save) <= 1 | 5 | NO |
| M3 | exact TEACH recall >= 85% and >= B + 30 | 81/125 = 64.8% (B 2/125 = 1.6%, diff +63.2) | NO |
| M3b | held back <= 12% of gold TEACH | 38/125 = 30.4% (37 QA + 1 guard on statement fams) | NO |
| M4 | exact ASK recall >= 90% | 37/40 = 92.5% | yes |
| M5 | median per turn <= 800 ms | median 880.1, p90 1826.8, max 2664.2 | NO |
| M6 | every A frame byte-identical in A_brake | 0 mismatches | yes |

Every arm's M1-M4 plus wrong-save rates (each arm run once; B = 138i + 228):

| Arm | M1 no_save saved | M2 wrong | per-fact wrong/saved | per-turn turns-wrong/turns | M3 hit/gold (%) | M4 hit/gold (%) |
|---|---|---|---|---|---|---|
| A_brake (canon + brake) | 3 | 30 | 30/125 = 0.2400 | 21/110 = 0.1909 | 95/125 (76.0) | 37/40 (92.5) |
| A261b (canon + brake + YES/NO checker 0.25 + guard) | 1 | 6 | 6/100 = 0.0600 | 5/110 = 0.0455 | 94/125 (75.2) | 37/40 (92.5) |
| A (registered: canon + brake + QA checker + guard) | 2 | 5 | 5/86 = 0.0581 | 5/110 = 0.0455 | 81/125 (64.8) | 37/40 (92.5) |
| B (138i + 228) | 0 | 9 | 9/11 = 0.8182 | 9/110 = 0.0818 | 2/125 (1.6) | - |

A vs A261b: M1 2 vs 1; M2 5 vs 6 (QA removed 1 net wrong save); M3 81 vs
94 (QA cost 13 hits); M4 37 = 37; per-fact 0.0581 vs 0.0600; per-turn
0.0455 = 0.0455.

Question families: 0 stray TEACH saves on questions/chain_questions in
every ear arm.

## Per family, arm A

| Family | n | TEACH hit/gold | wrong | saved | ASK hit/gold | exact | unsure (QA+guard) |
|---|---|---|---|---|---|---|---|
| plain_teach | 25 | 21/32 | 1 | 22 | 0/0 | 17 | 10 |
| varied_teach | 30 | 28/50 | 1 | 29 | 0/0 | 16 | 17 |
| full_names | 15 | 21/28 | 0 | 21 | 0/0 | 10 | 4 |
| corrections | 15 | 11/15 | 1 | 12 | 0/0 | 10 | 7 |
| no_save | 25 | 0/0 | 2 | 2 | 0/0 | 23 | 0 |
| questions | 25 | 0/0 | 0 | 0 | 25/25 | 25 | 0 |
| chain_questions | 15 | 0/0 | 0 | 0 | 12/15 | 12 | 0 |

## Per risk tag, arm A (comma-split notes; see D6)

| Tag | n items | TEACH hit/gold | wrong | ASK hit/gold | unsure |
|---|---|---|---|---|---|
| R1 pronoun across clauses (:stmt) | 10 | 16/20 | 0 | - | 4 |
| R2 statement-questions (:stmt 3 / :no_save 9) | 12 | 3/3 | 2 | - | 0 |
| R3 verb decides (:stmt) | 6 | 4/6 | 0 | - | 2 |
| R4 compound relatives (:stmt 6, :questions 1, :chain 1) | 8 | 8/8 | 0 | 2/2 | 0 |
| R5 everyday relations (:stmt 8, :questions 3) | 11 | 11/11 | 0 | 3/3 | 0 |
| R6 two-hop via relative (:chain 7) | 7 | - | 0 | 4/7 | 0 |
| R8 plans/goals (:stmt 4 / :no_save 4) | 8 | 3/10 | 1 | - | 2 |
| R9 pretend (:no_save) | 6 | - | 0 | - | 0 |
| R10 plural relatives (:stmt) | 4 | 3/14 | 1 | - | 2 |
| R11 appositives (:stmt) | 10 | 12/20 | 0 | - | 7 |
| R12 pronoun-after-R (:stmt) | 4 | 4/8 | 0 | - | 4 |
| R13 typo next to a name (:stmt) | 8 | 4/16 | 0 | - | 11 |
| R14 all-lowercase names (:stmt) | 6 | 8/9 | 0 | - | 1 |
| R15 name particles (:stmt) | 6 | 5/8 | 0 | - | 3 |
| R16 wrong-relation traps (:stmt) | 8 | 4/8 | 1 | - | 5 |
| R17 stale values (:stmt) | 6 | 4/6 | 1 | - | 5 |

Quota check (comma-split): every spec quota met (R1 10, R2 12, R3 6,
R4 8, R5 11, R6 7, R8 8, R9 6, R10 4, R11 10, R12 4, R13 8, R14 6, R15 6,
R16 8, R17 6).

## A's held-back and wrong frames (categories only, never quoted)

QA held 37 statement frames + guard held 1 (value_mix on a varied_teach
item, a good hold: the frame matched no gold). QA holds by failing
question: value-only 9, owner-only 10, relation-only 11, pairs/triples 8.
By family: varied_teach 17, plain_teach 10, corrections 7, full_names 4,
no_save 1.
Wrong saves, all passed by the QA checker (5): 2 no-save saves on
statement-shaped check turns; 1 plain_teach fine-grained confusion; 1
varied_teach relation-trap pass; 1 corrections stale-value pass.

## Arm B note (no bar)

Arm B saved 11 frames across 110 statement items (9 wrong, 2 right,
hence M2 9 and M3 2/125 = 1.6%): the rule reader abstained almost
everywhere on this panel, so the ">= B + 30" half of M3 is trivially met
and means nothing. Its per-fact wrong rate is 9/11 = 0.8182.

## Latency

Ear GPU (both resident on the 5070 Ti): 150 turns, median 123.2 ms, p90
266.3 ms, max 368.9 ms; 78/150 beamed; ckpt sha ok; no VRAM spill.
QA checker: 375 panel queries, 0 fallbacks, median 285.5 ms. pYES queries
for A261b: 250, 0 fallbacks, median 282.6 ms. Ear-greedy + QA + guard per
turn (sealed M5 definition; beam-decode time excluded): median 880.1 ms,
p90 1826.8 ms, max 2664.2 ms.

## Deviations

- D1-D5 as sealed in PASSMARKS (prompt wording v5, mapping D-rel-map,
  blind-panel protocol, llama-server relaunch, M5 definition). Wording and
  mapping froze at the seal; no post-seal change (seal rechecked 23/23 OK
  after all runs).
- D6 (writer-side, found after the seal): the blind writer comma-joined
  risk tags in notes ("R13,R11,typo") while the sealed loader (like
  261/261b) reads space-separated tokens. The panel schema (file/field/
  family names) passed exactly, so the run is VALID, not void. Marks are
  unaffected (they aggregate by family). The per-tag table above re-buckets
  the already-recorded row outcomes by comma-split tags via a new,
  unsealed reporting script that never reads turn/gold text; the sealed
  scorer's own space-split by_tag is preserved in panel264_score.json.
- D7: llama-server stop needed `taskkill /F` (it runs in session 0);
  stopped by its exact PID 1424, verified gone, GPU back to idle 282 MiB.
  pythonw 13036 and all other BensPC processes untouched.
- D8: the no-R7 rule held -- no panel turn uses we/us/our/ours/ourselves
  as owner (writer's spec); D_our dev reported in PASSMARKS for the record.
- D9: every arm ran exactly ONCE. earpanel257, earpanel261 and
  earpanel261b were never run. No panel item is quoted anywhere in this
  report.

## What it means (plain English)

The question-answering checker fails the registered bar, and the numbers
say why. Compared with the YES/NO checker on the same ear and panel, it
trades 13 true facts for 1 fewer wrong save (94 hits and 6 wrongs vs 81
hits and 5 wrongs). Asking three questions means three chances to say no:
about 30 of every 100 true facts get held back, while the wrong-save rate
barely moves. The misses pile up where the ear is already weak (plural
relatives: 3 of 14; typo-adjacent names: 4 of 16) and where the questions
are strict (relation traps 4 of 8, stale values 4 of 6). Three questions
also cost time: the middle turn takes 880 ms against an 800 ms bar.

## What it doesn't mean

It does not mean the idea is empty: pretend, plan and check-question
turns are all held (R9 0 wrongs, R2 statement-questions 3 of 3 held), the
checker never invents frames (M6 exact), and questions are untouched
(37 of 40). It does not mean the ear got worse: the ear alone read 95 of
125 here, and the YES/NO arm on the same panel reads 94 of 125 -- this
panel is harder than dev (plural relatives, typo and trap turns). It does
not mean a different cutoff would save it: there is no threshold to tune,
and the holds come from three agreeing questions, not one number.

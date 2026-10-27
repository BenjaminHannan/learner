# Exp 261 RESULTS: the ear with an entailment checker (builder, 2026-09-22)

## Result: registered FAIL

Arm A (v4.1 ear + canonicaliser + brake + checker at sealed theta 0.25) on the blind
panel (150 items, run once per arm after both seals): M1 pass, M2 FAIL (9 wrong saves,
bar 1), M3 FAIL (95/122 = 77.9%, bar 85%), M3b pass, M4 pass, M5 pass, M6 pass.
Overall verdict FAIL. Predictions P261.1, .4 (pass, range edge), .5, .6, .7, .8 right;
P261.2 and P261.3 ranges wrong (9 wrong vs 0-3 predicted; 77.9% vs 85-93% predicted).

## Marks, arm A (integer counts)

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | no_save saves <= 1 | 1 | yes |
| M2 | wrong saves (statement fams + no_save) <= 1 | 9 | NO |
| M3 | exact TEACH recall >= 85% and >= B + 30 | 95/122 = 77.9% (B 13/122 = 10.7%, diff +67.2) | NO |
| M3b | UNSURE <= 12% of gold TEACH | 6/122 = 4.9% | yes |
| M4 | exact ASK recall >= 90% | 39/40 = 97.5% | yes |
| M5 | median ear + checker ms/turn <= 800 | median 344.7, p90 700.9, max 1026.0 | yes |
| M6 | every A frame byte-identical in A_brake | 0 mismatches | yes |

Every arm's M1-M4 (run once; B = 138i + 228 on statement items):

| Arm | M1 no_save saved | M2 wrong | M3 hit/gold (%) | M4 hit/gold (%) |
|---|---|---|---|---|
| A_raw (canon, no brake) | 5 | 25 | 95/122 (77.9) | 39/40 (97.5) |
| A_brake (canon + brake) | 5 | 19 | 95/122 (77.9) | 39/40 (97.5) |
| A_gate (canon + brake + margin gate 9.3) | 1 | 8 | 79/122 (64.8) | 39/40 (97.5) |
| A (canon + brake + checker 0.25) | 1 | 9 | 95/122 (77.9) | 39/40 (97.5) |
| A_nocanon (brake + checker, no canon) | 1 | 12 | 92/122 (75.4) | 39/40 (97.5) |
| B (138i + 228) | 0 | 1 | 13/122 (10.7) | - |

Question families: 0 stray TEACH saves on questions/chain_questions in every ear arm.

## Per family, arm A

| Family | n | TEACH hit/gold | wrong | saved | ASK hit/gold | exact | unsure |
|---|---|---|---|---|---|---|---|
| plain_teach | 25 | 24/31 | 3 | 27 | 0/0 | 20 | 1 |
| varied_teach | 30 | 37/50 | 3 | 40 | 0/0 | 21 | 4 |
| full_names | 15 | 22/26 | 0 | 22 | 0/0 | 13 | 1 |
| corrections | 15 | 12/15 | 2 | 14 | 0/0 | 12 | 0 |
| no_save | 25 | 0/0 | 1 | 1 | 0/0 | 23 | 4 |
| questions | 25 | 0/0 | 0 | 0 | 24/25 | 24 | 0 |
| chain_questions | 15 | 0/0 | 0 | 0 | 15/15 | 15 | 0 |

## Per risk tag, arm A (R1-R12)

| Tag | n items | TEACH hit/gold | wrong | ASK hit/gold | unsure |
|---|---|---|---|---|---|
| R1 pronoun across clauses (:stmt) | 7 | 14/14 | 0 | - | 0 |
| R2 statement-questions (:stmt 3 / :no_save 4) | 7 | 3/3 | 0 | - | 0 |
| R3 verb decides (:stmt) | 5 | 5/5 | 0 | - | 0 |
| R4 compound relatives (:stmt 2, :questions 1) | 3 | 2/2 | 0 | 1/1 | 0 |
| R5 everyday relations (:stmt 6, :questions 2) | 8 | 6/6 | 0 | 2/2 | 0 |
| R6 two-hop via relative (:chain_questions) | 6 | - | 0 | 6/6 | 0 |
| R7 plural owners (:stmt) | 4 | 1/4 | 2 | - | 0 |
| R8 plans/goals (:stmt 3 / :no_save 3) | 6 | 2/3 | 0 | - | 3 |
| R9 pretend (:no_save) | 5 | - | 0 | - | 0 |
| R10 plural relatives (:stmt) | 4 | 4/16 | 0 | - | 0 |
| R11 appositives (:stmt) | 4 | 8/9 | 1 | - | 0 |
| R12 pronoun-after-R (:stmt) | 4 | 4/8 | 0 | - | 4 |

## Panel theta curve (recorded pYES, arm A)

| theta | 0 | .05 | .1 | .15 | .2 | .25-.35 | .4-.65 | .7-.8 | .85 | .9 | .95 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| recall % | 77.9 | 77.9 | 77.9 | 77.9 | 77.9 | 77.9 | 77.9 | 77.9/77.1/76.2 | 77.1 | 76.2 | 60.7 | 0 |
| wrong | 19 | 11 | 11 | 11 | 9 | 9 | 8 | 7 | 6 | 6 | 4 | 0 |

Recall is flat from theta 0 to 0.8 while wrong falls only 19 -> 7: on this panel the
checker is nearly a pass-through (only 6 UNSURE at 0.25) and no theta reaches the bar.

## A's held-back and wrong frames (category, pYES; claims described, never quoted)

Held back, all correctly held (10): 4 pronoun-after-relative claims (p 0.02-0.04);
3 plan/goal claims (p 0.003-0.005); 3 no-save claims - lowercase check-question style
(p 0.01-0.19). Wrong saves, all passed by the checker (9): 2 speaker-pet claims from
plural-owner turns, R7 (p 0.96-0.97); 1 appositive-relative pet misattribution, R11
(p 0.96); 2 typo-corrupted claims where a chat typo leaked into the rendered fact
(p 0.68, 0.85); 1 plain speaker-pet claim (p 0.97); 2 correction-family speaker-pet
claims keeping the stale value (p 0.94-0.95); 1 no-save residence claim saved at
p 0.37 (above theta, low confidence). 8 of the 9 wrongs passed with pYES >= 0.68.

## Report-only: arm A on the known 257 panel (run once, never tuned)

| Arm (261 pipeline, theta 0.25) | M1 | M2 | M3 | M3b | M4 |
|---|---|---|---|---|---|
| A (checker) | 3 | 6 | 100/112 (89.3%) | 2/112 (1.8%) | 39/40 (97.5%) |
| A_brake (canon) | 5 | 10 | 100/112 (89.3%) | - | 39/40 |
| A_gate (canon + gate 9.3, recomputed) | 1 | 2 | 80/112 (71.4%) | - | 39/40 |
| A_nocanon (checker, no canon) | 3 | 8 | 98/112 (87.5%) | - | 39/40 |
| 257's sealed A (no canon, for reference) | 1 | 4 | 78/112 (69.6%) | 24/112 (21.4%) | 39/40 |
| 257's sealed A_brake (for reference) | - | 12 | 98/112 (87.5%) | - | - |

On known ground the checker recovers recall (100/112 vs gate's 80/112) at the cost of
more wrong saves (6 vs 2). The canonicaliser alone accounts for the A_gate/A_brake
deltas vs 257's sealed numbers (+2 recall, -2 wrong: plural-owner subjects).

## Latency

Ear (both resident on the 5070 Ti; GPU medians per wave: dev 158 ms, panel-261
139 ms, panel-257 142 ms; n_beamed 87-88/150; no VRAM spill, timings stable).
Checker: 228 panel queries, 0 fallbacks, median 284 ms. Ear-greedy + checker per
turn (sealed M5 definition; beam-decode time excluded, full-turn GPU medians above):
median 344.7 ms, p90 700.9 ms, max 1026.0 ms on panel 261 (dev: 340.3 / 650.6 / 1091.3).

## Deviations

- D1 (sealed): the checker question is prompt variant B, rewording the brief's literal
  text and adding two NO clauses (other confirmations; filler words in the fact).
  Dev A/B: the literal prompt reaches <= 1% wrong only at theta 0.9 (recall ~51%);
  B gives 91.9% recall at 0.95% wrong. Sealing the literal text would fail M3 by design.
- D2: pre-seal, the builder listed the panel directory, verified hashes and counted
  lines (150) but never read any item text, turn or gold. Panel seal then verified
  2/2 OK from the repo root after this seal.
- D3: post-seal report-only driver `scripts/claude_earcheck261_score257.py` (new file)
  reuses the sealed scorer on the 257 panel; sealed files unchanged (seal rechecked
  18/18 OK after all runs).
- D4: M5 counts ear-greedy ms + checker ms (sealed definition in theta.py/scoremain);
  beam decoding is extra (GPU full-turn medians reported above for context).
- Incidental: one qbuild log line printed the first 120 characters of one synthetic
  prompt during the fixture pilot and one panel prompt head during query building;
  neither was read, used, or tuned on, and no panel text appears in this report.

## What it means (plain English)

The checker idea is half right. On familiar ground it catches the easy traps (all 10
of its hold-backs on the new panel were correct, including every pronoun-after-relative
case it was built for) and it saves almost all the true facts the old gate threw away
(recall 89-100% vs the gate's 65-71%). But on the fresh panel it failed the test:
9 confident wrong saves got a YES from the checker, most above 0.94. A reader that
understands the sentence would not approve giving one person's pet to the speaker or
saving a typo'd word as a fact. And a whole new miss appeared that no checker can fix:
when one turn names two sisters, the ear writes down fewer than half the facts (4 of
16), so recall capped at 78% before checking even starts. The speaker-canonicaliser
works (3 wrongs fixed and 3 facts gained vs no-canon), but it is a small fix.

## What it doesn't mean

It does not mean checkers are useless: M4, M5, M6 all pass, R7-R12 hold-backs were
all correct, and on the old panel the checker kept 100 of 112 facts with only 2 unsure.
It does not mean the ear got worse: the ear alone read 95 of 122 here vs 98 of 112 on
the easier old panel; the fresh panel is simply harder (plural relatives, appositives).
It does not mean a higher theta would have saved the run: the panel curve is flat at
77.9% recall while wrongs barely move, so no cutoff passes both bars. One more data
class will not fix this either: the misses (plural splitting) and the approvals
(misattributed owners, typo'd facts) are different failures in different models.

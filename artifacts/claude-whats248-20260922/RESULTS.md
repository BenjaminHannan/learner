# Exp 248 RESULTS: read "whats / whos / wheres" (cause C2)

**Result: FAIL as registered, on M1b alone.** The M1b bar is "0 wrong values on all 124 items". The run
has 6, on direction items q243-085 to q243-090. All six are base228's own leaks. The 248 replies
there are byte-identical to base228's `base_reply`, because 248 does not touch those turns. The 248
change added **0** wrong values. Every other mark passes: whats **12/12**, where base228 got
0/12. There is a conflict in the brief. M1e says base228's direction leaks are "listed, not counted",
but M1b's bar can't be met by any builder except 251 while those leaks exist. The director should
rule on it. I have not rescored anything.

## Marks (one registered run each; seals re-verified OK before the panel run)
| mark | bar | result | pass |
|---|---|---|---|
| M1a whats family | >= 11/12 | **12/12** (base228 0/12) | yes |
| M1b wrong values, all 124 | 0 | **6** (q243-085..090, all inherited from base228; 0 added by 248) | **no (as written)** |
| M1c question writes, all 124 | 0 | 0 | yes |
| M1d control byte-identical | 12/12 | 12/12 | yes |
| M1e other-family regressions | 0 | 0 | yes |
| M1e untaught with no stored value | 10/10 | 10/10 | yes |
| M1e new direction leaks vs base228 | 0 | 0 new; 6 already in base228 listed (085, 086, 087, 088, 089, 090) | yes |
| M1f combo (no bar) | per item | 1/8 (q243-097) | - |
| M2 dev248 | 34/34, 8/8, 15/15, 0 writes | 34/34 right, 8/8 traps clean, 15/15 unchanged, 0 question writes | yes |
| M3 suitediff vs 138i | 0 bad moves; moves = predicted (none) | 0 moves in rt136, rt143, sessions152, bench; GATE clean | yes |
| M4 sleep smoke | 138i marks | sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, overwrote 0, 92.3 s | yes |
| M5 median added ms | <= +5 | -0.14 ms (paired, same session; max +5.8, min -2602) | yes |

Panel family scores, 248 (base228 in brackets): compose 0/16 (0), no_apos 0/16 (0), whats 12/12 (0),
first_person 0/12 (0), verb_subject 0/12 (0), my_relation 0/16 (0), direction 4/10 (4),
combo 1/8 (0), control 12/12 (12), untaught 10/10 (10). The live base228 run matched the file's
base_reply on all 124 items.

## Every move (panel: 14 replies changed vs base228, all others byte-identical)
- whats q243-033..044: all 12 moved from the glued decline to the stored answer. Examples:
  "WHATS Rynan's school?" -> "Rynan's school is Hervek.", "Wheres Vrondo Laendix's city?",
  "whos Dygan Zinda's doctor?", "WHOS Linix's coach?". Full lines are in m1-panel/score.txt.
- combo q243-097 "whats my sister's city?" -> "your sister's city is Krivix." (right).
- untaught q243-121 "whats Tenett's pet?": the glued decline became "I don't know Tenett's pet."
  (still no value).
- Combo misses, each with a one-line diagnosis. All are unchanged from base228, and the second cause is outside this fix:
  095 "whats Mokixs city?" and 096 "whos Vrox Zizans spouse?" need the missing apostrophe
  repaired (C1). 098 "who is garkar dombyns spouse?" needs C1 plus lowercase handling. 099 "whos Fantar
  married to?" becomes "who is Fantar married to?", which needs the composer (A). 100 and 102 "my sisters/brothers"
  need C1. 101 "my boss married to" needs A/my_relation.
- Dev: 34 moved from decline to answer (d248-001..034, except d248-033, which base228 already
  answered). Traps and must-not-change: 0 moves.
- Suites: 0 moves.

## Deviations
- There were none after the seal: no file changed, no re-run, and no driver fix.
- Before the seal (pilot): trap d248-042 asked about a name that was itself a stored value, so the echoed
  name matched the whole-word rule. I replaced it, and added two must-not-change items (whens, "whats Pell?").
  I also added `--panel-dir` to the scorer for a synthetic self-test. The registered run used the default.
- "whens"/"hows" are expanded, but nothing below reads "when is"/"how is", so they fall back unchanged.
- The M1b/M1e conflict is described above.

## What it means
When someone types "whats", "whos" or "wheres" without the apostrophe, Premonition now reads it like
"what is". It answers from what it was taught: 12 of 12 blind panel questions, against 0 of 12 before. The fix changed
nothing else it was tested on. All other panel replies, the frozen test suites and the sleep check came out the same, and it
never saved anything from a question.

## What it doesn't mean
It does not fix the other ways of asking that still fail: a missing apostrophe in the name ("Mokixs"),
"married to", "Where do I live?", and lowercase names with verbs. Those are other builders' fixes, and
the combo items show they still fail. The six direction leaks ("Who does Brylto employ?" answered with
Brylto's employer) are an old bug that 248 did not cause or fix. The panel is small, 12 questions for this
family, so it shows the rule works on these forms, not how often real users type them.

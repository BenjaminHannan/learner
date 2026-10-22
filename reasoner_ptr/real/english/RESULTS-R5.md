# English, new kinds of question: results (6 paired seeds, 2026-10-04)

Marks: `PASS-MARKS-R5.md` (commit f5325267f, before training). Numbers: `ANALYSIS-R5.json`; rows in `results5/`.
Two runs per seed, both the round-4 recipe (allptr + 8000 generated examples): **full** (practice covers all six old
kinds) and **lofo** (negation and two-relations removed from practice, bank included). Bar = the bare 1.2B LM shown
the same 8 bank examples (none of the new kinds). Fast lane, not a sealed headline test.

## Judged A, six brand-new kinds (192 questions): PASS (shown)
full 79.9% vs bare LM 8-shot 67.7%: **+12.2, CI +6.6 to +17.8** (per seed 6 to 21; every seed above the bar).

| new kind | full (ours) | bare LM 8-shot |
|---|---|---|
| time (when) | 89.6 | 71.9 |
| cause (why) | 81.8 | 34.4 |
| counting (how many) | 43.8 | 15.6 |
| tool / purpose | 91.1 | 90.6 |
| attribute (what color/size) | 91.1 | 96.9 |
| location now / first | 82.3 | 96.9 |

"Contains" (answer inside the reply): ours 90.3, bare LM 81.8. Some of our cause and counting gain may be answer
format (the bare LM often says more than the key), so read per-kind gaps with care (suggested).

## Judged B, two old kinds never practised (64 fresh questions): IN BETWEEN
lofo 80.2% vs bare LM 8-shot 76.6% on the same 64: +3.6, CI -7.0 to +14.3 (per seed -8 to +16). Not shown to beat
the bare model on a kind it never practised; not worse by 10 either.

## Read, not judged
- Never practising a kind costs about 16 points on it: lofo 80.2 vs full 95.8 (paired -15.6, CI -25.7 to -5.5).
- Practising fewer kinds also hurt the brand-new kinds: lofo 66.0 vs full 79.9 (-14.0, CI -31.4 to +3.4; suggested,
  the interval crosses 0). On the four kinds both practised: -4.0 (CI -10.8 to +2.8).
- Reproducibility: full matches round 4 exactly on 5 of 6 seeds (seed 4: 86.5 vs 92.7, two runs shared a card).
- Zeroing the core's 8 vectors gives 0% in both runs.

## What this means (suggested)
Practice on more kinds of question transfers to new kinds: with six practised kinds the model beats the bare
1.2B model on six kinds it never saw. With four practised kinds it is only level with it on the two it never saw.
Counting is weak for everyone (44% ours). Next single change worth testing: more practised kinds (e.g. 12 instead
of 6), judged on these same new kinds.

## Caveats
Both test sets were written by helper agents and read once by me. Location questions sometimes need a preposition
change ("to the shelf" -> "on the shelf"; keys accept both). One 8-shot prompt format for the bare LM.

## Cost
About $1.08 on vast for 6 boxes (`LEDGER.md`); credit $2.76 at 07:11 UTC.

# Exp 267 REPORT: checker diagnostic (follow-up to 264's registered FAIL)

Diagnostic, not a registered test: no panel was run and no PASS is possible.
One ear run (v4.1, ckpt sha 55284dec… verified, brake + canonicaliser,
table v2) over the 120-turn dev set artifacts/claude-devset267-20260923/
(117 TEACH + 10 ASK gold; seal verified OK before PREDICTIONS was written;
dev opened only after the prediction seal). Three checkers scored on the
SAME 155 kept TEACH frames, each alone, no guard, 261b's sealed scorer with
Ruling 1. No earpanel* was opened. C3's prompt was sealed with the
predictions; no tuning after.

## Headline (integer counts)

| Checker | TEACH hits/gold | Held true* | Wrong saves | per saved fact | per turn | ms/turn med/p90/max |
|---|---|---|---|---|---|---|
| C0 ear, no checker | 90/117 (76.9%) | 27 (23.1%) | 65 | 65/155 = 0.4194 | 53/110 = 0.4818 | 115.1/139.8/189.0 |
| C1 YES/NO @0.25 | 90/117 (76.9%) | 27 (23.1%) | 63 | 63/153 = 0.4118 | 52/110 = 0.4727 | 413.1/696.6/988.5 |
| C2 QA x3 | 76/117 (65.0%) | 41 (35.0%) | 31 | 31/107 = 0.2897 | 30/110 = 0.2727 | 1090.4/1952.1/2830.8 |
| C3 pick-1-of-4 | 74/117 (63.2%) | 43 (36.8%) | 55 | 55/129 = 0.4264 | 47/110 = 0.4273 | 396.2/661.6/919.3 |

*Held true = gold TEACH not saved (includes ear misses: the ear never kept
25 of the 117; checker-removed true frames: C1 0, C2 14, C3 16).
ASK: 9/10 for every arm (the one miss is the ear's; questions never checked).

## By family (hits/gold, held, wrong / saved)

| Family | n | C0 | C1 | C2 | C3 |
|---|---|---|---|---|---|
| plain_teach | 50 | 50/50 h0 w26/76 | 50/50 h0 w26/76 | 43/50 h7 w19/62 | 49/50 h1 w26/75 |
| plural_relative | 15 | 14/32 h18 w0/14 | 14/32 h18 w0/14 | 10/32 h22 w0/10 | 0/32 h32 w0/0 |
| typo_filler | 15 | 8/15 h7 w21/29 | 8/15 h7 w21/29 | 7/15 h8 w6/13 | 8/15 h7 w20/28 |
| relation_trap | 10 | 8/10 h2 w10/18 | 8/10 h2 w10/18 | 7/10 h3 w3/10 | 7/10 h3 w3/10 |
| stale_value | 10 | 10/10 h0 w6/16 | 10/10 h0 w5/15 | 9/10 h1 w2/11 | 10/10 h0 w5/15 |
| no_save | 10 | w2/2 | w1/1 | w1/1 | w1/1 |
| questions | 10 | ask 9/10 | ask 9/10 | ask 9/10 | ask 9/10 |

## Category analysis (no turn quotes)

- D-GOLD (dev gold-scope effect, dominates absolute wrong counts): most
  "wrong" saves are appositive-relative frames (value == another gold
  frame's subject, e.g. stating the kin relation that introduces the
  person the turn is about). The 264 blind panel's R11 convention counts
  these as CORRECT gold; this dev writer left them out of gold. Counts:
  C0 40/65, C1 40/63, C2 29/31, C3 39/55. Non-relative wrongs (the real
  signal): C0 25, C1 23, C2 2, C3 16. All three checkers pass relative
  frames because they ARE truly stated; only the gold convention calls
  them wrong.
- C1 is a pass-through on this dev: held 2 of 155 frames (1 stale-value
  frame at p=0.04, 1 no-save frame at p=0.001; 7 frames below p=0.5).
  Removed 0 true, 2 wrong. The dev's cleanly-worded traps/stale/typo
  turns do not trigger its NO clauses the way the blind panel's did.
- C2 removes 14 true + 34 wrong (23 of 25 non-relative wrongs gone; the 2
  remaining non-relative wrongs stand). Single-question fails over 465
  calls: value 23, relation 20, owner 13 (union = 48 held frames).
- C3 removes 16 true + 10 wrong. Picks over 155 calls: 129x1, 14x3, 7x4,
  5x2, 0 fallbacks. Systematic failure on plural turns: all 14 kept
  plural frames held, 13 picked option 3 (the other name) and 1 picked
  option 2 -- with two names in the turn the model takes the subject
  swap. C3 cost 0 true on plain (49/50) but all of plural (0/32).
- Latency: Qwen medians C1 280.8ms, C2 291.6ms x3 sequential, C3 264.5ms;
  0 fallbacks everywhere. Ear (Qwen resident): median 258.0ms, p90 321.6,
  max 428.2, 94/120 beamed, ckpt sha ok, no VRAM spill (13.7/16.3 GB).

## Predictions check (P267.1-10)

P267.1 C1 held 15-30%: 23.1% right (but all ear misses; checker held 0
true -- reported, not hidden). P267.2 C1 wrong 2-7: 63 MISSED (40
D-GOLD + clean dev wording). P267.3 C2 held 25-40%: 35.0% right. P267.4
C2 wrong 2-7: 31 MISSED (29 D-GOLD; non-relative 2, in band). P267.5 C3
held 10-30%: 36.8% MISSED by 6.8pts (plural wipeout). P267.6 C3 wrong
1-5: 55 MISSED (39 D-GOLD; non-relative 16, still out). P267.7 order
C1>=C3>=C2: half -- C1 highest (90) right, C2 lowest wrong (C3 74 <
C2 76); bands all right (C1 76.9, C2 65.0, C3 63.2). P267.8 latencies:
all three bands right. P267.9 families: plural lowest + typo
second-lowest for every checker right; R16/R17 cost C2/C3 a little (1-3
true each) right; no-save saves <= 2 right (2/1/1/1); questions
untouched right. P267.10 ear recall 65-80% (76.9%) and wrongs >= 15
(65) right.

## Deviations / compute notes

- D1 (sealed pre-dev): checkers run WITHOUT the span guard so the
  comparison is checker-vs-checker (guard held 1/125 on the 264 panel).
- D2 (sealed pre-dev): C3 readings fixed order 1-4, ear first; position
  bias is a caveat. The plural result (13/14 pick option 3) suggests the
  model does not blindly pick option 1.
- D-GOLD (found after opening dev): dev gold excludes appositive-relative
  frames that the 264 panel counts correct; absolute wrong-save numbers
  are inflated for all arms alike. Reported raw + category split; no
  re-scoring, no hand fixes.
- Compute: BensPC RTX 5070 Ti, GPU idle at start (282 MiB). llama-server
  started detached via Win32_Process with 264's exact flags (PID 15380,
  /health ok). Ear run + C1 (155 calls) + C2 (465) + C3 (155) sequential,
  each wave under 15 min. Server stopped by exact PID (needed taskkill /F
  as in 264 D7); GPU back to 282 MiB idle; no llama-server tasks remain;
  pythonw 13036 untouched. Mac load was ~112 during Mac-side steps, but
  all Mac work was seconds-long plumbing/scoring (no heavy Mac suite).

## What it means (plain high-school English)

On the same 155 ear readings: the YES/NO checker kept everything good
and caught almost nothing bad (90 good kept, only 2 of 65 bad caught) --
on cleanly worded turns it is a rubber stamp. The question checker
caught nearly all the truly bad readings (23 of 25) but also threw out
14 good ones -- it is strict in every direction. The pick-one-of-four
checker kept plain facts almost perfectly but blanked on every plural
turn, always picking the other name -- one extra name in the turn breaks
it. Most of the "bad" readings all three keepers kept are sentences that
are actually true (like stating who someone's sister is); only this dev
set's answer key calls them wrong.

## What it doesn't mean

It does not mean the YES/NO checker is useless: on the blind 264 panel
it held back real check-questions and pretend turns; this dev set just
does not contain wordings that trigger it. It does not mean the question
checker wins overall: its 14 lost good readings are the same disease
that failed it in 264. It does not mean pick-one-of-four is hopeless:
outside plural turns it matched the YES/NO checker (74 vs 90 is all
plural + a few holds) at one third of the question checker's time -- but
it needs a fix for multi-name turns first. Nothing here changes 264's
registered FAIL.

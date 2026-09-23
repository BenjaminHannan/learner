# Exp 241b RESULTS: the mouth, stage A v2 (BUILD half)

**Verdict: BUILD HALF DONE, two flags for the director.** M2 (a, b, c),
M3, M5-latency, the sleep smoke and the mechanical M1 sub-marks pass.
M1-grader and M4-judge are unscored by design (the builder never grades;
the director launches fresh graders and a fresh judge). Two misses to
report: (1) the M5 suite wall is +8.1% over 228, above the +5% bar,
measured at extreme machine load (160-220, deviation D-B); (2) the S1
script exits 1 on 241b's own fresh rows with 22 listed confirm-decision
diffs, all of the intended article/case kind, with verdict-level identity
at 100% (details below; the director judges S1).

**Seals (both re-verified after the last run, 23/23 OK, 0 mismatches):**
- SEAL.sha256.txt: 19 files (PASSMARKS.md, say_forms.json, 17 scripts).
- SEAL2.sha256.txt:
  - sweep.jsonl 6c837ee3760ca5547c5ea01c9fb28a587bee20232d88c10b424294b90932b79e (1205 replies)
  - sweep-frames.jsonl 5ee5c793903bcaeb23d4106187e718dc547e411774aee3024a5bfe8dbf6f4bed
  - pairs.jsonl 9f4534880f021c39024ef997272f27832e87b43d057393fd5407bd6f6e893e64 (120 pairs)
  - pairs-key.jsonl f763b6dd2b011a485f974d77885a3e065a282453a1be3cbf9ef497fbe7238d54
- Nothing sealed was changed and nothing was re-sealed.

## Marks (integer counts)

| mark | bar | result | pass |
|---|---|---|---|
| M1 overall (grader) | ≥ 99.0% | not scored (director's grader pending) | pending |
| M1 per act (grader) | ≥ 97% each | not scored | pending |
| M1 mechanical sub-marks (6 S + 22 C) | 0 each | 0 in all 28 on the fresh sweep | yes |
| M2(a) sweep faithfulness | 0 | 0 unfaithful / 1205; 0 sev-1; 0 rule-9 fails | yes |
| M2(b) suite parse-back | 0 | 0 failures / 7646 lines (A 7268, passthrough 378, legacy 0) | yes |
| M2(c) notebook events | 0 | 1016/1016 logs identical normalised (raw 0/1016, as base vs base) | yes |
| M3 frozen suites | only predicted moves, GATE clean | GATE clean; 752 moves, all reply-only; 0 verdict changes; 0 abstain flips | yes |
| M4 naturalness | win ≥ 70% non-tie, loss ≤ 10% | not scored (director's judge pending; 120 pairs sealed) | pending |
| M5 latency | median ≤ 2 ms, p99 ≤ 20 ms | median 0.172 ms, p99 1.111 ms, max 2.056 ms (n = 1205) | yes |
| M5 suite wall | 241b ≤ 228 + 5% | median 45.5 s vs 42.1 s (limit 44.2 s), +8.1% | **no** |
| S1 anchor identity | 100% verdict identity | verdicts 100% (2400/2400 rows); script lists 22 confirm-decision diffs on 241b's own rows (all intended; 0 verdict diffs) | director judges |
| sleep smoke | identical to 228 | identical on every field except agent/label/seconds | yes |

M5 walls (D6 protocol, alternating runs; 1-min load 160-220 throughout):

| agent | run 1 | run 2 | run 3 | median |
|---|---|---|---|---|
| 228 | 42.1 s | 40.7 s | 44.3 s | 42.1 s |
| 241b | 42.8 s | 47.1 s | 45.5 s | 45.5 s |

Mouth render cost in the registered suite runs (per-line): run1 sum
2.22 s, run2 2.37 s, run3 2.37 s over 7646 lines (mean 0.30 ms/line,
median 0.19-0.20 ms). Base line cost ≈ 5.5 ms/line, so the +5% budget
allows ≈ 0.28 ms/line. The run-to-run spread (228: 3.6 s, 241b: 4.3 s)
is wider than the 3.4 s median gap, so load noise dominates, but the
mouth mean cost alone sits just above the budget.

## Moves (M3, registered 241b run 1 against 138i; every one reply-only)

By suite: rt136 45, rt143 24, sessions152 60, bench 623. Every move shows
new WRONG 0, new WRONG-WRITE 0, junk write 0, lost OK 0, write change 0.
Changed reply lines by act (all route A, all pre-registered): SAVED 3953,
CONFLICT 721, ANSWER 673, ABSTAIN_MISSING 7. Per-line record:
runs/mouth241b-run1.log; diffs: runs/out241b-run1/.

## Every miss / flag

### M5 wall: +8.1% (miss)
Medians 45.5 s vs 42.1 s against a 44.2 s limit. P241b.3 predicted
within +5% (p ≈ 0.8): wrong on the number. Diagnosis: mouth render sums
2.2-2.4 s of the 3.4 s gap (mean 0.30 ms/line vs ≈ 0.28 budget); the
rest is load noise (spread > gap). 241's wall was +17% with ≈ 1 ms/line,
so rule-7 caching removed roughly four-fifths of the structural cost.

### S1: script flag, verdicts 100% (director judges)
- reg228 rows (frozen): 800 v3 rows, 721 needle replies, 0 differences.
  PASS, exit 0.
- dev 241 rows (frozen): 800 v3 rows, 721 needle replies, 0 differences.
  PASS, exit 0.
- reg241b rows (new version live): 800 v3 rows, 0 verdict re-classify
  diffs, but 22 confirm-decision diffs on 11 items, exit 1. Every one is
  the intended kind: the reply renders the value with article/capital
  ("change it to the United Kingdom?") while the taught sentence has the
  bare form ("citizen of United Kingdom"); frozen says no, NEW-1 says
  yes. All 11 items are verdict 'correct' in BOTH the 228 run (frozen)
  and the 241b run (new), with equal confirms counts per item
  (bench132-4hop-197, bench65-mquake-028/036/064/065/066/072,
  bench121-4hop-177/189, bench103-s2fresh-4hop-019/033).
- Verdict-level identity: 2400/2400 rows (800 + 800 + 800) give the same
  verdict under both versions; 0 verdict differences anywhere; M3 shows
  0 verdict changes on the same runs.

### Report-only: 241 sweep re-rendered through A v2 (42 old misses)
All 42 old misses mechanically "changed", 0 sub-mark hits, all 1205
frames route A (full table: rer241.json). Whether each grader complaint
is gone is NOT judged here. Changed vs 241 by act: SAVED 1, CONFLICT 20,
FORGOTTEN_ONE 67, BROKEN_CHAIN 80, YESNO_NO 3, YESNO_NOTKNOWN 2,
ANSWER_LIST 6, AMBIGUOUS 30. Examples: "…change it to shethgean?" became
"…change it to Shethgean?"; "…, which is not someone I can look up."
became "…. I have nothing saved about that, so I can only follow the
chain this far."; "rowing and rowing" became "rowing"; "(E0012)" codes
are gone where full names differ.

### Report-only: rerender238
41,759 distinct harvest replies (2,788,212 occurrences); 13,072 changed
(1,379,141 occurrences). Line routes: A 38,729 (2,370,538 weighted),
passthrough 2,947 (417,510), legacy 83 (164). Changed lines by act:
SAVED 8659, ANSWER 3191, CONFLICT 854, FORGOTTEN 163, ABSTAIN_MISSING
161, BROKEN_CHAIN 28, others ≤ 7. Files: rerender238.jsonl,
rerender238-summary.json.

### Other registered outputs
- Fresh sweep (SEED241B = 241092283): 1205 replies, all route A,
  0 unused say rows, 30 AMBIGUOUS, strata exactly as registered.
- Fresh pairs (PAIRS_SEED241B = 241092297): 24 dialogs, 792 logged
  lines, 120 pairs in 17 act strata (thin strata took all available:
  REVERSE 4, SELF_ANSWERED 1, YESNO_YES 1, YESNO_NO 3, YESNO_NOTKNOWN 4;
  SELF_SLEPT 8). 241b is X in 63 of 120. No side-identifying keys in
  pairs.jsonl (checked).
- Unit tests 29/29 under the uv prefix. Say table rebuild byte-identical.
- 0 sev-1 on suites; unframed 378; ambiguous_identical 0 on suites.

## Deviations
1. **D-A (load):** the registered wall runs ran at 1-minute load 160-220
   (OPUS-RULES says wait while above 60). Two waits (2 + 3 min) saw load
   rise 124 → 163, so the alternating D6 protocol was run and every wall
   is reported with its load. Each run stayed far under 25 minutes
   (40-48 s suites, ~2 min sleep smokes).
2. **D-B (S1 script):** as above; the 22 diffs are listed in
   runs/s1-241b.out. No verdict difference exists, so nothing was
   re-run or re-sealed.
3. No other deviation: no sealed file changed (23/23 OK at end), no
   re-seal, no driver-only fix, no unpredicted move, no flake re-run
   (0 flips toward abstain, so no 5× re-runs were needed).

## Predictions (ledger P241b.n)
- **P241b.1** M2 0 failures: right (0/1205, 0/7646, 1016/1016).
- **P241b.2** M3 as predicted: right (GATE clean, 45/24/60/623, 0 verdict
  changes, 0 abstain flips; act counts match 241 exactly).
- **P241b.3** latency: right. Wall within +5%: wrong (+8.1% at high load).
- **P241b.4** sub-marks 0: right on the fresh sweep (28/28 zero).
- **P241b.5** M1 grader: pending (director).
- **P241b.6** M4: pending (director).
- **P241b.7** sleep identical: right.
- **P241b.8** 0 sev-1, 378 unframed, 0 ambiguous_identical: right.
- **P241b.9** S1 100%: verdict-level right (2400/2400); script exit 1 on
  241b's own rows with 22 listed intended diffs.

## What it means
- Stage A v2 changes only reply text: 0 verdict changes, 0 notebook-event
  changes, 0 unfaithful renders across 1205 fresh sweep lines and 7646
  suite lines.
- All 42 of 241's grammar misses were reworded by the fixes, with zero
  mechanical complaints left on them or on the fresh sweep (28/28 zeros).
  Whether the human graders agree is still open.
- The new 172b scorer version agrees with the frozen one on all 1600
  old-version rows and changes no verdict anywhere; its only behavior
  difference is 11 intended extra "yes" answers, each on a 'correct' item.
- Rule-7 caching cut the mouth's suite cost from ≈ 1 ms/line (241, +17%
  wall) to 0.30 ms/line mean — but the +5% wall bar was still missed at
  +8.1% under extreme load.

## What it does not mean
- It is not a PASS: the wall bar missed, M1 and M4 are unscored, and S1
  needs the director's ruling on the 22 listed diffs.
- The grammar fix is not proven until the director's graders score the
  fresh sweep; mechanical zeros are a machine check, not English judgment.
- The wall number is not a clean lab measurement: at load 160-220 the
  run-to-run spread exceeds the gap, so +8.1% mixes real cost (≈ 0.30
  ms/line vs ≈ 0.28 budget) with noise.
- M4 pairs are single replies with no dialog context from one fictional
  run, so they say nothing about conversation-level naturalness.
- Results cover fictional names and the 150-relation say table only.

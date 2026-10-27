# Exp 241 RESULTS: the mouth, stage A

**Verdict: FAIL.** M1 (grammar) and the M5 suite-wall bar missed. M2 (a, b, c), M3, M4, M5 latency and the sleep smoke passed. There was no SCHEMA-MISMATCH, so the run is not VOID.

**Seal:**
- SEAL.sha256.txt was written at 17:19 EDT on 2026-09-22 and covers 15 files.
- SEAL2.sha256.txt covers the sweep, the sweep frames, the pairs and the pairs key.
- Both were re-verified before scoring, with 0 mismatches.
- Nothing sealed was changed and nothing was re-sealed.

**Marks and grading:**
- Bars are defined in PASSMARKS.md.
- The grader and judge were launched by the director, not by me:
  - grades: artifacts/claude-grade241-20260922/m1-grades.jsonl, sha256 18fc62c2…7635
  - judgments: artifacts/claude-judge241-20260922/m4-judgments.jsonl, sha256 b202a0e2…091df
- Scored with the sealed scripts/claude_mouth241_score.py. Output: score241.json and runs/score.out.
- The grader used the director's style sheet (briefs/241-stylesheet.txt), not PASSMARKS §6.

## Marks

| mark | bar | result | pass |
|---|---|---|---|
| M1 overall | ≥ 99.0 % | 1163/1205 = 96.51 % | **no** |
| M1 per act | ≥ 97 % each | CONFLICT 60/80 (75.0 %), BROKEN_CHAIN 63/80 (78.75 %); all other 20 strata ≥ 97 % | **no** |
| M1 mechanical sub-marks (6 + 17 covered 238 classes) | 0 each | 0 in all 23 | yes |
| M2(a) sweep faithfulness | 0 | 0 unfaithful / 1205; 0 sev-1; 0 rule-9 anchor fails | yes |
| M2(b) suite parse-back | 0 | 0 failures / 7646 lines (A 7268, passthrough 378, legacy 0) | yes |
| M2(c) notebook events | 0 | 1016/1016 logs identical after normalising (raw 0/1016, as base vs base; D1) | yes |
| M3 frozen suites | only predicted moves, GATE clean | GATE clean; 752 moves, all reply-only; 0 verdict changes; 0 flips toward abstain | yes |
| M4 naturalness | win ≥ 70 % non-tie and loss ≤ 10 % all | 111 win / 9 lose / 0 tie: 92.5 % and 7.5 %; meaning-change flags 0 | yes |
| M5 latency | median ≤ 2 ms, p99 ≤ 20 ms | median 1.134 ms, p99 4.559 ms, max 40.750 ms (n = 1205) | yes |
| M5 suite wall | 241 ≤ 228 + 5 % | median 50.4 s vs 43.1 s (limit 45.3 s), +17 % | **no** |
| sleep smoke | identical to 228 | identical on every field except agent/label/seconds (both: sleeps 1, installed 1, episodes 20, probes 5/5, wrong 0, abstain 0, broken=abstain, taught 50/50, overwritten 0) | yes |

M5 walls (D6 protocol, alternating runs):

| agent | run 1 | run 2 | run 3 | median |
|---|---|---|---|---|
| 228 | 43.1 s | 43.2 s | 39.7 s | 43.1 s |
| 241 | 50.4 s | 50.3 s | 51.2 s | 50.4 s |

The load average was 18–30 throughout, caused by other agents.

## Moves (M3, registered 241 run 1 against 138i; every one is a reply-only move)

**By suite:**

| suite | moves |
|---|---|
| rt136 | 45 |
| rt143 | 24 |
| sessions152 | 60 |
| bench | 623 |

Every move shows new WRONG 0, new WRONG-WRITE 0, junk write 0, lost OK 0 and write change 0.

**Changed reply lines by act** (all route A, all in the pre-registered act list):

| act | changed lines |
|---|---|
| SAVED | 3953 |
| CONFLICT | 721 |
| ANSWER | 673 |
| ABSTAIN_MISSING | 7 |

No other act changed on the suites. The per-line record is in runs/mouth241-run1.jsonl, and the per-suite diffs are in runs/suitediff-241-run1/.

These counts are the same as the pilot's (pilot 241d).

## Every miss

### M1: 42 lines the grader marked ungrammatical

**CONFLICT (20 misses).** Every one is the new value after "Do you want me to change it to", which A keeps verbatim (D9) so the bench v3 confirm needle still matches.
- 15 are lowercase proper-noun values (the sweep's "lower" filler class): s0141, s0142, s0143, s0144, s0146, s0147, s0148, s0149, s0150, s0151, s0156, s0157, s0158, s0159, s0160.
  - The 15 lowercase values include ones like "ludrerk books".
- 5 are count-noun values with no article: s0102 "euphonium", s0105 "electric van", s0153 "green van", s0154 "heron", plus s0101.
  - s0101 is "…is 6 years old. Do you want me to change it to 72?". The grader flagged the old-value clause as rule 3, but the underlying problem is the bare new value against an old value that has units.
- I declared this before the seal as a known risk (D9, and P241.5 named CONFLICT). The fix is outside sealed A. It needs either:
  - the 172b driver to match the value without regard to case or article, or
  - a confirm anchor that allows "the/a" and capitalisation.

**BROKEN_CHAIN (17 misses).** "…, which is not someone I can look up." follows a value that is not a person: a number, date, year, thing, address, code or adjective.
- Lines: s0495, s0508, s0510, s0513, s0518, s0521, s0522, s0524, s0525, s0536, s0537, s0539, s0541, s0543, s0544, s0547, s0558.
- A keeps this phrase because it is a scorer anchor. It is in 224a's DECLINE_MARKERS224 and bench ABSTAIN_PHRASES ("which is not someone i can look up"), and "not someone" is in rt143 (rule 9).
- I did not predict this miss. The grader's style sheet did not exempt it.
- The fix needs a registered change to those anchors (owner: 224c / scorer owners), then an A form such as "…, and I can't look anything up from that."

**FORGOTTEN_ONE (2 misses):**
- s0248 "noodles is the favorite food of …": a plural-looking mass-noun value with "is".
- s0303 "the Quiet Tide is your notable work": a title's leading "The" was lowercased by the value-article path.
- Both are real A defects.

**YESNO_NO (1) and YESNO_NOTKNOWN (2): the same item repeated in a list.**
- s0657 "rowing and rowing", s0753 "an abacus and an abacus", s0756 "an iguana, an iguana and an iguana".
- These come from a sweep-generator defect: it drew duplicate multi-values, which a real notebook would not store twice. The legacy line has the same repetition. They count as misses all the same.
- The director notes that the grader parts disagreed on this class.

### M4: the 9 losses (the judge preferred the base)

- **"Saved: You live in X." against "Saved: your city is X." (3 losses: p017, p049, p073).** The judge disliked the capital after the colon.
  - The 238 class LOWERCASE_START requires that capital, so the two graders' preferences conflict here.
- **The "of" form with multi-word names (5 losses):**
  - BROKEN_CHAIN, 4 losses: p020, p029, p040, p047, e.g. "The city of Griotuth Krortulx is …".
  - ANSWER, 1 loss: p113.
  - The judge preferred the direct possessive. A uses the of-form for these, so the choice is too aggressive.
- **p117 ABSTAIN_MISSING: "I don't know the cousin rollrill trifork of Drumioth Theallbreus."** The base parsed a lowercase multi-word name as part of the relation, and A's of-form makes the garble more visible.
  - This is a real A weakness: A renders a relation phrase that is not a known noun.

### M5 wall

- **Diagnosis:** A's render time summed over the 7,646 suite lines is 7.2 s (in-suite median 0.94 ms, p99 2.07 ms). That covers the whole 7.3 s gap between the medians.
- **Why the two bars conflict:** the suites do about 5.6 ms of base work per reply line, so a +5 % wall budget allows about 0.3 ms per line. The latency bar (median ≤ 2 ms) and the wall bar cannot both pass at A's current cost.
- **What would fix it:** a cheaper rule 7, for example caching reader results per frame, or skipping the reader for rows whose forms were already round-tripped when the say table was built.

## Other registered outputs

**Sweep** (sealed seed): 1205 replies, all route A, 0 unused say rows. See runs/sweep.out.

**Pairs** (sealed seed): 24 dialogs, 792 logged lines, 120 pairs in 15 act strata.
- Strata with fewer than 9 available lines took all they had: BROKEN_CHAIN 8, REVERSE 4, SELF_ANSWERED 4 and YESNO_NOTKNOWN 6. SELF_SLEPT got 8 of its 24 because the round-robin reached 120 pairs first.
- 241 is X in 55 of 120 pairs.
- The pairs file has no side-identifying keys.

**(e) rerender238** (report-only, post-seal; script scripts/claude_mouth241_rerender238.py, not sealed):
- Scale: 41,759 distinct 238-harvest replies (2,788,212 occurrences); 13,048 changed (1,378,889 occurrences).
- Lines by route:

| route | lines | weighted by count |
|---|---|---|
| A | 38,730 | 2,370,686 |
| passthrough | 2,946 | 417,362 |
| legacy (sev-1) | 83 | 164 |

- The 83 sev-1 lines are lines the parser framed but every candidate failed the brake, so the legacy text was kept. They include "You told me: …", "…, but I don't know X's city.", "OK, X's boss is not Y. I still have Z." and "Saved: X's pet is probably Rex."
- The harvest has no notebook records, so a live run may render some of these differently.
- Top change: "Saved: United States of America's capital is Washington, D.C.." became "Saved: The capital of the United States of America is Washington, D.C." (81,306 occurrences).
- Also visible in the re-render: "director of The Beatles's officeholder" became "The officeholder of director of The Beatles". This is a relation-phrase residue that 242 / table growth owns.
- Files: rerender238.jsonl and rerender238-summary.json.

## Deviations

1. **The first registered suite pass was aborted.** In the first run script (scratchpad reg241/run.sh), bash's `python3` pointed to a binary that would not run on this Mac, so no wall times were recorded.
   - I stopped it after 228 run 1 had finished (GATE clean, 0 moves, 40.0 s) and while 241 run 1 was still in progress, before it printed any output.
   - I restarted the whole protocol in reg241b with a perl timer. All reported numbers come from reg241b.
   - No 241 result was seen before the restart, and none was discarded.
2. **The grader's style sheet was the director's own, not PASSMARKS §6.** The director reports that entity ids were allowed anyway. Lowercase proper-noun values and "someone" for non-person values were marked as errors. Under PASSMARKS §6 item 7 ("echoed as stored"), the 15 lowercase CONFLICT lines might have been judged differently. I did not re-grade anything. The M1 result stands as scored.
3. **The sweep generator produced 3 duplicate-value lists.** This is a generator defect, not an A rendering choice. The lines count as misses.
4. **Report-only additions after the seal:** the rerender238 script, and the runs/ copies of the check outputs.

## Predictions (ledger P241.n)

- **P241.1** M2 0 failures: **right**.
- **P241.2** M3 GATE clean, reply-only: **right**.
- **P241.3** M5 latency passes: **right**. Wall within +5 % (p ≈ 0.7): **wrong** (+17 %). The cause is structural, not load.
- **P241.4** mechanical sub-marks 0 (p ≈ 0.8): **right**.
- **P241.5** M1 passes (p ≈ 0.45): it **failed**. CONFLICT was named as a risk and was right. BROKEN_CHAIN, the second failing stratum, was not predicted.
- **P241.6** M4 passes (p ≈ 0.65): **right**. 92.5 % is well above the bar.
- **P241.7** sleep smoke identical: **right**.
- **P241.8** 0 sev-1 on suites, 378 unframed lines: **right**.

## What it means

- Stage A changes only reply text. There were 0 verdict changes, 0 notebook-event changes and 0 unfaithful renders across 1,205 sweep lines and 7,646 suite lines.
- A blind judge preferred A's wording in 111 of 120 pairs.
- A cleared all 23 mechanical checks for the 238 bug classes it covers.
- All remaining grammar misses fall into three groups:
  - two anchor-bound phrasings that rule 9 deliberately protects (CONFLICT's verbatim new value, and BROKEN_CHAIN's "not someone");
  - two small A defects (a mass-noun "is", a title's "The");
  - a sweep-generator artifact.
- The cost of A is about 1 ms per line, which makes the suites about 17 % slower.

## What it does not mean

- It is not a pass, and A is not ready to be the live mouth under these bars.
- M1 cannot be passed by changing A alone. The two failing strata need a registered scorer / driver anchor change first (owners: 224a/224c decline markers, rt143, the bench abstain list, the 172b confirm needle).
- M4 was judged on single replies with no dialog context, from one fictional 241 run, so it says nothing about conversation-level naturalness.
- The grammar results are for fictional names and the say table's 150 relations only. Relations and phrasings outside the table pass through unchanged and were not graded.
- The rerender238 figures are indicative only: no records, not graded.

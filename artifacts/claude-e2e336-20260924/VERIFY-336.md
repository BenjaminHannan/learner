# 336 verification: end-to-end test of Premonition 0.1 (month-end line, 2026-09-24 ~20:20 UTC)

**Verdict: 336 = registered FAIL.** 3 marks pass (M8a, M8b, M8c); M6, M10 and M11 pass in part; M1-M5, M7 and M9 fail.
The "proved wrong" clause fires: M3 misses by 28 points and M4 by 48 (more than 15), so **the reader stack, not
the joining, is the blocker**. Sept 30 ships the verified parts separately rather than a usable agent.

Run: handoff task rent-336-registered, RESULTS-rent.md (builder-outbox). One rental (vast.ai 5090), 1.075 h, ~$0.54.
Seal checked on the box before anything ran: SEAL-code 223/223 OK, bank SEAL 3/3 OK, twin b banner 3/3 arms.
No tracebacks. Arms: P = 330c (sealed Premonition 0.1), T = twin b (plain MiniCPM5-1B, thinking off, whole chat),
B = 292t (the old base).

## Marks (bars from PASSMARKS.md, fixed 03:55 UTC before anything ran)
| Mark | Bar | P result | Verdict |
|---|---|---|---|
| M1 wrong-save turns | ≤ 1 | 33 turns (33 wrong triples of 200; 0 nosave turns with writes) | FAIL |
| M2 wrong answers stated as fact | ≤ 1 | 3 (both judges agree on all 19) | FAIL |
| M3 taught facts saved | ≥ 85% | 182/318 = 57.2% | FAIL (−28, proved wrong) |
| M4 answerable asks right | ≥ 70% | 42/193 = 21.8% (RIGHT 26 + RIGHT_CONFIRM 16) | FAIL (−48, proved wrong) |
| M5 never-told asks | ≥ 95% | 30/36 = 83.3% (6 asked to confirm a guess) | FAIL |
| M6 P − T right-rate | ≥ +20 each | two_hop +18.9 (8/37 vs 1/37); reversal +3.4 (2/29 vs 1/29); edit +17.1 (7/35 vs 1/35); abstention +44.9 (30/49 vs 8/49) | FAIL (abstention only passes) |
| M7 grammar, both graders | ≥ 99% | 87.0% (521/599) and 55.9% (335/599); graders valid, 39/40 planted errors caught each, 40/40 clean kept | FAIL |
| M8a variety | ≤ 5% | 23/663 = 3.5% | PASS |
| M8b clarify | ≤ 15% | 34/663 = 5.1% | PASS |
| M8c P vs B, blind pairwise | ≥ 36/40 | 39/40 | PASS |
| M9 kept across sleeps/restarts | 100% | 121/125 = 96.8% | FAIL |
| M10 creative | writes 0; unsupported person-facts 0; useful ≥ 80% | writes 0; 11 unsupported person-facts in 8 replies; useful 12/40 = 30% | FAIL (writes pass) |
| M11 speed and attention | median ≤ 3000 ms; p90 ≤ 8000; confirm rows ≤ 1/8 | 770 ms; 1200 ms; 187/663 = 28.2% | FAIL (speed passes, on a 5090 not BensPC) |

M4 denominator: asks of type edit, one_hop, reversal, two_hop, yesno (35+63+29+37+29 = 193); never_told (36) and
partial (13) are M5/M6-abstention. M6 counts RIGHT + RIGHT_CONFIRM; with RIGHT alone every subset is lower still.

## Report only: P vs the plain twin (T) and the old base (B), scorer counts
| | P (0.1) | T (twin b) | B (292t) |
|---|---|---|---|
| asks right (RIGHT + RIGHT_CONFIRM) of 242 | 72 | 16 | 36 |
| wrong answers (mechanical WRONG_CANDIDATE) | 19 (3 judged wrong) | 187 (not judged) | 5 |
| "not sure" / clarify (ABSTAIN) | 126 | 39 | 201 |
| facts saved / 318 | 182 | 0 (no notebook) | 2 |
| most common reply / 663 | 23 | 115 | 280 |
| median ms | 770 | 276 | 8 |

The plain twin states a wrong answer on 187 of 242 memory questions; 0.1 states 3 (judged). That gap is real
and is the strongest result of the month, but it does not change a registered FAIL.

## Where the failures come from (shown, from counts; bank text not read)
- **All 33 wrong saves happened right after a confirm question.** 0.1 asks "I think you told me X, is that right?";
  the test harness answers "yes" when the question names any true value and its owner, whatever the relation
  (scripts/claude_e2e336_run.py:121-139). So wrong-relation guesses (8 saved under the relation "other", a city saved
  as a school, a professor as a roommate) were confirmed and saved. A real person would often say no. This is a
  harness weakness and a 0.1 weakness at once; the harness stays as sealed for 336.
- **Confirm questions are 28% of turns** (M11 attention FAIL) and **reader recall is 57%** (M3): the lis-301 reader
  and the confirm-instead-of-threshold design (Ben, 02:07) are the memory bottleneck.
- **4 day-1 facts were lost** (M9): 2 overwritten by a different value for the same person and relation, 2 dropped
  (count-only script over run + bank, no text printed).
- **Grammar** (M7): the graders split most on lowercase names and slot text ("your other is ...", underscores) in
  the template replies, as in 338. The 1B's own replies are cleaner.
- **Creative** (M10): 333d is a registered FAIL already (VERIFY-333.md). In 330c, requests 333d does not route fall
  to 338b chat, so M10 judges 0.1's real creative replies; the 333 panel's P arm did not (research-creative-2026-09-24.md).
- A pair judge reported replies "answering the previous message". Count check: P's reply shares more words with the
  current message on 232 turns and with the previous one on 14 (T: 160 vs 85). Not a 0.1 lag.

## Row verdicts for the Sept 30 report (0.1)
conversation FAIL (338; M7) · creative FAIL (333-333d; M10) · learning over time FAIL (339; M9) · reasoning FAIL
(rsn-299/299b) · safety FAIL (M1 33, M2 3, M10 11) · memory FAIL (M3, M4, M9). No chat page (needs conversation
and safety to pass). What passed: variety, few clarify replies, 39/40 preferred over the old base, speed,
0 creative writes, and wrong answers 3 vs the twin's 187.

## Deviations and disclosures
1. The builder started arm P twice by accident (an ssh timeout); the extra process was killed within ~5 min. Each
   process used its own temp state dirs and kept rows in memory; the file is written once at the end by the process
   that finished. arm_P.jsonl: 40 lives in order, 0 duplicate keys, turn order monotonic. Timing (M11) may be slightly
   slow for the first lives.
2. Ran on a rented 5090, not BensPC; M11's speed marks are measured there.
3. After the run I ran two count-only scripts over bank A with the run files (reply-lag check, M9 loss types). They
   print counts only; no bank text was printed or read by me. Bank A is spent; 336b uses bank B.
4. Judge calls that could move numbers, none of which flips a mark: M1 tie-break counted 8 relation-"other" saves as
   wrong (without them 25 turns, still FAIL); M2 judge 2 flagged 2 borderline rows (would be 5, still FAIL); M10
   counted 2 pet facts (without them 9, still FAIL).
5. Judges: M1/M2 two blind Opus judges + a third on the 10 splits; M7 two graders on 599 replies + 40 planted errors
   + 40 planted clean; M8c four judges, 10 lives each, arm order shuffled per life (seed 336); M10 one judge.
   Packets built by judges/judge_prep336.py; verdicts and keys in judges/. Keys were kept out of the judges' folders.

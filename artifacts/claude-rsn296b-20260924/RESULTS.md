# rsn-296b results (builder report, 2026-09-24)

## Verdict: FAIL

Being told the answer after a miss did fix counting but did NOT teach comparing.
The registered idea-killer triggered: P296b.2 fails on both seeds (comparing 93/200 and
88/200 on generated episodes, bar 160). P296b.4 also fails seed 1 (226/298, bar 228).
P296b.1, P296b.3 and P296b.5 pass on both seeds.

## Training (plain arm, 30M params: 30938261, 6000 copy + 6000 practice steps, --workers 6)

| run | minutes | copy loss first -> last | practice reward first -> last |
|---|---|---|---|
| plain-s1 (seed 1) | 34.1 | 4.1244 -> 0.0020 | 0.6426 -> 0.9602 |
| plain-s2 (seed 2) | 33.3 | 4.1609 -> 0.0010 | 0.6631 -> 0.9724 |

## Marks (checked answers, finals; integer counts)

| mark | bar | seed 1 | seed 2 |
|---|---|---|---|
| P296b.1 invented, fresh | <= 2 | 0 PASS (raw 5, check fixed all; missing_fact checked 30/30) | 0 PASS (raw 5, check fixed all; missing_fact checked 30/30) |
| P296b.1 invented, transfer | <= 2 | 0 PASS (missing_fact checked 30/30; raw 0) | 0 PASS (missing_fact checked 30/30; raw 0) |
| P296b.2 diag counts 1-7 /200 | each >= 160 | 200/200 PASS | 200/200 PASS |
| P296b.2 diag comparing /200 | each >= 160 | 93 FAIL | 88 FAIL |
| P296b.3 fresh counting+comparing /60 | >= 40 (296: 28, 28) | 29+13=42 PASS | 29+16=45 PASS |
| P296b.4 fresh total /298 | >= 228 | 226 FAIL (miss by 2) | 230 PASS |
| P296b.5 fresh code-doable /178 | >= 168 | 170 PASS (30+30+30+30+20+30) | 170 PASS (30+30+30+30+20+30) |
| P296b.5 transfer total /300 | >= 228 (296: 238) | 261 PASS | 255 PASS |

Code-doable = one_step, two_step, backwards, yes_no, newest_correction (n=28), missing_fact.
OVERALL: FAIL (P296b.2 both seeds, P296b.4 seed 1). Copy-only checkpoints (for context, no bar):
fresh 178/298 (s1), 177/298 (s2); transfer 204/300 (s1), 206/300 (s2); invented after check 0 on all 8 evals.

## Fresh panel by category, finals (checked_right/n)

| category | s1 | s2 |
|---|---|---|
| backwards /30 | 30 | 30 |
| before_after /30 | 14 | 15 |
| comparing /30 | 13 | 16 |
| counting /30 | 29 | 29 |
| heldout_three_step /30 | 0 (30 idk) | 0 (30 idk) |
| missing_fact /30 | 30 | 30 |
| newest_correction /28 | 20 | 20 |
| one_step /30 | 30 | 30 |
| two_step /30 | 30 | 30 |
| yes_no /30 | 30 | 30 |
| TOTAL /298 | 226 | 230 |

## Transfer panel by category, finals (checked_right/n)

| category | s1 | s2 |
|---|---|---|
| backwards /30 | 30 | 30 |
| before_after /30 | 18 | 17 |
| comparing /30 | 18 | 13 |
| counting /30 | 30 | 30 |
| heldout_big_notebook /15 | 15 | 15 |
| heldout_three_step /15 | 0 (15 idk) | 0 (15 idk) |
| missing_fact /30 | 30 | 30 |
| newest_correction /30 | 30 | 30 |
| one_step /30 | 30 | 30 |
| two_step /30 | 30 | 30 |
| yes_no /30 | 30 | 30 |
| TOTAL /300 | 261 | 255 |

## Diagnosis, finals (generated episodes only, checked; --n 200)

Counts 1-7: 200/200 on both seeds (s1: 35+24+34+19+28+36+24; s2 identical buckets).
Counts 8-12 (never practised): 0/200 on both seeds (all wrong, 0 idk).
Comparing: s1 93/200 (12+42+16+6+11+3+3), s2 88/200 (15+31+9+12+15+3+3) - both far below 160.
Before/after: s1 72+40+23+62+25+12=234/400 buckets; s2 71+29+5+62+6+0=173/400.
Dated-2 rows are perfect (134/134 s1, 133/134 s2); dated-3/4 collapse, worse on s2.

## Moves, misses, deviations

- Rental 1/1: vastai offer 43165153 (RTX 5090, 32 effective cores, $0.4727/h, reliability 0.9952),
  instance 52383936 labelled rsn-296b, ~1.3 h, ~$0.60 total spend. No re-rents, no guard trip.
  Credit before: $5.63 (above $4 floor). No duplicate instance at start.
- Seals: SEAL-code (7 lines), reasonpanel296 SEAL-v2, reasonpanel294 SEAL-v3 all OK via sha256sum -c
  before training. 4 checkpoint hashes sealed to SEAL-run.sha256.txt after training, before eval;
  post-copy hashes match the seal exactly.
- Evals: exactly 8 (4 checkpoints x 2 panels) + 2 diags, once each. Panel items never opened or read;
  only category-level count JSONs were handled.
- DEVIATION 1 (environment, code untouched): image torch 2.4.0/cu121 has no sm_120 kernels for the
  5090 (pilot crashed with "no kernel image available"); installed venv torch 2.11.0+cu128+numpy
  on the instance and ran everything in it. Sealed code files never edited or patched.
- DEVIATION 2 (filenames only, no re-eval): evals wrote panel296-copy_only.json / panel294-copy_only.json;
  renamed to panel296-copy.json / panel294-copy.json with mv to match the task's <copy|final> names.
- DEVIATION 3 (client-side only): two ssh commands timed out under load, but both training runs were
  already launched under setsid/nohup and survived (s1 from 09:21, s2 from 09:23 UTC); no run restarted.
- Pilot: 100 copy + 50 practice steps in 0.3 min -> estimated ~26 min/full run; actual 34.1/33.3 min
  for both in parallel (about 44 min wall). Under the 90-min / $3.00 gate.
- LESSON honored: all of W/ (8 result JSONs, 2 diag txt, 2 logs, 2 summaries) plus the 4 checkpoints
  copied back and hash-checked BEFORE the instance was destroyed. runs/plain-s1 and runs/plain-s2
  hold train_log.jsonl, train_summary.json, panel296-copy/final.json, panel294-copy/final.json,
  diag-final.json/txt. Checkpoints (4 x ~124 MB) at ~/premonition-models/rsn296b/<R>/.
  Instance destroyed and confirmed gone (0 live). Panel items read 0, sealed files edited 0.

## What this means / doesn't mean (plain high-school English)

- What it means: telling the model the right answer after a miss DID teach it to count things it
  practised (counts 1-7 went from "a few fixed numbers" to 200/200 on both seeds). But comparing two
  numbers did not improve at all (93 and 88 out of 200, basically the same fixed-pick failure as 296),
  and anything never practised (counts 8-12) is still 0. So the one change worked for counting and
  failed for comparing - and comparing is exactly the registered test of the idea. FAIL stands.
- What it doesn't mean: this does not say practice is useless - fresh counting+comparing rose from
  28 to 42/45 per seed and transfer totals (261, 255) beat 296's 238. It says being told the answer
  is not enough for THIS small network to learn comparing, which points at the network's design
  (architecture), not at more practice, as the next thing to question.
- The fact-check still catches every made-up answer (0 invented after the check on all 8 evals),
  and one/two-step, backwards, yes/no, missing-fact stay perfect (30/30 nearly everywhere).

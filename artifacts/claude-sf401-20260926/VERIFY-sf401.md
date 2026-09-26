# sf-401 verify: PASS (all six marks), as a hand-written baseline only

Written 2026-09-26 16:23 UTC (`date -u`) by the wrong-as-fact thread (0.2c row H1). Counts only; no panel text,
reply text, names or facts were opened by the builder. The 0.2c and 0.2d-r H1 verdicts are unchanged by this run.

## What ran
Registered run rent-sf401 on a vast rental (RTX 5090, instance 52762309), job report RESULTS-rent.md, rc 0.
A = 0.2c's joined assistant as 0.2d-r's X'. B = A + the stale-fact guard (scripts/claude_sf401_agent.py), nothing
else different. Panel: 24 fresh blind lives, 610 turns, 231 asks (74 edit), 70 corrections, 48 decoys; sealed
0136c8f7d before the run, seals checked on the rental (17/17 and 0.2c SEAL-code all OK).

## Checks done here
- Scorer re-run in the cloud (scripts/claude_e2e336_score.py on panel + run/arm_A, arm_B): mechanical.json and all
  six judge/grammar files byte-identical to the job's score/.
- Guard counters summed from run/sf401_counts_B.jsonl match the job report exactly.
- Judges: two blind Opus judges, JUDGE-sf401.md verbatim, each given only a copy of judges/asks.jsonl (36 packets:
  A 23, B 13, seed 4011). Each wrote 36 of 36 ids; agree on 36 of 36; 0 splits, so judges/j3.jsonl is empty
  (the marks script takes it as a positional argument).
- Diagnosis script: all 610 panel turns joined to B's events, 0 unmatched.
- Blind recount (RECOUNT-sf401.md): see below.

## Marks (scripts/claude_sf401_judges.py marks)
| Row | What | A | B | Bar | Result |
|---|---|---|---|---|---|
| M1 | judged wrong answers stated as fact, all asks | 8 | 2 | B <= A - 4 | PASS |
| M2 | right, control asks | 45 | 44 | B >= A - 2 | PASS |
| M3 | right, edit asks (of 74) | 21 | 32 | B >= A | PASS |
| M4 | "don't know", control asks | 67 | 68 | B <= A + 2 | PASS |
| M5 | judged wrong, control asks | 2 | 2 | B <= A + 1 | PASS |
| M6 | "don't know", never-told asks (of 20) | 20 | 20 | B >= A - 1 | PASS |
Valid: A has 6 judged-wrong edit asks (INCONCLUSIVE only below 5). Judged wrong split: A edit 6, control 2; B edit 0,
control 2.

## Report-only rows
- Guard (B): doubts by rule a 25, b 8, c 0; fired 17 (all confirm questions, 0 hedges); offers answered yes 16, no 1;
  cleared by a repeat 2, by "no" 1; explained_skip 0.
- Confirm questions asked (the user's attention cost): A 137, B 149 (+12), counted as user turns that asked one
  (each matched one to one by a confirm answer row). The marks script's "confirms" 143 and 155 also count 6 confirm
  answer rows per arm that carry confirm_asked; the difference is the same. In the test the runner answers them from
  the truth sheet, so a real user who answers wrongly or not at all is not measured.
- Guard fired on non-edit asks 4 times (one-hop 3, two-hop 1), each where A was right; control asks right in A but
  not in B: 5.
- Edit asks by correction style (scripts/claude_sf401_reportrows.py, written after the run, report only; asks;
  right A/B; judged wrong A/B): 1 own mistake, old named (12; 2/4; 1/0);
  2 own mistake, old not named (11; 1/3; 2/0); 3 real change, old named (13; 8/10; 0/0); 4 real change, old not named
  (12; 5/6; 0/0); 5 negation (13; 1/3; 1/0); 6 in passing (13; 4/6; 2/0).
- Decoy-checking asks (48): right A 14, B 13; "don't know" A 20, B 21; judged wrong 0 and 0.
- Facts saved A 295, B 305; new triples whose owner and value are not on the truth sheet A 14, B 15.
- ms per turn, median A 807.8, B 811.6; p90 A 1284.4, B 1293.0.

## Diagnosis (claude_sf401_diag.py, counts only)
- All 70 correction turns were framed by the reader (act not empty), but a doubt was raised at the correction turn
  on only 24 of 70 (by style 5, 3, 3, 5, 3, 5).
- A's 6 judged-wrong edit asks: 5 are asks where B's guard fired (B was not judged wrong on any), 1 where a doubt
  had been raised and cleared earlier. B has no judged-wrong edit ask.
- What is left is not stale answers but missing ones: B still gets 42 of 74 edit asks not right (28 "don't know",
  11 confirm of another value, 3 mechanical wrong candidates judged ok). The notebook mostly never gets the new value.

## Deviations (from the job report; none changes the comparison, both arms share each one)
1. The task's `--bank P` was run as `--bank artifacts/claude-sf401-20260926/panel` (P is the panel variable).
2. Runtime data the sealed code reads was streamed read-only from main (relation tables, abstain76, table237,
   nameval171b and small fable-* config dirs); no panel or bank dirs.
3. Container torch upgraded 2.2.1 -> 2.11.0+cu128 for the RTX 5090 and transformers 5.
4. The reasoner base (fable_reasoner44 --stage base --seed 4102) sha256 bc44f919... differs from 0.2c's 4655b761...;
   both arms used the same file, so A is not bit-identical to 0.2c's X'.
5. Arm A crashed four times before writing any row (bank path, two torch/torchvision import errors, a missing data
   file); the report text says "two" but lists four tracebacks. Output stayed empty each time; each arm measured once.
6. 3 rentals (2 destroyed under the 6-minute rule). EP382_LOG wrote nothing (the runner does not emit it).
7. Results first missed builder-outbox (task line "PUSH to builder-outbox:"); the Director's watcher fix 5f6119809
   republished them at 16:19 UTC. Cost is the job's own figure, about $1.27, not yet checked against the ledger.

## What this means
Plain words: when you correct a fact, the old assistant sometimes kept saying the old one. The extra checker asks
"you told me X before, is it still X?" when it notices a correction, and on 24 new test lives the wrong answers
stated as fact dropped from 8 to 2 without costing right answers elsewhere. It asked the user 12 more questions.

What it does not mean: the checker is a hand-written rule. Under Ben's Redirect (16:04 UTC) it is a baseline for
the learned route to beat, not a part for the next build; addendum 2's replication on top of lis-319k is off
because lis-319k failed. The bigger gap is that the assistant mostly never learns the new value (42 of 74 correction
questions still not answered right), which is the reader's and the memory answer's job.

## Blind recount (RECOUNT-sf401.md, one blind Opus agent, its own script, finished by 16:24 UTC)
Same numbers on every row: judged wrong all A 8, B 2; control 2, 2; edit 6, 0; control right 45, 44; edit right 21,
32; control "don't know" 67, 68; never-told right 20, 20. M1-M6 PASS; not INCONCLUSIVE (A edit judged wrong 6).
Panel asks 231: control 137, edit 74, never-told 20. Its checks: every ask joins one user row per arm; confirm answer
rows match confirm-asking user rows one to one (A 137, B 149); its WRONG_CANDIDATE asks are exactly the asks in
judge_asks_A/B (23, 13); all 36 packets map to one ask of their keyed arm and every packet's facts equal truth.jsonl
at that turn; j1 and j2 cover 36 ids each, 10 wrong each, 0 splits. It noted 6 confirm answer rows per arm with
confirm_asked set, which the scorer does not count.

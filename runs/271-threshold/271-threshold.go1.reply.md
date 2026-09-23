Building your QA checker and cutoff diagnostic — locking predictions before measuring.
I've got the background — the YES/NO checker rubber-stamped this dev set. Now I'll map the inputs to seal predictions.
264 is already sealed and recorded — my job is the 271 diagnostic. I'll reuse the sealed matching logic, then seal predictions before computing.
Now I'll check the sealed scorer's matching rules (read-only) so my labeling matches, then seal predictions before computing anything.
Predictions sealed. Appending the prediction ledger lines, then computing.
Rules confirmed. Writing the analysis script (new file, imports sealed modules read-only).
Strong separation found. Auditing the 40 relabeled frames for false-goods before writing the report.
All 40 relabels are genuine appositive frames. Pulling key cutoff rows for the report.
Verdict: YES — on the fresh 267 dev set, a cutoff on the YES/NO checker's score separates good ear frames from wrong ones (AUC 0.948, n=155).

Marks table (integer counts; diagnostic, no PASS bars):

| Item | Count |
|---|---|
| Frames scored | 155 |
| Good (90 gold-hit + 40 appositive-relative + 0 plural-fix) | 130 |
| Wrong (typo 13, trap 7, stale 3, no_save 2; plain 0, plural 0) | 25 |
| ROC AUC (Mann-Whitney, ties 0.5) | 0.948 |
| Best cutoff t=0.8999: kept-good / kept-wrong / lost-good | 122 / 5 / 8 (0.79 wrongs per 20 saved) |
| Sealed theta 0.25: kept-good / kept-wrong | 130 / 23 (3.01 per 20 — fails the bar) |
| First zero-wrong cutoff t=0.96: kept-good / lost-good | 89 / 41 |
| Family AUC: trap 0.909, stale 1.000, typo 0.861; plain/plural/no_save single-class (undefined) | — |

Every move/miss: the 5 kept-wrong at best cutoff are all high-p approvals — 1 stale occupation ("baking"), 2 trap misreads (colleague-for-employer, near-city for in-city), 1 typo-glued subject span, 1 employer misread. The 8 lost-good are 7 typo-turn true frames the checker half-doubted (p 0.79–0.87) plus 1 true cousin frame on a trap turn at p=0.28. All 40 appositive relabels audited (each "My <R> <Name>…" with value == another gold subject, truly stated); the plural rule fired 0 times — the ear never kept a plural sister frame, so the case is absent. Fidelity exact: manifest 155/155, C0 90/65, C1@0.25 90/63/153 reproduced.

Predictions: P271.1 RIGHT (130/25), P271.4 RIGHT (wrong locations); P271.2 WRONG (0.948 vs 0.50–0.70), P271.3 WRONG (128 cutoffs qualify; falsifier P271.6 tripped — best keeps 93.8% of goods), P271.5 WRONG (0.861–1.000, not 0.45–0.75). My "rubber stamp" prior was wrong because 267's gold marked 40 true statements wrong; once counted good, the score separates cleanly.

Deviations: D1 plural rule 0 fires (case absent from kept frames); D2 no new exp-264 files — 264 is already sealed, run, and ledger-recorded, so new files would have collided; D3 files left uncommitted/unpushed per OPUS-RULES standing rule vs the brief's PUSH line (ready at artifacts/claude-diag271-20260923/ + scripts/claude_diag271_roc.py); D4 no panels opened, CPU seconds only, prediction seal re-verified OK.

What it means: the checker's score works like a dial on this dev set — at ~0.90 it keeps 122 of 130 good readings with only 5 bad slipping through, far better than the sealed 0.25 setting (23 bad through). The checker was never a rubber stamp; the old answer key just graded 40 true statements as wrong.

What it doesn't mean: 0.90 is not certified anywhere else — on the blind 261b panel the same checker confidently approved fine-grained misreads at high p, and this dev set is clean and tunable. It doesn't fix the ear, which still misses whole plural facts before checking starts, and the best cutoff still drops 7 typo-turn goods. It changes nothing about 264's FAIL or 267's report — it re-reads 267's numbers with corrected labels.

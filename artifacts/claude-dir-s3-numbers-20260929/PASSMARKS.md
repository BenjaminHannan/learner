# dir-s3 numbers, "nearest valid answer": pass marks (written 2026-09-29T02:20Z, before any run they judge; helper S3)

Marks come from design/research/lead-sweep-2026-09-29/SYNTHESIS.md section 3, test 3. They are fixed now and nobody changes
them after a score is seen. A separate blind recount reads only the raw files and this page. Labels: SHOWN = counted from
files or code, SUGGESTED = fits the counts, UNTESTED = nobody ran it. The small card experiments and the village model are
not part of any claim here.

Director's ruling (brief S3): picking among code-enumerated valid answers is kind-blind, because the checker only builds
training data. It is never run at test time, and the net is still not told the puzzle kind (fixed env 0, as in 358u and h2).
Other rules kept: dev panel only; the sealed numbers4 test (300 held-out hands) is read once per net by the sealed `eval`.

## The one change (plain words)
dir-h2 trained every 4-number draw against ONE stored answer, the solver's first find. Its nets either memorised the pool
(plain: practice exactness 1.00, held-out numbers4 6 and 4 of 300) or could not fit it (loop: 0.38 and 0.56, numbers4 4 and 4
of 300; artifacts/claude-dir-h2-recount-20260928/RECOUNT.md). The grader accepts any valid answer. So here each draw keeps all of
its valid answers (code-made, exact checker) and the token loss is measured against the one the net currently finds cheapest
("min-loss"). The halt target stays "equals the chosen target", which is the same as "the answer is valid". Nothing else moves:
same pool (36,782 practice pairs, 300 dev pairs, 0 held-out hands in it), same seeds 13 and 14, steps, nets, tests, own stop.

Code: scripts/claude_dir_s3_labels.py (all valid answers per pair), scripts/claude_dir_s3_run.py (imports dir-h2 and the sealed 358u code).
Arms (all four nets each, seeds 13 and 14):
- MIN (primary): loop and plain, `--mode min`. Judged by the marks below.
- RANDOM-VALID (control, report only): loop and plain, `--mode random`: one valid answer drawn at random per draw. This is the
  random-vs-min comparison of the one-of-many literature (Nandwani et al., authors only; UNTESTED here). It cannot rescue or overturn a MIN verdict.

## Measures (all from the raw files of each net)
- Practice validity = mean of `exact_by_kind.numbers4` over the last 3 lines of train_log.jsonl. In these runs "exact" means "the answer is valid"
  (dir-h2 logged "equals the stored answer", which is at most this; H2's 0.38 and 0.56 are therefore lower bounds on H2's validity, and the
  comparison to them is loose in the direction that favours dir-h2).
- numbers4: held-out sealed test, of 300, right at the net's own stop (loop) or one pass (plain), tests.json.
- sums4, grids5 (loop and plain), sums6, grids6 (loop): the same sealed tests, gates only.
- P_other (300 dev pairs, hands seen at other targets), P_train24, P_practice_other (300 practice pairs, target not 24): extra.json, report only.
  Read as in ADDENDUM-1 of dir-h2: the no-search floor F on P_other is 12.00 of 300; 9 to 29 is inside the no-search band.

## Validity (V). Any miss = INCONCLUSIVE
V0: steps_block_nograd = 0 on every loop net. V1: poison identical on every net. V2: each log prints the pool line "h2 pool: 36782 practice pairs over
1519 hands, 300 dev pairs, 0 held-out hands in the pool, 0 dev pairs in the pool". V3: the 358u seal (20 of 20) and SEAL-s3.sha256.txt (this file and the
two scripts) match before the run. V4 (new): `claude_dir_s3_run.py selftest` prints "s3 run selftest ok" on BensPC before training (the loss equals the sealed
loss when one answer is allowed, equals the brute-force minimum over all valid answers, and "valid" agrees with the sealed checker).

## PASS-LOOP (MIN arm; V0-V4 met)
ALL of, on BOTH loop seeds (13 and 14):
1. practice validity >= 0.90 (H2: stored-exact 0.38 and 0.56);
2. numbers4 >= 36 of 300 (3 times the no-search level of 12; the twelve old nets and the four h2 nets scored 0 to 6);
3. sums4 >= 295, grids5 >= 295, sums6 >= 285, grids6 >= 275 (the h2 gates).
Plain-net row (the loop's-own-gain test, a plain net can fail it and did in h2): the gain counts as the LOOP's only if, on both seeds,
numbers4(loop) minus numbers4(plain, same seed) >= 12 of 300. If PASS-LOOP holds but this fails, word it "the valid-answer target fixed it, and the plain
net does as well: not the loop's doing". PASS-PLAIN (plain both seeds numbers4 >= 36, sums4 and grids5 >= 295) is reported the same way.
Random-vs-min row (fair comparator, report only): min counts as better than random-valid on a seed only if numbers4(MIN loop) minus
numbers4(RANDOM loop) >= 12 of 300 on both seeds. If RANDOM-VALID also passes PASS-LOOP, word it "valid-answer targets help; the min-loss choice is not shown to matter".

## The result that would prove the idea wrong
WRONG (the label rule was not the blocker) = V0-V4 met and either:
- (a) practice validity < 0.60 on BOTH loop seeds; or
- (b) practice validity >= 0.90 on both loop seeds and numbers4 <= 12 of 300 on both: memorised again. Then the next step is the larger fresh pool, a separate change.
Read with the "every seed" rule: WRONG needs both seeds to break; one seed on each side is PARTIAL.
Numbers4 of 13 to 35 on either seed, or a pass on one seed only: PARTIAL, no claim, no second change until the Director reads the marks.
"Not shown" is the label for anything that is neither PASS nor WRONG.

## Marks self-check (Ben 09-28 21:37; H8 checklist), one line each
1. Bars above noise: old run-to-run spread of numbers4 is 0 to 6 of 300 over 16 nets (sd about 1 to 2); the 36 bar is 24 above the 12 no-search level,
   about 4 binomial sd there (sqrt(300 x 0.04 x 0.96) = 3.4); validity 0.90 vs 0.60 is far apart against h2's seed-to-seed gap of 0.18.
2. Every-seed reading: WRONG needs both seeds to break a gate (a) or (b); PASS needs both seeds; one seed = PARTIAL, a non-win is "not shown".
3. Fair comparators: each loop is compared with its same-seed plain net (12 of 300) and with the RANDOM-VALID loop of the same seed (12 of 300);
   h2's stored-answer rows are the "before" and are lower bounds on validity (above).
4. A row a plain net can fail: the plain-net row (loop minus plain >= 12). Memorising check: P_other and P_practice_other beside numbers4, and
   (b) above names "valid on practice, at floor on held-out" as the failure.
5. F_few (k = 1 to 64) does not apply: this test has no few-example episodes and touches no F_eq run. Not measured, not claimed.
6. Sleep gates do not apply: no sleep is run in this test.
Also kept: two seeds, one change, blind panels untouched, no weights pushed, $0 (BensPC only, no vast).

## Prediction (SUGGESTED, not a result)
The synthesis gives about 25% for a full pass and about 50% that the loop fits (validity high). The likeliest failure is (b).

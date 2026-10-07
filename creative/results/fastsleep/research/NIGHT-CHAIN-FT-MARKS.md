# Pilot: can weights learn the multi-step kinds from night-search records? Marks (written 9:56 AM ET 10-07, before any run)

This is part of Ben's request (9:34 AM ET 10-07) for more research into fast sleep. It is a 2-parent pilot, not a confirm. It cannot be adopted on its own; a pass only earns a 6-parent check.

## Why
- The notebook replays whole programs. Night search (the C records in NIGHT-CHAIN-MARKS.md) writes about 200 affine and about 200 sq_plus records per parent, but memory sleep with them still scores 0% on affine (first parents s100/s101).
- The job-6 fine-tune B, trained on the night's own W records, also scores about 0-4% on affine, 0-10% on sq_plus and 0-16% on double_add on all six confirm parents. So the multi-step gap comes from the records the night writes, not only from the notebook.
- The open question: given correct multi-step records, can a weight update learn those kinds, where the notebook cannot?

## Arm
- **BC:** the job-6 fine-tune with each parent's own B settings (lr 1e-3, 16 visits) and B's number of updates (`n_w = |W|`, so the cost matches B). The record set is W + C instead of W. C is the chain records from NIGHT-CHAIN-MARKS.md: the shortest P2(P1(x)) of two library programs that fits the 3 examples, for each pool question with no W record. The key is never read.
- **Compared with:** the confirm's B run on W for the same parent (`confirm.json`, same seed and settings).
- **Parents:** s200 and s201, the first two confirm parents. Both use B settings lr 1e-3, 16 visits.

## Measures (DEV, the tuning split)
- DEV right by kind, plus pooled gain over N.
- Chain-5 harm, the nightly guard's measure.
- FLOPs, measured.

## Marks
- **Weights learn multi-step kinds:** on both parents, BC's mean DEV right over affine, sq_plus and double_add is at least B's mean + 20 points.
- **Proved wrong:** that mean is below B's + 5 points on both parents. The C records then do not teach the multi-step kinds through weights either.
- Chain-5 harm is reported. Any later adoption would need it to be at most 2 points.

DEV is the tuning split. A pass leads to a marked 6-parent check, not adoption.

## Result (10:25 AM ET 10-07): between the marks. It does not pass, and it is not proved wrong.

DEV right by kind (%), with each parent's B on W from the confirm beside BC on W + C. Both runs use the same settings and the same number of updates (s200: 210, s201: 172).

| Parent | Arm | affine | sq_plus | double_add | Mean of the three | square | last_digit | DEV gain | Chain-5 harm | TFLOP |
|---|---|---|---|---|---|---|---|---|---|---|
| s200 | B (W) | 0.0 | 0.0 | 0.0 | 0.0 | 98.0 | 82.4 | 35.9 | 1.2 | 39.4 |
| s200 | BC (W + C) | 3.8 | 27.5 | 2.0 | 11.1 | 88.2 | 98.0 | 43.8 | 1.3 | 39.3 |
| s201 | B (W) | 1.9 | 2.0 | 7.8 | 3.9 | 96.1 | 90.2 | 39.1 | 0.8 | 32.3 |
| s201 | BC (W + C) | 1.9 | 19.6 | 7.8 | 9.8 | 94.1 | 96.1 | 43.4 | -0.1 | 32.2 |

- **Weights learn multi-step kinds: FAIL.** The mean over the three kinds rose by +11.1 points on s200 and +5.9 on s201. The mark needed +20 on both.
- **Proved wrong: no.** Both rises are above +5.
- **What moved:**
  - sq_plus rose from 0-2% to 20-27% on both parents.
  - affine stayed at 2-4% and double_add did not move.
  - Total DEV gain was +7.8 and +4.3 points above B at the same cost. Harm stayed within 2.
- **Reading (2 parents, a pilot):** with the search records, a weight update partly learns the one-constant rule x²+k. It does not learn the two-constant rule a·x+b at B's budget. The notebook learned neither.

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

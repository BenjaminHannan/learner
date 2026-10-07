# Fresh harm check for C2b's arm M: mark (written 3:10 AM ET 10-07, before the check runs)

The roadmap asked for this check (commit 2056152a9d, relayed by the coordinator). Memory with the answer note off becomes the creative loop's
nightly recall step only after a fresh harm check. The check must use a skills slice that no fast-sleep run has scored, pass harm <= 2 points
on every parent, and have its mark written before it runs.

## Setting (frozen by the roadmap)
M = memory + 512 old notes with the answer note OFF:
`knn: c 50, theta 0.9, cal 0.99, old 512, ans 0`, with k 16 and tau 0.05.
The records are each parent's own W records, saved in its setup.pt. Nothing is tuned, and the check runs once.

## Parents
All eight kept parents:
- s100 and s101: `/mnt/project-files/fast-sleep/parents/`
- s200-s205: `/mnt/project-files/fast-sleep/confirm/`

## Slice (never scored by any fast-sleep run)
The slice is `data_big/dev/in_dist.jsonl`, keeping only rows whose family is NOT one of the five chain families. That is 5,800 rows across
29 families, 200 per family.

Every fast-sleep harm number so far, and the s205 diagnosis, read only the chain-5 rows of that file (skills5 and diag205). No other split
or family was scored. The gate calibration reads TRAIN rows from a different file (`data/train.jsonl`), so it never touched this slice.

## Measure
Exact match with `custom_io.evalx.evaluate`, greedy. Harm = N's exact minus M's exact on the whole slice, pooled, in points. Per-family drops
are reported but not marked.

## Mark
- **PASS:** harm <= 2.0 points on every one of the eight parents.
- **FAIL:** harm > 2.0 on any parent.

No re-runs and no alternative slices. If it fails, the failing parents and families are reported as they are.

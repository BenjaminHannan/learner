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

## Result (3:19 AM ET 10-07): PASS

| Parent | N exact | M exact | Harm (points) |
|---|---|---|---|
| s100 | 84.67 | 85.03 | -0.36 |
| s101 | 86.66 | 86.93 | -0.28 |
| s200 | 86.19 | 86.53 | -0.34 |
| s201 | 86.52 | 86.93 | -0.41 |
| s202 | 85.62 | 86.03 | -0.41 |
| s203 | 85.78 | 86.10 | -0.33 |
| s204 | 85.86 | 86.17 | -0.31 |
| s205 | 86.03 | 86.41 | -0.38 |

Harm is at most 2.0 on all eight parents, so the check passes. M scored slightly better than N on every parent.

- 28 of the 29 families are unchanged on every parent.
- The one family that moved is `fewshot_number_rule`, a rule-from-examples family close to C2. There M is 8 to 12 points better than N.
- The step gates fired on 2.2-2.7% of step decisions (874-1,100 of 40,600). The answer note never fired (theta_ans = inf).

Raw numbers are in each parent's `harmcheck.json` and in `harmcheck-REPORT.json`.

**Disclosure.** The first launch, at 3:05 AM ET, ran with a code bug. In `m_knn`, the answer-memory tuple shadowed the `ans` flag, so the
answer note stayed ON. Two parents finished, and their JSON writes failed on a tensor. I stopped that launch at 3:08 AM ET, deleted its two
partial files and used nothing from it. Then I fixed the shadowing, checked that `theta_ans` is inf with `ans` 0, and relaunched at
3:09 AM ET. The table above is that relaunch, the first run of the frozen setting. The bug did not affect the earlier answer-note-off
diagnosis, because that set `theta_ans` directly.

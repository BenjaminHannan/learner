# A1: join-gap audit (evaluation only). Marks written before any scoring, Mon Oct 12, 2026, 9:48 AM ET

Thread "Far transfer (ultracode)". No training; scores kept checkpoints on probe rows only (no panel row).
Labels: **shown** = measured, **suggested** = reasoned, **untested** = never run.
Source: the outside opinions of 10-12 (Opus 5.5 "join-gap audit", Fable 5.1 "first-error split";
reviews/far-transfer-api-2026-10-12/ on branch claude/project-thread-s3y3gg).

## The question

On joined questions, is the model failing at the pieces or at joining them? This decides between the two remaining
routes: an outside splitting tool (code splits a formula at its top-level join; the model answers each piece alone;
the model then answers the join of its two numbers) or more join practice / a bigger model.

## Measure (per checkpoint, on probe cells F4-two (420 rows) and F5-far (420 rows))

The row's formula is split syntactically at its top-level join (`K+J` or `(K)*(J)`: bracket depth 0, one `+` or `*`).
- **W**: the whole question right (as the probe scores it now).
- **P**: both pieces right when each is asked alone on the same grid (`... ; =K`, `... ; =J`, answers checked by the tool).
- **T**: P and the model's answer to `... ; =a+b` (or `=a*b`) right, where a and b are its own piece answers; T is what
  the splitting tool would score.
- **first error** (failed W rows): the first round whose call differs from the tool's working (either operand order
  for ADD/MUL/MIN/MAX): inside K's calls, inside J's calls, or the final join call; and by pair type (range+range,
  range+cell, cell+cell).

Checkpoints (all kept in the scratchpad): L8-LB, L8-LA64 (with its add-on), L7-LB (every weight on L5's hand-made
joins), and the parent T1SDR s200.

## Marks

| Question | Yes | No |
|---|---|---|
| G1 joining is the bottleneck (L8-LB, F4) | T - W >= 15 and T >= 25 | T - W < 5 |
| G2 a splitter would move far (L8-LB, F5) | T >= 10 (far is 1.2 now) | T < 3 |

- G1 yes: a splitting tool would lift joined questions now; worth building as an outside tool (the model then does the
  pieces and the arithmetic, code finds the split), reported as such.
- G1 no with P small: the pieces themselves fail on joined grids; join practice or a splitter cannot help yet.
- L7-LB (trained on joins) is the reference for how close W gets to T when joins are practised.

## Prediction (suggested, written now)

L8-LB F4: W 3, P 45-70, T 35-60. L8-LA64 F4: W 4, T 25-45. L7-LB F4: W 46, T 55-80. F5 (L8-LB): T 10-30. First errors on
L8-LB F4: mostly at the first call of the second piece or the final join, not inside K.

## Result (shown, Mon Oct 12, 10:00 AM ET; domain/far/join_gap.py, outputs in the session scratchpad a1/)

Split rule as written, plus one shown necessity: a cell-arithmetic piece `Rr+Rr*2` contains a top-level `+` and `*`, so
it is read as one piece in the `K+J` form (73 of 420 F4 rows, 66 of 420 F5 rows need this; every row then splits).
Sanity: W equals the probe's scores (L8-LB F4 13/420, L7-LB F4 192/420). The LA64 checkpoint holds the add-on merged.

| checkpoint | cell | W | P | T | T-W | first error K / J / join / stopped-extra (failed rows) |
|---|---|---|---|---|---|---|
| L8-LB | F4 | 3.1 | 72.9 | **40.2** | **+37.1** | 310 / 92 / 0 / 5 (407) |
| L8-LB | F5 far | 1.2 | 22.6 | **9.0** | +7.8 | 391 / 23 / 0 / 1 (415) |
| L8-LA64 | F4 | 4.3 | 56.0 | 44.8 | +40.5 | 310 / 87 / 0 / 5 (402) |
| L8-LA64 | F5 far | 0.5 | 13.1 | 11.9 | +11.4 | 399 / 8 / 0 / 11 (418) |
| L7-LB | F4 | 45.7 | 96.7 | 1.7 | -44.0 | 45 / 104 / 79 / 0 (228) |
| L7-LB | F5 far | 1.9 | 6.0 | 0.0 | -1.9 | 396 / 16 / 0 / 0 (412) |
| parent | F4 / F5 | 0.7 / 0.0 | 0.0 | 0.0 | - | about half stopped/extra |

Verdicts: **G1 yes** (L8-LB F4: T-W +37.1, T 40.2). **G2 between** (L8-LB F5 T 9.0: above the "no" line 3, below 10;
the rank-64 add-on gives 11.9).
Also shown:
- On the whole joined question the first wrong call is almost always inside the FIRST piece (310 of 407), although the
  same piece asked alone is right 73% of the time: the second piece in the prompt disturbs the first, it is not the join
  call that fails (0 first errors at the join). Pieces right alone by pair type (L8-LB F4): range+range 88.1,
  range+cell 68.1, cell+cell 46.2.
- L7-LB (every weight, trained on joins, old skills 90 -> 37) gets the pieces 96.7% but answers `=151+92` with one of
  the numbers (85, 89, 52): plain sums of two literal numbers were lost, so its T is not a splitter score.
Reading (suggested): a splitting tool would lift joined questions from 3-4% to 40-45% now and far to about 9-12%, but
then code does the splitting. The model's own failure is keeping two pieces apart in one prompt, which is what joined
practice teaches (L1, L5) and what the join-last practice change would have to supply.

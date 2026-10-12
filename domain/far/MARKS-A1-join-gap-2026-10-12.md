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

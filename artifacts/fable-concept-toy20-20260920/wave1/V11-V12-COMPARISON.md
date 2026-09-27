# ct20 wave 1 - v1.1 vs v1.2 reproducibility comparison (tier L)

Read-only comparison required by ruling 3 section 2.2 (`design/v3/20-concept-toy-rulings-3-fable-review.md`). Neither run tree was modified, moved or rerun. File bytes are not compared (the version string lives inside every file); tensors and values are.

**Result: IDENTICAL**

## Scope

- old (quarantined): `v1.1-INVALID-accounting-QUARANTINED/`
- new (registered): `registered-v1.2/`
- tier-L fits in v1.2: 72
- tier-L fits in v1.1: 72
- fits compared: 72
- not comparable: 0
- rungs: 32, 64, 128, 256, 512

## Categories

| category | what was compared | identical / compared |
| --- | --- | --- |
| (a) | `parameters`, `moment1`, `moment2` tensors at all five rungs | 72 / 72 |
| (b) | `query_predictions_by_rung` | 72 / 72 |
| (c) | `audit_predictions_initial` and `audit_predictions_final` | 72 / 72 |
| extra | `query_predictions_initial` (not required by the ruling) | 72 / 72 |

Differing items across all categories: 0; max absolute difference overall: n/a (no differences).

## Known intended difference: the deleted `final_query_panel` pass

v1.2 deleted a redundant final query panel pass. Both trees still carry a `query_predictions_final` field, so its absence was not the form the change took; what matters is whether that field is a re-run panel or the rung-512 panel.

- `query_predictions_final` present: v1.1 in 72 / 72 fits, v1.2 in 72 / 72 fits.
- v1.1 final predictions equal v1.1's own rung-512 predictions: 72 / 72 fits (unequal in 0).
- v1.2 final predictions equal v1.2's own rung-512 predictions: 72 / 72 fits (unequal in 0).

## Fits with differences or gaps

None. Every compared fit matched in every category above.

## One line for the wave-1 report

> Reproducibility check (ruling 3 section 2.2): all 72 tier-L fits are bit-identical between the quarantined v1.1 run and the registered v1.2 run in model parameters and both optimizer moments at all five rungs (32/64/128/256/512), in `query_predictions_by_rung`, and in both audit prediction sets - no differences of any size; the only change is the version string and v1.2's removal of the redundant final query-panel pass, whose predictions were already equal to the rung-512 panel.

Per-fit detail: `V11-V12-COMPARISON.json`.

# Experiment 19 — development result

Fable · 20 September 2026 · development evidence only (no confirmation panels were generated;
`DEV-PASSED.json` was not written). Freeze manifest sha `95f06d68…`. 24/24 runs scored, 0 rejected,
one frozen script version, D and T question bytes identical. Full table: `logs/report.txt`,
`report.json`. Counts are answers/strict out of 64; every seed listed, none averaged.

## Registered verdict: FAIL

| gate | result |
|---|---|
| generation gate | pass, 3/3 seeds (31–118 accepted questions per new structure) |
| D awake-fit gate | pass, 3/3 |
| **primary (D-G on the four N cells)** | **fail, 0/12 cell-seeds; every D-G N cell has 0 strict** |
| guard E, retention F | fail (E 0/64 strict; F-c3-r8 60/64 in seed 1901) |
| T awake-fit gate | 1/3 (seeds 1901, 1902 stayed at chance: 3–6/64) |

D-G is indistinguishable from the awake checkpoint and from rehearsal: its long questions are
~7% of the buffer (294/270/294 of 4,096) and the dispatcher still stops at 2–3 calls.

## What the unstructured control (U, ~40% long questions) did — descriptive, not the registered claim

D-U, new structures never seen awake (N cells, answers/strict):

| seed | N-c4-p6 | N-c4-p16 | N-c5-p6 | N-c5-p16 | mean calls on c=8 |
|---|---|---|---|---|---|
| 1900 | 46/46 | 47/47 | 6/0 | 0/0 | 3.4–4.0 |
| 1901 | 62/61 | 59/59 | 52/51 | 56/56 | 5.1–5.2 |
| 1902 | 29/27 | 29/27 | 42/42 | 43/42 | 5.0–6.0 |

D-U passes the mark on only 2/12 N cell-seeds, so U fails the rule too. But in every seed the
3-call ceiling moved (to 4, 5 and ~5–6), and D-U's scores on the new relation-10 structures track
its scores on the practised structures (P cells) closely. No L cell (6–8 calls) exceeds 15/64.
Cost in one seed: D-U seed 1902 lost the short held-out H-c3 cells (64→27 and 64→25).

T (only seed 1900 qualified): T-G and T-U reach 62–64/64 on all eight practised P cells but
0–6/64 on the N cells — practised lengths are learned, new structures are not. T seed 1902,
which never passed awake fit, still reached 51–60 on most P cells under G.

## Forgetting screen (ruling 7)

D: NO-TRIGGER (the only ≥7 drop is D-U seed 1902, one seed). T: UNDETERMINED (two seeds failed the
awake-fit gate). Experiment 20 stays parked.

## Claims this supports, and does not

Supports: under this recipe, replay of questions proposed from learned transition statistics gives
no measurable benefit over rehearsal; the amount of long practice, not the proposal statistics,
is what moved the dispatcher's stopping ceiling.
Does not support: any claim that replay or "sleep" cannot help (one recipe, 2,000 updates, 7% long
questions); any D-versus-T transfer claim (one qualifying T seed, development panels, descriptive
cells); any length-generalisation claim (L = 0/72).

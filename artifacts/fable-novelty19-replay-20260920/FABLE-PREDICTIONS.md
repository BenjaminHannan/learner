# Novelty-19 compositional replay — Fable's predictions

Written 2026-09-20 ~14:05 local, after reading Astra's draft `design/v3/19-novelty-experiment-preregistration-draft.md` and BEFORE any code for it exists.
No awake run, buffer, panel or score exists. My record today: 14 hits / 12 misses; I was under-confident on our own recipes and over-confident on mechanisms.

Arithmetic I did from the spec alone (not an outcome): awake strings give P(LINK→LINK) = 1/3, P(BOS→LINK) = 2/3, P(LINK→10) = 0. So a sampled string is
c=4 with p ≈ 0.049 and c=5 with p ≈ 0.016. The G buffer (4,096 questions) should hold ≈ 200 four-call and ≈ 65 five-call questions (~6.5 % of practice),
versus 40 % in U. Composite r=10 cannot be sampled at all (zero LINK→10 edges), so the quarantine should never fire.

| id | forecast | p | falsified by |
|---|---|---|---|
| P51 | generation gate passes in 3/3 seeds (≥16 accepted questions in ≥16 worlds for each of the four new structures) | 0.90 | any seed misses a structure |
| P52 | D awake-fit gate (7 cells ≥61/64 answers+strict, cap 8) passes in 3/3 seeds | 0.70 | any seed fails |
| P53 | T awake-fit gate passes in 3/3 seeds (I1-H1 was 5/6 across machines) | 0.50 | any seed fails |
| P54 | PRIMARY: D-G passes every N, E, F mark with the ≥13/64 gain over D-R in 3/3 seeds | 0.08 | it passes |
| P55 | D-U reaches ≥58/64 answers on all four N cells in ≥ 2/3 seeds (generic long practice is enough; r=10 transfers once length is learned) | 0.40 | ≤ 1 seed |
| P56 | D-U ≥ D-G on summed N-cell answers in ≥ 2/3 seeds (G's long questions are too rare) | 0.80 | G > U in ≥ 2 seeds |
| P57 | D-R stays at ≤ 12/64 on every N cell in 3/3 seeds (still stops at 3 calls) | 0.85 | any N cell > 12 |
| P58 | no T arm reaches 58/64 on any N cell in any seed (T already fails r=10 at c=2/3) | 0.90 | any T arm/seed/cell ≥ 58 |
| P59 | T-U and T-G reach ≥58/64 on ≥ 6 of the 8 P cells (practised endings at c=4/5) in ≥ 2/3 seeds — supervised steps make length easy once practised | 0.65 | ≤ 1 seed |
| P60 | some D arm passes ≥ 1 L cell (c=6..8) at 58/64 in ≥ 1 seed | 0.12 | none |
| P61 | if D-U or D-G learns c=4/5, its mean calls on c=8 questions is ≤ 5.2 in every such seed (the ceiling moves, it does not vanish) | 0.75 | mean calls > 5.2 |

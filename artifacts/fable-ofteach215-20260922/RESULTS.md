# RESULTS — Exp 215: "X IS THE R OF Y" MEANS "Y'S R IS X" (Muse)

Registered verdict: **PASS** (M1–M6 all hold; seal 8/8 OK post-runs, no
post-seal edits). One agent file, additive only: nothing else touched.

## The one change

`scripts/fable_loop215_agent.py` subclasses loop138i. Outermost ears
rewrite, before the normal pipeline: `"X is the R of Y."` ->
`"Y's R is X."` (any 1–3 lowercase-word R without clause/function words;
Y name-like or a known entity; last-`of` split; never first-person /
article-less / non-name Y / hearsay / wh-subject / glued turns).
`"Who/What is the R of Y?"` -> `"Who/What is Y's R?"` iff the notebook
already holds R. All director probes now save and answer:
`Sam is the boss of Kim.` -> `Saved: Kim's boss is Sam.`;
`Ada Pell is the composer of Blue Rain.` ->
`Saved: Blue Rain's composer is Ada Pell.` (was junk `composer_of`).

## Marks table (integer counts, every case reported)

| mark | bar | result |
|---|---|---|
| M1 P1 (40 sets) | 40/40, 0 junk | 40/40, junk 0 |
| M2 P2 (25 traps) | 25/25 identical | 25/25 |
| M3 rt136 (145) | only C013,C019–C031 move | exactly those 14; rest 0 moves |
| M3 rt143 (124) | gate-open class only, 0 new wrong | J8,K9,O3; new_wrong 0, 0 new writes |
| M3 sessions152 | 0 moves | 0 moves, 0 new writes |
| M3 bench 3 splits (600) | 0 moves | 0 moves, 0 new wrong |
| M3 bench edit200 | only 25 `-fwd` rows | f00–f24-fwd; true answers vs stale golds |
| M3 marks123 | per-case identical + 25 bench rows | identical except those 25 (+volatile secs) |
| M4 reversal210 (70) | junk 26→0, all reported | junk 0/70, 70/70, tables match 138i |
| M5 sleep smoke | pass | installed, 5/5 probes, 0 wrong, 50/50, 151.6 s |
| M6 | 0 new wrong writes | 0 outside predicted set |
| seal | 8/8 OK | 8/8 OK post-runs |

Stale-gold note (evidence, not excuse): bench65 `-fwd` golds echo the
junk object for a subject-question (e.g. Q `Who is the discoverer of
Crimson Candles?` gold `Crimson Candles`); loop215 answers the true
subject (`Isolde Vell`). The 25 correct→wrong flips are the fix working;
the 14 rt136 `WRONG-WRITE` labels likewise judge against the old junk
triples (`Mira's composer of is Requiem`). New triples are true readings
with 0 junk `*_of` relations stored anywhere.

## Deviations

None from the sealed plan. Two pre-seal hardenings from pilots (in seal):
wh-word subjects never rewrite (`What is the capital of Peru.` stays a
refuse); hearsay-attribution vocab in X stays on the base path.

## What it means

`The R of Y` teaches now land as first-class facts for any relation
word, so the reversal gap (26 junk saves, 9 refuses) is closed to 0.

## What it does not mean

It does not learn inverses: asked the untaught direction it still
abstains (reversal 0/50 right, same as base) — only the taught direction
is repaired.

## Questions for Ben

Should the 25 bench65 `-fwd` golds (which reward the junk echo) be
corrected upstream, so the fix stops scoring as 25 wrong?

Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_ofteach215_marks.py --only <suite> --out <dir>`
(sealed runs used `--out artifacts/fable-ofteach215-20260922/<suite>`).

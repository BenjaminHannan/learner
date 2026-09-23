# 119h outcome (director, 2026-09-22 13:39)

**Registered verdict: FAIL** (primary mark M1 missed). 5 of 6 predictions true.

| Mark | Bar | Seed 11911 | 11912 | 11913 | Result |
|---|---|---|---|---|---|
| M1 occupation exact, reading94b, K=3 | >= 10/94 each | 6 | 8 | 9 | **FAIL** (119g: 1/1/1) |
| M2 non-occupation exact, K=3 | >= 81/73/89 | 87 | 91 | 96 | pass |
| M3 ungated precision, K=3 | >= 0.143/0.116/0.154 | 0.191 | 0.198 | 0.209 | pass |
| M4 gated writes | vacuous or wrong-write <= 5% | 0 | 0 | 0 | pass (vacuous) |
| Wave time | <= 2400 s | 2177 s total | | | pass |

Checks: PASSMARKS seal OK; all 7 code hashes in DIRECTOR-codehashes.md match; wave log complete (pool gates passed first try: synth 60,000, occupation 5,000, kept 141,398, steps 8,838).

## Director fresh probe (my own sentences, not a panel; sealed before any 119h model existed)

Probe: DIRECTOR-fresh119h-probe.json (sha256 prefix 230d8135); script scripts/claude_diag119h_freshprobe.py; output DIRECTOR-freshprobe-diag119h.json. Group A = shapes like the new generator's, B = new shapes, C = no job stated (any occupation read is false).

| Model | A exact /16 | B exact /16 | B forced-relation exact | C false reads /8 |
|---|---|---|---|---|
| 119g (each seed) | 5 | 0 | 1-2 | 0 |
| 119h 11911 | 15 | 5 | 9 | 1 |
| 119h 11912 | 14 | 4 | 9 | 2 |
| 119h 11913 | 14 | 7 | 11 | 1 |

With the relation forced to occupation, group A reads 16/16 on all 119h seeds.

## Diagnosis

- The data change worked on the shape it taught: "X is/was a (Nationality) Job" now reads almost perfectly and generalises to job words outside the generator's list (in-list 8-10/17, out-of-list 10-11/15).
- It does not reach other shapes: appositives ("the Kenyan runner X"), job before name, "works as", relative clauses. There the relation classifier says UNSURE or citizenship, and in one case even the forced read takes the job word as the subject.
- New false reads: "X is a Demonym Noun" on non-person subjects ("Brekkefjord is a Norwegian fishing village.", 3/3 seeds; one seed also on a company).
- The panel gap (6-9 of 94 against a ceiling of about 51 reachable) is consistent with the real-text shapes above plus the relation classifier, not with model size.

## What it means / what it does not mean

- Means: varied-shape synthetic rows teach the reader a real, generalising pattern for one sentence shape, with no loss on other relations.
- Does not mean: it can read occupations from encyclopedia text yet, or that any reading may be written to the notebook (the gate still passes 0 writes).

## Next step

The one-change follow-up (119i: wider generator shapes + same-shape non-person negatives + fixed death-before-birth dates) is designed but **paused**. The 2026-09-22 improvement review recommends stopping encyclopedia-reading waves until Ben decides whether the ears aim at chat sentences or encyclopedia text. The ears safety map (class -> notebook relation, no "any content word" fallback) plus an LTT gate rescore of the frozen 119g/119h checkpoints is useful either way and goes first.

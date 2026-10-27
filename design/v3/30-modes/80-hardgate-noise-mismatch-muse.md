# 80 — Hardgate noise-mismatch stress (eps fixed, true noise swept)

## Background

Exp 46 is the live sleep recipe: robust loss `-log((1-eps)*p + eps/N)` with
eps=0.10, plus snapping the router to its single best chain before the
unchanged 4-fold CV gate. The independent audit (doc 75) confirmed exp 46
with one load-bearing caveat: eps=0.10 MATCHED the true teacher noise by
construction (2–4 wrong of 20 ≈ 10–20%), and the only nonsense tested was
20/20 wrong. This experiment removes the match: eps stays exactly 0.10 while
the true wrong count sweeps 0, 2, 4, 6, 8, 10, 20 of 20 lessons.

## Design (one change)

Everything is imported read-only from `scripts/fable_hardgate46.py` (which
patches `fable_reasoner44.fit_word` with the harden step and sets the robust
loss): same gate floors (OOF match >= 0.80, refit agreement >= 0.90, base
probe unchanged, reload identical), same optimiser/start/checkpoints, same
villages and words, same `N.episodes()` lesson stream (levels 0/2/4/20 reuse
exp 46's identical episodes), same 60-start audit as evaluation only. The
only new content is three extra true-noise levels (6, 8, 10) where the loss
understates the noise, plus fresh seed 4101 alongside 4102–4103. New files
only: `scripts/fable_hardgate80_noise.py`,
`artifacts/fable-hardgate80-20260921/`, this doc.

## Why this shape

A fixed eps is what a shipped system has: we cannot retune the loss per
teacher. The question is which failure appears first under mismatch —
installing a wrong word (unsafe) or refusing to install (safe but useless).
The 60-start audit plus fresh-village accuracy define "wrong install"
exactly as in exp 46, so any behavioural change is attributable to the noise
level alone.

## Results

At most 20% wrong lessons (0/2/4 of 20), all 27 cells install with audit
0/60 and fresh 1.00, replicating exp 46's decisions field-for-field on the
overlapping seeds. At 30% wrong (6/20) and above, every cell on every seed
is refused — 0/9 installs at 6, 8, 10, and 0/9 at 20/20 — with zero wrong
installs across all 63 rows. The gate's OOF floor, not the audit, does the
refusing: no checkpoint reaches 0.80 cross-validated match once the lessons
contradict each other that often. Wave wall-clock 276 s.

## Reading for a human teacher

Occasional slips (up to ~1 in 5 lessons wrong) cost nothing. Past ~1 in 3
wrong, the system goes silent rather than confident-and-wrong. That is the
desired asymmetry for a teachable assistant: a confused teacher produces no
new skill, never a corrupted one.

## Limits and next step

The cliff edge is localised only to between 4 and 6 wrong (5/20 untested);
only uniform-random wrong answers and 20/20 nonsense were tested (a
systematically misleading teacher is a different, harder stress); toy
village, three seeds, no language. The natural single next change is testing
5/20 to pin the edge, or sweeping eps itself — not both at once.

## What it does not show

It does not show the recipe survives a teacher who is wrong most of the
time (it refuses — correctly — but teaches nothing), nor anything about
real-language teaching, scaling past toy worlds, or which chain the router
picks under mismatch (moot: nothing installs).

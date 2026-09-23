# 112 — Ledger backfill (Muse): hygiene pass over the live predictions ledger

Exp 82 found 392 ids with 34 missing outcomes, P234–P237 collisions, 7 stale
opens. Since then exps 83–111 added predictions and several owners appended
outcome lines. This pass re-ran the exp-82 checker
(`scripts/fable_ledger82_check.py`, unchanged, read-only, `--selftest` green)
on the current ledger and backfilled what finished artifacts can decide.

## Before/after (integers, checker output)

Sealed run (769 ledger lines, incl. my P112.1–5 predictions, before any
backfill): 483 ids, 487 with-p at pre-backfill re-run; TRUE 317, FALSE 127,
VOID 2, NOT SCORABLE 12, MISSING 36; 441 scored, overall Brier 0.1537
(first sealed snapshot: 483 ids, 436 scored, mean 0.1530).
After my append (793 lines): 494 ids; TRUE 327, FALSE 129, VOID 2,
NOT SCORABLE 12, MISSING 24; 453 scored, overall Brier 0.1519.
Duplicates 4 → 4, order violations 0 → 0, stale opens 4 → 2.

## Backfilled (one ledger line each, `## Outcomes backfill (exp 112, 2026-09-22)`)

- P13 TRUE (p=0.80, brier 0.04) — forecast "arm A starts 3/3", falsified by
  "any fails". Evidence: `artifacts/fable-startup-factorial-20260920/A/seed-{0,
  1,2}/completion.json`, key `started=true` in all three seeds.
- P16 FALSE (p=0.15, brier 0.0225) — forecast event "arm D starts ≥2/3" did
  not occur. Evidence: `.../D/seed-{0,1,2}/completion.json`, key
  `started=false` in all three. (Low-prob forecast correctly assigned: small
  Brier.)
- P209 UNDECIDABLE, left open and unscored — the exp-47 wave `RESULTS.md` is
  finished but contains no loader-vs-reference `max|diff|` number, so the
  under-1e-3 bar cannot be checked in that file. The loader comparison lives
  in exp-58 prose under a different bar, and "at first try" is a process
  claim no JSON records. Never guessed.

Counts: TRUE 1, FALSE 1, VOID 0, UNDECIDABLE 1.

## Still open (24 MISSING — running experiments, not scored)

P95.1–6 (only single-seed partial `probe.json`/`speed.json`, no report),
P101.1–4 (CPU smoke log only, GPU half missing, no report), P104.1–6
(seed-1/2 runs present, seed-3 and report missing), P110.1–6 (cases sealed,
no report). Stale with no deciding artifact: P5 (marg-staged-dense folder
holds only `PREREGISTRATION.md`) and P209 (above).

## Collisions and a new cross-talk finding

Id collisions: P234–P237 (55b/57/58/59), unchanged; no new id collision
(dotted namespaces P66.x/P200.x/P102.x stay distinct). New finding: bare
P1/P2/P4 read parser-TRUE via ledger line 745 ("Outcomes 102 … (P1 16/16 OK
…)"), but those tokens are exp-102's internal mark labels, not the early
baseline predictions — a second collision class (mark-label reuse). Those
09-20 runs have no results JSON, so P1/P2/P4 stay genuinely open; the ledger
line itself is another agent's and was not touched. Future runs should use
dotted mark labels only.

## Live-ledger races (handled, not hidden)

During this pass the owners appended Outcomes-105 (2/5 TRUE, registered
FAIL — matches `self105-results.json` keys `marks.K1.wrong=6`,
`K2.got=43/need=45`, `K3.got=8/need=10`, `K4.pass=true`, `seconds=0.9`) and
Outcomes-111 (4/5 TRUE). I re-ran the audit just before appending and
backfilled only ids still missing, so nothing was double-scored; the after
counts above include the owners' lines. My own P112.1–5 (audit mechanics,
90/85/90/90/95%) resolve 5/5 TRUE, Brier 0.011; SCORE PASS (L1–L5).

## Limits (claims stop here)

Backfill lines quote deciding keys only; aggregates were not computed from
raw rows (exp-95-style rows stay open for their owners). Brier deltas across
snapshots mix my backfill with owners' concurrent scoring. Artifacts:
`artifacts/fable-ledger112-20260922/` (PASSMARKS, SEAL, before/after status
JSONs, `fable_ledger112_audit.json`, RESULTS.md). Ledger discipline: append-only;
no existing line edited. Reproduce: see PASSMARKS.md.

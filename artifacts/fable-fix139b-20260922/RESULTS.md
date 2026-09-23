# Exp 139b RESULTS — open and-name rule on loop129b (Muse). REGISTERED PASS.

Target: loop139b = loop129b + ValueGuard139BMixin
(scripts/fable_fix139b_valueguard.py; wrapper
scripts/fable_loop139b_agent.py; config
artifacts/fable-fix139b-20260922/loop139b-config.json). THE ONE CHANGE vs
exp 139: the gold-sourced KNOWN_AND_NAMES allowlist (test leakage, deleted)
is replaced by a rule + an open code table. A bare "and"/"or" value now
stores exactly when (a) the "and" sits inside an "of"-phrase of a
capitalised name ("United Kingdom of Great Britain and Ireland"), or (b) the
whole span is in OPEN_AND_NAMES (14 UN member-state / territory names with
"and", written from general knowledge before any run; no bench file read to
build it). Every other bare "and"/"or" still clarifies with no write.
Negation/hedge, sentence-boundary, strip, and clarify reply unchanged.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar (PASSMARKS.md, sealed) | got | verdict |
|---|---|---|---|
| V1 139's 56-case probe re-run through loop139b | 56/56 (0 wrong writes; 24/24 exact) | 56/56: 24/24 exact, 32/32 no-write | PASS |
| V1 NEW 45-case probe through loop139b | 22/22 must-write exact; 0 wrong writes overall | 45/45: 22/22 exact (10 invented of-names + Ireland value + 11 UN/territory), 23/23 no-write | PASS |
| V2 redteam136 re-run (145 sealed cases) | 7/7 focus no-write; all prior-OK stay OK | 7/7 no-write; 0 per-case moves vs loop139 (OK 126 / WW 14 / MISSED 5) | PASS |
| V3 marks123 suites + bench per-item | all suite verdicts identical to loop129b; 600/600 per-item identical except the 11 predicted returns | 10/10 suite verdicts identical (sleep SKIP text differs only by agent filename); bench 600/600 identical to loop129b rows (all 11 flips back, 0 other moves); marks bench rows 400/400 identical | PASS |
| V4 wave < 1500 s wall-clock Mac CPU | < 1500 s | 372 s span (v4-start to v4-end) | PASS |

Bench detail loop139b: edit200 150/150/0; old-s2fresh 157/43/0; new-121
136/63/1 -- each identical per-item to the sealed loop129b rows
(verdict_moves=[] on all three splits, reply_moves=0). The 11 exp-139 flips
(bench121-4hop-019 047 136 139 142 195 196; bench103-s2fresh-4hop-056 103
124 196) all answer through the taught Ireland citizenship again.

## What it means

Compound values ("Peru and Chile", "Ann and Bob", lower-case, double-and
of-phrases, "or"-in-name) still never enter the notebook, while real
and-names -- of-phrase names like the Ireland value plus UN/territory names
-- now store exactly; the 139 bench regressions are gone with zero new
moves anywhere (marks, redteam, benches).

## What it does not mean

It does not judge truth -- a confidently-stated false single value still
stores; bare non-UN "A and B" names outside an of-phrase (e.g. "North and
Central America") still refuse by design, so a future bench teaching such a
value would fail V3 the same honest way.

## Deviations

1. New-probe C10 ("Tom and Ann's boss" value) is already no-write on base
   (129b ears SPLIT-clarify any "'s"-in-value shape); kept per the brief's
   example list, plus C23 ("Mira's city is Oslo and Paris.") so 22/23
   must-not-write compounds discriminate on base. Pre-seal only.
2. First marks139b attempt killed by the 120 s tool timeout (not a suite
   failure); re-ran clean to completion (137.6 s) inside the 372 s span.
3. V3 loop129b reference is 140's sealed marks123-129b (per the brief), not
   a fresh 129b wave; the bench half re-diffs the sealed 129 rows directly.

Reproduce: PASSMARKS.md command block (sealed SEAL.sha256.txt).
Ledger: P139b.1 TRUE, P139b.2 TRUE, P139b.3 TRUE, P139b.4 TRUE.

# 103 — Fable-Edit-SCALE follow-ups: two one-change arms (2026-09-22)

For Ben in plain language: exp 92 failed in two exact places, and each
place had a named one-line fix. This experiment applies exactly one fix
per arm and checks the failure goes away without breaking anything else.

## Arm A: S4-clean (notebook arm)

Exp 92 taught 1,000 cases into one notebook. 21 shared bridge slots
(countries' leaders, capitals…) got edited to different values by
different cases; the last writer won and 25 earlier cases answered with
someone else's value. The fix under test: remove those cases — drop any
case that edits a slot another case edits differently (71 cases), plus
any case whose chain merely passes through such a slot (5 cases). The
reasoner and notebook are untouched; only the case list changes. This
mirrors what the MQuAKE authors did for the same problem
(MQuAKE-CF-3k-v2 removed conflicting cases).

Result: the kept 924 cases score 924/924 with 0 wrong in the same shared
notebook. The interference was in the teaching list, not the hop loop.

A second number from Arm A is an observable, not a fix: 106 times, one
case's edit overwrote a value a *different, earlier* case had taught.
Each of those is a moment a real assistant should speak up ("you told me
X before; replacing it with Y") instead of silently swapping the fact.
That behavior is not built here — it is counted here so it can be.

## Arm B: pattern order (English arm)

Exp 92's English parser tried the generic pattern "The X is Y" before
the three specific ones (director/manager, head coach, original
broadcaster), so "The director of The Beatles is …" parsed with subject
"director of The Beatles" and 41 answers went confidently wrong. The fix
under test: try specific patterns first, generic last. Same patterns,
same words, only the order changes — a wrapper, no new code in the old
files.

Result: 0 wrong on S1 (199/0/1), S2 (190/0/10), S3 (198/0/2). Because the
question-word cues were tuned while looking at S1–S3, a fresh check was
required: S2-fresh, 200 new 4-hop cases from MQuAKE items exp 92 never
used (new seed 10300, zero case-id overlap, proved in the build
manifest). On S2-fresh the re-ordered English scores 193/0/7, and the
notebook control scores 200/200. Remaining misses are honest
abstentions: the question uses phrasing no cue covers, so the parser
says MISSING_FACT instead of guessing.

## Limits

S4-clean is triage, not a cure: dropping 76 of 1,000 cases diagnoses the
bug but a real agent needs case isolation (namespacing), still untested.
English still misses 20 questions across the four splits for lack of cue
words; adding cues without re-tuning discipline would re-introduce the
tuning-on-the-test problem S2-fresh was built to guard against.

## What it means

Both exp-92 breaks have confirmed minimal fixes: de-conflict the batch,
order specifics before generics.

## What it does not mean

It does not mean either arm is finished — isolation and cue coverage are
open work with these numbers as the baseline to beat.

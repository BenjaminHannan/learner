# 119d — Ears diagnosis: why 119 still reads 0 facts (Muse, Mac CPU)

Status: DIAGNOSIS ONLY. No training, no GPU, no sealing, no new model files.
Seed 11901 (`artifacts/claude-ears119-run-20260922/w-11901/ear.pt`,
verified 438,712,507 bytes) loaded on Mac CPU through the exp-119 code by
import (`fable_ears119_score` / `fable_ears47_*`; SciBERT snapshot from
`~/.cache/huggingface`, nothing downloaded). One ungated decode per each of
the 400 reading94 sentences; each of the 312 gold triples bucketed exactly
once, priority act → relation → subject → value → confidence → exact.
Machine-readable detail: `artifacts/fable-ears119d-20260922/diag119d.json`.
Runs: panel decode + t_trap decode, 385 s + 489 s wall-clock, Mac CPU.

## 1. Bucket table (312 gold triples, seed 11901)

| bucket | n | sub-split |
|---|---|---|
| act wrong (all 5 → NO_FACT) | 5 | — |
| relation wrong | 224 | §2 |
| subject span wrong | 50 | boundary 5 / elsewhere 45 |
| value span wrong | 22 | boundary 6 / elsewhere 16 |
| all right but conf < tau (0.9602) | 11 | max conf 0.52 |
| exact (match and conf ≥ tau) | 0 | — |

Boundary = predicted and gold span share a token; elsewhere = no shared
token. Multi-triple sentences reuse the single frame per triple (stated
limitation). Cross-check: 11 below-tau + 0 exact = 11 raw exact, matching the
registered W3 = 11 for 11901.

## 2. Top-10 relation confusions (224) with 2 examples each

1. `located in…` → `country` (80). "Drenthe is a province in the northeast
   of the Netherlands." → (country, Drenthe, Netherlands); "The Ateneo de
   Manila University … is a private university … in the Philippines." →
   (country, Ateneo, Philippines). Pattern: any geographic containment
   collapses to `country`, subject often a sub-country region.
2. `occupation` → `date of birth` (24). "Edward Theodore Gein (August 27,
   1906 – July 26, 1984) was an American murderer…" → (dob, Gein,
   american); "…Carolina Evelyn Klüft (born February 2, 1983) is a Swedish
   athlete." → (dob, Klüft, February 2, 1983). Parenthesised dates hijack
   the frame; value span is then empty or a demonym.
3. `date of death` → `date of birth` (16). Same Gein sentence → (dob, Gein,
   american); "Claudio Monteverdi (b.Cremona, 1567; d.Venice 25 November
   1643)…" → (dob, Monteverdi, 25 November 1643). Birth/death dates are
   interchangeable to the head.
4. `occupation` → `country of citizenship` (12). "Tom Whedon is an American
   television writer." → (citizenship, Whedon, American); "Adi Shankara …
   was an Indian Vedic scholar…" → (citizenship, Shankara, Indian).
   Demonym + profession → citizenship, occupation lost.
5. `date of birth` → `country of citizenship` (7). Same Shankara sentence;
   "Fiona Apple … (born September 13, 1977) is an American musician." →
   (citizenship, Fiona Apple…, American).
6. `capital of` → `country` (7). "Recife is a Brazilian city, capital of
   the state of Pernambuco." → (country, Recife, Brazilian); "Delémont …
   is the capital of the Swiss canton of Jura." → (country, "", "").
7. `occupation` → `country` (5). "Pierre de Fermat … was a French lawyer …
   and a mathematician." → (country, Fermat, French); "…Schultz … is an
   American … actor." → (country, Maryland, American) — subject span also
   wrong (birthplace, not the person).
8. `date of birth` → `country` (4). Same Fermat/Schultz sentences.
9. `date of birth` → `date of death` (3). "Dr Robert Anton Wilson (January
   18, 1932 – January 11, 2007)…" → (date of death, Dr, January 18, 1932).
10. `place of birth` → `country` (3). "…Schultz (born November 24, 1947 in
    Baltimore, Maryland)…" → (country, Maryland, American); "…Pulver (born
    … in Sunnyside, Washington) is an American mixed martial artist." →
    (country, Pulver, American).

## 3. Confidence, threshold, NO_FACT

Exact-frame conf: n=11, max 0.52, median 0.18. Non-exact: n=389, max 0.92,
median 0.13. Descriptive sweep (exp-107 method): 0 correct at ≤1% wrong AND
at ≤5% wrong — the top of the ranked list is wrong, so no threshold exists;
NO_FACT writes "at that threshold" is 0 by vacuity. Stated plainly: fitting
any threshold on reading94 would contaminate it as a test set; the sweep is
evidence that confidence cannot separate right from wrong, not a tuning
result. All 11 fully-correct frames sit below the sealed tau (0.96), which
is why W2 = 0 writes on every seed: the gate is above every correct decode.

## 4. The 5 t_trap silent wrong writes

Seed-11901 single at its tau: 0 silent (consistent with W2 = 0 — the gate
blocks everything). The registered 5 are ensemble verdicts; seeds
11902/11903 weights are not on the Mac, so the exact 5 cannot be reproduced
here. What bounds them: at the ensemble tau (0.819) seed 11901 alone
EXECUTEs wrong on 9 t_trap rows — the 5 must be a subset on which all three
seeds vote the same wrong frame. All 9 are family `trap.leftover`, e.g. "Um,
Lisontaine's sport is drawing, Elif too" → (sport, lisontaine, drawing),
conf 0.85; "Fertelovic aside, Migos's training data is dogs" → conf 0.93.
Why the brakes passed: ok4 vacuously true (no UNK pieces); ok5 true because
`pick_surface` falls back to any content word, so the validator nearly
always accepts; conf ≥ tau because min-of-softmaxes is overconfident on
short template-shaped rows; ensemble agreement follows because all seeds
learned the same shortcut. The `aside`/leftover construction never forces
abstention — no brake inspects it.

## 5. Comparison with exp 107

Frame-level, seed 11901: 278 raw STATE frames → exact 11,
relation-right-span-wrong 42, wrong-relation 97, invented 128 (122 no-STATE).
Exp 107 (seeds 4701/2/3): 276/306/288 STATE → exact 9/11/10,
rel-right-span-wrong 28–33, wrong-relation 108–112, invented 124–155.
Same shape, same size, same inverted confidence. Length coverage (192 +
lengthened synth) changed the ungated reads essentially not at all —
confirming doc 107's "wrong relations, not timid".

## 6. Ranked next changes (at most 3)

1. Fix the relation namespace before anything else. Evidence: 224/312
   relation-wrong; `located→country` alone is 80; spans are often right (42
   rel-right-span-wrong frames, 11 fully-correct-but-below-tau). Concrete
   step: closed-list WebRED→inventory remap plus a label audit on real
   sentences (demonyms, containment, birth/death dates). Falsifier: after
   the remap, relation-wrong stays ≥50% of non-exact triples on a fresh
   panel — then the head itself, not the labels, is at fault.
2. Make brake 5 a real brake and teach `trap.leftover`. Evidence: ok5 true
   on all 9 trap executes via the content-word fallback; 5 ensemble silent
   writes. Concrete step: remove the fallback (validator must accept a
   relation wording grounded in the utterance) and add leftover-style
   distractors to CAL so tau sees them. Falsifier: silent trap writes
   persist with the fallback removed — then agreement, not the validator,
   is the hole.
3. Recalibrate instead of re-gating. Evidence: correct frames peak at
   0.52 while tau sits at 0.96; no threshold separates right from wrong.
   Concrete step: temperature/conditioning rework judged by the
   descriptive sweep (correct-at-≤5%), never by moving tau on reading94.
   Falsifier: the sweep stays at 0 correct at ≤5% after recalibration —
   then confidence carries no signal and the head needs retraining, not
   rescaling.

## 7. Deviations / limits

Single seed (11901) — 11902/11903 weights never reached the Mac; per-triple
bucketing reuses one frame per sentence; direction ignored; span
boundary/elsewhere by token overlap. No reading94 number here was tuned on.

What it means: the ears point at roughly the right entities with
systematically wrong relation words, and confidence ranks wrong first —
length was never the bottleneck.
What it does not mean: that any fix is validated, or that reading94 can
still serve as an untouched test set for threshold choices made against it.

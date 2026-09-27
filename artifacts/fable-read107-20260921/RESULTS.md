# RESULTS — Exp 107: reading behind the gate (DIAGNOSTIC, measurement only)

**Result: (b) mostly wrong.** Rung-2's raw ungated STATE frames on real text
are exact only 9/276 (4701), 11/306 (4702), 10/288 (4703) — ~3–4% each.
Nearly half are invented on NO_FACT sentences (124/155/139); most of the
rest use the wrong relation (110/112/108). The confidence order is inverted:
the highest-confidence frame is wrong in every seed, so NO threshold gets
even 1 correct at ≤ 1% or ≤ 5% wrong. The 87 rung-1-unencodable sentences
are not special (same mix). No gate was changed or certified.

## 1. What ran

400 sealed reading94 sentences through frozen rung-2 ears (seeds 4701/4702/
4703, SciBERT snapshot, Mac CPU, 39.5 s, OMP=1). One UNGATED decode per
sentence/seed (`S47.decode`); raw STATE = `act == "STATE"` whatever the
brakes say. Triples via the exp-106 normaliser. New files only, all
`fable_read107_`: `scripts/fable_read107_behind_gate.py`, this folder
(PASSMARKS.md, SEAL.sha256.txt, `fable_read107_results.json`, this file),
`design/v3/30-modes/107-reading-behind-the-gate-muse.md`.

## 2. Marks (integers, per seed, never averaged)

M1 = raw STATE frames vs gold (a+b+c+d = raw STATE). M4 = same on the 87
rung-1-unencodable sentences.

| seed | raw STATE | (a) exact | (b) rel-right span-wrong | (c) wrong rel | (d) invented | M4 (n/exact/b/c/d) |
|---|---|---|---|---|---|---|
| 4701 | 276 | 9 | 33 | 110 | 124 | 68 / 2 / 19 / 28 / 19 |
| 4702 | 306 | 11 | 28 | 112 | 155 | 70 / 4 / 14 / 30 / 22 |
| 4703 | 288 | 10 | 31 | 108 | 139 | 71 / 4 / 15 / 29 / 23 |

Raw acts replay exp 106 exactly (P107.1): STATE 276/306/288, NO_FACT
124/94/110 (+2 UNSURE in 4703).

M2 conf (same score the gate uses): correct frames sit LOW —
max 0.497/0.595/0.527, median 0.17/0.18/0.16 — while wrong frames reach
higher (max 0.695/0.729/0.681, median 0.07/0.07/0.05; ~2/3 of wrong frames
have conf exactly 0.0, the rest spread to ~0.7). Best operating point
(descriptive sweep, high→low conf): top-1 frame is wrong in EVERY seed, so
**0 correct at ≤ 1% wrong and 0 correct at ≤ 5% wrong, all 3 seeds.**
The certified gate (0.88–0.95) is untouched.

M3 relations proposed (top): `unsure` 93/103/103, `country` 90/97/87,
`located in…` 23/23/30, `country of citizenship` 20/22/23, `date of birth`
20/16/13 — vs gold top: `located in…` 137, `occupation` 44, `date of birth`
37, `date of death` 23. The ears' favourite move is `country`/`citizenship`
where gold says `located in…`/`occupation`: a relation-namespace mismatch
(WebRED training labels vs panel inventory), not random noise.

## 3. Wrong frames verbatim (top 6 per seed; full top 15 in the JSON)

Shared across seeds — the same sentences fail the same way 3/3:

1. `El Alamein is a town in Egypt.` → `(country, el alamein, egypt)`
   (gold: `located in…`; conf 0.69/0.73/0.68 — the #1 wrong frame every seed).
2. `Saint-Paul-en-Jarez is a town in France.` → `(country, …, france)`
   (gold: `located in…`; conf 0.48/0.51/0.48).
3. `Tom Whedon is an American television writer.` →
   `(country of citizenship, tom whedon, american)` (gold: `occupation`;
   conf 0.58/0.67/0.37).
4. `Scott Bakula (October 9, 1954) is an American actor.` →
   `(country of citizenship, scott bakula, october 9, 1954)` — right
   relation family, wrong span AND wrong fact (gold: date of birth +
   occupation; conf 0.33).
5. `The Channel Islands are a group of islands near the coast of France.`
   → `(country, channel islands, france)` on a NO_FACT sentence (invented;
   conf 0.34/0.47).
6. `Gucci, is an Italian fashion house…` → `(country, gucci, italian)`
   (invented; conf 0.33/0.41/0.40).

Its few exact hits are date-of-birth/location sentences, e.g.
`(date of birth, carolina evelyn klüft, february 2, 1983)` at conf
0.50/0.59/0.53 — still below the top wrong frames' confidence.

## 4. Reproduce (exact)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
  scripts/fable_read107_behind_gate.py --snapshot <scibert-snapshot> \
  --out artifacts/fable-read107-20260921/fable_read107_results.json
shasum -a 256 artifacts/fable-read107-20260921/PASSMARKS.md  # must equal SEAL
```

## 5. Deviations

None. One registered run, 39.5 s, output as sealed.

## 6. Predictions (ledger P107.1–P107.4): 3/4 TRUE

P107.1 TRUE (276/306/288 replayed) | 0.0025. P107.2 TRUE (9/11/10 ≤ 20) |
0.09. P107.3 TRUE (0 correct at ≤ 5% in every seed) | 0.16. P107.4 FALSE
(invented 124/276 = 44.9% in 4701 and 139/288 = 48.3% in 4703, majority
only in 4702 at 50.7%) | 0.49.

## 7. What it means / What it does not mean

- Means: behind the gate rung-2 reads real text mostly wrong, not
  under-confident: ~3% exact, ~half the frames invented or mis-related,
  and confidence ranks the wrong frames first — lowering the gate cannot
  recover a clean operating point (0 correct even at ≤ 5% wrong).
- Does not mean: the ears see nothing — spans are often right (33/28/31
  relation-right-span-wrong) and the top error is a systematic
  `country`-vs-`located-in` namespace mismatch, i.e. a labelling/interface
  problem as much as a perception problem; nor does it re-judge the
  certified gate, which stays as sealed.

Questions for Ben: none — measurement only, per plan.

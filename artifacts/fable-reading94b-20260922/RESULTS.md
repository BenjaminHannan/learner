# RESULTS — Exp 94b assembly + adjudication (TEST panel rows 400–799, data build only)

Panel `data/open/reading94b/panel.jsonl` (400 rows) is built, adjudicated and sealed.
Panel sha256: `9ca7035ca1995dabe85ece101c0e7af65277d78b695b8d5a1295c1ab11340fba`.

## Marks (integer counts, every seed/case reported, never averaged)

| mark | bar | result |
|---|---|---|
| M1 panel 400 rows, ids == heldout rows 400–799 in order | PASS/FAIL | PASS (400/400, order exact; sentences/pages copied mechanically) |
| M2 pass2 80 rows == sealed sample ids in order, seed 9402 | PASS/FAIL | PASS (80/80, seed 9402) |
| M3 agreement integers present | PASS/FAIL | PASS: exact triple-set 54/80; NO_FACT agree 72/80; fact/no-fact FF=35 FN=5 NF=2 NN=38, kappa 0.8250 |
| M4 counts + 10 hard examples | PASS/FAIL | PASS (see below) |
| M5 nothing from panel in any notebook/training input | PASS/FAIL | PASS (see evidence) |

## M4 counts (adjudicated panel)

- Sentences with ≥1 triple: 165/400 (0.4125); NO_FACT: 235/400.
- Triples total: 378 over 38 relations. Top: located in the administrative territorial entity 107, occupation 94, date of birth 56, date of death 36, place of birth 14, genre 13, place of death 7, located in or next to body of water 5, capital of 4, part of 4, publication date 4, sport 3, manufacturer 3, material used 2, used by 2, based on 2, plus 22 relations at 1 each (country of origin, platform, director, member count, has part, time period, religion, language of work or name, country, child astronomical body, atomic number, followed by, creator, winner, performer, iconographic symbol, start time, end time, discoverer or inventor, spouse, location of formation, tributary).
- NO_FACT by reason: relation-not-in-inventory 174, vague-pronoun-subject 51, fragment 6, opinion 2, list-or-table 2.

## 10 hard examples (all from the 26 adjudicated diffs)

1. `sw86_6470750fd8ad` "Mistreat is a hard rock/Oi!/Rock Against Communism band from Kouvola, Finland." → 3 genre triples + country of origin Finland (pass 2 adopted; slash list = 3 stated genres).
2. `sw86_af771aace6d5` "The winners of the most recent World Series in 2024 were the Los Angeles Dodgers." → winner + time 2024 (pass 2 adopted; "winners" named explicitly, so stated not inferred — judgment call on rule 6).
3. `sw86_1d8a42ecdba9` "Polysaccharides are polymers made up of many monosaccharides." → has part monosaccharides (pass 2 adopted; composition explicitly stated).
4. `sw86_67b7d494f93a` "MySQL is a database system used by many websites on the Internet." → used by many websites (pass 1 kept; rule 2 covers vague subjects, not objects).
5. `sw86_f8f0345daef1` "Sea turtles … found in all the world's oceans except the Arctic Ocean …" → located in or next to body of water, exception kept verbatim (pass 1 kept).
6. `sw86_89e8334af88b` "Natto … is a traditional Japanese food made by fermenting soybeans." → material used soybeans (pass 1 kept; demonym emits nothing).
7. `sw86_b648ef9bbea5` "Sydney Cricket Ground … is located in the Moore Park area of Sydney, in New South Wales." → Sydney + New South Wales (pass 2 adopted; area is not an admin kind).
8. `sw86_a8bc0f2ed414` "Antonio Prohias (January 17, 1921 – February 24, 1998) was a Cuban-born cartoonist." → place of birth "Cuban" verbatim, no normalization to Cuba (pass 1 kept, rule 3).
9. `sw86_07f145f711bb` "Among the collapsed buildings is the spire of Christchurch cathedral." → part of, spire as subject (pass 2 adopted; direct reading of "the spire of X").
10. `sw86_1aa0f7852885` "The Deir el Qamar Synagogue is a synagogue in Deir el Qamar, Lebanon; it is the oldest synagogue in Mount Lebanon." → 3 located-in triples (pass 2 adopted; in-sentence name resolves "it").

## Ledger: P94b.1 TRUE, P94b.2 TRUE, P94b.3 FALSE (0.675 < 0.80), P94b.4 TRUE (0.8250 ≥ 0.70). 3/4.

## M5 evidence

- `notebook/events.jsonl`: 0 hits for `sw86_` (panel ids live only in the source heldout + own files).
- No tracked repo file outside `data/open/reading94b/` and `artifacts/fable-reading94b-20260922/` references the panel (git grep `reading94b`; only hit is the new build script).
- Untracked `scripts/fable_ears119f_*` files reference the panel name; per instruction they were not opened. Their TEST use is the panel's registered purpose (P119f.3 scores on reading94b); training-input contamination there cannot be checked from this seat — director to confirm.

## Deviations

- D1 (director's log, unchanged): pass 1 was done by 4 sessions (100 rows each), pass 2 by a 5th — agreement measures across-session consistency of one model, not within-session. Adjudication/assembly is this 6th session.
- No new deviation: PASSMARKS.md untouched (seal `c434ae0d…` verified before the run); agreement written before any adjudication; new seal file `SEAL-panel.sha256.txt` (never overwrote `SEAL.sha256.txt`); ledger append-only (one outcomes line added, no existing line touched).

## What it means

Ben gets a fresh 400-sentence TEST panel (rows nobody has trained on) with hand labels, ready to confirm whether the exp-119f fix works on new text.

## What it does not mean

It does not prove the labels are truth — one model labelled, relabelled, and adjudicated against itself, so blots it shares with itself survive; and exact-match relabel agreement missed its own bar (54/80 vs 64/80).

## Reproduce

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_reading94b_build.py --validate
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_reading94b_build.py --agree
shasum -a 256 data/open/reading94b/panel.jsonl data/open/reading94b/pass2.jsonl artifacts/fable-reading94b-20260922/agreement94b.json
```

(No model calls for labels; no ears/119f file or checkpoint opened; Mac CPU only.)

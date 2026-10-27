# RESULTS — Exp 138j: MERGE LAYER C onto loop138i (Muse)

One loop carries all ten director-verified pieces as mixins over the
accepted 138i base. Registered verdict: **PASS** — every move was
predicted by id in the sealed PASSMARKS.md, seal re-verified OK after
all runs. No post-seal edits to agent code, config, or case files.

## Marks table (counts are per-case, every seed/case reported)

| Mark | Bar | Got |
|---|---|---|
| M1 180b 42/44, 193 33/40, 164b 49/50 | own-identical except predicted | predicted X05/X11, Q12+6 traps, D08 |
| M1 189 36/38, 189b 42/44 | own-identical except predicted | S19/S20, B25/B26 (187 maker) |
| M1 190 63/70, 190b 45/46 | own-identical except predicted | C0b/C0c/S13 (192), E1-E5 (190b whose) |
| M1 187b 24/34 | own-identical except predicted | T01-T03 older-base, U01-U07 188 |
| M1 192 38/40 | own-identical except predicted | n18/n19 154e-multi-friend (stored [Zoe,Ann]) |
| M1 154f 86/90 | own-identical except predicted | n77/n88 pretend, n80/n81 188 |
| M1 154g 76/91 | own-identical except predicted | 15 reply-only Updated, stored == own |
| M1 188 36/40 | own-identical except predicted | S03 saves (167d), Q01/Q05/H09 older-base |
| M1 155-check | no 155 class/module | clean, every run |
| M2-M1/M2-A/M2-B | == sealed 138i except predicted | all joins prediction-exact (142/168 identical, 146d PASS) |
| M2-G3 | 6/6 identical | 6/6 identical |
| G1 bench-v3 800 items | 0 moves, 0 new wrong vs 138i | 0 moves, 0 new wrong |
| G2 rt136 145 | identical except predicted, 0 new wrong | 33 reply-form 188 moves, 0 stored diffs |
| G2 rt143 124 | identical except predicted, 0 new wrong | Q1-Q7 HARNESS-ERROR (frozen Saved-gate; stored+Q verified identical in-process) |
| G2 sessions152 | identical except predicted, 0 new wrong/write | 16 moves, 0 new wrong, 0 new writes |
| G2 marks123 | per-case vs marks138i, 0 new wrong/write | rt81 10, l5z1 9 (7 reply-only + idx28/29 stored==154g-own), soak wrong 40 (all Actually→Updated), q1-m5 casing, sleep filename, l6 kill-timing; rest 0 moves |
| G3 (a)-(i) | exact frozen replies, fresh loop each | 9/9 EXACT |
| G4 1000 turns | on-vs-off identical | 0 reply diffs, facts equal, events 1129/1129 |
| Open re-run rt110/soak | report both | rt110 per-case identical (0 herr both); soak wrong 40 both |

## What it means

Layer C is merged: case-insensitive names, missing apostrophes, about-questions, repeats, reverse lookup, self answers, named replacements, negation retraction, bare corrections, and the statement fallback coexist on one loop, with the director's single Updated wording used for every replacement and every interaction verified against the owning piece.

## What it does not mean

The Updated template never invents an old value (it fires only on real superseding writes); frozen harnesses that judge teach replies by literal "Saved:" (rt143 Q1-Q7, rt81 corrections, soak corrections) report gate errors, not behavior errors — stored facts and follow-up answers were verified identical.

## Deviations

Two pre-seal fixes, both piloted: (1) a driver bug in my M1 jsonl state reader (missing fixture-empty branch — agent was correct); (2) a real agent bug — the 154d yes/no peek re-runs `hear()` before the real hear, which consumed 154g's pending replace-answer; fixed by consuming the pending in `_act` (runs once per real turn) with an idempotent ask replay. No changes after the seal.

## Questions for Ben

None. Most conservative default already taken: 159-T08 keeps 180b-own's stored form ("red Ball"), listed as predicted.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix138j_m1pieces.py --out <p> && python -B scripts/fable_fix138j_m2.py --out <m> && python -B scripts/fable_fix138j_suites.py --only g3,g4,rt136,rt143,sessions,benchv3 --out <d> && python -B scripts/fable_marks123_all.py --agent scripts/fable_loop138j_agent.py --config artifacts/fable-agent138j-20260922/loop138j-config.json --out <mk> --suites p2,p3,p4,rt110,q1,bench,rt81,sleep,soak,q4 --workers 2`
Seal check: `shasum -a 256 -c artifacts/fable-agent138j-20260922/SEAL.sha256.txt` → 4/4 OK.

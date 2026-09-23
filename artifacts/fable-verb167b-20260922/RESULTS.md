# Exp 167b RESULTS (plain words for Ben) — SCORE: PASS

The idea: loop167 saved anything after "lives in" / "works for" / "was
born in" -- even "a flat" or "Accra now". Now the verb path checks the
object first: trailing chat words (now, too, lol, btw...) are stripped
with loop139e's sealed tail list, and if what is left starts with
a/the/my-type word or a small common word (home, town, abroad), nothing
is saved and you get "I didn't understand that..." instead. Clean names
still save and answer exactly like the "X's city is ..." form. The
"place_of_birth" underscore in Saved replies is kept as is (future work
below -- fixing it would be a second change).

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 probe (64: 22 mapped + 16 tail + 16 descr + 10 neg) | 64/64 OK, exact replies | 64/64 PASS (2.1 s) |
| T1 mapped: verb teach = possessive-twin triple, verb-Q + possessive-Q answer, exact Saved | 22/22 | 22/22 PASS |
| T1 tail: saved WITHOUT the tail word, asks answer clean value | 16/16 | 16/16 PASS |
| T1 descr + neg: 0 writes, byte-identical clarify | 26/26 | 26/26 PASS |
| T2 wrong writes (64 rows) | 0 | 0 PASS |
| G1 bench 600/600 vs frozen loop167 AND loop162b rows | 0 moves, 0 new wrong | 0 moves PASS (42.3 s) |
| G2 marks123 per-case vs marks167 | identical except predicted | predicted-only PASS (203.0 s) |
| G3 redteam136 (145) + redteam143 (124) + sessions152 (180 turns) | 0 moves vs 162b and vs 167 rows, 0 new wrong | 0 moves PASS (13.0 s) |
| G4 every run < 1500 s Mac CPU | < 1500 s | max 203.0 s PASS |

G2 detail: p2 64/64, p4 30/30, p3 L1-L6 PASS, q1/bench/rt81/soak/q4
per-case identical (suite-level FAILs on p2/q1/rt81/q4 match loop167
exactly, as 167 matched 162b); sleep SKIP identical, reason names
loop167b; rt110 62/62 identical incl. P1/P3 saving/answering Oslo with
the sealed 167 replies; summary numbers identical on every suite; no
flakes, so no open re-run was needed.

## What it means

The director's two wrong writes are gone ("a flat" refuses, "Accra now"
saves "Accra"), clean verb facts still teach and answer both question
forms with the possessive form's own triples, and nothing else moved:
600/600 bench, 449 G3 turns, and every marks123 case identical to
loop167.

## What it does not mean

It does not mean every description is caught -- only the shape rule
(article/determiner-first or lowercase-first) guards the verb path, and
the possessive path ("Ivy's city is a flat.") still saves; capitalised
tails ("Accra Now") still save; "The Hague"-shaped names refuse
(conservative edge, disclosed in the design doc).

## Deviations

None. Seal 11/11 shasum-clean after all runs; one registered run per
suite; no post-seal edits; no open re-runs needed.

## Questions for Ben

1. The possessive path still saves "Ivy's city is a flat." -- want the
   same screen there next, or leave it?
2. "Saved: Raj's place_of_birth is Pune." keeps the underscore because
   the Saved text and the answer text use different render functions --
   want one shared label renderer next?

## Future work

Shared relation-label renderer (Saved + answers); possessive-path value
screen; "The Hague"-shaped determiner-led real names; capitalised tails.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167b_probe.py --out artifacts/fable-verb167b-20260922/probe167b-loop167b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167b_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167b_agent.py --config artifacts/fable-verb167b-20260922/loop167b-config.json --out artifacts/fable-verb167b-20260922/marks167b --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167b_marksdiff.py

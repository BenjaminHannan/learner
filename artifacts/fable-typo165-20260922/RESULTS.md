# Exp 165 RESULTS (plain words for Ben) — SCORE: PASS

The idea: the assistant used to demand a perfect apostrophe ("Tom's
boss"). If you typed "Toms boss" it just said "I didn't understand that"
and saved nothing. Now, when the name without the last "s" (here "Tom")
is someone it already knows, and "Toms" itself is not a name it knows, it
silently reads it as "Tom's" and answers normally. Unknown names are never
guessed: "Zorgs boss" still says "I didn't understand that".

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 typo (29, 7 relations, teach+Who+What, lower+capital, incl. Chriss→Chris) | 29/29 exact | 29/29 PASS (2.3 s) |
| T1 guard+other identical to loop162b (12+12) | 24/24 byte-identical | 24/24 PASS |
| T2 wrong writes (53 rows) | 0 | 0 PASS |
| G1 bench 600/600 vs frozen loop162b rows | 0 moves, 0 new wrong | 0 moves PASS (49.7 s) |
| G2 marks123 per-case vs marks162b | 0 moves except predicted | 0 semantic moves PASS (207.0 s) |
| G3 redteam136 (145) + redteam143 (124) + sessions152 (180 turns) | 0 moves, 0 new wrong | 0 moves PASS (17.0 s) |
| G4 every run < 1500 s Mac CPU | < 1500 s | max 207.0 s PASS |

Suite detail: p2 FAIL identical to base (2 OK→BUG / 4 still-BUG, 0 moves);
q1 F5+M5 FAIL identical; rt81 61/0/13 identical (0 moves); q4 leaks
identical; bench tables identical (seconds only differ); p3 l1-l6 all PASS;
rt110 62 cases 0 moves, still-bug same 6, 0 harness errors; sleep SKIP both
(reason names the new agent file only); soak 2000 turns 0 lost/0 wrong.
Summary-table WHOLE-DIFF is agent/config paths + seconds only.

## What it means

Missing-apostrophe possessives for known names now teach and answer in both
question forms across 7 relations, with zero movement anywhere else:
600/600 bench, every marks123 suite per-case identical, 449 G3 turns
move-free.

## What it does not mean

It does not mean unknown names get guessed: stripped-unknown ("Zorgs"),
a taught "Toms"/"Chris", the "The Toms"/"The Beatles" plural block, office
relations, and multi-word frames all take the base path byte-identical.

## Deviations (one, reported)

- Post-seal fix to my own sealed case file (artifacts/fable-typo165-20260922/
  cases165.json): typo rows teach a setup fact plus the typo fact but
  `expect` listed only the typo triple, so the registered probe run scored
  29 WRONG-WRITE against correct behaviour (reply "Saved: Tom's boss is
  Lee.", both triples stored). Fix: `expect` = [setup triple, typo triple]
  (still exact, still 0 extra writes). Old hash
  95e4a0ec… / new hash 3c410856… (see SEAL.sha256.txt for the sealed hash).
  The probe re-ran after the fix as the registered run in the open: 53/53.
  No rule change; no agent-code change; bench/G2/G3 never read this file.

## Questions for Ben

None.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix165_probe.py --out artifacts/fable-typo165-20260922/probe165-loop165.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix165_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix165_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop165_agent.py --config artifacts/fable-typo165-20260922/loop165-config.json --out artifacts/fable-typo165-20260922/marks165 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix165_marksdiff.py

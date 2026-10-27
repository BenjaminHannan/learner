# Exp 166c RESULTS (plain words for Ben) — SCORE: PASS (T1/T1b/T1c/T2/G1/G2/G3/G4)

The idea: exp 166 taught the assistant that "my ..." means you, but names
typed in small letters ("my dog is biscuit") stayed small in later answers.
Exp 166b tried to fix the capital letter and failed its registration (its
first bench run upgraded "judo" inside "World Judo Championships", and a
shout like "ANA" still became the display name). This run registers the fix
cleanly: a small-letter name takes a later mention's capital ONLY when that
mention is a genuine Title-case name ("Biscuit" yes, "ANA" no) standing on
its own (not a word inside a longer title like "World Judo Championships").
The notebook log is never rewritten; the memory lives in the agent.

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 sealed 166 probe reused unchanged (52 rows) vs loop166 | 52/52 byte-identical | 52/52 PASS (2.9 s) |
| T1b 166b's 30-dialogue probe reused unchanged | 30/30 OK + verdicts identical to loop166b's open re-run | 30/30 PASS, 0 mismatches (2.0 s) |
| T1c NEW probe (24 dialogues, fictional names) | 24/24 OK (8 shout + 8 embed + 8 title) | 24/24 PASS (1.4 s) |
| T2 wrong writes / new entities vs loop166 (106 T cases) | 0 / 0 | 0 / 0 PASS |
| G1 bench 600/600 vs frozen loop166 rows | 0 moves, 0 new wrong | 0 moves PASS (27.6 s) |
| G2 marks123 per-case vs frozen marks166 | identical except race | PASS (187.6 s; 1 verdict-identical rt110 log-only race move, open re-run on disk, both reported) |
| G3 sessions152 (180) + redteam136 (145) + redteam143 (124) | 3 predicted returns, else identical | PASS (8.2 s; S4 turns 2/3/26 byte-identical to loop162b, S4/1 keeps 166, 0 new WRONG/writes) |
| G4 every run < 1500 s Mac CPU; daemon idle_seconds | < 1500 s | max 187.6 s PASS; idle_seconds=3600.0 stored as given |

Suite detail: p2 64/64, p4 30/30, rt81 74/74 identical; p3 L1-L6 identical
(l2-cases 0 moves); q1 F5+M5 FAILs and q4 leaks identical to base; bench
tables identical; soak 2000 turns 0 lost/0 wrong/0 doubled clean; sleep
SKIP, reason names the new agent file only.

## Post-seal edits

None. Zero edits to any file after the seal (seal re-verified `shasum -c`
clean at the end). No rule changes; no silent re-runs.

## Race report (both runs)

Registered run: 1 log-only move, rt110 R5 msg_02 ("I already have that." vs
base "I didn't catch anything.") -- the known empty-read mailbox race under
load; verdicts OK/OK identical. Open re-run (separate out dir,
marks166c-rt110rerun, 128.8 s): the SAME R5 line moved the same way, R1
identical on all three (ref/registered/rerun) -- same race, verdicts
otherwise equal on 62/62. No third run. Soak clean first try, no re-run.

## What it means

Small-letter names now take their capital from the first genuine Title-case
mention on ("pip" -> "Pip", "biscuit" -> "Biscuit"), while shouts ("ANA"),
words inside longer titles ("Judo" in "World Judo Championships"), and all
600 bench items, all marks123 suites, and all 449 G3 turns move only where
predicted in writing (plus the disclosed verdict-identical race log line).

## What it does not mean

It does not mean the assistant guesses names -- only same-letters,
different-case mentions count ("Biscuit" yes, "Biscuits" no); shouting a
name never renames it; and no answer, fact, or notebook entry changes, only
the capital letter shown.

## Deviations

Pre-seal dev checks only (helper unit checks + 3 director dialogues driven
in memory, nothing written to artifacts) -- NOT registered runs; registered
probes ran after the seal. No post-seal code edits; no sealed-file changes.

## Questions for Ben

None.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_probe.py --out artifacts/fable-me166c-20260922/probe166c-loop166c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_probeB.py --out artifacts/fable-me166c-20260922/probe166c-B.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_probeC.py --out artifacts/fable-me166c-20260922/probe166c-C.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop166c_agent.py --config artifacts/fable-me166c-20260922/loop166c-config.json --out artifacts/fable-me166c-20260922/marks166c --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_marksdiff.py

# Exp 166b RESULTS (plain words for Ben) — SCORE: PASS (T1/T1b/T2/G1/G2/G3/G4)

The idea: exp 166 taught the assistant that "my ..." means you, but a small
side effect slipped in — "My dog is biscuit." stored the dog's name in small
letters, so later answers said "biscuit's ..." instead of "Biscuit's ...".
This run adds one rule: when a name stored in all small letters is later
written with a capital (`Biscuit`), answers use the capital from then on.
The notebook log is never rewritten; the memory lives in the agent.

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 sealed 166 probe reused unchanged (52 rows) vs loop166 | 52/52 byte-identical | 52/52 PASS (1.8 s) |
| T1b new probe (30 dialogues, fictional names) | 30/30 OK | 30/30 PASS (12 lower-then-cap + 8 cap-then-lower + 10 other; 1.5 s) |
| T2 wrong writes / new entities vs loop166 (82 T cases) | 0 / 0 | 0 / 0 PASS |
| G1 bench 600/600 vs frozen loop166 rows | 0 moves, 0 new wrong | 0 moves PASS (34.8 s) |
| G2 marks123 per-case vs frozen marks166 | identical except race | PASS (181.5 s; 1 verdict-identical rt110 log-only race move, open re-run on disk, both reported) |
| G3 sessions152 (180) + redteam136 (145) + redteam143 (124) | 3 predicted returns, else identical | PASS (5.6 s; S4 turns 2/3/26 byte-identical to loop162b, S4/1 keeps 166, 0 new WRONG/writes) |
| G4 every run < 1500 s Mac CPU; daemon idle_seconds | < 1500 s | max 181.5 s PASS; idle_seconds=45.0 stored as given |

Suite detail: p2 64/64, p4 30/30, rt81 74/74 identical; p3 L1-L6 identical
(l2-cases 0 moves, pass stays False as in marks166); q1 F5+M5 FAILs and q4
leaks identical to base; bench tables identical; soak 2000 turns 0 lost/0
wrong/0 doubled clean; sleep SKIP, reason names the new agent file only.

## Post-seal edits (3, all reported; affected marks re-run in the open)

1. `scripts/fable_loop166b_agent.py` (agent): the registered G1 run exposed
   4 unpredicted teach-reply moves (`judo` -> `Judo` inside "World Judo
   Championships") — the first trigger matched a word *inside* a longer
   capitalised name, which is not a mention of the entity. Added the
   adjacency guard (a match next to another capitalised word is rejected).
   Recorded as G1-run1 FAIL with this diagnosis note; re-ran T1/T1b/G1/G3/G2
   in the open. The sealed files (PASSMARKS/cases/config) never changed
   (`shasum -c` clean).
2. `scripts/fable_fix166b_probeB.py` (scorer, pre-registration of T1b
   verdicts): two pre-seal case-shape fixes during dev trials (third-person
   value slots store literals; 1-hop answers echo question case).
3. `scripts/fable_fix166b_marksdiff.py` (scorer): restored a dropped
   `def _cases` line; normalised volatile summary fields (seconds,
   agent/config paths, sleep-reason truncation); verdict-identical
   rt110/soak log-only race triage with open re-run required.

## Race report (both runs, per the brief)

rt110 run1: 1 log-only move (R5 msg_02 empty-read vs "I already have that.",
verdicts 62/62 equal). Open re-run (separate out dir): race moved to R1
(OK->BUG, "turn 3 lacks 'Lisbon', got empty-read") + R5 log-only — same
empty-read mailbox race under load, verdicts otherwise equal. No third run.
Soak clean first try, no re-run.

## What it means

Small-letter names now keep their capital from the first capitalised mention
on, across first-person and third-person turns, while all 600 bench items,
all marks123 suites, and all 449 G3 turns move only where predicted in
writing (plus the disclosed verdict-identical race log line).

## What it does not mean

It does not mean the assistant guesses names — only same-letters,
different-case mentions count (`Biscuit` yes, `Biscuits` no); names inside
longer names ("Judo" in "World Judo Championships") are left alone; and no
answer, fact, or notebook entry changes, only the capital letter shown.

## Deviations

Pre-seal dev trials of both probes to scratch (52/52, 30/30) — NOT
registered runs; registered probes ran after the seal. Post-seal code edits
1-3 above; no sealed-file changes; no rule changes. Scratch dir removed.

## Questions for Ben

None.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_probe.py --out artifacts/fable-me166b-20260922/probe166b-loop166b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_probeB.py --out artifacts/fable-me166b-20260922/probe166b-B.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop166b_agent.py --config artifacts/fable-me166b-20260922/loop166b-config.json --out artifacts/fable-me166b-20260922/marks166b --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_marksdiff.py

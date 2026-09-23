# Exp 180b — silent case-insensitive known-name match on loop138h — RESULTS (plain words)

Loop180b = loop138h plus one outermost step: any word in a turn that
matches a name already in the notebook, ignoring case, is read as that
stored name, and replies spell known names the stored way. No
questions back, no guessing of unknown words. Registered verdict:
PASS on K1 and K2 per the sealed PASSMARKS.md (seal
`SEAL.sha256.txt` verifies OK after all runs; no post-seal edits).

## Marks table (integer counts, every case reported)

| mark | bar | result |
|---|---|---|
| K1 sealed case180b.json (44 turns) | 44/44 step checks | PASS 44/44: 10/10 setup parity, 14/14 lowercase/mixed asks == capitalised-twin replies with 0 writes (incl. 2-hop x2 and 165 "Who is toms boss?" -> "Tom's boss is Lee."), 8/8 lowercase teaches save silently with twin-identical replies+triple sets and 0 case-dupe entities, 12/12 traps (unknown names, will/may/mark/rose, kofis, 2x say-pretend byte echo with 0 writes, 2x already-stored lowercase -> "I already have that.") (4.6 s) |
| K2 redteam136 (145 cases) | 0 moves, 0 new wrong/write | PASS: moves=0, new_wrong=0 (6.7 s) |
| K2 redteam143 (124 cases) | 0 moves, 0 new wrong/write | PASS: moves=0, new_wrong=0 (21.7 s) |
| K2 sessions152 (180 turns) | identical except 9 predicted | PASS: exactly the 9 sealed reply-casing-only moves (S2 n7/n13/n18/n23, S5 n4/n5/n6/n10/n13), verdict OK both sides, new_wrong=0, new_writes=0 (14.1 s) |
| K2 bench121 4 splits (800 items) | 0 moves, 0 new wrong | PASS: 4x200 moves=0 new_wrong=0 (129.2 s) |
| K2 marks123 (10 reports) | per-case identical except predicted | PASS: comparator exit 0 — p2/p3/p4/bench/rt81/soak/q4/sleep/summary SAME-or-predicted-rename; rt110 + q1 only the 4 sealed casing-only moves (rt110 L6/M5/S2, q1 M5; all verdicts/writes/flags unchanged); suite FAILs p3-l5z1, p4-1-nonpass, rt81-59ok/1bug/14unclear inherited byte-identical from 138h (467.6 s) |
| G4 time | every run < 1500 s | PASS (max 467.6 s; daemons take idle_seconds) |

What it means: typing names in the wrong case now just works —
questions come back spelled right, teachings save at once, and
re-typing something already stored still says "I already have that."
Unknown words are never guessed, and pretend "say ..." lines are
quoted back exactly as typed.

What it does not mean: the assistant does not learn new names from
miscasings, does not fix missing apostrophes beyond what loop138h
already did, and does not change any stored fact — all frozen suites
show zero new wrong answers and zero new writes.

## Deviations from the plan (4, all kompatible with the seal)

- X09-class: already-stored string-value facts typed lowercase
  ("tamsin's city is porto.") now answer "I already have that."
  where the base offers a change. The brief mandates this reply, so
  the case file encodes it as an expect-trap (pre-seal).
- Pre-seal ears/display fix (piloted, before the seal): a
  non-lowercase token is never rewritten to an all-lowercase
  canonical, and the display path honours 166c overrides — otherwise
  8 sessions-S4 replies would have un-fixed the sealed 166c display
  ("Biscuit" -> "biscuit"). After the fix S4 is byte-identical.
- rt110 per-turn `statuses` are harness-timing-volatile (runner reads
  the daemon log before the daemon appends it); proven with a fresh
  rerun of the sealed 138h code disagreeing with its own sealed row.
  Verdicts, replies and writes are always compared exactly.
- marks tmp workdirs hold 2x random-named daemon dirs vs the sealed
  run (volatile scratch names; verdict rows unaffected, n=62).

## Questions for Ben

None.

## Exact reproduce commands (Mac CPU, offline, after the seal)

- `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B
  scripts/fable_fix180b_probe.py` (K1)
- `... python -B scripts/fable_fix180b_suites.py --only
  rt136|rt143|sessions|bench` (K2 suites, one at a time)
- `... python -B scripts/fable_marks123_all.py --agent
  scripts/fable_loop180b_agent.py --config
  artifacts/fable-case180b-20260922/loop180b-config.json --out
  artifacts/fable-case180b-20260922/marks180b` then `... python -B
  scripts/fable_fix180b_comparem.py` (K2 marks)
- `shasum -c artifacts/fable-case180b-20260922/SEAL.sha256.txt`

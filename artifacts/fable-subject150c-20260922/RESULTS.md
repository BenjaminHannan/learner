# Exp 150c RESULTS — closed-class-subject guard on loop150 (Muse)

## Result

PASS on C1, C2, G1, G3, G4; G2 PASS with two handled deviations (one
post-seal one-line daemon fix, re-run in the open; one rt110 telemetry
flake, re-run clean). The one change works exactly as specified.

## What was built (new files only, no commits)

- `scripts/fable_fix150c_closedclass.py` — ClosedClass150CMixin + sealed
  42-entry whole-subject set (wh-words, pronouns, deictic time, here/there).
- `scripts/fable_loop150c_agent.py` — loop150c = loop150 + mixin (ears hear
  + loop _act, `--daemon` with idle_seconds).
- `scripts/fable_fix150c_probe.py`, `fable_fix150c_bench.py`,
  `fable_fix150c_session152.py` — runners (150b pattern, target swapped).
- `artifacts/fable-subject150c-20260922/` — PASSMARKS.md, cases150c.json
  (72), loop150c-config.json, SEAL.sha256.txt, all run outputs.
- `design/v3/30-modes/150c-closed-class-subject-muse.md` — design doc.

## Marks table (integer counts, every seed/case reported, never averaged)

| mark | bar | result |
|---|---|---|
| C1 probe (72) | 48 closed-class refuses -> 0 writes; 24 must-write incl. 17 titles -> >= 90 % exact, 0 wrong writes | 48/48 OK, 0 writes; 24/24 exact triples, 0 wrong writes (4.4 s) |
| C2 cases150.json (57) | per-case identical to sealed probe150-loop150.json | 57/57, 0 moves (4.0 s) |
| G1 bench 600 | identical except predicted; 0 new wrong | 600/600 verdict+reply identical; only teach_replies of item bench103-s2fresh-4hop-004 changed (2 Yesterday teaches Saved->generic, verdict abstain unchanged); 0 new WRONG (79.7 s) |
| G2 marks123 | per-case identical to marks150 | identical per-case everywhere (see notes); p2/q1/rt81/q4 suite FAILs byte-identical to base (pre-existing); sleep SKIP reason names new file only (537.9 s) |
| G3 sessions152 (180 turns) | 0 reply diffs, 0 new WRONG, 0 writes | 0 reply diffs, 0 new WRONG, 0 write deltas (7.6 s); 1 mechanical-vs-handcorrected label (S5n16, same as 150b) |
| G4 time | each run < 1500 s | slowest 537.9 s |

## Deviations (both handled per brief, in the open)

1. Post-seal one-line fix: `Loop150cDaemon.__init__` missed
   `self.idle_seconds = float(idle_seconds)` (my transcription error; 150
   and 150b both have it). Subprocess daemons crashed on boot, so G2/p3
   stalled twice at run_l1. Fixed, G2 re-run fully in the open. The mixin
   screen is untouched; C1/C2/G1/G3 (in-process paths) stand as run.
2. rt110 registered run: 1 telemetry-only diff (P5 msg_03 statuses
   ["OK"] vs [], reply+verdict identical) under load ~147. Open re-run:
   62/62 per-case identical to base. Both reported.

## Other notes

- Parse path: `scripts/fable_agent_loop.py:96,102,134-147` via
  `scripts/fable_loop90_agent.py:184-190`.
- Known collision by design: the song "Yesterday" refuses (whole-subject
  rule; case cannot separate it from the time word). G1 verdicts unchanged
  because item 004 abstains either way. Question for Ben: an exact-collision
  name table would be a separate experiment.
- Brief-literal multi-word possessive titles are already nowrite on loop150
  (one-word-names rule); guard never engages, 0 moves verified.
- Soak 2000 turns 0 lost/0 wrong; p3 L1-L6 PASS; rt110 62/62, 0 harness errors.

## Reproduce

Sealed commands in PASSMARKS.md; ledger predictions P150c.1-6 written
before the runs. Seal: `shasum -c
artifacts/fable-subject150c-20260922/SEAL.sha256.txt` (PASSMARKS.md
70f1ba2a…, cases150c.json 7572fb32…).

What it means: chat/idiom "'s" sentences no longer create fake entities, and nothing real stopped teaching.
What it does not mean: song titles that ARE closed-class words ("Yesterday") still refuse -- that needs a name table, not this guard.

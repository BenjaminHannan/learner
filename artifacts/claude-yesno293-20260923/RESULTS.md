# Exp 293: yes/no reader — RESULTS (registered verdict: PASS)

**Result first: PASS.** All five marks pass on the first registered try.
293 answers yes/no questions that 138nb calls incomprehensible, never
guesses, never writes on a question turn, and changes nothing else.

## Marks table (integer counts; 138nb's number beside every figure)

### M1: yesnopanel293 (fresh blind panel, 85 items, once per arm, sealed scorer)

| Family | n | 138nb right | 293 right | 293 wrong | 293 writes |
|---|---|---|---|---|---|
| have_true | 10 | 0 | 10 | 0 | 0 |
| have_unknown | 8 | 0 | 8 | 0 | 0 |
| live | 10 | 0 | 10 | 0 | 0 |
| work | 8 | 0 | 8 | 0 | 0 |
| born | 6 | 0 | 6 | 0 | 0 |
| is_multiword | 8 | 1 | 8 | 0 | 0 |
| is_of_form | 6 | 0 | 6 | 0 | 0 |
| taken_back | 6 | 2 | 6 | 0 | 0 |
| is_single_control | 8 | 8 | 8 | 0 | 0 |
| wh_control | 8 | 8 | 8 | 0 | 0 |
| statement_control | 7 | 7 | 7 | 0 | 0 |
| TOTAL | 85 | 26 | 85 | 0 | 0 |

- Yes/no families together: 293 62/62 = 100% (bar ≥ 90%; 138nb 3/62).
- 0 wrong (bar 0; 138nb 0). Wrong ids: none, either arm.
- taken_back: 6/6 right; 0 Yes on the 3 denial items (bar 0).
- 0 question writes (bar 0; 138nb 0). Write ids: none, either arm.
- Controls byte-identical to 138nb: 23/23 (reply and stores).
- Panel seal 5/5 OK; schema exact (85 items, spec families/counts/fields);
  138nb fidelity 85/85 vs the panel's `base138nb.jsonl`; schema gate
  clean on the scored rows (see D2).
- Per-item ids, families, stages and counts (no text): `run/m1/score-293.json`
  and `run/m1/score-138nb.json`.
- 293 stages on the panel: 59 `loop293-yesno+none`, 9
  `loop154d-yesno+none` (154d's own shapes, byte-identical), 3
  `loop138-nhop`, 6 `fake`, 1 `loop221-table-rekey`, 7 `none`
  (statement controls).

### M2: invpanel138nb + chainpanel266b (regression, 70 + 70, once per arm)

| Panel | 138nb rows | 293 rows | Moves |
|---|---|---|---|
| invpanel138nb | 70 | 70 | 0 |
| chainpanel266b | 70 | 70 | 0 |

Bar 0 moves: PASS (predicted 0/70 + 0/70).

### M3: frozen suites vs 138nb's rows

| Suite | Result | Predicted |
|---|---|---|
| sessions152 | 0 moves, GATE clean | 0 |
| bench (4 × 200) | 0 moves, GATE clean | 0 |
| marks123 | exactly 1 reply-only: `rt81-report.json:D_q_vs_s-04` OK → UNCLEAR | same 1 |
| rt136 | 16 moves vs 138j (13 WRONG-WRITE, 0 WRONG, 3 reply-only), identical to 138nb's own registered run; 0 field diffs 293-vs-138nb rows | same |
| rt143nogate (124 rows) | exactly 2: M3 Q2 → Yes, O5 Q2 → honest IDK | same 2 |

0 new WRONG, WRONG-WRITE, junk write or lost OK beyond the predicted
list: PASS. (rt136's NOT-clean GATE is pre-existing — see D3.)

### M4: restart and verifier dialogs (146 dialogs, 7 files, once per arm)

0 reply/event moves, 0 ghost answers, 0 write changes: PASS (predicted 0).

### M5: latency (158 turns × 4 reps, alternating arms)

Medians: base 2.16 / 2.12 ms, 293 2.55 / 2.43 ms → added ≤ +0.4 ms per
turn (bar ≤ +5 ms): PASS (predicted ≤ +5).

## Every move (ids only, never panel text)

- Dev (111 dialogs, registered once per arm): exactly the 72 predicted
  ids moved, every predicted reply and stage byte-exact, 0 unpredicted,
  0 missing, 0 writes. Moved ids (Q2 → Yes/No/IDK): dh-true1, dh-true2,
  dh-true-2word, dh-never1, dh-never2, dh-never-2word, dh-taken-forget,
  dh-taken-isnot, dh-corrected, dh-noart, ip-true-2word, ip-unknown-rel,
  ip-unknown-subj, ip-taken-forget, ip-taken-isnot, ip-ofform,
  ii-unknown-subj, ii-unknown-rel, ii-2word, ii-taken, dl-true, dl-false,
  dl-unknown, dl-2word-true, dl-taken-forget, dl-correct-new,
  dl-taken-isnot, dw-sameval, dw-diffval, dw-unknown, dw-2word, dw-taken,
  df-sameval, df-diffval, df-unknown, df-2word, df-taken, h-true,
  h-never, h-taken, n-hasgot-true, n-hasgot-uncle, n-hasgot-unknown,
  n-hasgot-2word, n-hasgot-taken, n-dh-multi-yes, n-dh-multi-unknown,
  n-dh-corrected, n-dh-noart2, n-dl-2word-false, n-dl-emp-only, n-dl-taken,
  n-dl-corrected, n-dw-yes, n-dw-no, n-dw-for, n-dw-2word, n-dw-taken,
  n-dw-unknown, n-df-yes, n-df-no, n-born-was, n-born-was-no,
  n-born-2word, n-born-taken, n-ip-multivalue, n-ii-multivalue,
  n-ii-multivalue-no, n-of-2word, n-of-no. Full predicted records:
  `predicted_moves293.json`. Still Q2 (predicted pass-through): the 5
  chain items, the inverted-wh boundary, the lowercase-subject item.
- M1: all 62 yes/no-family ids move toward right (per-item ids in
  `run/m1/score-293.json`); 23 control ids unchanged.
- M3: `rt81-report.json:D_q_vs_s-04`; rt143 `M3`, `O5` (above).
- Misses: none — every bar met, every move predicted.

## Deviations

- D1 (driver-only fix, disclosed): the sealed `scripts/claude_293_runall.sh`
  died instantly under `set -u` (`W` used on line 18, set on line 25)
  before any run. New file `scripts/claude_293_runall2.sh` (3-line diff:
  panel paths use `$R/work` directly) ran all registered M2–M5 steps.
  Sealed model/config/prediction files untouched (seal 10/10 OK after).
- D2 (driver-only fix, disclosed): the first M1 scoring attempt hit the
  panel's schema gate (exit 3, SCHEMA-MISMATCH — the arm runner wrote 2
  extra diagnostic fields). New file `scripts/claude_293_rowstrip.py`
  derived field-exact copies from the once-per-arm rows (no re-run, no
  text touched); the sealed scorer then ran clean on both arms. That
  VOID attempt scored nothing.
- D3: rt136 GATE NOT clean (13 WRONG-WRITE) is pre-existing 138nb-vs-138j
  behavior — 138nb's own registered `run/sd136` shows the identical 16
  moves; 293-vs-138nb rows have 0 field diffs.
- D4: pre-seal pilots ran dev293 twice (a reader bugfix in between);
  post-seal, every registered suite ran once per arm (M1 panel exactly
  once per arm). `scripts/claude_293_runall2.sh` and
  `scripts/claude_293_rowstrip.py` are post-seal disclosed drivers, not
  sealed files.
- Env: 1-min load 17–56 (bar 60), free disk 12 GB (bar 3 GB), 1 process
  per step, CPU only. No `timeout` command on this Mac (waits use
  sleep loops).

## What it means / what it doesn't mean

- Means: on questions like "Does Ana have a dentist?", "Does Ana live
  in Oslo?", "Is Oslo the city of Ana?" or "Has Ana got a coach?", 293
  answers from the notebook when it knows (Yes/No with the stored value
  named) and says "I don't know" when it doesn't — 85/85 on a blind
  panel the builder never saw, with zero wrong answers and zero writes.
  Everything else (who/what/where answers, statements, chains, frozen
  suites, restart behavior, speed) is unchanged from 138nb.
- Doesn't mean: the machine now understands every question — 7 dev
  shapes still get "didn't understand" (two-link chains like "Does
  Ana's boss live in Oslo?", odd word orders, lowercase names), work/from
  questions asked while only the city is stored get an honest "I don't
  know" instead of a Yes/No, and "No" is never said for multi-valued
  relations like sister or friend.

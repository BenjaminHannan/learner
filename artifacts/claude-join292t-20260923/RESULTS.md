# Exp 292t — RESULTS (registered verdict: PASS M1–M2–M3)

**Verdict: PASS.** The talking line's three layers (281 + 280/280b + 282/282b, in 280m's order) install
cleanly on main base 292 with no new behaviour: 292t agrees with the mechanical owner on 90/90 blind
panel turns, moves only the 5 pre-listed suite/probe rows (each owned by one layer), and matches or beats
292 on smalltalkpanel234. Seals: own 13/13 OK after the runs, panel 2/2 OK. No sealed file changed.
No re-runs: panel once per arm, suites/probes once, st234 once per arm.

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| M1 agreement 292t vs mechanical owner | 90/90 | 90/90 |
| M1 overlaps (2+ single-layer arms differing from 292) | 0 | 0 |
| M1 question-turn writes on 292t | 0 | 0 |
| M1 smalltalk-turn writes on 292t | 0 | 0 |
| M1 store diffs 292t vs 292 | 0 except owned | 0 |
| M1 old-sheet hits on 292t | report | 0 |
| M1 wrong called/control answers | 0 (director) | 0 moves; reply files listed below |
| M2 sessions152 moves | exactly the 3 listed | 3 (the same 3 ids) |
| M2 bench moves | 0 | 0 |
| M2 rt136 diffs (145 units) | 0 | 0 |
| M2 rt143 moves (124 rows) | 0 | 0 |
| M2 verifier vp moves (98 rows) | exactly N06+E04 | N06+E04 |
| M2 verifier vs moves (12 rows) | 0 | 0 |
| M2 GATE vs 292 | identical | identical (3/3) |
| M3 wellbeing 292t vs 292 (20 items) | ≥ | 17 vs 16 |
| M3 other items identical (36) | 36/36 | 36/36 |
| M3 writes / setup / store diffs | 0 | 0 |

## Every move, every miss, deviations

- **Moves (5 total, all predicted in P292t.2, each owned by one layer):**
  - S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9 (sessions152, reply-only,
    UNHELPFUL->UNHELPFUL, 0 writes): owner **280b** (281 arm: 0 moves, 282b arm: 0 moves on pilot).
  - N06 (verifier vp): owner **281** (281 arm moves exactly N06; 280b/282b arms move 0).
  - E04 (verifier vp): owner **282b** (282b arm moves exactly E04).
- **Misses: 0.** No panel miss, no suite miss, no probe miss.
- **Deviations: 0.** Panel ran once per arm after its seal checked OK; suites/probes ran once as a
  registered post-seal run; st234 ran once per arm and was never run pre-seal; no sealed file changed
  (own seal 13/13 OK re-checked after every run); no driver fix was needed.
- Not a deviation: 281 owns 0 blind-panel turns (all 12 called turns agree with 292 or another owner;
  agreement is unaffected). Not a deviation: 292's rt136 GATE string is NOT clean — it is inherited
  from 292 byte-identical, which is the registered bar.

## What it means / doesn't mean (plain high-school English)

- The three talking add-ons work on the new main base 292 exactly like they worked on the old base 260:
  on every one of 90 fresh test turns, the combined system gave byte-for-byte the same answer as the one
  add-on responsible for that turn (or the base when none was responsible).
- The add-ons change 5 things outside the panel, all written down before the test and nothing else:
  3 ability answers use the sealed honest text, 1 name question gets answered from saved notes, and
  1 greeting gets the normal greeting reply. None of them writes anything it shouldn't.
- This does NOT grade whether the answers are true or well written — the director checks that from the
  reply files below. It also does NOT test speed, and it does NOT prove anything about wordings that
  were never tested.

## Detail (categories only, never quoted)

- M1 (90 turns, 78 dialogs): ability 25/25, teach 8/8, called 12/12, smalltalk 25/25, mixed 10/10,
  control 10/10. Mechanical owners: 292: 65, 280b: 20, 282b: 5, 281: 0. Sealed-text replies on 292t: 19
  ability + 1 mixed; on 292: 10 ability + 1 mixed.
- M2 registered (runall + regscore292t.json, VERDICT PASS): sessions152 n_moves=3 reply-only;
  bench n_moves=0; rt136 145 rows 0 diffs; rt143 124 rows 0 diffs; vp diffs [N06, E04]; vs diffs [].
- M3 (56 items): wellbeing 292t 17/20 vs 292 16/20; other 36/36 identical; 0 writes; 0 setup/store diffs.
- Pre-seal pilot (not a mark): 66 own dev dialogs / 111 turns, 292t == mechanical owner 111/111,
  0 overlaps (280b fired 12 turns, 281 fired 4, 282b fired 0), 0 question writes, 0 old-sheet hits.
  Mock e2e in /tmp (not sealed): clean 8/8 PASS exit 0; overlap mock 7/8 FAIL exit 1; writes-only-diff
  owner PASS exit 0; empty exit 4; schema exit 3.

## Reply files for the director's claim check

- `artifacts/claude-join292t-20260923/run/panel-292t.json` (every 292t panel reply + per-turn stores)
- `artifacts/claude-join292t-20260923/run/panel-score292t.json` (owner + old-sheet scan per turn: 0 hits)
- `artifacts/claude-join292t-20260923/run/probes-292t.json` (canonical-probe replies)
- `artifacts/claude-join292t-20260923/run/regscore292t.json` (registered suite/probe verdict)
- `artifacts/claude-join292t-20260923/run/st234-292t.json` (smalltalk replies)

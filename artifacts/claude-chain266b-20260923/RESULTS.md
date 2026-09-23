# Exp 266b multi-word chain-subject lift: RESULTS

**Result: FAIL.** M1 misses one bar on the blind panel (broken_chain 9/12,
bar 12/12). Every other M1 bar passes, and M2, M3 and M4 pass exactly as
predicted, with 0 wrong values, 0 question writes and stored facts
identical on every panel row. One diagnosis note below; no re-runs, no
changes to sealed files after the seal.

266b = 266 + one detector change (`scripts/claude_fix266b_detector.py`,
via `scripts/claude_loop266b_agent.py`).
- Spec: `design/v3/30-modes/266b-multiword-chain-base.md`.
- Ledger lines P266b.1-6.
- Panels: `artifacts/claude-chainpanel266b-20260923/` (M1; present
  byte-identical to origin/builder-outbox, seal 5/5 OK from the repo root
  before running; never edited, never quoted below) and
  `artifacts/claude-chainpanel266-20260923/` (M2 regression; seal 5/5 OK;
  never read at item level, never quoted).
- Counts-only score JSON (ids, families, counts; no item text, no
  replies): `artifacts/claude-chain266b-20260923/run/panel266b-counts.json`
  (M1), `artifacts/claude-chain266b-20260923/run/panel266-reg-counts.json`
  (M2). Raw panel rows live in /tmp only and are not published.

## Marks

| Mark | What | Bar | Result (266 beside every figure) |
|---|---|---|---|
| M1 | Blind panel chainpanel266b, 70 items, one run per arm with the sealed scorer | multiword_chain >= 22/24 | 266b: 24/24 vs 266 6/24. **PASS** |
| M1 |  | three_link >= 7/8 | 266b: 8/8 vs 266 3/8. **PASS** |
| M1 |  | oneword_chain: no 266-RIGHT item lost | 266 RIGHT 8/8 ids; 266b RIGHT the same 8/8, replies byte-identical 8/8. **PASS** |
| M1 |  | broken_chain 12/12 honest abstain | 266b: 9/12 (ids c266b-046, c266b-050, c266b-052 other) vs 266 7/12. **FAIL** |
| M1 |  | 0 wrong over all 70 | 266b wrong 0/70 vs 266 wrong 0/70. **PASS** |
| M1 |  | 0 question writes | 266b: 0/70 vs 266 0/70; stored facts identical 70/70 rows. **PASS** |
| M1 |  | plain_control 8/8 + statement_control 6/6 byte-identical | 8/8 and 6/6 identical replies, stored facts and write flags. **PASS** |
| M1 | (no bar) my_live | reported | 266b 4/4 vs 266 4/4, replies identical. |
| M2 | chainpanel266 regression, 80 items, one run per arm | 0 new wrong; moves only the 8 cause-(b) ids | 8 moves, exactly the predicted ids, all OTHER -> RIGHT; other 72 ids byte-identical; 0 wrong; 0 writes. **PASS** |
| M3 | Frozen suites vs 266 saved rows | move sets = predicted; 0 new bad labels; exceptions identical | sessions152 0, bench 0, marks123 0 moves; rt136 15 = C019-C031 + C076 + C079 (exactly 266's set); direct vs 266 rows [] over 145 rows; exceptions 63/63; rt143 0 moves, 0 verdict flips. **PASS** |
| M3 | Restart + verifier vs 266 (115 dialogs, 7 restart audits) | 0 ghosts, 0 dup fails, 0 write changes, changes = predicted (none) | 0/0/0/0. **PASS** |
| M4 | Median latency, alternating processes 266/266b | <= +5 ms vs 266 | 1.976 vs 1.971 ms (+0.005 ms, 624 turns each). **PASS** |

## Every move

### M1 panel (ids only, never item text)

- multiword_chain RIGHT on 266b (24): the 6 already right on 266 plus 18
  lifted (other -> RIGHT): c266b-001, c266b-002, c266b-003, c266b-004,
  c266b-005, c266b-006, c266b-013, c266b-014, c266b-015, c266b-016,
  c266b-017, c266b-018, c266b-019, c266b-020, c266b-021, c266b-022,
  c266b-023, c266b-024.
- three_link RIGHT on 266b (8): the 3 already right on 266 plus 5 lifted
  (other -> RIGHT): c266b-025, c266b-026, c266b-030, c266b-031, c266b-032.
- oneword_chain: c266b-033-040 RIGHT on both arms, 8/8 byte-identical
  replies and stored facts.
- my_live: c266b-041-044 RIGHT on both arms, 4/4 identical.
- broken_chain: c266b-048, c266b-049, c266b-051, c266b-053, c266b-054,
  c266b-055, c266b-056 RIGHT (honest abstain) on both arms; c266b-045 and
  c266b-047 other -> RIGHT on 266b; c266b-046, c266b-050, c266b-052 other
  on both arms (052's reply changed 65 -> 66 chars with flags unchanged:
  other -> other, no wrong, no write).
- plain_control 8/8 and statement_control 6/6 identical replies, stored
  facts and write flags on both arms.
- No WRONG on either arm on any of the 70 items; stored facts identical
  266-vs-266b on all 70 rows.

### M2 panel (ids only, never item text)

- 8 moves, exactly the predicted cause-(b) ids, all OTHER -> RIGHT:
  c266-005, c266-008, c266-015 (chain_verb: 19 -> 22/30),
  c266-031, c266-032, c266-033, c266-035, c266-036 (chain_verb_three:
  1 -> 6/6).
- chain_possessive 10/10, broken_chain 12/12, plain_control 11 + 3 other,
  statement_control 8/8: identical verdicts on both arms.
- Reply diffs exactly the 8 moved ids; stored facts identical on all 80
  rows; 0 writes on either arm; the 266-arm run reproduces 266's
  registered numbers exactly (19/30, 1/6), confirming runner fidelity.

### M3 frozen suites vs 266 (run/score266b.json)

- sessions152: 0 moves. bench: 0 moves. marks123: 0 moves.
- rt136 (labels vs 138j, same method as 266): 15 moves = C019-C031 (13
  inherited 222 WRONG-WRITE) + C076 + C079 (reply-only), exactly 266's
  sealed set.
- rt136 direct vs 266 `run/sd136/rt136-rows.json`: moved = [] (145 rows).
- 63 inherited 222 exceptions identical to 266's rows: 13/13 + 25/25 +
  25/25 (rt136 `seconds` field excluded, as registered).
- rt143 no-gate vs 266 `run/rt143nogate-n.json`: 0 moves, 0 verdict
  flips (124 rows).

### M3 restart/verifier vs 266

- 5 M6 files (p3-dialogs, p3c-restart2, p3d-ghost, v-dialogs, v-supp):
  0 reply changes, 0 event changes, dup_ok on every audit.
- 138m probes.json (98 dialogs) + probes-supp.json (12 dialogs), vs
  266's `run/probe266.json` / `run/probe266-supp.json`: 0 reply
  changes, 0 ev/stored/triples changes, 7 restart audits clean.
- 0 ghost answers, 0 failed duplicate checks, 0 write changes.

### Dev (pre-seal pilot, 49 dialogs; mechanism check, not a gate)

- 26 lifts MISS -> RIGHT: e01-e26.
- 5 lifts MISS -> honest ABSTAIN: e31-e35 (e32 in the base's own
  three-word-base wording, verified on 138m itself).
- 4 untaught multi-word names MISS on all three arms: e27-e30 (no lift,
  no guess).
- 14 byte-identical 266-vs-266b: e36-e49 controls, statements and
  one-word chains.
- 0 question writes; equal event counts on all 49 dialogs, all arms.

## Diagnosis (the one note for the FAIL)

The 12/12 broken_chain bar is unreachable under the registered spec, and
the panel run shows exactly where: 2 of the 3 remaining others
(c266b-046, c266b-050, c266b-052) are the panel's untaught-head
last-word traps. The spec's falsifier #3 forbids lifting a multi-word
name the notebook does not hold (it would risk answering about the wrong
person, e.g. "Voss" for "Mara Voss's boss"), so 266b passes these
through by design; the base answers that verb shape with "I didn't
understand", which the sealed scorer (right = "i don't know" / "i
couldn't" only) counts as other, not abstain. The third other is a
taught-head item where no counted abstain resulted: the lift either did
not fire for it (the longest-first name match refuses a span whose full
base is not a stored triple subject) or the canonical path clarified;
either way it passed through with no guess and no write, and its flags
never moved toward wrong (052's reply changed by one char with flags
unchanged: other -> other). Nothing was guessed anywhere: 0 wrong and 0
writes on all 70 items on both arms, and stored facts are identical on
all 70 rows.

## Deviations

1. **Post-seal helper file (additive, not a sealed-file change).**
   `scripts/claude_266b_panelrun.py` (blind-panel runner mirroring each
   panel's sealed `run_base.py` one-for-one, parametric in panel and
   arm) was created after the seal to run each panel once per arm. It
   contains no agent logic, prints ids only (never replies or item
   text), and writes rows outside the sealed panel dirs. Sealed files
   verified unchanged after the runs (see below).
2. **Scoring method for the arms.** `chainpanel266b/score_panel.py` takes
   `<panel> <rows>` argv and was used as-is (sealed, unedited).
   `chainpanel266/score_panel.py` hardcodes its rows path, so each arm
   was scored by importing the sealed module unchanged with only the
   ROWS path pointed at the /tmp rows file (sealed file unedited; panel
   seal still 5/5 OK).
3. **M2 266-arm panel run started at 1-minute load 67**, above the 60
   gate (checked `uptime` immediately before; the driver gate applies to
   the heavy-suite driver). It is a ~1-minute light run that completed
   normally and reproduces 266's registered numbers exactly; every other
   registered step started at load <= 60.
4. **Panel rows are not published.** Raw rows live in /tmp only; the
   repo holds only counts JSON with ids, families and counts (no item
   text, no replies).

## Seal re-check (after all runs; sealed files untouched)

`shasum -c artifacts/claude-chain266b-20260923/SEAL.sha256.txt`: 21/21 OK.

## What it means (plain high-school English)

- Questions about a chain headed by a two- or three-word name now work:
  24/24 two-link and 8/8 three-link (266 managed 6 and 3). One-word
  chains, user-anchored chains and all controls are byte-identical to
  266, and the 8 old-266 misses on the regression panel are fixed with
  nothing else moving.
- Nothing ever guesses: 0 wrong values on all 150 panel items on either
  arm, 0 writes from questions, stored facts identical everywhere.

## What it doesn't mean

- It does not fix every broken chain: when the head name was never
  taught (the panel's 2 traps) the agent honestly says it doesn't
  understand instead of the counted don't-know wording, so broken_chain
  is 9/12, not 12/12. That is the registered FAIL above, not a guess or
  a wrong answer.
- It does not add question forms the base lacks (birthday and no-'s
  "my"-live forms are untouched by design) and it proves nothing about
  any other panel or base.

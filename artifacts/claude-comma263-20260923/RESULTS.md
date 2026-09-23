# Exp 263 — RESULTS: PASS (M1–M4 all PASS)

Blind panel M1 run once per arm on 2026-09-23 with the sealed scripts
(`bash scripts/claude_263_panel.sh artifacts/claude-comma263-20260923/run`).
Both seals checked OK from the repo root before the run
(comma seal 13/13 OK, panel seal OK). Schema check: SCHEMA OK.
Raw rows: `run/commapanel-263.jsonl`, `run/commapanel-260.jsonl`; score:
`run/commapanel-score263.json`, `run/commapanel-score.txt`.
M2 run once on 263 (`bash scripts/claude_263_openpanel.sh .../run`, openpanel
seal OK). M3/PROBES/M4 figures are from the sealed `run/regscore.txt`
(all PASS); M2's verdict is in `run/openpanel-score263.json` (PASS).

## M1 — blind commapanel263 (60 items), 260's number next to every figure

| bar | 263 | 260 | verdict |
|---|---|---|---|
| 0 stored subjects containing a comma over all 60 | 0 | 16 | PASS |
| unlisted_opener_teach ≥ 16/20 exact | 20/20 | 1/20 | PASS |
| comma_value_ok 0 lost vs 260 | 8/8, lost 0 | 8/8 | PASS |
| question 0 writes | 0 | 0 | PASS |
| control 14/14 right and byte-identical | 14/14, identical 14 | 14/14 | PASS |

Totals: 263 right 46/60, 260 right 27/60. Fidelity of my 260 arm vs the
writer's `base260.jsonl`: 60/60 identical, 0 diffs.

## Every move vs 260 on the panel (19 items, all toward right, 0 against)

- unlisted_opener_teach (19): c263-001 … c263-019 (260 stored a comma
  subject on c263-001 … c263-016, and stored nothing usable on
  c263-017, c263-018, c263-019; 263 stores the plain fact on all 20).
- comma_value_ok (0 moved): 8/8 on both arms, lost 0.
- question (0 moved): 4 misses on both arms (c263-043 … c263-046, gold
  not in reply), 0 writes on both arms.
- appositive_subject (0 moved, not a bar): 0/10 exact on both arms —
  store_ok holds on both (nothing comma-subjected stored) but the gold
  substring is in neither arm's followup reply (c263-021 … c263-030).
- control (0 moved): 14/14 on both arms, every reply byte-identical.

## M2 — openpanel260 run once on 263

Every 260 figure equal, 0 moves: opener_teach 20/20, opener_question 12/12,
greeting_question 8/8, bare_greeting 6/6, junk_guard 8/8 junk 0, name_trap
10/10 newly-wrong 0, junk writes 0/80, question writes 0, control 16/16
byte-identical. 0 items right-on-260 wrong-on-263, 0 new junk. PASS.

## M3 — suites vs 260's saved rows

- rt136 145/145 units, 0 moved; suitediff labels equal to 260's (13
  inherited C019–C031 + C076 + C079 + the predicted C122 stated-fact row).
- rt143_nogate 124/124, 0 moved, 0 verdict flips vs 260.
- sessions152 180/180, 0 moved. bench 4×200, 0 moved.
- 0 new WRONG, 0 WRONG-WRITE, 0 junk, 0 lost OK. PASS.

## M4 — latency

Median 260 1.859 ms, 263 2.101 ms, delta +0.243 ms (n 624 + 624),
bar ≤ +3 ms. PASS.

## PROBES — 138m verifier probes (reported, not a mark)

Changed rows exactly the predicted 7 (B15:t0, B15:t1, D08:t1, D10:t0,
D10:t1, E06:t0, E10:t0) with 260's exact reply/ev/triples; stored-set
changes exactly B15 and D10; 1 allowed new write (B15:t0, the user-name
save); supp 0 changes. PASS.

## Deviations

1. The retry trigger is wider than one literal reading of the design note:
   it also fires when the head never parses the opener turn at all
   (multi-word openers store nothing), because the panel's expect_store
   (the plain triple) requires saving the plain fact. Stated in the fix
   docstring and PASSMARKS known behavior before the seal; dev 20/20 and
   M1 20/20 confirm it.
2. A name-internal comma exemption (title/ordinal/abbreviation tail) was
   added after the first pilot showed 13 bench verdict flips on real
   names ("Washington, D.C.", titled names, "Hasbro, Inc."). Re-pilot and
   the registered run show 0 moves everywhere. Reported, not hidden.
3. The first `runall` invocation died in its load-wait (1-min load
   130–209, other agents busy) before any step ran; it was re-invoked
   once after the load dropped. No step ran twice; `run/uptime.log` shows
   the wait history.
4. `run/regscore263.json` contains an M2 error entry ("openpanel263.jsonl"
   not yet present) because `runall` scores all marks including M2, which
   runs later via its own sealed script. M2's verdict is in
   `run/openpanel-score263.json` (PASS). Cosmetic only; no sealed file changed.
5. No abstain flips were observed anywhere, so no 5× single-item
   follow-ups were needed. The TEST-ONLY panels were never read item by
   item and no item text is quoted here. No git push was made (OPUS-RULES
   forbids commits/pushes); all deliverables are present in the worktree.

## What it means (plain high-school English)

Starting a sentence with a casual opener the agent has never seen ("yo",
"get this", "real talk") no longer poisons the fact: the agent now saves
the plain fact underneath ("Kestrel's job is fisher") instead of saving a
junk name like "Yo, Kestrel" or saving nothing. Values that correctly hold
commas ("Tollan, Vesk") are untouched, questions still never write, and
every frozen suite, probe, and timing check is unchanged from 260.

## What it doesn't mean

It doesn't mean every comma shape is fixed: turns with two commas lose
the fact on purpose (single retry after the last comma), questions with
unlisted openers still get 260's didn't-understand reply, and names with
title commas ("Washington, D.C.") are deliberately passed through
untouched. This was one panel of 60 items plus the frozen suites, not
every sentence a user could ever type.

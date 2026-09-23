# Exp 266 chain-subject lift: RESULTS

**Result: FAIL.** M1 misses two bars on the blind panel (chain_verb 19/30,
chain_verb_three 1/6). M2, M3 and M4 all pass exactly as predicted, with 0
wrong values, 0 question writes and 0 reply changes anywhere outside the
lift. One diagnosis note below; no re-runs, no changes to sealed agent
files after the seal.

266 = 138m + one outermost ears stage
(`scripts/claude_fix266_chainlift.py`, via
`scripts/claude_loop266_agent.py`).
- Spec: `design/v3/30-modes/266-chain-subject-questions.md`.
- Ledger lines P266.1-6.
- Panel: `artifacts/claude-chainpanel266-20260923/` (copied unchanged from
  origin/builder-outbox; seal checked OK from the repo root before
  running; never edited, never quoted below).

## Marks

| Mark | What | Bar | Result (138m beside every figure) |
|---|---|---|---|
| M1 | Blind panel chainpanel266, 80 items, one run per arm with the sealed scorer | chain_verb >= 27/30 | 266: 19/30 vs 138m 8/30. **FAIL** |
| M1 |  | chain_verb_three >= 5/6 | 266: 1/6 vs 138m 1/6. **FAIL** |
| M1 |  | chain_possessive: no 138m-RIGHT item lost | 138m RIGHT 10/10 ids c266-037-046; 266 RIGHT the same 10/10, all byte-identical replies. **PASS** |
| M1 |  | broken_chain 12/12 honest abstain | 266: 12/12 (ids c266-047-058) vs 138m 12/12. **PASS** |
| M1 |  | 0 wrong over all 80 | 266 wrong 0/80 (1 abstain, 18 other) vs 138m wrong 0/80. **PASS** |
| M1 |  | 0 question writes | 266: 0/80 vs 138m 0/80. **PASS** |
| M1 |  | plain_control 14/14 byte-identical | 14/14 identical replies, stored facts and write flags. **PASS** |
| M1 |  | statement_control 8/8 byte-identical | 8/8 identical. **PASS** |
| M2 | Frozen suites vs 138m saved rows | move sets = predicted; 0 new bad labels; exceptions identical | sessions152 0, bench 0, marks123 0 moves; rt136 15 = C019-C031 + C076 + C079 (exactly 138m's set); direct vs 138m rows [] over 145 rows; exceptions 63/63; rt143 0 moves, 0 verdict flips. **PASS** |
| M3 | Restart + verifier (5 M6 files + 98 + 12 verifier dialogs = 115 dialogs, 7 restart audits) | 0 ghosts, 0 dup fails, 0 write changes, changes = predicted (none) | 0/0/0/0. **PASS** |
| M4 | Median latency, alternating processes | <= +5 ms vs 138m | 2.448 vs 2.489 ms (-0.04 ms, 624 turns each). **PASS** |

## Every move

### M1 panel (ids only, never item text)

- chain_verb RIGHT on 266 (19): the 8 already right on 138m plus 11
  lifted (MISS/OTHER -> RIGHT).
- chain_verb misses on 266 (11): c266-005, c266-008, c266-009, c266-015,
  c266-016, c266-017, c266-018, c266-019, c266-020, c266-023, c266-028.
  - 10 of 11 are byte-identical replies on both arms (the lift did not
    fire; OTHER on both).
  - c266-009 changed OTHER -> ABSTAIN (lift fired; canonical abstained).
- chain_verb_three: 1/6 RIGHT on both arms (same id); misses c266-031,
  c266-032, c266-033, c266-035, c266-036, all byte-identical on both arms.
- chain_possessive: c266-037-046 RIGHT on both arms, identical replies.
- broken_chain: c266-047-058 RIGHT (honest abstain) on both arms.
- plain_control 11 RIGHT + 3 OTHER on both arms, all 14 identical;
  statement_control 8/8 identical, 0 writes.
- No WRONG on either arm on any of the 80 items.

### M2 frozen suites vs 138m (run/score266.json)

- sessions152: 0 moves. bench: 0 moves. marks123: 0 moves.
- rt136 (labels vs 138j, same method as 138m): 15 moves = C019-C031 (13
  inherited 222 WRONG-WRITE) + C076 + C079 (reply-only), exactly 138m's
  sealed set.
- rt136 direct vs 138m `run/sd136/rt136-rows.json`: moved = [] (145 rows).
- 63 inherited 222 exceptions identical to 138m's rows: 13/13 + 25/25 +
  25/25 (rt136 `seconds` field excluded, as registered).
- rt143 no-gate vs 138m `run/rt143nogate-m.json`: 0 moves, 0 verdict
  flips (124 rows).

### M3 restart/verifier vs 138m

- 5 M6 files (p3-dialogs, p3c-restart2, p3d-ghost, v-dialogs, v-supp):
  0 reply changes, 0 event changes, dup_ok on every audit.
- 138m probes.json (98 dialogs) + probes-supp.json (12 dialogs): 0 reply
  changes, 0 ev/stored/triples changes, 7 restart audits clean.
- 0 ghost answers, 0 failed duplicate checks, 0 write changes.

### Dev (pre-seal pilot, 44 dialogs; mechanism check, not a gate)

- 14 lifts MISS -> RIGHT: d01-d14.
- 6 lifts MISS -> honest ABSTAIN: d17, d18, d20, d21, d22, d44.
- 24 byte-identical incl. the when-born boundary (d15, miss on both).
- 0 question writes; equal event counts on all 44 dialogs.

## Diagnosis (the one note for the FAIL)

The lift fires only when the placeholder probe yields exactly one one-hop
ask frame for the placeholder; 15 of the 16 panel misses are
byte-identical passthroughs in three shapes the specced gate cannot see:
(a) 5 when-birthday questions (c266-016-020) - no plain-name reader
exists for that form, so the probe clarifies (out of scope by design);
(b) 3 two-link + 5 three-link questions whose chain base is a two-word
name (c266-005, c266-008, c266-015, c266-031-033, c266-035-036) - the
detector assumes a single-token base, so the rewritten probe is
ungrammatical and clarifies; (c) 2 wh-city "my" forms with no 's in the
question (c266-023, c266-028) - the notebook-gated reader yields no ask
frame for the unknown placeholder. The 16th miss (c266-009) fired but the
canonical question abstained. Nothing was guessed: 0 wrong, 0 writes.

## Deviations

1. **Driver-only path fix after the seal (reported with diff).**
   `scripts/claude_266_runall.sh` wrote the M3b outputs as
   `run/probe266-probes.json` / `run/probe266-probes-supp.json` while the
   sealed scorer reads `run/probe266.json` / `run/probe266-supp.json`.
   Fix (no measurement re-run; the two files were renamed to the
   documented names and only the read-only scorer was then run once):
```diff
-  PY artifacts/claude-verify-20260922/138m/run_probes.py $AN $CN $W/probe266-$p \
-    $VM/$p.json $R/probe266-$p.json > $R/probe266-$p.log 2>&1
+  case $p in probes) o=probe266.json;; probes-supp) o=probe266-supp.json;; esac
+  PY artifacts/claude-verify-20260922/138m/run_probes.py $AN $CN $W/probe266-$p \
+    $VM/$p.json $R/$o > $R/probe266-$p.log 2>&1
```
   The sealed agent, config, cases, predictions and marks are untouched;
   `SEAL.sha256.txt` still verifies for every other file (the driver file
   itself now differs by these 2 lines, disclosed here).
2. **Post-seal helper file (additive, not a sealed-file change).**
   `scripts/claude_266_panelrun.py` (blind-panel runner mirroring the
   writer's `run_base.py` one-for-one, parametric in the arm) was created
   after the seal to run the panel once per arm. It contains no agent
   logic and reads no panel content beyond feeding turns.
3. **Scoring method for the 266 arm.** The sealed `score_panel.py`
   hardcodes its rows path, so the 266 rows were scored by a
   byte-identical copy (sha256 cc0642d1... verified) in /tmp with the 266
   rows in place of the rows file. The in-place sealed scorer was also
   run unmodified and reproduces the writer's README base table exactly.
4. **Load above 60 at the 138m panel-run start** (65.87; waited to 58.79
   before the 266 run). Load affects timing only; the 138m panel rows
   reproduce the sealed `base138m.jsonl` byte-for-byte (80/80), so no
   measurement was affected.
5. **Rows compared field by field.** The 63-exception check compares every
   field except rt136's wall-clock `seconds` field (registered in
   PASSMARKS before the seal).
6. **No 5x rerun was needed.** No unpredicted flip toward an abstain or
   "Was that a question?" occurred (M2/M3 move sets equal predictions
   exactly).

## What it means

The one change works where its gate can see the question: on the blind
panel it converts 11 chain-verb misses into answers (8 -> 19 right) with
no wrong value, no guess on any broken chain (12/12), no lost possessive
answer (10/10 kept), and no change at all to plain questions, statements,
restarts, frozen suites or speed. In plain English: the agent learned to
answer verb questions about "someone's someone" by re-asking itself the
possessive version it already knew, and it still says "I don't know"
instead of guessing whenever a link is missing.

## What it doesn't mean

- It does not mean the gap is closed: when-birthday chains, two-word-name
  chains and gated wh-city "my" forms still go unanswered (19/30 and 1/6
  miss the registered bars, so the verdict is FAIL).
- It does not mean anything about wording outside the panel: only the
  sealed 80 items were measured, each arm exactly once; nothing was tuned
  on the panel and no panel item is quoted anywhere in this report.
- The FAIL is a scope FAIL, not a safety FAIL: every safety bar held (0
  wrong, 0 writes, 0 ghosts, frozen suites and latency clean).

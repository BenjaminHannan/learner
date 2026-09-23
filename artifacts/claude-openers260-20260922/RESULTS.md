# Exp 260 — RESULTS: PASS (M1–M6 all PASS)

Blind panel M1 run once per arm on 2026-09-23 with the sealed scripts
(`bash scripts/claude_260_panel.sh artifacts/claude-openers260-20260922/run`).
Both seals checked OK from the repo root before the run
(openers seal 17/17 OK, panel seal 4/4 OK). Schema check: SCHEMA OK.
Raw rows: `run/panel-260.jsonl`, `run/panel-138m.jsonl`; score:
`run/panel-score260.json`, `run/panel-score.txt`. M2–M6 figures below are
copied from the sealed prior run `run/regscore.txt` (written 18:21,
all PASS); this handoff run did not re-run them.

## M1 — blind openpanel260 (80 items), 138m's number next to every figure

| bar | 260 | 138m | verdict |
|---|---|---|---|
| opener_teach ≥ 16/20 | 20/20 | 3/20 | PASS |
| opener_question ≥ 10/12 | 12/12 | 5/12 | PASS |
| greeting_question ≥ 7/8 | 8/8 | 1/8 | PASS |
| bare_greeting ≥ 5/6 | 6/6 | 3/6 | PASS |
| junk_guard 8/8 with 0 junk | 8/8, junk 0 | 0/8, junk 8 | PASS |
| name_trap: no item newly wrong vs 138m | 10/10, newly wrong 0 | 10/10 | PASS |
| 0 junk writes over all 80 | 0 | 13 | PASS |
| 0 question writes | 0 | 0 | PASS |
| control 16/16 right and byte-identical | 16/16, identical 16 | 16/16, identical 16 | PASS |

Totals: 260 right 80/80, 138m right 38/80. Fidelity of my 138m arm vs the
writer's `base138m.jsonl`: 80/80 identical, 0 diffs. 260 misses: 0.

## Every move vs 138m (42 items, all toward right, 0 against)

- opener_teach (17): o260-001, o260-002, o260-003, o260-004, o260-005,
  o260-006, o260-007, o260-009, o260-010, o260-012, o260-013, o260-014,
  o260-016, o260-017, o260-018, o260-019, o260-020
- opener_question (7): o260-022, o260-023, o260-025, o260-027, o260-028,
  o260-031, o260-032
- greeting_question (7): o260-033, o260-034, o260-035, o260-036, o260-037,
  o260-039, o260-040
- bare_greeting (3): o260-041, o260-042, o260-046
- junk_guard (8): o260-057, o260-058, o260-059, o260-060, o260-061,
  o260-062, o260-063, o260-064
- name_trap (0 moved): 10/10 on both arms, newly wrong 0
- control (0 moved): 16/16 on both arms, every reply byte-identical

## M2–M6 (from sealed `run/regscore.txt`, prior agent's registered runs)

- M2 suites: PASS. rt136 145/145 units, 1 moved (C122, the predicted
  stated-fact exemption); rt143_nogate 124/124, 0 moved; sessions152
  180/180, 0 moved; bench 4×200, 0 moved; 0 verdict flips.
- M3 sleep smoke: PASS (differing fields only .agent .config .label .seconds).
- M4 verifier probes: PASS (changed rows exactly B15:t0, B15:t1, D08:t1,
  D10:t0, D10:t1, E06:t0, E10:t0; 1 predicted new write B15:t0; supp 0).
- M5 restart dialogs: PASS (0 reply changes, 0 ghosts, 0 failed checks).
- M6 latency: PASS (median 138m 2.698 ms, 260 2.552 ms, delta −0.146 ms).

## Deviations

None. Sealed runner and scorer used unchanged; panel run exactly once per
arm (14 s total); no re-runs, no driver fixes, no new scorer.
`design/v3/30-modes/260-openers-opus.md` already existed (it is in the
seal), so no new design note was written. No abstain flips observed, so no
5× single-item follow-ups were needed. The TEST-ONLY panel was never read
item by item and no item text is quoted here.

## What it means (plain high-school English)

Starting a sentence with "so", "well", "please", "hey" or "hi" no longer
confuses the agent: it now hears the actual fact or question underneath,
saves the right name, and answers follow-up questions correctly. All 80
blind test items pass, and names that just happen to start with those words
are still saved correctly.

## What it doesn't mean

It doesn't mean the agent understands every casual opener — two tricky
shapes (a greeting glued to one name with no comma, an opener before a
two-word name with no comma) are still saved with junk on purpose, because
they look exactly like real titles. It also doesn't mean zero risk: this
was one panel of 80 items plus the frozen suites, not every sentence a user
could ever type.

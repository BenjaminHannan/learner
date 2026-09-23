# Exp 263 — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **263** = `scripts/claude_loop263_agent.py` + `artifacts/claude-comma263-20260923/loop263-config.json`
(260 + `scripts/claude_fix263_comma.py`, outermost; SrcGuardMixin228 first in the daemon MRO).
Base arm: **260** = `scripts/claude_loop260_agent.py` + `artifacts/claude-openers260-20260922/loop260-config.json`.
Design note: `design/v3/30-modes/263-comma-guard.md` (on `origin/claude/project-thread-p68q5v`; read, not copied).
Predicted moves (machine-readable): `predicted_moves263.json`.

The verdict is PASS only if M1–M4 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## Commands (from the repo root)

- M3/PROBES/M4: `bash scripts/claude_263_runall.sh artifacts/claude-comma263-20260923/run` (checks `uptime` before
  every step; scorer `scripts/claude_comma263_regscore.py` writes `run/regscore263.json`).
- M2: `bash scripts/claude_263_openpanel.sh artifacts/claude-comma263-20260923/run` — seal check of the openpanel260
  folder, then the panel once on 263 (`claude_comma263_run.py panel`), then M2 only of the regscore
  (263 figures vs 260's sealed `run/panel-score260.json`).
- M1: after the panel writer's `artifacts/claude-commapanel263-20260923/SEAL.sha256.txt` exists and checks OK:
  `bash scripts/claude_263_panel.sh artifacts/claude-comma263-20260923/run` — seal check, then schema check
  (`claude_comma263_score.py schema`; SCHEMA-MISMATCH → exit 3 → the run is VOID, reported, never scored by
  hand), then the panel once on 260 and once on 263 (`claude_comma263_run.py panel`), then the scorer.
- If the panel is not sealed 90 minutes after this seal (polled every 2 min): report and stop.

## M1 — blind commapanel263 (60 items), 260's number reported next to every figure

Scored exactly per `commapanel263-spec.txt` with `openpanel260-spec.txt` judgement rules (normalise = lowercase +
strip edge punctuation/spaces; junk = any triple stored after the turn or followup that is in neither
stored_after_setup nor expect_store; store_ok = expect_store ⊆ stored_after_turn and nothing else added;
question_write = a question turn or the followup changes the store; reply_ok = gold "" or gold ⊆ scored reply).
Scorer: `scripts/claude_comma263_score.py panel` (prints only ids, counts and flags, never item text).

| bar | pass if |
|---|---|
| 0 stored subjects containing a comma over all 60 | 263 count == 0 (260's count beside it) |
| unlisted_opener_teach | ≥ 16/20 exact |
| comma_value_ok | 0 lost vs 260 (no item right on 260 and wrong on 263) |
| question | 0 writes |
| control | 14/14 right and every reply byte-identical to base260.jsonl |

Also reported (not a bar): appositive_subject exact figures on both arms, fidelity of my 260 arm vs the writer's
base260.jsonl (all reply/store fields), and every miss on both arms by id.

## M2 — openpanel260 run once on 263 (no-regression check)

Scored with 260's sealed scorer functions (`claude_openers260_score.py`, read-only) against the writer's
`base138m.jsonl` and 260's sealed `run/panel-score260.json` figures
(opener_teach 20/20, opener_question 12/12, greeting_question 8/8, bare_greeting 6/6, junk_guard 8/8 junk 0,
name_trap newly-wrong 0, junk writes 0/80, question writes 0, control 16/16 byte-identical).
Pass = every 260 figure on 263 equal or better, 0 items right-on-260 wrong-on-263, 0 new junk, control 16/16
right and byte-identical. Predicted: figures exactly equal (80/80), 0 moves.

## M3 — frozen suites vs 260's saved rows (0 moves)

Suites: rt136 (145 units), rt143_nogate (124 rows), sessions152 (180 units), bench132_4hop, edit200,
new_121_4hop, old_s2fresh_4hop (200 each). Same commands and bases as 260's runall; rows compared directly with
260's saved `run/` rows (timing excluded), suitediff move labels compared with 260's saved diffs, rt143 verdicts
compared with 260's saved rows under rt143's own rule.
**Predicted moves (exactly this list): none — 0 moved units on all 7 files**, suitediff labels equal to 260's
(rt136 keeps 260's C122 move + labels vs the 138j base), 0 rt143 verdict flips vs 260.
Why: comma-subject teaches do not occur in these suites except name-internal commas ("Washington, D.C.",
titled names like "Tony Hall, Baron Hall of Birkenhead", "Hasbro, Inc."), which pass through like 260.
Pilot: 0 moved units everywhere; GATE clean on sessions152+bench; rt136 rows byte-equal to 260's.

## M4 — latency

`claude_merge138k_latency.py`, 2 reps, alternating processes 260,263 ×3 in the same session, on the p3 dialog files.
Pass = median(263) − median(260) ≤ **+3 ms** per turn. Pilot (1 pair, 1 rep, load ~125): +0.449 ms.

## PROBES — 138m verifier probes (not a mark; predicted, reported)

Compared with 138m's saved `rows-138m.json` / `supp-rows-138m.json`. Every changed row must be exactly 260's
predicted 7 (B15:t0, B15:t1, D08:t1, D10:t0, D10:t1, E06:t0, E10:t0, with 260's exact reply/ev/triples);
stored-set changes exactly B15 and D10; 1 allowed new write B15:t0; supp 0 changes. Pilot: exact match.

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and reported,
with whether the 228 guard was installed (the agent refuses to build without it).

## Dev set (not a mark; tuned on)

`devcases263.json` (55 dialogs, from `scripts/claude_comma263_devcases.py`), scored by
`claude_comma263_score.py dev`. Pilot: **263 55/55, 260 34/55**.
Families: unlisted 20, appositive 8, comma_value 6, question 6, control 8, restart 2, multcomma 1, pretend 4.
Gap reproduced: unlisted 0/20 on 260 (junk "Yo, Kestrel" stored, or nothing stored for multi-word openers).

## Known limits (predicted, not hidden)

- Name-internal commas pass through: "Washington, D.C.", titled names, "Hasbro, Inc." keep 260's exact stores.
  A comma subject whose tail starts with a plain name but is really a title ("Kennedy, John F.") would be
  mutilated by the retry; none occurs in the suites (pilot: 0 moves).
- "Yo, Mara's boss is Wren, obviously." (two commas): single retry after the LAST comma loses the fact
  (0 writes, save-failure reply) by design.
- Questions with unlisted openers keep 260's reply (didn't-understand); only 0 writes is barred.
- Pretend/correction markers (suppose/imagine/say/no/wait/sorry/anyhow-led chunks) are never stripped,
  exactly like 260's guard-only words.

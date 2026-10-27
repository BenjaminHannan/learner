# Exp 180b — silent case-insensitive known-name match on loop138h — PASSMARKS (sealed BEFORE any registered run)

Base: loop138h (`scripts/fable_loop138h_agent.py`, sealed rows in
`artifacts/fable-agent138h-20260922/`). ONE CHANGE, one mechanism
(`scripts/fable_loop180b_agent.py`: `Case180bMixin` outermost over
`Loop138hEars`, `Loop180bAgentLoop._listening_tick` display pass;
`Loop180bDaemon`, config identical in shape to 138h).

## The closed rule

`notebook_names180b(nb[, overrides])`: lower(name) -> canonical casing
for taught+active single-token subjects and single-token values
(multi-word values are phrases, never names — the 180-D1 guard) plus
the user's own name. The display path additionally honours the loop's
166c override map (an entity's Title-case override IS its canonical
render; resolving to the raw lowercase display would undo the sealed
166c display fix).

`resolve180b(text, names)`: every token/possessive matching a known
name in any case takes the canonical casing; every other byte kept.
Guard (166c ownership): a non-all-lowercase token is NEVER rewritten
to an all-lowercase canonical ("Biscuit" stays "Biscuit" when the
notebook holds "biscuit" — the base stores the surface as typed and
renders Title-case; 180b does exactly the same). Pretend `say ...`
turns skip both paths (echo quotes user bytes exactly, 0 writes).

Consequences (all silent, no confirms): lowercase asks reply in
stored casing (byte-identical to the capitalised twin); 165's
"Who is toms boss?" replies "Tom's boss is Lee."; lowercase teaches
naming only known entities save at once with the twin's events (no
second entity differing only in case); already-stored lowercase keeps
"I already have that."; unknown lowercase words and common words that
are not notebook names pass through byte-identical.

## K1 — sealed case file `case180b.json` (44 turns)

- 10 cap setup teaches A1-A10 (identical on both agents).
- 14 lowercase/mixed asks Q01-Q14 (1-hop, 2-hop, first-word-only,
  all-lowercase, 165 no-apostrophe Q11): PASS iff loop180b reply ==
  loop138h capitalised-twin reply with 0 writes.
- 8 lowercase teaches E1-E8 (both ends known entities, all facts new):
  PASS iff loop180b saves SILENTLY at once with reply == twin reply
  and full triple set == twin loop's triple set, 0 case-dupe entities.
- 12 traps X01-X12: X01/X02 unknown names, X03-X05 will/may/mark,
  X06/X07 rose (ask + save-new, events identical), X08/X09
  already-stored lowercase (expect exactly "I already have that.",
  0 writes; X09's base twin offers a change — the brief mandates
  already-have), X10/X11 say-pretend (byte echo, 0 writes), X12 kofis
  typo; non-expect traps PASS iff reply AND triple set byte-identical.
- K1 PASS = 44/44 step checks, every turn reported, never averaged.
  Driver: `scripts/fable_fix180b_probe.py`.

## K2 — frozen suites vs sealed loop138h rows (0 new WRONG/WRONG-WRITE/junk writes)

- redteam136 (145), redteam143 (124): 0 moves. bench121 4 splits
  (200 each): 0 moves, 0 new wrong. Driver:
  `scripts/fable_fix180b_suites.py`.
- sessions152 (180 turns): exactly 9 reply-casing-only moves, verdict
  OK on both sides, 0 writes (pilot evidence):
  S2 n7 "june's teacher is patel."->"June's teacher is patel.",
  n13 "wren's city is miami."->"Wren's city is miami.",
  n18 "marta's father's city is dallas."->"Marta's father's city is dallas.",
  n23 "marta's mother's city is boston."->"Marta's mother's city is boston.";
  S5 n4 "rosa's friend is Tess."->"Rosa's friend is Tess.",
  n5/n6 "tess's city is Omaha."->"Tess's city is Omaha.",
  n10 "vera's city is lima."->"Vera's city is lima.",
  n13 "ned's teacher is quinn."->"Ned's teacher is quinn."
- marks123 (`scripts/fable_marks123_all.py --agent
  scripts/fable_loop180b_agent.py --config
  artifacts/fable-case180b-20260922/loop180b-config.json --out
  artifacts/fable-case180b-20260922/marks180b`): per-case identical to
  `artifacts/fable-agent138h-20260922/marks138h/` after scrubbing,
  EXCEPT (pilot evidence): (a) reply-casing-only moves
  (rt110 L6 msg_02 "mira."->"Mira.", M5 "MIRA's city is
  Lisbon."->"Mira's city is Lisbon.", S2 "also mira."->"also Mira.";
  q1 m5_reply likewise; verdicts/writes/ok-flags unchanged, marks
  pass unchanged); (b) rt110 per-turn `statuses` arrays are
  timing-volatile (runner reads daemon.log.jsonl after outbox+done
  are visible but the daemon appends the log line after moving the
  file — a fresh rerun of the SEALED 138h code disagrees with its own
  sealed row: T3 msg_01 [] vs ["clarify"]); (c) sleep SKIP reason
  agent filename + summary agent/config paths (predicted renames);
  (d) total_seconds timing. Comparator:
  `scripts/fable_fix180b_comparem.py` (exit 0 iff only the above).
  Suite-level FAILs p3-l5z1, p4-1-nonpass, rt81 bug/unclear are
  inherited byte-identical from 138h (not new).

## G4 + etiquette

- Each registered run < 1500 s wall-clock Mac CPU,
  `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, offline; daemon wrappers
  take `idle_seconds`. Heavy suites one at a time. Never write to the
  repo-root notebook. Fictional names only. Every seed/case reported,
  never averaged.
- Sealed with the marks: `scripts/fable_loop180b_agent.py`,
  `scripts/fable_fix180b_probe.py`,
  `scripts/fable_fix180b_suites.py`,
  `scripts/fable_fix180b_comparem.py`,
  `artifacts/fable-case180b-20260922/case180b.json`,
  `artifacts/fable-case180b-20260922/loop180b-config.json`, this file.
  Any edit after the seal (code, config, cases, drivers, scorers)
  makes the registered verdict FAIL whatever a re-run shows. A FAIL
  is recorded as FAIL with one diagnosis note; no silent re-runs.

## Predictions pointer

Ledger block `## 2026-09-22 — Experiment 180b ...` with P180b.1-P180b.7
is appended to `artifacts/fable-predictions-ledger.md` BEFORE the runs.

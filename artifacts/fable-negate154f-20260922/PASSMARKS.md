# PASSMARKS — Exp 154f: plain negation removes a taught value (Muse)

Sealed before any registered run. Base: loop154e frozen rows in
`artifacts/fable-lang154e-20260922/` (bench rows, marks154e, g3 rows).
Every seed/case reported, never averaged. One change only versus
loop154e: `scripts/fable_loop154f_agent.py` (+
`scripts/fable_fix154f_negate.py`) adds the `negate_one154f` ears
pre-scan + action; every other turn falls through to the 154e stack
byte-identical. No 154e/154c/154b/138b file is touched.

## Sealed mechanism

Parser `parse_negate154f` matches ONLY single-hop
`X's R is not Y.` / `X's R isn't Y.` (one-word name anchored at turn
start, no `?`, no possessive in R or Y). Questions, multi-hop
negations, correct-not (`No, X's R is Y, not Z.`), forget shapes and
`Say`/`Pretend`/`Please say` prefixes never match. Unknown X falls
through (base unknown-name reply). Hit (Y current): notebook RETRACT
event — the same event kind 154c's correct-not path appends via
`nb.retract()` (`scripts/fable_loop154b_agent.py:165`) — retracting
exactly the rows showing Y. Miss (Y not current): 0 writes.

## Sealed reply forms

- Hit with remainers: `OK, Rana's language is not Hindi. I still have
  Urdu and Bengali.`
- Hit with none left (single-valued included):
  `OK, Kim's boss is not Lee. I don't have another boss for Kim.`
- Miss: `I don't have Tamil as Rana's language.` (0 new events).
- Unknown X / questions / multi-hop / pretend: loop154e reply
  byte-identical (unknown: `I can take one fact at a time — could you
  split that?`).

## N1 (sealed case file `case154f.jsonl`: 90 turns, 12 reset-segments)

- N1: 102/102 checks PASS (90 replies exact + 12 resets): 8
  multi-valued removals (named value gone, others kept, follow-up ask
  lists the rest); 6 single-valued removals (follow-up ask ->
  `I don't know Kim's boss.` etc.); 8 not-a-current-value (0 new
  events each); 4 unknown names (base reply, 0 events); 19 traps
  (correct-not, forget-one, `Say`, questions, 2 multi-hop negations,
  possessive value, `not` inside names/values, citizenship
  change-prompt + `no.`) reply- AND write-flag-identical to live
  loop154e. Every ask: 0 new events.
- Pre-seal evidence (open): all 90 pilot replies matched hand
  predictions (new) or live loop154e (traps); hit appends exactly one
  RETRACT event; miss/unknown/question/multi-hop append 0 events.

## N2 (regressions vs loop154e frozen rows; predicted move set below)

- G1 bench (4x200 vs `fable_bench121_loop154e_*_rows.jsonl`): 0 moves,
  0 new wrong. Predicted: EMPTY (pre-seal scan: 0 possessive-negation
  turns in all bench items; redteam136 C072 `Mira's city is not
  Lisbon.` runs on a fresh notebook where Mira is unknown, so the
  154f ears fall through to the base reply).
- G2 marks123 (per-case verdict+reply vs `marks154e`, every suite):
  per-case identical except predicted volatile lines (agent/config
  paths, sleep-SKIP agent filename, seconds, boot timestamps, random
  event_id hex, rt110 `statuses` log-flush race, l6
  `replied_before_kill` kill-timing race — l6 spawns the loop96
  daemon, not this agent). Suite numbers identical incl. inherited
  p3 l5z1/l5z2 FAILs and rt81 14 unclear. 0 new WRONG/WRONG-WRITE/junk
  writes. Predicted move set: EMPTY (scan: 0 negation turns in any
  marks123 case source).
- G3 redteam136 (145) + redteam143 (124) + sessions152 vs
  `g3/*-loop154e.json`: 0 moves, 0 new WRONG/WRONG-WRITE, 0 new
  writes. Predicted: EMPTY (scan: 0 negation turns in rt143 cases and
  all 180 session turns; C072/C075 fall through as above).
- G4: every registered run < 1500 s wall-clock Mac CPU with
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; daemon wrappers take
  idle_seconds=30.0.

## Deviation note (pre-seal, open)

Two pilot turns wrote to the repo-root `notebook/` (state_dir default
`.` in ad-hoc pilots). No further root-notebook writes after; all
drivers use isolated state dirs. `notebook/` is untracked scratch.

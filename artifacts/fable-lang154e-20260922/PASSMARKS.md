# PASSMARKS — Exp 154e: language becomes multi-valued (Muse)

Sealed before any registered run. Base: loop154c frozen rows in
`artifacts/fable-multival154c-20260922/` (bench rows, g3 rows, marks154c,
probe154c_cases.jsonl). Every seed/case reported, never averaged. One
change only versus loop154c: `is_multi154e` =
`MULTI_VALUED_154C + {"language"}` (`scripts/fable_fix154e_allowlist.py`);
citizenship and every other deny-listed relation stay single-valued.

## Sealed reply forms (154c's forms, extended to language only)

- Second language teach ADDS: `Saved: Rana's language is Urdu. (I also
  have Hindi.)` (3rd: `Saved: Rana's language is Bengali. (I also have
  Hindi and Urdu.)`) — no change-prompt, no overwrite.
- Language ask lists notebook order: `Rana's language is Hindi and
  Urdu.` (3+: `Hindi, Urdu and Bengali.` — no Oxford comma).
- Correct-not on language: `Saved: Rana's language is Tamil. (I also
  have Urdu and Bengali.)` (+ `(I didn't have {old}.)` when the named
  old value was not current); only that value removed.
- Forget-one on language: `Forgotten: Rana's language Urdu.` / miss:
  `I don't have Rana's language Punjabi.`; only that value removed.
- Repeat: `I already have that.` with 0 new facts (never stored twice).
- Citizenship/city/boss re-teaches: loop154c change-prompt
  byte-identical (`I have Rana's citizenship as India. Do you want me
  to change it to Nepal?` + `no.` -> `Okay, I left it as it was.`).
- Unknown people: loop154c replies byte-identical (`I don't know Zed's
  language.`). Taught values never overwritten by inferences (asks write
  nothing; verified: 0 new facts on every ask in the pilot).

## L1 (sealed case file `case154e.jsonl`: 76 turns, 5 reset-segments)

- L1: 76/76 exact (reply + every pinned state map + every full_state).
  Quotas: 8 two-language pairs (teach, teach, ask lists both); 4
  three-language triples (ask lists all three); 4 removals (2
  correct-not + 2 forget-one, each followed by an ask proving only that
  value left); 3 repeats (`I already have that.`, 0 new facts each);
  12 traps (citizenship x4 incl. change-prompt + `no.` + ask,
  city x3, boss x3, unknown-person asks x2) reply byte-identical to
  loop154c, scrubbed trap-segment events structurally identical
  (volatile random event_id hex suffixes excepted).
- Pre-seal evidence (open): all 76 pilot replies matched hand-written
  predictions; trap replies 12/12 equal live loop154c; repeat adds 0
  facts; trap events 10/10 structurally equal (same kinds/relations/
  functional flags/values/counts).

## L2 (regressions vs loop154c frozen rows; predicted move set below)

- G1 bench (4x200 vs `fable_bench121_loop154c_*_rows.jsonl`): 0 moves,
  0 new wrong. Predicted: EMPTY (pre-seal scan `trigger_scan154e.json`:
  0 language second-value/correct-not triggers in all 800 items).
- G2 marks123 (per-case verdict+reply vs `marks154c`, every suite):
  per-case identical except the predicted sleep-SKIP-reason agent
  filename line (`fable_loop154e_agent.py`) + volatile
  seconds/statuses; 0 case-moves, 0 whole-diffs; 0 new
  WRONG/WRONG-WRITE/junk writes. Predicted move set: EMPTY (scan: 0
  language flags in p2, rt110, rt81, q1, p4, p3-literals).
- G3 sessions152 + redteam136/143 vs `g3/*-loop154c.json`: 0 moves,
  0 new WRONG/WRONG-WRITE, 0 new writes. Predicted: EMPTY (scan: 0
  language flags in all three input sets; 154c already 0 moves vs
  138b there).
- Informational (NOT a mark; listed so nothing is silent): 154c's
  sealed `probe154c_cases.jsonl` through 154e differs in exactly 3
  replies (n=9 second language teach now adds; n=10 orphaned `no.` now
  `I wasn't waiting for an answer.`; n=11 ask now lists both) plus
  knock-on state maps in segment A only; segments B/C identical.
- G4: every registered run < 1500 s wall-clock Mac CPU with
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; daemon wrappers take
  idle_seconds=30.0.

## 167d composition (doc, no code)

`scripts/fable_fix167d_verb.py:69` rewrites `Rana speaks Hindi.` to the
possessive twin `Rana's language is Hindi.` (relation surface
`language` -> key `language` via the loop's lowercase+underscore map).
Under 154e that key is allow-listed, so verb-taught `speaks` values
accumulate multi-valued for free through the same `_act_multi_teach`
path; `What language does Rana speak?` rewrites to `What is Rana's
language?` and lists all values. Key-name check: 167d twin surface is
`language`, `relation_key154b("language")` = `language`, and
`is_multi154e("language")` = True — no mismatch; no alias (`languages`,
`spoken`, `speaks` as keys) is allow-listed, so only the canonical twin
path benefits.

Predictions ledger: P154e.1..P154e.8 (appended before any registered run).

## Sealed files (hashes in SEAL.sha256.txt)

- `artifacts/fable-lang154e-20260922/case154e.jsonl`
- `artifacts/fable-lang154e-20260922/loop154e-config.json`
- `artifacts/fable-lang154e-20260922/trigger_scan154e.json`
- `artifacts/fable-lang154e-20260922/PASSMARKS.md`
- `scripts/fable_loop154e_agent.py`
- `scripts/fable_fix154e_allowlist.py`
- `scripts/fable_fix154e_probe.py`
- `scripts/fable_fix154e_regress.py`
- `scripts/fable_fix154e_g3.py`
- `scripts/fable_fix154e_scan.py`

Open pre-seal helpers (NOT sealed, NOT registered):
`scripts/fable_fix154e_buildprobe.py` (wrote the L1 case file from a
pilot run; all 76 expects hand-predicted first, pilot matched 76/76).
Any code edit after the seal (including driver/scorer/case files) is
reported and the affected marks re-run in the open. A FAIL is recorded
as FAIL with one diagnosis note; no silent re-runs.

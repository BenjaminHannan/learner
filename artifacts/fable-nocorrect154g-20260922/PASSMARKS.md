# PASSMARKS — Exp 154g: "No," corrections replace on multi-valued relations (Muse)

Sealed before any registered run. Base: loop154e frozen rows in
`artifacts/fable-lang154e-20260922/` (bench rows, marks154e, g3 rows,
loop154e-config.json). Every seed/case reported, never averaged. One
change only versus loop154e: a bare explicit correction
("<No,|Actually,|Correction:> X's R is Y." with R multi-valued per
`is_multi154e`) replaces instead of adding
(`scripts/fable_fix154g_nocorrect.py` +
`scripts/fable_loop154g_agent.py`, subclassed read-only; no 154e/154c/
154b/138b file touched).

## Prefix lineage (found, listed)

- `scripts/fable_agent_loop.py:95` `_CORRECTION`: actually / no,.
- `scripts/fable_loop102_agent.py:92-95` `_CORRECTION_PREFIX_RE`:
  actually, / actually / no, / correction: / sorry-i-meant.
- `scripts/fable_fix154b_multival.py:83-86` `_NOT154B`: actually / no, /
  correction: / sorry, (the "Y, not Z" shape).
- `scripts/fable_fix160_barecorrect.py` docstring: actually, / no, /
  correction: / sorry-i-meant.
154g seals exactly three: "No," / "Actually," / "Correction:".

## Sealed reply forms (the one change; everything else 154e-identical)

- One current value: `Saved: Zara's language is Urdu. (It was Hindi.)`
  (base Saved correction style naming the old value). Events: one taught
  FACT (Listening._teach correction=True, the exact call the base
  "correct" act makes) plus one RETRACT of the replaced row -- the
  contract sets `supersedes` only on functional relations, so on a
  non-functional key this FACT+RETRACT pair is the replace (same two
  kinds the 154b correct-not path writes; never CONFLICT, never pending).
  Follow-up ask shows only the new value.
- Two or more current values: 0 writes +
  `Which one should Urdu replace: Hindi or Tamil?` (3+:
  `Which one should Urdu replace: Hindi, Tamil or Telugu?`). The next
  turn naming exactly one listed value (exact display match, optional
  trailing "."/"!", never "?") replaces that value (same mechanics and
  reply). Any other next turn cancels (0 writes) and is processed
  normally (it may itself open a fresh question).
- No current value: behaves like a plain teach (`Saved: ...`; for
  "Correction:" via an emulated plain teach, because the base stack
  misparses that prefix into a junk subject). Prefix-repeat of the
  single value: `I already have that.`, 0 writes.
- Plain teaches without a prefix keep adding (154e unchanged), as do
  correct-not (`Y, not Z`), forget-one, repeats, asks, quotes and every
  single-valued turn.

## C1 (sealed case file `case154g.jsonl`: 91 turns, 4 reset-segments)

- C1: 95/95 lines exact (91 turns + 4 resets; reply + pinned state maps
  + full_state + `events0` 0-event turns). Quotas: 8 one-value
  corrections (n=2,4,6,10,13,15,18,21, each replaced, follow-up ask shows
  only the new value); 6 several-value corrections (n=25/26,28/29,34/35,
  39/40,44/45,47/48: question, then the answer replaces the named
  value); 4 cancelled questions (n=52/53 ask-cancel, 56/57 teach-cancel,
  61/62 correct-not-cancel, 66/67 other-relation-cancel; 0 writes, next
  turn processed normally); 3 no-value corrections (n=69,71,72: plain
  teach); 19 traps (n=73-91: plain multi teaches, single-valued
  corrections, correct-not forms incl. miss, forget-one, repeat,
  quote-shape, unknown-person ask, citizenship change-prompt + `no.` +
  ask, no-value sister correction) reply byte-identical to loop154e with
  structurally identical events (entity ids normalised, volatile
  event_id hex suffixes excepted).
- Pre-seal evidence (open): pilot 95/95; trap differential 19/19
  reply-equal with structurally equal events; every question/cancel/
  repeat turn wrote 0 events.

## C2 (regressions vs loop154e frozen rows; predicted move set below)

- G1 bench (4x200 vs `fable_bench121_loop154e_*_rows.jsonl`): 0 moves,
  0 new wrong. Predicted: EMPTY (pre-seal scan
  `trigger_scan154g.json`: 0 bare-correction multi triggers in all 800
  items).
- G2 marks123 (`--marks
  p2,p3,p4,rt110,q1,bench,rt81,sleep,soak --workers 4`, compare vs
  `marks154e`): per-case identical except (a) the predicted sleep-SKIP
  agent filename line (`fable_loop154g_agent.py`), (b) volatile seconds,
  (c) rt110 log `statuses` harness race (proven volatile: the harness
  reads daemon.log.jsonl the moment the reply lands in done/, but
  process_file moves the file before appending the turn event, so a fast
  poll observes `[]`; the daemon log written moments later always holds
  the full records -- the compare driver verifies each such leaf against
  the case workdir daemon log and only passes it as `race_confirmed`).
  0 real moves, 0 new WRONG/WRONG-WRITE/junk writes, bench reply texts
  all identical. Predicted move set: EMPTY (scan: 0 flags in
  p2/rt110/rt81/q1/p4/p3-literals). p3 FAIL (l5z1/l5z2) and rt81 FAIL
  (60/0/14) are pre-existing bars inherited byte-identical from
  marks154e.
- G3 sessions152 + redteam136/143 vs `g3/*-loop154e.json`: 0 moves,
  0 new WRONG/WRONG-WRITE, 0 new writes. Predicted: EMPTY (scan: 0 flags
  in all three input sets).
- G4: every registered run < 1500 s wall-clock Mac CPU with
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; daemon wrappers take
  idle_seconds=30.0.

Predictions ledger: P154g.1..P154g.6 (appended before any registered run).

## Sealed files (hashes in SEAL.sha256.txt)

- `artifacts/fable-nocorrect154g-20260922/case154g.jsonl`
- `artifacts/fable-nocorrect154g-20260922/loop154g-config.json`
- `artifacts/fable-nocorrect154g-20260922/trigger_scan154g.json`
- `artifacts/fable-nocorrect154g-20260922/PASSMARKS.md`
- `scripts/fable_loop154g_agent.py`
- `scripts/fable_fix154g_nocorrect.py`
- `scripts/fable_fix154g_probe.py`
- `scripts/fable_fix154g_regress.py`
- `scripts/fable_fix154g_g3.py`
- `scripts/fable_fix154g_scan.py`

No open pre-seal helpers: the case file was hand-written (all 91
expects hand-predicted first, open pilot matched after two diagnosed
code fixes: a regex group bug and the Correction:-vs-137-upgrade
cross-check). Any code edit after the seal (including
driver/scorer/case files) is reported and the affected marks re-run in
the open. A FAIL is recorded as FAIL with one diagnosis note; no silent
re-runs.

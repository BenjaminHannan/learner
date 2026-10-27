# RESULTS — Exp 154e: language becomes multi-valued (Muse)

Base: loop154c (`scripts/fable_loop154c_agent.py`), subclassed read-only;
no 154c/154b/138b file edited. Agent: `Loop154eAgentLoop`
(`scripts/fable_loop154e_agent.py`). The one change: `is_multi154e` =
`MULTI_VALUED_154C + {"language"}` (`scripts/fable_fix154e_allowlist.py`).
Citizenship and all other deny-listed relations keep the loop154c path
byte-identically. Full design:
`design/v3/30-modes/154e-language-multi-muse.md`.

## The one change versus loop154c (sealed forms)

Second language teach ADDS (`Saved: Rana's language is Urdu. (I also
have Hindi.)`); language asks list notebook order (`Rana's language is
Hindi and Urdu.`, 3+: `Hindi, Urdu and Bengali.`); correct-not /
forget-one on language remove only that value; repeats say `I already
have that.` with 0 new facts. Citizenship/city/boss re-teaches keep the
change-prompt; unknown-person asks keep `I don't know ...`.

## Marks table (integer counts, every seed/case reported)

| mark | bar (sealed) | number | status | secs |
|---|---|---|---|---|
| L1 probe (76 turns, 5 segs) | 76/76 exact | 81/81 lines (76+5 resets) | PASS | 0.1 |
| quotas | 8 pairs / 4 triples / 4 removals / 3 repeats / 8+ traps | 8 / 4 / 4 (2 correct-not+2 forget) / 3 (0 new facts each) / 12 traps, 12/12 reply-equal to 154c | PASS | — |
| G1 bench 4x200 | 0 moves, 0 new wrong (predicted EMPTY) | 0 moves, 0 new wrong | PASS | 43.9 |
| G2 marks123 | per-case identical except predicted sleep filename + volatile | 11/11 reports identical; raw diffs only timings + 1 sleep reason line; bench reply texts 5150/5150 identical | PASS* | 252.6 |
| G3 rt136/rt143/sessions | 0 moves, 0 new wrong/write (predicted EMPTY) | 145/124/6 sessions: 0 moves, 0 new wrong | PASS | 6.7 |
| probe154c differential (info) | exactly n=9,10,11 reply moves | exactly n=9,10,11; segs B/C identical | HELD | — |
| G4 clock | every run < 1500 s | max 252.6 | PASS | — |

*G2 suite verdicts p3 FAIL (l5z1 58/60, l5z2 149/50/0/1) and rt81 FAIL
(60/0/14) are inherited byte-identical from marks154c (pre-existing
bars); 0 case-moves, so G2 PASSES its regression bar.

Predictions: P154e.1 TRUE | P154e.2 TRUE | P154e.3 TRUE | P154e.4 TRUE |
P154e.5 TRUE | P154e.6 TRUE (static; no mismatch found) | P154e.7 TRUE |
P154e.8 TRUE. 8/8.

## Deviations / notes

1. Open pre-seal helper `scripts/fable_fix154e_buildprobe.py`
   (un-sealed) generated the L1 case file; all 76 expects
   hand-predicted first, pilot matched 76/76. Sealed files untouched
   (`shasum -c SEAL.sha256.txt` 10/10 OK post-run).
2. Trap-segment events: structurally identical to loop154c (same
   kinds/relations/functional flags/values/counts); only random
   event_id hex suffixes differ per run.
3. `*-tmp` daemon workdirs differ run-to-run only in timestamps,
   random ids and hash-chain prefixes; all 5150 bench reply texts
   identical; no open re-runs (one registered run per suite).

## Questions for Ben

None — ruling implemented exactly: language accumulates, citizenship
still replaces.

## Reproduce (Mac CPU, offline)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154e_probe.py --cases artifacts/fable-lang154e-20260922/case154e.jsonl --out artifacts/fable-lang154e-20260922/probe154e --state-dir <fresh-dir>
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154e_regress.py --bench
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154e_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154e_regress.py --marks p2,p3,p4,rt110,q1,bench,rt81,sleep,soak --workers 4
```

## What it means

A person can now have more than one language: second teaches add
instead of prompting, asks list every value oldest-first, and the
existing removal forms delete one value at a time, while citizenship,
city, boss and all frozen suites behave exactly as before.

## What it does not mean

It does not make citizenship or any other relation multi-valued, and it
does not stack the 167d verb layer (the `speaks` composition is Gabor
only, verified statically, not run here).

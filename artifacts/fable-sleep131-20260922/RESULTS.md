# Exp 131 RESULTS — taught beats sleep (fix for the exp-116 E finding)

The one-change fix works. On `Sleep131Daemon`, taught gran facts win:
E2/E3/E4 answer Z01/Z02/Z03 with source `taught`, and every other sealed
verdict is unchanged. **MARKS T1–T5 PASS, 5/5. Ledger P131.1–P131.5 all TRUE.**

## The fix in one paragraph

`Sleep104Reasoner.answer` sent every bare-word question straight to the
installed mother+mother derivation, so an installed rule shadowed a
directly taught word-fact. `Sleep131Reasoner` (new file,
`scripts/fable_sleep131_agent.py`, subclass only) checks first: if the
notebook has an ACTIVE TAUGHT row for the asked (entity, word), it
answers from that row with source `taught` and the row's own fact_id as
trail; otherwise it behaves exactly as 104, including the identical
single episode-queue call. Sleeper, recipe, gate, logging, word/marker
filenames: untouched (`Sleep131Daemon` inherits `process_file` verbatim).

## Marks (every seed/case reported, never averaged)

| mark | result |
|---|---|
| T1 E-family re-run (seed 15) | PASS: installed (8 eps, OOF 1.0, agree 1.0), rows stored 3/3; E1 OK; E2/E3/E4 answer Z01/Z02/Z03, source `taught` 3/3 |
| T2 other 116 cases vs rescored report | PASS: 33/33 verdicts identical (all OK; C3 aggregate also matches); B/D/F derivations stay sleep-derived |
| T3 exp-104 marks Z1–Z5 (class swap) | PASS: seeds 1/2/3 install 20 eps, 5/5 probes sleep-derived, taught 50/50, 0 overwrites, 0 wrong installs; Z4 pass (200/200 taught, restore 5/5); Z5 noise4 install 5/5, noise8 refuse + 5 abstain, 0 wrong |
| T4 teach AFTER sleep (seed 31) | PASS: TA taught Z01 source `taught` trail [F00026] ow 0; TB control H02 source sleep-derived trail heads report F00025 |
| T5 wave budget | PASS: 815 s wall (< 1800), Mac CPU, OMP=1/MKL=1 per process |

Wave: e116 735.2 s + z104 407.7 s in two parallel processes, then t4
72.6 s; total 815 s start-to-finish. Seeds 11–21, 1–3, 31; one training
per process, shared machine.

## Deviations

- D1 (checker, not daemon): the reused 116 driver looks up turn records
  by bare probe name ("p01") while the log stores mailbox names
  ("p01.txt"), so raw 131 output showed F1/F2 BUG and empty src fields —
  the same checker bug as exp-116 D3. Rescored read-only from frozen
  evidence (`scripts/fable_sleep131_rescore.py`, no daemon booted):
  `wave-report-116-rescored.json`, `t4-rescored.json`, `t-marks.json`.
  Raw files kept. Verdicts above are the rescored ones.
- T2 counts 33 (C3a/C3b in, C3 aggregate out); the aggregate matches too.
- Parallel processes were used to fit the ~735 s 116 re-run plus the
  104 re-run inside the 1800 s budget, as T5 allows; each stayed
  single-threaded (OMP=1/MKL=1).

## Questions for Ben

None. The open question from 116 (block install vs answer-time
taught-wins) is settled by evidence for answer-time: taught wins at
answer time with zero notebook damage, and installs still serve
derivations where nothing was taught.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
--python 3.12 --with torch --with numpy python -B \
scripts/fable_sleep131_drive.py --only e116   # + z104, t4
Rescore (read-only): `python -B scripts/fable_sleep131_rescore.py`
Seal: `shasum -a 256 artifacts/fable-sleep131-20260922/PASSMARKS.md`
(hash abe0db57… in SEAL.sha256.txt, sealed pre-run).

## What it means

A taught fact now beats a sleep-installed inference at answer time, with
no change to training, gating, provenance, or any previously passing
behaviour: 33/33 old verdicts and all Z1–Z5 fields identical.

## What it does not mean

One word slot and small families only; a taught fact that arrives
*before* an install blocking/qualifying the install itself was not
tested, and noisy mixes beyond 116's families were not re-attacked.

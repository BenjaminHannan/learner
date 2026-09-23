# Exp 122 RESULTS — learned intent classifier, fresh blind panel (Muse, 2026-09-22)

Registered FAIL. One run, 3.7 s, Mac CPU, offline. The frozen learned router
(`scripts/fable_self122.py`, sha
ce11b15b516d75097fc357760d3c9928a1aa5b14136a24e7109a4e6f4d162112;
head weights sha 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25,
both hashed into PASSMARKS.md and sealed BEFORE the run, ledger P122.1–P122.5
appended before the run) rebuilt the exact exp-99 session (gate exact: 19
taught, 6 people, 1 quarantine, 2 corrections, 1 forgotten, 0 sleeps, 26
turns) and answered the 100 sealed fresh blind questions via `answer_self()`
with no new turns. Panel seal verified OK before scoring; router and head
hashes re-verified in-run. Answer bodies inherited untouched from exp 99 via
exps 105/114; only the scorer is new (frozen MiniLM encoder + trained
41-way head, seed 12202, tau=0.6, mu=1.5).

## Marks (integers, never averaged)

| mark | bar | got | verdict |
|---|---|---|---|
| K1 | WRONG == 0 over all 100 | 3 wrong | FAIL |
| K2 | CORRECT >= 45/70 on existing-intent rephrasings | 44/70 | FAIL (by one) |
| K3 | TRICK 10/10 decline | 10/10 | PASS |
| K4 | exp 99's 40 still 40/40 and exp 100's 80 WRONG == 0 | 40/40 and 0 | PASS |

Split of the 100: 44 CORRECT, 53 HONEST_DECLINE, 3 WRONG. Existing-C: 44
correct / 16 decline / 0 wrong. Existing-D: 10/10 decline. New: 17/20
decline, 3 wrong. Trick: 10/10 decline. Zero hallucinated names/numbers:
all 3 WRONGs state live-state-true neighboring-intent content (verbatim in
`WRONGS.md`). The scope guard fired on 14 of the 100 (all declines that
already declined or still decline); the 3 WRONGs carry no scope trigger by
design. Unregistered dev context, same invocation: exp-105 panel 0 WRONG,
exp-114 panel 0 WRONG (both 100/100, as at freeze).

## Reading the FAIL honestly

Coverage more than doubled over exp 114 (17 → 44 existing correct) with zero
existing-intent misfires — the vocabulary ceiling lifted. The remaining
failure is over-answering novel blends: all 3 WRONGs are NEW intents phrased
next door to a trained intent (percentage-confidence about Paris → C15;
French translation about Mira → C5; relation-type counting → C29/C28), each
passing the confidence bar the dev panels set. K2 missed by a single
question: 16 honest declines on oblique existing phrasings. The decline path
is intact (53/100 honest declines, tricks perfect), so the failure is
precision on near-intent novelty, not honesty.

## What it means

A frozen borrowed encoder with a small trained head generalises far past
keywords (44/60 existing-C correct vs 17/70 overall before) while keeping
every safety property: guard-first, margin/confidence declines, no invented
names/numbers, K4 regressions green.

## What it does not mean

Not a knowledge failure (every value stated was live-state true) and not a
fix for adversarial novelty: questions that borrow an intent's vocabulary
for a new task still clear the bar. No claim about real-English ears: this
tests the scaffolding router only.

## Deviations and notes

D0: pre-run change of frozen constants only (my own runner file, router and
head untouched): runner asserts router + head hashes and the panel seal.
D1–D3 as in design doc 122 (MiniLM via our loader; diag script; type-guard
kept as restrictor). Training 10.3 s on Mac CPU (< 15 min budget). No
questions for Ben.

## Reproduce

```bash
shasum -c artifacts/fable-self122-20260922/SEAL.sha256.txt  # seals PASSMARKS.md (pre-run)
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_self122_runner.py --run --out artifacts/fable-self122-20260922
```

New files only (`fable_self122_` prefix + artifact folder + doc 122):
`scripts/fable_self122_data.py` (training data), `scripts/fable_self122_train.py`,
`scripts/fable_self122_diag.py` (dev-only printer), `scripts/fable_self122.py`
(frozen router), `scripts/fable_self122_runner.py`,
`artifacts/fable-self122-20260922/` (PASSMARKS, SEAL, data, head, report,
RESULTS, WRONGS, results JSON, notebook state), design doc 122.

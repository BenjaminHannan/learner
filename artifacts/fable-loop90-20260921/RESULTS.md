# Exp 90 RESULTS — integrated loop (Muse, 2026-09-22)

One loop composes every verified piece; the real ears/mouth drop in without
touching it. All five sealed marks PASS. No other agent's files touched; no
commits; Mac CPU; offline.

## Marks table (integers, every seed/case reported, never averaged)

| mark | result |
|---|---|
| Z1 60-turn acceptance through the mailbox | 60/60 statuses match, 0 wrong writes, boot_ok, 5.1 s — PASS |
| Z2 Fable-Edit-200 through the loop notebook | 150 correct + 50 abstain_ok = 200/200, 0 WRONG, 0 WRITE_FAULT, 0 pending stalls, 2.9 s — PASS |
| Z3 69 core + 56 web red-team cases by import | core 64 OK / 3 BUG / 2 UNCLEAR, web 53 OK / 1 BUG / 2 UNCLEAR — verdicts identical to sealed baselines (0 new, 0 changed); 8/8 loop-notebook/thinker checks — PASS |
| Z4 kill-9 + restart (D2 helpers reused) | seed 1: 200/200, 0 wrong, 0 dupes; seed 2: 200/200, 0 wrong, 0 dupes; seed 3: 200/200, 0 wrong, 0 dupes; chain_ok all three; 13.7 s — PASS |
| Z5 `--config` plug-point document | 6/6 plugs documented, file-built loop smokes OK, all 5 Protocols hold — PASS |

Z3 non-OK ids are exactly the sealed ones: core RT40 UNCLEAR, RT49b/RT65/RT66
BUG (the three fix77 findings), RT68 UNCLEAR; web RT79-09 UNCLEAR, RT79-18
BUG, RT79-53 UNCLEAR. Z2: all 575 teach turns took the bench73 stage (score
1.0 ≥ tau-hat 0.088756); the FakeEars stage never fired; ears47 absent (no
checkpoint under `artifacts/fable-ears47-20260921/runs/`, recorded skip).
Thinker resolved to exp-89 `QuarantinedThinking89` (module existed at run
time). Wave total ≈ 31 s + harness overhead, far under the 30-min bar.

## What it means

The verified parts (sealed notebook, fix77 gate + reasoner, bench73 ears,
certified abstention gate, exp-46 sleep recipe, m2/exp-89 thinker, daemon74
mailbox) now run as one agent: teach it in English, ask it, kill -9 it, and
it keeps every fact with 0 wrong writes.

## What it does not mean

The ears and mouth are still stand-ins (template parsers/sentences, not the
neural rung-2/mouth53 models), and no live sleep install fired here (episode
feed idle); the loop is integration-proven, not linguistically general.

## Deviations

None from the brief. Two judgments: (1) Z3 "against the loop's
notebook/thinker" = probes imported unmodified (their writers redirected to
the exp-90 dir) plus 8 doctrinal checks on the actual Loop90Notebook/thinker,
since probe cases build their own isolated notebooks by design. (2) Z2 drives
each item through a fresh loop from the same factory (bench73 semantics are
per-item isolated notebooks) rather than one shared notebook.

## Questions for Ben

None.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_loop90_marks.py --mark all` (reads PASSMARKS.md sealed as
`SEAL.sha256.txt`; predictions P90.1–P90.6 in `artifacts/fable-predictions-ledger.md`).

# Experiment 57 — wiring end-to-end: sleep installs "grandmother" (2026-09-21)

**PASS**, all marks W1–W6, predictions P234–P237 **4/4 TRUE**. Marks sealed
(`PASSMARKS.md` + `SEAL.sha256.txt`) before the registered 3-seed wave.

## Marks (integer counts, every seed reported, never averaged)

| Mark | need | 5701 | 5702 | 5703 |
|---|---|---|---|---|
| turns | 80 | 80 | 80 | 80 |
| W1 attempts | ≥ 1 | 1 | 1 | 1 |
| W2 gate recorded | recorded | accepted | accepted | accepted |
| W3 new-people probes | 5/5 or MISS 5/5 | 5/5 | 5/5 | 5/5 |
| wrong answers on probes | 0 | 0 | 0 | 0 |
| W4 wrong writes | 0 | 0 | 0 | 0 |
| W5 hash chain verifies | yes | yes | yes | yes |
| W6 wave < 15 min | — | 72.3 s | 73.0 s | 70.7 s |
| episodes queued | ≥ 20 | 20 | 20 | 20 |
| OOF best / refit agreement | — | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| bridge | — | down (skipped, no mark) in all 3 |

Session: 50 mother-chain teaches (20 train + 5 test triples), 20
"Who is Kxx's maternal grandmother?" episode questions, 5 fillers, auto-sleep
at experience 75, then 5 "Who is Txx's maternal grandmother?" probes on NEW
people. FakeEars is a declared stand-in emitting the same action dicts the
English ears would.

## What this means

- The two paths wire51 never exercised now run: sleep attempted exactly one
  install per seed on 20/20 queued episodes and the gate accepted 3/3 with a
  perfect CV table (OOF 1.00, agreement 1.00).
- The installed word generalises: 5/5 grandmother answers on people never seen
  in the episodes, with 0 wrong answers and 0 wrong writes anywhere.
- The loop is intact: audit clean, notebook hash chain verifies from genesis,
  whole wave ≈ 4 min.

## What this does not mean

- **Not an English-learning demo.** FakeEars bypasses parsing; the Qwen
  bridge was down, so the real-ears run was skipped. The parser's rejection
  of "maternal grandmother" (wire51 deviation 3) is untouched.
- **Not a dense-village gate.** The regression probe was 128 questions
  (64 hop-1 + 64 hop-2); hop-3 was untestable because taught chains are only
  2 deep. The install decision itself used the unchanged Exp-46 rule.

## Deviations from plan

1. **Base net fixed to sealed base-seed4102.pt** in all seeds (no 5701+
   checkpoints exist; training fresh bases would break the clock). Seeds
   5701–5703 drive only the sleeper's gate RNG.
2. **Village-sized probe** (`SparseVillageSleeper` in my file): best-effort
   64 per hop length, skip lengths with < 4 resolvable. Gate thresholds
   unchanged; unchanged-rule stays exact equality.
3. **Word bridge**: after an accepted install the script copies the hardened
   `words.0` logits into the loop's own reasoner50 (`load_word`). Adapters
   save the checkpoint but never load it — without this the reasoner would
   keep abstaining. Read-only copy, nothing else edited.
4. **Phased run** (75 turns, sleep, bridge, 5 probes) — one 80-turn session;
   phasing only lets the install land before the probes.

## Predictions (ledger P234–P237, written before the wave)

P234 TRUE (1 attempt 3/3). P235 TRUE (accepted 3/3). P236 TRUE (5/5 probes
3/3, never wrong). P237 TRUE (0 wrong writes, chain verifies 3/3). **4/4.**

## Reproduce (exact command)

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_wire57_e2e.py --root artifacts/fable-wire57-20260921/runs --report artifacts/fable-wire57-20260921/wave-report.json
```

## Artifacts

- `scripts/fable_wire57_e2e.py` — session builder, phased runner, word
  bridge, bridge check, chain verifier.
- `artifacts/fable-wire57-20260921/`: `PASSMARKS.md`, `SEAL.sha256.txt`,
  `wave-report.json`, `runs/seed{5701,5702,5703}/` (notebook + sleep
  checkpoint each).

# Exp 128 PASSMARKS (sealed BEFORE any registered run, 2026-09-22)

Exp 128 = per-turn cost growth in the joined-up agent (loop102): diagnose, then ONE change.
Diagnosis (unregistered, done): contention-robust CPU microbenchmark
(artifacts/fable-perf128-20260922/diag.json) with time.process_time() inside the
daemon process at 1k/5k/10k/15k taught facts from the seed-93 soak plan:
teach p50 4.08/13.79/24.77/38.56 ms, correct 3.99/14.05/24.84/38.53 ms,
ask 4.75/18.63/32.20/48.89 ms; ratios 15k/1k = 9.45x/9.65x/10.3x.
Every per-turn cost grows ~linearly. Biggest components at 15k: filtered_view77
~12.5 ms, state.json _save ~11.5 ms, notebook_triples ~9.1 ms.

THE ONE CHANGE under test (new wrapper file only, no existing file edited):
scripts/fable_perf128_index.py — IndexedNotebook (subclass of Loop90Notebook)
maintaining incremental in-memory indexes (subject,relation)->fact list,
relation->fact list, known-relations set, cached active-taught triples) plus a
fast reasoner view, lazy triples build, incremental daemon bookkeeping, and
bounded state.json persistence. Notebook file format unchanged; every reply
must stay byte-identical to unwrapped loop102.

Environment: Mac CPU, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B ...`

Registered runs (all AFTER this seal):
- C1: `python -B scripts/fable_perf128_c1.py --out artifacts/fable-perf128-20260922/c1.json`
  per-turn CPU (process_time, in-process) at 1k and 15k taught facts
  (seed-93 plan order; 15k tail synthesized by extra corrections, documented),
  25 samples/kind/size, p50 per kind. PASS: each ratio (15k p50 / 1k p50) <= 1.5.
- C2: `python -B scripts/fable_perf128_c2.py --out artifacts/fable-perf128-20260922/c2.json`
  first 5,000 turns of the seed-93 plan through fresh unwrapped loop102 and the
  wrapped agent, reply streams diffed. PASS: 5000/5000 byte-identical.
- C3: `python -B scripts/fable_perf128_c3.py --out artifacts/fable-perf128-20260922/c3.json`
  exp-102 marks P2/P3/P4 re-run with the wrapped agent swapped in (runtime
  monkeypatch only). PASS: P2 ok_to_bug==[] and still_bug==[] (sealed: 16 BUG->OK,
  0 still_bug, PASS); P4 false_refusals==[] and nonpass==[] (sealed PASS);
  P3 L1/L2/L3/L4/L5z1/L5z2/L6 all pass (sealed PASS).
- C4: `python -B scripts/fable_perf128_soak.py --turns 20000 --seed 93
  --artifact-dir artifacts/fable-perf128-20260922/soak93` (defaults --kills 5,
  --graceful 3, --budget-s 1500; same plan/schedule/driver as exp-108 seed 93;
  daemon = loop102 + exp-108 exactly-once wrapper + the index change).
  PASS: 0 wrong / 0 lost / 0 duplicate (K1/K2 semantics); wall-clock p50/p99
  curve reported next to exp-108's loop102 curve (informational, contention noted).
- C5: total wall-clock of C1+C2+C3+C4 < 1800 s. PASS: < 1800.

Falsification: first failing mark stops the claim; run recorded as FAIL, never
re-run into a pass. Every seed/case reported, never averaged. Replies decide C2;
logs/state.json may differ in bytes but never in replies or notebook content.

Sealed dependency hashes (read-only; never edited):
ee19f73a4a7a97439074f1ea74c97ea0ab7f0cad944fea44e14c1d92e15baf1e  scripts/fable_loop102_agent.py
3ae71d1c8567be6006699951e4d897495b58dd5eb81eeba1916e6b3256952646  scripts/fable_loop90_agent.py
7bd68fd071ef209d12683db2ac3a9b29d1d6e64990f65643436e717a7fb5ea4b  scripts/fable_notebook_contract.py
cd0b9ebab84a27bb0f11e12d930fab8fb51bd197f08ff6e1e045d480808c9ead  scripts/fable_agent_loop.py
6a206bf27b886eac3045e2c366f374fb541cafe4608309a80e94a1818c7a2380  scripts/fable_daemon74_run.py
371e03483df5a799ed9c9548ecb72eb256e5eeb33c525929f841f7db6a1742f7  scripts/fable_daemon108_run.py
a00ac6413c502f736112d9f953599805c66e8e0f298ac6ac3d8beeb14dde2cc4  scripts/fable_soak108_run.py
e4f5f4c65669ad0104d72c007a7d3165746578a1fb39e2e5fae7dfe5f9618d2e  scripts/fable_fix77_core.py
e81d189e448c46d2a259762bb734ac0efa563cc0069d83f362763cdb33c78530  scripts/fable_listening_m1.py
12e85b1bd2d54701b4b6036c32ba0c4a3eda31e4790af668783384ff63e419bd  scripts/fable_loop102_marks.py
cef989143d93fa9994dcc1901bdec473388db700043a6f53fe3bdd58e5ea08b4  scripts/fable_perf128_diag.py

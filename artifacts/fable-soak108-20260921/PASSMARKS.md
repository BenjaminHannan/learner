# Exp 108 PASSMARKS (sealed BEFORE the registered run, 2026-09-22)

Registered single-change follow-up to exp 93 (soak FAIL): exactly-once turn
handling on boot. A real daemon108 subprocess (scripts/fable_daemon108_run.py,
new file wrapping sealed scripts/fable_daemon74_run.py) is driven through its
mailbox. THE ONE CHANGE under test: on boot the daemon either finishes the
in-flight message once (if its reply was not yet durably written) or drops it
(if it was), never both -- stable id = mailbox filename, receipts in
<dir>/receipts.jsonl, loop.inbox crash artefact dropped, already-replied
inputs moved to done/ without re-execution.

Seed-93 run: SAME driver, SAME seed 93, SAME plan (20,000 turns: 11,288
teaches + 2,715 corrections + 5,997 asks over 2,000 people x 6 relations;
verified identical kinds and identical restart points: kills at 3797, 5281,
17710, 18711, 18898; graceful at 6214, 8556, 12968), pointed at daemon108.
Turn language, ground-truth checking, per-restart notebook audit, checkpoints,
and first-failure-stops procedure are exp 93 verbatim.

Environment: Mac CPU, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B ...`
- K1-K5 (seed 93): `python -B scripts/fable_soak108_run.py --turns 20000 --seed 93
  --artifact-dir artifacts/fable-soak108-20260921/seed93` (defaults: --kills 5,
  --graceful 3, --budget-s 1500). Pipeline depth 3; latency is submit->reply;
  restart-straddlers excluded from latency stats.
- G1: `python -B scripts/fable_soak108_ghostdemo.py`
- G2 (seed 931): `python -B scripts/fable_soak108_run.py --turns 6000 --seed 931
  --kills 10 --graceful 0 --aim-midturn
  --artifact-dir artifacts/fable-soak108-20260921/seed931`

Source sha256 (sealed; daemon74/loop/agent/notebook/listening identical to exp 93's seal):
- scripts/fable_daemon108_run.py 371e03483df5a799ed9c9548ecb72eb256e5eeb33c525929f841f7db6a1742f7
- scripts/fable_soak108_run.py a00ac6413c502f736112d9f953599805c66e8e0f298ac6ac3d8beeb14dde2cc4
- scripts/fable_soak108_ghostdemo.py bc5389671089f7e6ff9a38a9163a7c98bc2d1962a26e2ea4439963fb9c057f4e
- scripts/fable_daemon74_run.py 6a206bf27b886eac3045e2c366f374fb541cafe4608309a80e94a1818c7a2380
- scripts/fable_agent_loop.py cd0b9ebab84a27bb0f11e12d930fab8fb51bd197f08ff6e1e045d480808c9ead
- scripts/fable_notebook_contract.py 7bd68fd071ef209d12683db2ac3a9b29d1d6e64990f65643436e717a7fb5ea4b
- scripts/fable_listening_m1.py e81d189e448c46d2a259762bb734ac0efa563cc0069d83f362763cdb33c78530

Marks (K1-K5 copy exp 93's wording exactly):
- K1: 0 wrong answers and 0 wrong writes over the full 20,000 turns
  (ask reply must contain "is <expected>."; teach/correct reply must be
  "Saved: ..." or "I already have that."). Falsified by >= 1 wrong/unanswered.
- K2: no taught fact whose reply was written is lost or duplicated across the
  8 restarts (per-restart log audit: lost == 0 AND dupes == 0 AND wrongval == 0
  AND dupe_entities == 0). Falsified by any nonzero audit count.
- K3: final boot time + final chain-verification time < 10 s.
  Falsified by >= 10 s.
- K4: p99 reply latency over the last 1,000 turns < 10x p99 over the first
  1,000 turns (the growth curve is reported per-1,000-turn checkpoints).
  Falsified by ratio >= 10.
- K5: whole soak < 25 min (1500 s) wall-clock on Mac CPU, all 20,000 turns
  completed. Falsified by >= 1500 s or an incomplete run.
- G1: the 93 ghost reproducer (GHOST93) now shows exactly one reply:
  the Carol reply contains Carol only (no Bob ghost sentence), and at mailbox
  level the Bob and Carol replies are each exactly one sentence, receipts show
  each id processed once, Bob's fact stored once. Falsified by any ghost
  sentence, any doubled reply, any id processed twice, or any duplicated fact.
- G2: a new seed 931 run (6,000 turns) with 10 kill-9s aimed deliberately
  mid-turn (victim submitted solo on a drained pipeline; state.json polled
  until loop.inbox is nonempty -- after the inbox write; kill -9 at once --
  before the reply write; per-kill aim evidence in aims.jsonl) gives
  0 duplicate replies (doubled-sentence scan over every reply AND every
  receipts.jsonl id processed exactly once), 0 lost replies (every submitted
  turn reconciled with a reply), 0 wrong writes (check_turn on every reply).
  Falsified by any nonzero count, or by any of the 10 kills landing un-aimed.

Falsification procedure: the first failing point stops the run; the driver
writes REPRODUCER.md (seed, turn index, text, reply, expectation) and the run
is recorded as FAIL, never re-run into a pass. Every seed reported, never
averaged. If a mark fails, stop and give a reproducer.

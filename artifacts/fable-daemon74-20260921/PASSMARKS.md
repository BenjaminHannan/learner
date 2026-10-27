# Exp 74 PASSMARKS (sealed BEFORE the registered run, 2026-09-22)

Environment: Mac CPU, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_daemon74_selftest.py` (selftest runs seeds 1, 2, 3; every seed reported).

Source sha256 (sealed):
- scripts/fable_daemon74_run.py 6a206bf27b886eac3045e2c366f374fb541cafe4608309a80e94a1818c7a2380
- scripts/fable_daemon74_selftest.py ed181f17922223e0c3fe0fcf56f73ee827e86dabc984a4f262e322f1bad73140
- scripts/fable_agent_loop.py cd0b9ebab84a27bb0f11e12d930fab8fb51bd197f08ff6e1e045d480808c9ead
- scripts/fable_notebook_contract.py 7bd68fd071ef209d12683db2ac3a9b29d1d6e64990f65643436e717a7fb5ea4b

Marks (each must hold in ALL of seeds 1, 2, 3):

- D1: teach 50 facts through the mailbox, STOP, restart same dir, ask 50 questions
  -> correct == 50/50 AND wrong == 0.
- D2: kill -9 (subprocess.kill) the daemon while mid-write during 200 rapid teaches,
  restart -> (chain verifies cleanly OR the exact broken line is reported in
  daemon_status.json / notebook/torn-tail.txt, never silently accepted)
  AND correct == 200/200 AND wrong == 0 AND duplicated == 0 among the facts whose
  outbox reply was written (exactly one taught FACT event per fact).
- D3: 100 turns (50 teaches + 50 asks) end-to-end < 60 s wall-clock on Mac CPU.
- D4: STOP file -> process exits with code 0 within 10 s.

Falsification: any seed missing any clause above is a FAIL for that mark.

Deviation before the registered run: attempt 1 voided (no marks produced) -- the
harness left the STOP file in the dir across the D1 restart, so the rebooted daemon
exited at once and ask-000 timed out. Fixed spawn() to unlink STOP/heartbeat/status
before launching (proving the new boot came up); re-sealed below and re-ran.

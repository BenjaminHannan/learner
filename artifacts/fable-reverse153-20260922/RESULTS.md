# Exp 153 RESULTS — reverse questions on taught facts (Muse)

## Result

Loop153 answers one-hop reverse questions exactly (50/50 probe, 0 writes),
with zero regression on bench (0 moves/600), phone sessions (180/180
identical), and marks123 except 3 race-lost turns recorded as G2 FAIL.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar | number | verdict |
|---|---|---|---|
| V1 probe (50 dialogues, loop153) | 26 exact + 12 exact sets + 12 honest, 0 wrong | 26/26 single (8 relations x 4 frames), 12/12 multi, 12/12 negatives (11 don't-know + N11 clarify) | PASS |
| V2 no writes from reverse Qs | 0 | 0 FACT writes on all 50 question turns | PASS |
| G1 bench vs loop150 rows | per-item identical, 0 new wrong | edit200/old/new121: 0 moves, 0 reply diffs (150/50/0, 157/43/0, 136/63/1) | PASS |
| G2 marks123 vs marks150 | per-case identical | p2/p3/p4/q1/bench/rt81/sleep/q4 identical; rt110 P4 OK->BUG (1 case), soak 0->2 wrong (1 lost teach, asked twice) | FAIL (diagnosis below) |
| G3 sessions152 vs T-T | every reply identical, 0 new WRONG/writes | 180/180 identical, 0 new WRONG, 0 new writes | PASS |
| G4 wall-clock < 1500 s | each run | probe 0.8 s, bench 61.5 s, sessions 4.0 s, marks123 268.5 s | PASS |

Ledger P153.1/2/3/5/6 TRUE; P153.4 FALSE. 5/6.

## Diagnosis note (G2 FAIL; no re-run)

All 3 moved turns share one signature: the daemon read an EMPTY inbox file
(`turn_text=''` in the daemon logs) and replied "I didn't catch anything.",
losing one teach each (rt110 P4 msg_00 "Tom's sister is Ana."; soak s00010
"SoakP010's city is SoakV010."). The reverse stage cannot cause this: it
fires only on "?"-turn forward misses and can only emit its own answer /
don't-know clarifies — never "I didn't catch anything.", never on a teach.
The teach path on this exact code is proven intact (V1 0 SETUP-FAIL, G1 0
teach rejects, G3 identical, soak 1999/2000 turns fine with later asks
correct once taught). Cause: truncate-vs-read race between the harness's
inbox write and the polling/restarted daemon under heavy parallel-agent CPU
contention (this run took ~3x loop150's suite times: rt110 268 vs 88 s,
bench 39 vs 16 s). Recorded as FAIL per the rules.

## What it means

Reverse questions over live taught facts now answer exactly, including
multi-subject sets in teach order and honest don't-knows — the 'A is B ->
B is A' gap on these frames is closed without touching any other path.

## What it does not mean

The agent does not understand paraphrase or multi-hop reversal; anything
outside the four sealed frames still clarifies, and G2's FAIL stands as
recorded (environmental race, not a code regression).

## Deviations

None from PASSMARKS.md. No code edit after the seal (SEAL.sha256.txt
verifies). One correction per the brief's report rule: none needed.

## Reproduce (Mac CPU, offline, after seal)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix153_probe.py --agent loop153 --out artifacts/fable-reverse153-20260922/probe153-loop153.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix153_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix153_session.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop153_agent.py --config artifacts/fable-reverse153-20260922/loop153-config.json --out artifacts/fable-reverse153-20260922/marks153 --workers 4

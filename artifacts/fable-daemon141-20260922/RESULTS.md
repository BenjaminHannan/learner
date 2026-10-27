# Exp 141 RESULTS — mailbox settle gate (2026-09-22)

One-change daemon-side fix for the exp-135 mailbox race (soak turn 238
"What is SoakP038's city?" answered "I didn't catch anything.": the daemon
polled an inbox file between its creation and its first write). New files
only: `scripts/fable_daemon141_settle.py` (settle gate + loop134 wrapper +
108+141 combined daemon), `scripts/fable_daemon141_stress.py` (harnesses).
Nothing else created or edited. PASSMARKS sealed (`SEAL.sha256.txt`)
before any registered run; ledger block P141.1–P141.6 written before,
outcomes appended after.

## Marks table (integer counts, every seed/case reported)

| Mark | Bar | Number | Verdict |
|---|---|---|---|
| R1a unpatched loop134, 300 non-atomic msgs (seed 141) | ≥ 1 "didn't catch" on non-empty | run 1: 2 such replies, 24 wrong, 274 multi-served; run 2 (D1): 4 such, 16 wrong, 275 multi-served; 0 lost both | PASS |
| R1b patched, 3000 non-atomic msgs (seed 141) | 0 such replies, 0 lost/wrong/dupes | 0 such replies, 0 lost, 82 wrong, 93 dupes (all prefix-serves, §2) | FAIL |
| R2 24 genuinely-empty files, patched | each exactly one "I didn't catch anything." | 24/24 replied, 0 lost, 0 wrong-content, 0 dupes | PASS |
| R3 marks123 soak,p2,p4,rt110, patched vs sealed loop134 | verdicts identical; p50 added ≤ 0.05 s | soak 2000/2000 0/0/0 identical; p2 64/64 verdicts + 64/64 reply texts identical; p4 PASS/PASS; rt110 62/62 identical; seq p50 +0.059 s (0.1175 vs 0.0581) | verdicts PASS, latency FAIL → R3 FAIL |
| R4 combined daemon, 12 aimed kill-9s | 0 dup / 0 lost / 0 wrong | 12/12 replied, 1 turn event each, 0/0/0; 72 receipts, 9 reconciles | PASS |
| R5 whole wave < 1500 s Mac CPU | time | 10.8 + 13.6 + 94.5 + 2.8 + 9.8 + 236.3 ≈ 368 s | PASS |

## §2 Why R1b failed (mechanism, verified)

The specified rule serves a file whose (size, mtime) is unchanged across
two 50 ms polls. My harness writes ~30% of messages in two chunks with a
second gap U(0, 100 ms): a first chunk stable for two polls gets served as
a prefix ("FixV0", "F"), then the writer's final chunk recreates the moved
file and it is served again (93 files, 2 turn events each; 82 wrong, all
prefix/poisoned-ask artifacts, 0 empty-serves). So the specified two-poll
rule eliminates the reported race (empty-file serves: 0/3000 patched vs
2–4/300 unpatched) but not mid-write pauses longer than two poll
intervals — a heuristic limit, not a code bug: no daemon-side poll rule
can distinguish "writer paused" from "writer done". Single-open writers
(R3 soak, real clients) cannot recreate served files and are unaffected.

## What it means

The exp-135 symptom is fixed without changing any reply logic: under the
exact risk conditions, empty-serves went to zero, empty messages still get
their one existing reply, all marks123 verdicts are bit-identical to
loop134 (128/128 verdicts, 64/64 reply texts), and the 108+141 combined
daemon survives aimed kill-9s with exactly-once replies.

## What it does not mean

It does not make non-atomic multi-stage writers safe: pauses > ~100 ms
mid-write still produce prefix-serves + duplicate serves (R1b). Writers
that pause mid-message must use atomic writes; the daemon cannot fix that
side. The +59 ms latency figure is confounded (patched notebook held 3000
turns vs 300 unpatched) but misses the ≤ 50 ms bar on its face.

## Deviations

D1: added `--seq-probe` (50 atomic sequential msgs) post-seal to measure
added latency outside queueing; R1a re-ran once, same seed/conditions
(first run kept, both reported, bar met in both). D2: killburst writer uses
create→gap→single-write (the exp-135 race shape; R4 specifies no writer).
D3: daemon class names end in `Daemon` so the marks123 loader finds them.

## Reproduce (from worktree root, after `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`; prefix `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B`)

- `python -B scripts/fable_daemon141_stress.py stress --agent scripts/fable_loop134_agent.py --config artifacts/fable-loop134-20260922/loop134-config.json --out <D> --n 300 --seed 141 --writers 6 --seq-probe 50`
- same with `--agent scripts/fable_daemon141_settle.py --out <D2> --n 3000`
- `... stress.py empty --agent scripts/fable_daemon141_settle.py --config <cfg> --out <D3> --n 24 --seed 141`
- `... stress.py killburst --agent scripts/fable_daemon141_settle.py --config <cfg> --out <D4> --kills 12 --seed 141`
- `python -B scripts/fable_marks123_all.py --agent scripts/fable_daemon141_settle.py --config <cfg> --out <D5> --suites soak,p2,p4,rt110 --workers 4`

Questions for Ben: none.

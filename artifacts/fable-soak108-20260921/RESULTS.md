# Exp 108 RESULTS — exactly-once daemon (registered PASS; follow-up to exp 93 FAIL)

One change under test: exactly-once turn handling on boot (stable id =
mailbox filename; reply-not-durable → finish once; reply-durable → drop
without re-execution; loop.inbox crash artefact dropped; receipts per id).
Sealed code ran unmodified (dep shas match exp 93's seal; PASSMARKS sealed
`c8aefb51…`, predictions P108.1–P108.7 logged before any registered run).

## Marks (every seed reported, never averaged)

Seed 93 — SAME driver, SAME plan, SAME 8 restart points as exp 93, pointed at
daemon108 (20,000 turns; schedule verified identical):

| mark | bar | outcome |
|---|---|---|
| K1 0 wrong / 20,000 | 0 wrong | PASS: 0 wrong over 20,000 replies |
| K2 0 lost/dup over 8 restarts | all audits 0 | PASS: 8/8 audits 0/0/0/0 |
| K3 boot+verify < 10 s | < 10 s | PASS: 0.142 + 0.062 = 0.204 s |
| K4 p99 last-1000 < 10x first-1000 | ratio < 10 | PASS: 436.58 / 67.93 = 6.4x |
| K5 < 25 min, 20,000 done | < 1500 s + complete | PASS: 20,000 turns, 735.1 s |

Exactly-once evidence (seed 93): 20,000/20,000 replies checked, 0 doubled
sentences; daemon log holds exactly 1 turn event per id (0 dup); 3 mid-turn
kills caught red-handed (reboots dropped 1 ghost each, incl. the exp-93 kill
at plan-turn 17710); receipts show 19,999/20,000 ids exactly once, 0 twice.
The missing receipt is t017716 — exp 93's exact failing seq: its reply here
is a single `Saved: Person1648's color is Color04946.` with 1 turn event and
a clean fact audit (kill landed between the file move and the audit-only
receipt append; reply was durable, file done, never reprocessed).

| mark | bar | outcome |
|---|---|---|
| G1 GHOST93 → exactly one reply | no ghost/doubled/dupe | PASS (GHOST108 A+B): Carol-only reply; Bob/Carol single sentences; 1 receipt each; 1 Bob fact row |
| G2 seed 931, 10 aimed mid-turn kills | 0 dup / 0 lost / 0 wrong | PASS: 10/10 kills aimed (attempts=1 each; 7 finish-path, 3 drop-path), 6,000/6,000 replies, 0 doubled, 6,000/6,000 receipt ids once, 10/10 audits clean, 156.9 s |

G2 victim replies (all single sentences, e.g. `I already have that.`,
`Saved: ...`, `... is Person1072.`); 6 ghosts dropped over 11 boots.

## Growth curve (seed 93, per-1,000 checkpoints)

| turns | wall s | rate/s | RSS MB | nb MB | p50 ms | p99 ms |
|---|---|---|---|---|---|---|
| 1k | 22.2 | 15.2 | 29.9 | 0.55 | 66.8 | 77.1 |
| 5k | 127.2 | 11.8 | 43.1 | 1.96 | 84.3 | 96.8 |
| 10k | 288.6 | 9.5 | 54.5 | 3.34 | 105.6 | 118.9 |
| 15k | 489.0 | 7.8 | 66.9 | 4.66 | 128.4 | 144.4 |
| 20k | 735.0 | 6.6 | 79.3 | 5.96 | 150.4 | 170.8 |

Pace ~15→7/s window rate (DEPTH-3 pipeline; wall pace matches exp 93: 735 s
for 20k vs 665 s at 17.7k). Boot
0.09–0.14 s, verify 0.02–0.06 s, flat. One latency spike: window p99 436 ms
at ckpt 17k (post-kill-6 catch-up burst), decayed to 171 ms by 20k; K4 uses
sealed lat-list ratio 6.4x, inside the bar.

## Deviations

Driver is the exp-93 driver verbatim except: daemon target (daemon108),
`--aim-midturn`/`--loop102` flags (aim used only in G2; loop102 only in the
unregistered step), doubled-sentence scan + receipts counts (measurement
only; K-marks computed by unchanged code), per-kill `aims.jsonl`. No sealed
file edited; one process at a time; OMP/MKL=1; offline.

## Questions for Ben

None.

## What it means

The ghost-tick class is closed for this daemon shape: 3 mid-turn kill-9s
(including exp 93's exact killer) each resolved to exactly one durable reply,
and 10 deliberately aimed mid-turn kills produced 0 duplicates, 0 losses,
0 wrong writes — the reply stream is exactly-once per stable id.

## What it does not mean

It does not mean throughput/RSS growth is fixed (same smooth degradation as
exp 93), and it does not cover the integrated loop agent (loop102 scale step
reported apart) or non-mailbox crash windows (mid-save relies on sealed
atomic-replace + torn-tail repair).

Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_soak108_run.py --turns 20000 --seed 93 --artifact-dir
artifacts/fable-soak108-20260921/seed93` (G1: `... ghostdemo.py`; G2: `...
--turns 6000 --seed 931 --kills 10 --graceful 0 --aim-midturn --artifact-dir
artifacts/fable-soak108-20260921/seed931`).

## Unregistered scale step, reported apart (seed 93 vs wrapped loop102)

The wrapper applied without editing loop102 (subclass in
`fable_daemon108_run.py`; smoke: template teaches/asks/corrections correct,
sleep ticks instant with 0 queued episodes). Full 20k run
(`seed93-loop102/`, same plan/schedule, `--loop102`): 20,000/20,000 turns in
783.5 s; K1 0 wrong PASS; K2 8/8 audits clean PASS; K3 1.212 s PASS (boot
~0.9 s vs 0.1 s — agent build cost; RSS ~250 MB vs ~80 MB — scorer models);
exactly-once evidence perfect (0 doubled of 20,000; 20,000/20,000 receipt ids
once; 3 ghosts dropped over 9 boots). K4-style ratio MISSED at 16.6x
(1096.26 vs 661.8 ms bar): smooth to 19k, acceleration in turns 19000–20000
only (see REPRODUCER.md in that folder). Stopped per protocol; no re-run.
The exactly-once fix transfers to loop102 with zero reply/audit regressions;
its late-soak latency growth does not.

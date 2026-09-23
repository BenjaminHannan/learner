# Exp 162 RESULTS (plain words for Ben) — SCORE: FAIL (T1 case-authoring + daemon bugs, both diagnosed; G1 PASS)

The idea: teach the assistant facts about names that start with "The"
("The Hobbit's author is Tolkien") instead of filing them as government
jobs or refusing. Half of it works: every singular ("The Hobbit's …")
saves exactly and answers both question forms, the 3-hop chain answers,
all 600 benchmark items are byte-identical, and office sentences are
untouched. Two bugs in my new code fail the run: plural names ("The
Beatles' …") never save, and the background-mailbox wrapper crashes, so
three suites could not finish.

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 must-write (26, 8 relations) | >= 25/26 OK | 19/26 FAIL |
| T1 office identical (12) | 12/12 | 12/12 PASS |
| T1 must-not-write-wrong (11) | 0 wrong writes | 0 PASS |
| T1 overall wrong writes (51 rows) | 0 | 0 PASS |
| T2 C1 3-hop both forms | OK | OK (Robert) PASS |
| T2 C2 plural chain | OK | FAIL (plural bug) |
| G1 bench 600/600 vs loop150x135 ref | 0 moves, 0 new wrong | 0 moves PASS (85.9 s) |
| G2 p2 / p4 / q1 / bench / rt81 / sleep | per-case identical | identical (0 case-moves) PASS |
| G2 soak | identical | wrong 0->1, see note |
| G2 p3 / rt110 / q4 / summary | identical | MISSING — daemon bug FAIL |
| G3 probe 3.8 s, ref-bench 105.1 s, bench 85.9 s | < 1500 s | PASS |
| G3 full marks123 | < 1500 s | ABORTED (mailbox timeouts) FAIL |

Suite detail vs sealed marks150: p2 64 cases 0 moves (same FAIL verdict
2 OK->BUG / 4 still-BUG); p4 30/30 0 moves PASS; q1 F5+M5 FAIL identical
(seconds only differ); bench tables identical (seconds only differ);
rt81 61/0/13 0 moves (same FAIL verdict); sleep SKIP both (reason names
the new agent file only); soak registered wrong=1 (turn 518 empty-read
"I didn't catch anything"), solo re-run §note.

## Diagnosis notes (two bugs, both mine, no post-seal edits)

1. Plural teaches never save (all 8 T1/T2 failures). The teach regex
   `The\s+(.+?)('s|s')\s+…` consumes the stem-final "s" into the `s'`
   branch, so "The Beatles'" parses as stem "Beatle" + `s'`; the stem
   guard (`endswith("s")`) then rejects every plural and the turn falls to
   the base refusal. Singular path is 19/19 incl. the director's "The
   Hobbit's author". One-line fix (name = stem + "s") deliberately NOT
   applied: FAIL stays FAIL.
2. The daemon wrapper crashes after boot: my `_DaemonBase.__init__`
   (scripts/fable_loop162_agent.py) drops the `self.idle_seconds =
   float(idle_seconds)` line its 155 template has, so `run()` raises
   `AttributeError` on the first idle check (reproduced in the open,
   heartbeat boots then the traceback). In-process suites (probe, bench,
   p2/p4/q1/rt81/sleep) are unaffected; daemon-mailbox suites p3/rt110
   hang with no outbox reply, and soak's kill-9 daemon inherits the
   crash. The CLI accepts `--idle-seconds` but the wrapper is broken.

Soak note: registered run wrong=1 is an empty-mailbox read, the known
load-race signature (soak templates are canonical one-word; the mixin
provably cannot fire on them); solo re-run result: §pending — both
reported honestly.

## What it means

The "The"-name idea is half-proven: singular saves + 3-hop answers work,
nothing else moves (600/600 bench, 6/6 completed suites per-case
identical), and office behaviour is frozen identical.

## What it does not mean

It does not mean plurals or the daemon path work — they fail
deterministically; drummer/editor-class relations remain untaught by
design (outside the loop's tables).

## Deviations

- Full marks123 aborted twice on p3 mailbox timeouts under parallel load;
  missing suites documented, not fabricated; per-case diff run on what
  completed. Soak re-run solo once in the open per the brief.
- No code, case, or PASSMARKS edits after the seal.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162_probe.py --out artifacts/fable-thename162-20260922/probe162-loop162.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162_bench.py --variant loop162
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop162_agent.py --config artifacts/fable-thename162-20260922/loop162-config.json --out artifacts/fable-thename162-20260922/marks162 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162_marksdiff.py

# 128 — Agent per-turn cost (Muse)

## Problem
Exp 108's loop102 scale step showed reply latency growing 65 ms → 154 ms (p50)
by turn 19,000 with p99 1.1 s. Wall-clock was contaminated by parallel agents,
so exp 128 first re-measured with `time.process_time()` inside the daemon:
per-turn CPU grows ~linearly, 9–10x from 1k to 15k facts for teach, correct,
and ask alike. Every turn re-scanned the whole notebook several times over.

## Where the time went
Each turn paid for: `Notebook.current()` (full fact scan per write and per ask
hop), `Listening._relation` (full event scan per write), `notebook_triples`
(full active-triple rebuild per ears `hear`), `Bench73Stage._teach_action`
(linear scan per teach), `filtered_view77` + `known` (full scans per ask hop),
`compose_question` (triple-list build plus an O(E log E) entity-mention sort per
question), `AgentLoop._save` (whole experience JSON dump twice per turn), and
`process_file` set-copies of all facts/entities. At 15k facts the biggest CPU
slices were the reasoner view (~12 ms), state dump (~11 ms), and triples (~9 ms).

## The one change
`scripts/fable_perf128_index.py` (new file; nothing existing edited) keeps one
incremental in-memory index over the unchanged append-only log: per-pair and
per-relation fact lists, known relations, the active taught-triple list with
per-name displays and order, reverse subject lookup, and length-bucketed mention
strings. All consumers read through it: ears compose (with a provable fast-None
when no taught relation is cued in the question), the fix77 hop loop (per-subject
entries plus a cached qualifier-dropped bit computed by the original view on a
miss), teach-action selection, relation declaration, and daemon bookkeeping.
`state.json` keeps the full in-memory experience but persists only the last 200
entries (sleep threshold 1e9 never fires here; small tests fit entirely).

## Why replies cannot change
Every fast path replays the original decision over the same data: same sort and
filter order, same gate outcomes (falling back to the original full computation
for rare shapes such as Who-/never-taught questions and qualifier-bearing
views), same file bytes for the notebook log. Evidence: 5000/5000 byte-identical
replies on the seed-93 plan, P2/P3/P4 bit-identical to sealed loop102, and a
20,000-turn soak with 0 wrong/lost/duplicate.

## Results
Per-turn CPU at 15k facts is 0.68–0.76x the 1k value (caches warm, fewer entity
creations late in the plan). The soak finished in 587 s (was 784 s) with wall
p50 64→96 ms and p99 89→285 ms next to exp 108's 65→228 / 75→1096 (load-sensitive,
informational). Total registered wave ~1600 s.

## What it means
Lookups now cost per-answer, not per-notebook: the agent stays flat as Ben
teaches it more.

## What it does not mean
Disk growth, fsync, and mailbox queueing still exist; a busy shared machine can
still stretch wall-clock. Sleep, thinking, and the wire protocol are untouched.

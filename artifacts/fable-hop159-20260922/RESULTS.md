# Exp 159 RESULTS — hop through known names (Muse)

One change on loop150: a mid-chain literal continues the walk iff it
exactly names one live taught subject
(`scripts/fable_fix159_hop.py:bridge159`; thin agent
`scripts/fable_loop159_agent.py`). Design:
`design/v3/30-modes/159-hop159-muse.md`. Seal (pre-run):
`artifacts/fable-hop159-20260922/SEAL.sha256.txt`.

## Marks table (integer counts, every seed/case reported, never averaged)

| mark | bar | number | verdict |
|---|---|---|---|
| H1 probe (48 dialogues, fresh loop159 each) | 26 chains correct; 11 nobody old-reply; 11 traps old-reply; 0 wrong; 0 question-turn writes | 26/26 chain OK (pets 6, objects 5, places 5, orgs 5, works 5, incl. five 3-hop); 11/11 nobody OK; 11/11 trap OK; 48/48 teaches Saved; 0 wrong; 5.2 s | PASS |
| G1 bench vs sealed loop150 rows (600 items) | per-item verdict+reply identical except predicted; 0 new wrong | edit200 150/50/0, old_s2fresh 157/43/0, new_121 136/63/1 — verdict_moves 0, reply_moves 0, new_wrong 0 on all 3 splits; 135.8 s | PASS |
| G2 marks123 vs sealed marks150 | per-case verdict-identical except predicted | p2/p4/q1/bench/rt81/soak/q4 reports identical; p3 verdict files identical; rt110 62/62 verdict tuples identical; sleep SKIP (agent filename only, as in 150); 0 moves; 338.1 s | PASS |
| G3 sessions152 vs sealed T-T (180 turns) | identical except predicted; 0 new WRONG; 0 new writes | 176/180 byte-identical; exactly S4 turns 7+27 WRONG→OK ("Ana's pet's color is brown."), 20 OK→OK ("Ana's pet's owner is Ana."), 26 OK→OK ("Biscuit's owner's pet is Biscuit."); new_wrong 0; write_diffs 0; 1.7 s | PASS |
| G4 time | every run < 1500 s Mac CPU | 5.2 / 135.8 / 338.1 / 1.7 s | PASS |

SCORE: PASS (H1, G1–G4). Predictions 5/5 TRUE (see ledger Outcomes 159).

## Notes on G2 noise (all verdict-neutral, all also present in the base run)

- rt110 log `statuses: []` on 4 entries (T2/T4/R3/L4 first msgs):
  the sealed harness reads `daemon.log.jsonl`, whose turn line is appended
  after the outbox reply the harness already consumed — a log-line race.
  Replies, fact_writes, and all 62 verdict tuples identical; the base
  loop150 run shows the same `[]` on 201 entries.
- p3 workdir diffs are pids/timestamps/uuid-seeded hashes only; l6-report
  differs only in the kill-timing counter `replied_before_kill`
  (verdicts 200/200, wrong 0, chain_ok true both runs).
- sleep SKIP reason names `fable_loop159_agent.py` instead of
  `fable_loop150_agent.py` (predicted allowance, same as exp 150).

## What it means

The 152 red-team WRONG is fixed at its root: "Who is Ana's pet's color?"
now answers "brown", and the turn-26 shape answers "Biscuit" — while 600
bench rows, all marks suites, and 176/180 session turns behave exactly as
before. A literal that names a taught subject is now a bridge, never a wall.

## What it does not mean

It does not guess: loose matches ("brown" vs "Brown Hall", "cat" vs
"Cats", "red ball" vs "Ball") still abstain with the old reply, and
ambiguous names still refuse. Multi-hop questions the composer truncates
to one hop are untouched by this change.

## Deviations

Pre-seal case-authoring fixes only (in PASSMARKS.md): N03's employer-tail
question truncates in the 113b composer when ungrounded (replaced with a
gift/boss shape); T09 used "boss", which is a person-relation entity hop
(replaced with "assistant"). Zero code edits after the seal; no re-runs.

## Exact reproduce (worktree root; OMP_NUM_THREADS=1 MKL_NUM_THREADS=1)

uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix159_probe.py --out artifacts/fable-hop159-20260922/probe159-loop159.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix159_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop159_agent.py --config artifacts/fable-hop159-20260922/loop159-config.json --out artifacts/fable-hop159-20260922/marks159 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix159_session.py

Questions for Ben: none.

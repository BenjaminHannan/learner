# 126 — Demo transcript harness — RESULTS

**Two registered runs 22 Sep 2026, loop117 (7.1 s) + loop113b (6.8 s).
PASSMARKS sealed before the runs. SCORE: PASS (A1–A8 on both agents).**

## Frozen sources (sha256)

```
de1d0749b3fa7804459d84d7bf56e54c9681c650e04a9818e4dfe4850c5b9119  artifacts/fable-demo126-20260922/PASSMARKS.md  (SEAL)
e66b14c8a9a773a9c82c6f51c05454ee53017cbabc42fc17a22243b0e5b50b48  scripts/fable_demo126_run.py
```

Reproduce (Mac CPU, no install):

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_demo126_run.py --agent scripts/fable_loop117_agent.py \
  --config artifacts/fable-loop117-20260922/loop117-config.json \
  --out artifacts/fable-demo126-20260922
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_demo126_run.py --agent scripts/fable_loop113b_agent.py \
  --config artifacts/fable-bench113b-20260922/loop113b-config.json \
  --out artifacts/fable-demo126-20260922
```

## Marks (per act, never averaged)

| act | loop117 | loop113b |
|---|---|---|
| A1 knows nothing (2/2 abstain) | PASS | PASS |
| A2 eight teaches (8/8 Saved) | PASS | PASS |
| A3 Porto + Norway + four-hop | PASS (four-hop SKIP, not supported) | PASS (four-hop Quechua via composer) |
| A4 forget cycle | PASS | PASS |
| A5 Oslo refused, Lisbon kept | PASS | PASS |
| A6 clarify/clarify/abstain | PASS | PASS |
| A7 3/3 word abstains, sleeps 1, 0 installs | PASS | PASS |
| A8 panel equals files | PASS | PASS |
| wall-clock < 900 s | PASS (7.1 s) | PASS (6.8 s) |

## Predictions (ledger P126.1–P126.6, written before the runs)

6/6 TRUE: both runs < 900 s; loop117 all PASS with four-hop SKIP; loop113b
all PASS with four-hop Quechua; Oslo refused naming Lisbon on both;
3/3 sleep abstains with 1 audit-only sleep tick and 0 installs on both;
panel reproduces bench113b split-A 150/50/0 of 200, fresh 145/50/5 of 200,
bench66 incontext 52 / raglite 38 / finetune 1 correct of 200, bench125
present (4 row files at run time).

## Files

`transcript-loop117.md`, `transcript-loop113b.md` (every turn verbatim +
one plain-English note), `fable-demo126-results.json` (per-turn + per-act),
`daemon-loop117/`, `daemon-loop113b/` (fresh mailbox dirs, state.json,
notebook); design `design/v3/30-modes/126-demo-harness-muse.md`; script
`scripts/fable_demo126_run.py`.

## Observations (not deviations)

- A5 leaves a pending "change it?" question; the next teach honestly replies
  "(I dropped my earlier question.) Saved: …" — verbatim in the transcript.
- loop117's mouth renders relation names with spaces, loop113b's keeps
  underscores ("maternal_grandmother"); the checker normalises both.
- bench125 grew a 4th row file between the dry run and the registered run
  (another agent's live folder); the panel read all 4 at run time.

## Deviations

None from PASSMARKS.

## What it means

- One command replays a full honest evening with any `--agent/--config`
  pair: ignorance, 8 teachings, two/three/four-hop joins, forgetting,
  refusal to overwrite, self-knowledge limits, audit-only sleep, and a
  file-read comparison panel — all verbatim, all PASS on both agents.

## What it does not mean

- Not broad English (only templates the agents parse), not overnight
  learning (sleep ticks audit but install nothing here), not new evidence
  from the panel (it re-quotes earlier sealed files).

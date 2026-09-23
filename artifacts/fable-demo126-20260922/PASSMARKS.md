# 126 — Demo transcript harness — PASS MARKS (sealed BEFORE the registered runs)

Written 22 Sep 2026 before the registered runs of `scripts/fable_demo126_run.py`.
Hashed in `SEAL.sha256.txt`. Development (mailbox dry runs to scratchpad dirs
while writing the code) is not a registered run. The REGISTERED runs are the two
clean invocations below, run after this file is sealed and the script source is
frozen (sha256 recorded in RESULTS.md). A registered FAIL is reported as FAIL
and is never re-run into a pass. Every turn reported, never averaged.

## The frozen experiment

One new script, additive only (loop agents spawned read-only, never edited):

- `python -B scripts/fable_demo126_run.py --agent scripts/fable_loop117_agent.py
  --config artifacts/fable-loop117-20260922/loop117-config.json
  --out artifacts/fable-demo126-20260922` (default args = this run)
- `python -B scripts/fable_demo126_run.py --agent scripts/fable_loop113b_agent.py
  --config artifacts/fable-bench113b-20260922/loop113b-config.json
  --out artifacts/fable-demo126-20260922` (merges under its own agent key)

Each drives ONE fresh daemon dir through the mailbox with the frozen ~37-turn
script (TURNS in the script): A1 knows-nothing (2 asks), A2 eight teaches,
A3 two-hop + three-hop + four-chain teaches + four-hop + retention re-ask,
A4 ask/forget/ask/re-teach/ask, A5 contradiction + ask, A6 three self-asks,
A7 six mother-teaches + three word probes, A8 file-read panel. Four-hop is
sent only to composer agents; loop117's transcript carries the "not supported
by this agent" note and SKIP. Output: `transcript-<agent>.md` (every turn
verbatim + one plain-English note) and merged `fable-demo126-results.json`.

## Marks

| # | mark | threshold |
|---|---|---|
| A1 | asks on empty notebook abstain | 2/2 honest don't-knows |
| A2 | teaches saved | 8/8 Saved |
| A3 | joins answered; four-hop Quechua iff composer else SKIP | Porto + Norway + (Quechua \| SKIP) |
| A4 | forget cycle | Forgotten, abstain, Saved, Lisbon |
| A5 | contradiction refused, old kept | refusal names Lisbon, no save, ask = Lisbon |
| A6 | self-asks honest | clarify/clarify/abstain, no fabrication |
| A7 | sleep probes abstain, ticks fired, nothing installed | 3/3 abstains, state.json sleeps >= 1, 0 sleep-derived facts |
| A8 | panel equals the files | bench113b/bench66/(bench125 if present) numbers exactly as read |
| V1 | wall-clock per run (Mac CPU, OMP/MKL=1) | < 900 s |
| V2 | transcript verbatim | every Ben line + reply present (asserted in-script) |

## What the marks can and cannot support

- A1–A8 support: "in this scripted evening each agent behaved exactly this
  way, word for word in the transcript."
- A7 supports: "the daemon's sleep ticks fired but installed nothing, and the
  agent honestly said it had not learned the word" — not overnight learning.
- A8 supports: "the panel re-quotes the sealed files" — not new evidence.
- Nothing here supports broad English or any claim beyond these two runs.

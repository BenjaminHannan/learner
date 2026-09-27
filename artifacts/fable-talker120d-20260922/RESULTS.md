# RESULTS — Experiment 120d: talker don't-know routing (Muse), 2026-09-22

## Result

Registered runs BLOCKED: the mandated checkpoint
`artifacts/claude-talker120b-run-20260922/fable_talker120b_ckpt_last.pt` is
absent (directory holds only logs + JSON; verified 07:2x local; no copy in any
worktree). The one change itself is built, sealed, and proven by diagnostics:
3/3 open replay runs with the surviving mask-fixed smoke checkpoint reproduce
wire51's `replay-report.json` counts exactly, with both missed turns speaking
wire51's sentences verbatim.

## Marks table (integers; every seed/case reported, never averaged)

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| R1 registered x3 (director ckpt) | 12/3/0/6 identical to wire51 | not run — ckpt missing | BLOCKED |
| R2 registered 500-record score | after-brake 0, status ≥486, OK 250/250 | not run — ckpt missing | BLOCKED |
| R3 wall-clock | < 25 min/run | n/a (blocked) | BLOCKED |
| DIAG replay x3, smoke ckpt | — | wrong [0,0,0], correct [12,12,12], abstentions [3,3,3], missed [0,0,0], two-hop [6,6,6], empty 5/run, english 40/40 x3 | identical to wire51 |
| DIAG score 500, smoke ckpt | — | after-brake 0, OK 250/250, status 287/500, contract_routed 0, 202 s | driver works; status gap is the weak smoke model, not the mouth |
| DIAG routing (no weights) | — | both wire51 sentences verbatim; old mouth "" on both; six-status fallbacks byte-identical | PASS |

Diagnostic per-turn proof (all 3 runs): "Where is Zed's city?" →
"I don't know anyone called Zed."; "Where is Ana's city's mother?" →
"Ana's city is Porto, which is not someone I can look up." `contract_routed`
= 6 (2/run, zero decodes on those turns).

## What it means

The silence/unfaithfulness on untrained statuses is fixed at the routing
level: non-six statuses can never reach the talker or come back empty.

## What it does not mean

It does not show the registered marks pass — those need the director's
checkpoint. It also does not fix the underlying copy-head weakness (smoke
model needed fallback on 15 OK turns; fallbacks happened to be identical).

## Deviations

None from the sealed plan except the forced substitution: registered runs
replaced by same-shape open diagnostics with the 100-step mask-fixed smoke
checkpoint (`artifacts/fable-talker120b-20260922/smoke/`), explicitly labeled.
No model copies written; 120c files untouched; PASSMARKS verified
`shasum -c` clean.

## Exact reproduce (Mac)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_talker120d_replay.py --ckpt <ckpt> --tok artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json --replay 3 --out artifacts/fable-talker120d-20260922/replay.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_talker120d_score.py --data artifacts/fable-talker120-20260922/data --ckpt <ckpt> --tok artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json --out artifacts/fable-talker120d-20260922/score.json
```

## Questions for Ben

None. Conservative default taken: report BLOCKED rather than substitute a
different checkpoint into registered marks.

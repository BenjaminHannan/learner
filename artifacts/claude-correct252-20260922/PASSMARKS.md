# Exp 252 — corrections and denials on 138k — PASSMARKS (sealed before any registered run)

Base: 138k (`scripts/claude_loop138k_agent.py` + `artifacts/claude-merge138k-20260922/loop138k-config.json`).
Mine: `scripts/claude_loop252_agent.py` + `artifacts/claude-correct252-20260922/loop252-config.json`
(138k + `scripts/claude_fix252_correct.py`). Design note: `design/v3/30-modes/252-correct-opus.md`.

`py` = `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B`.
D = `artifacts/claude-correct252-20260922`. Each registered run is done once and its output goes to `$D/run/`.
I check `uptime` before each run and wait while the 1-minute load is above 60.

## Marks

| Mark | What | Bar |
|---|---|---|
| M1a | panel, my arm, per family | verb_denial ≥ 13/14, possessive_denial ≥ 9/10, contextual_denial ≥ 11/12, contextual_correction ≥ 13/14, explicit_correction ≥ 11/12 |
| M1b | panel wrong values (the followup reply still states a value from expect_gone) | 0 on my arm (base count reported beside it) |
| M1c | panel | 0 junk writes, 0 followup writes; question_trap 12/12, ambiguous 6/6, unstored_denial 8/8, each with the store unchanged |
| M1d | panel control | 12/12, and turn and followup replies byte-identical to `base138k.jsonl` |
| M2 | dev (`$D/dev252.jsonl`, 81 items, my own wordings) | every item right; 0 junk writes; the 10 traps write nothing; restart items 5/5 right |
| M3 | `fable_suitediff218.py --only rt136,rt143,sessions152,bench --base-dir $D/run/base138k-rows` | 0 new WRONG / WRONG-WRITE / junk write / lost OK; the moves are exactly the predicted list below |
| M4 | `fable_sleepsmoke206.py --idle-seconds 5.0` | every field of the report equal to `artifacts/claude-merge138k-20260922/run/smoke-k.json`, except agent, config, label and seconds |
| M5 | `claude_merge138k_latency.py` on v-dialogs + v-supp, 2 reps. Three runs per arm, alternating k, 252, k, 252, k, 252, in the same session | median of the three per-run medians: mine − 138k ≤ +5 ms |
| M6 | `claude_merge138k_probe.py` on `artifacts/claude-verify-20260922/138k/v-dialogs.json` and `v-supp.json`, run on both arms in the same session; checked by `scripts/claude_corr252_m6check.py m6` | 0 ghost answers; 0 failed duplicate checks; replies and final stores identical to 138k (predicted moves: none) |

The dev and panel scores come from `scripts/claude_corr252_score.py`, which enforces the corrpanel252 schema (SCHEMA-MISMATCH → exit 3 → VOID; never scored by hand).
The runner is `scripts/claude_corr252_run.py`, with one fresh work dir per item.
In dev mode, control items are compared with my 138k run of the same file, made in the same session.

## Base suite rows (director note)

138k's saved suite rows (`artifacts/claude-merge138k-20260922/run/sd/`) are named `rt136-rows.json` and so on. `fable_suitediff` looks for base files by the fragments `redteam136` / `redteam143` / `sessions152`, so it cannot find those three suites there; it would skip them.

So before the seal, in this session, I ran the four suites on 138k myself:
- command: `fable_suitediff218.py --agent 138k --base-dir artifacts/fable-agent138j-20260922`, output in `$D/run/sd-k/`, log in `sd-k.log`;
- result against 138j: 0 moves in every suite, GATE clean, the same as 138k's own K3.

I copied those rows into `$D/run/base138k-rows/` under names suitediff finds:
- `redteam136-rows138k.json`
- `redteam143-rows138k.json`
- `sessions152-rows138k.json`
- the four `bench-*-rows.jsonl` files, unchanged.

A pilot run of 138k against this folder gave 0 moves in all four suites. M3 compares against these rows, which are sealed below.

## Predicted moves (by id)

**M3**, all reply-only. Verdict and stored triples are unchanged.
- rt136 C071 "Tom is not a citizen of Peru." → "I don't have anything saved about Tom, so I didn't change anything."
- rt136 C072 "Mira's city is not Lisbon." → "I don't have anything saved about Mira, so I didn't change anything."
- rt136 C073 "Tom was not born in Lyon." → "I don't have anything saved about Tom, so I didn't change anything."
- rt136 C075 "The capital of Peru is not Lima." → "I don't have anything saved about Peru, so I didn't change anything."
- sessions152 S3-teachers-correction#6 "no wait, it's denver" (after a two-hop answer) → "I worked that out from: Nadia's teacher is Rao and Rao's city is seattle. Which of those facts is wrong?" (UNHELPFUL → UNHELPFUL)
- rt143: none. bench: none.

**M6:** none. **M4:** none.

## Ledger predictions (P252.n)

- P252.1 M2 dev passes: 81/81, 0 junk, 0 trap writes, restart 5/5.
- P252.2 M3 moves are exactly the 5 listed; GATE clean.
- P252.3 M4 identical; M6 0 moves, 0 ghosts, 0 duplicate failures; M5 added time under 1 ms.
- P252.4 M1a: I expect a pass in each family I can build for, with about 65% chance that all five families pass together. The panel uses wordings I have not seen, and the likely misses are wordings the base teach reader does not parse.
- P252.5 M1b 0 wrong values on my arm, about 75%. On 138k the count is high, because 138k removes almost nothing.
- P252.6 M1c: 0 junk and 0 followup writes, and traps / ambiguous / unstored all right, about 70%.
- P252.7 M1d controls 12/12 identical: about 85%.
- P252.8 Overall registered PASS: about 40%.

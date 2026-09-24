# rsn-350 pass marks (fixed before any run; 2026-09-24)

Design: design/v3/30-modes/350-bigger-reasoner.md. One change from 296: plain arm 91,588,629 numbers
instead of 30,938,261. Twin: 296 plain, same seed (recounted). Scoring: "checked right", after the
fact-check, with 294's sealed scorer. Panels TEST-ONLY, category counts only.

| mark | what (350 plain, each seed) | pass |
|---|---|---|
| Z1 | fresh panel296 v2 total | ≥ 296 same seed + 10 (s1 ≥ 235, s2 ≥ 227) |
| Z2 | fresh three-step, never practised (the generalization question) | ≥ 6/30 on at least one seed (296: 0/30 both) |
| Z3 | transfer panel294 v3 total | ≥ 233 each seed (296: 238 each) |
| Z4 | invented answers (checked), each panel | ≤ 2 |

Verdict: **PASS = Z1, Z3 and Z4 on both seeds.** Z2 gets its own verdict: it answers Ben's question
whether size alone makes the reasoner handle longer chains it never practised.

Why +10: at 30M the two seeds differ by 8 on the fresh total (225 vs 217), so a gain under 10 could
be seed noise.

**What proves "size is the bottleneck" wrong at this scale:** fresh total ≤ 296 same seed + 3 on both
seeds AND three-step 0/30 on both seeds.

**10x trigger:** Z1 passes on both seeds.

Predictions (logged before the run):
- Z1 uncertain. The headroom is counting (12/30), comparing (16/30, near chance, likely a readout
  problem that size won't fix), before/after and corrections.
- Z2 likely FAIL: three-step is never practised, and length generalization usually needs practice
  or a variable-depth model, not only width.
- Z3 likely pass. Z4 likely pass (the fact-check turns unsupported answers into "I don't know").

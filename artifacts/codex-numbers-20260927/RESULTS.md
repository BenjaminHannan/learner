# Step 1 diagnostic result — no registered candidate experiment yet

**Status: DIAGNOSTIC ONLY. N1–N4 and the registered proved-wrong criterion have not been tested.**

SHOWN: a new fixed-env loop baseline ran on this Mac's M3 Pro GPU using MPS float32, torch 2.11.0. Seed 9276191, width128 × 2 layers, 8 heads, 430,238 weights (including 256 unused env weights), 20,000 steps, batch128, original mixed sums/grids/numbers practice and v2 own-stop rule. Training took 14.16 minutes.

| Panel | Valid at own stop | Exact stored answer |
|---|---:|---:|
| Practice numbers3 | 508 / 1,346 | 494 / 1,346 |
| Practice numbers4 | 46 / 1,062 | 44 / 1,062 |
| Disclosed design numbers4 | 2 / 300 | 1 / 300 |
| Sums4 | 298 / 300 | 298 / 300 |
| Grids5 | 248 / 300 | 248 / 300 |

SHOWN: this run is underfitted on number practice. It does not reproduce the historical full-size perfect-training result. All 300 design number hands reached the fallback round 48; only six had a valid expression at any round. The main observed errors were incorrect use of the supplied numbers (142), malformed expressions (100), and wrong arithmetic (54). The hidden-kind poison checks passed for all kind values on representatives of every evaluated panel.

SHOWN independently from historical raw outputs: the eight 358i3 runs report final-window number training exactness 1.0, with held-out numbers4 at 0–5/300 and numbers5 at 0. This historical result and our underfitted local diagnostic must not be conflated.

SHOWN by exact, code-checked enumeration: 2,333 of 2,408 practice puzzles have alternative valid postfix answers that the original single-answer objective labels incorrect. This proves a target mismatch. SUGGESTED: it can impede learning, but its causal effect on transfer is UNTESTED.

SHOWN: the small puzzle loop has recurrent hidden state, but no explicit interface to write its own scratch cards or restore a branch snapshot. Broader card-memory code and thought-memory proposals are separate. Ben raised this distinction during brainstorming; DIAGNOSIS.md and diagnostics/WORKING-MEMORY-NOTE.md preserve it.

For Ben: the small model learned sums well, made progress on grids, and still struggled even with number puzzles it practised. We also found that training unfairly demands one particular correct answer. Those are different problems. We have not yet shown that fixing the answer target, adding scratch cards, or teaching intermediate steps solves either one. The next comparison needs a clearly specified single change and an adequately fitted baseline.

No five-number sealed panel was generated or read in this diagnostic. There is no candidate efficacy result, four-seed registered comparison, or build approval here. These results say nothing about the 1B chat model or joined build.

Reproduce/recount from repo root:

```sh
python3 -B scripts/codex_numbers_20260927_labels.py --precompute-practice artifacts/codex-numbers-20260927
python3 -B scripts/codex_numbers_20260927_diagnose_predictions.py --eval artifacts/codex-numbers-20260927/diagnostics/baseline-s9276191/numbers4.json --out artifacts/codex-numbers-20260927/diagnostics/baseline-error-breakdown.json
python3 -B scripts/codex_numbers_20260927_history.py --ref 43b4d6f487f3ac67cc4deaf4c889e28b2416d0a0
```

The general registered-run supervisor and recount script are preparation for the comparison; this diagnostic section contains no registered result.

## Revised diagnostic: completed 60,000-step fit check

SHOWN: width256/2-layer fixed-env baseline seed9276193 reaches 919/962 practice exact at step20,000 and 933/962 (96.99%) at step25,000, while scoring 0/100 on its own four-number dev split at both probes. Step25,000 fresh dev sums4 is 200/200 and grids5 is 197/200. Saved interim proof: diagnostics/fit-gate-step25000/evidence.json and checkpoint.pt.

SHOWN: at the completed step60,000 own-stop probe, it scores 962/962 practice four-number hands valid and stored-exact, 0/100 disjoint development hands, and 200/200 on each fresh sums4 and grids5 panel. The final training window reports 1.0 exactness on numbers3 and numbers4. Runtime is 73.88638 minutes on MPS float32. The final checkpoint SHA256 is `6b33d9ddf241e4c66aa43d461251d118a334e671b67fc78bb04031720ffa136a`; input/round stream SHA256 is `843fc3276aad748c44ce89905005702a58127ba98550212076f83510263d87c2`. The split manifest SHA256 is `9635ecefc358a30c51cc19b7f7f9544365e4238bd8361c941d1b753306d0f3f5`. These values are recorded in diagnostics/fit-baseline-s9276193/train_summary.json, with per-step evidence in probe_log.jsonl and train_log.jsonl.

This confirms the prerequisite for testing the candidate and reproduces the memorization gap on this Mac without the hidden kind label. Ben selected learned scratchpad-only after reviewing a combined scratchpad/bookmark design. SELECTED-DESIGN.md records the candidate. No candidate accuracy or registered PASS is claimed. The original registered panels remain reserved for the fixed registered sweep, and no fresh five-number sealed panel is part of this diagnostic.

For Ben: the larger local baseline now reproduces answers to every number hand it practised, yet solves none of our 100 development hands. That is the failure we wanted to reproduce. The planned scratchpad comparison will wipe its cards at test time to check whether stored information actually helps.

# critical-thinking-128: saved outputs of the old fresh-panel test (STUDY ONLY)

**Status: the 16 questions in this folder are CONSUMED. This data is for design study only. Do not reuse these questions or this gold for training, tuning, checkpoint selection, or any new "fresh" evaluation.** (Ben approved study of these saved outputs via the coordinator.) Provenance: `docs/premonition-status/CURRENT.json` -> `current_science`, and the receipts under `artifacts/cap256-launch/contextual-input-compare-v1/FRESH-TERMINAL-EVAL-PREPARATION-v1/`.

Not included on purpose: model checkpoints (.pt), reserved/blind user panels, training data, any credentials (scanned: none found). Claim scope in the source receipts: one newly authored 16-question arithmetic panel; novelty checked only against named available metadata. No generalization claim.

## What the 128 are
8 checkpoints x 16 questions = 128 saved model outputs. The 8 checkpoints = 2 seeds (0, 1) x input type (contextual / static) x learning-rate condition (control LR 1e-3 / low_lr 1e-4). The 16 questions = 8 matched pairs (an ADD-needed and a SUB-needed question about the same two numbers, e.g. `inventory-01-add` / `inventory-01-sub`).

Totals (all independently recounted, `summaries/INDEPENDENT-POSTGOLD-RECOUNT-v1.json`):

| measure | count of 128 |
|---|---|
| correct final answer | 15 |
| correct calculator call (ADD commutative-equivalent, SUB ordered) | 86 |
| correct call then wrong final answer | 71 (86 - 15) |
| wrong/absent call | 42 (38 by choosing the wrong operation; others operand errors, 1 omitted call, 3 tool errors) |
| complete matched pairs correct (both questions of a pair right) | 0 of 64 |

Per checkpoint (`summaries/TERMINAL-FRESH-SCORED-TABLE-v1.tsv`; final/16, correct calls/16, correct-call-wrong-final): s0 contextual control 3/11/8; s0 contextual low_lr 3/11/8; s0 static control 2/11/9; s0 static low_lr 2/11/9; s1 contextual control 1/9/8; s1 contextual low_lr 2/9/7; s1 static control 1/12/11; s1 static low_lr 1/12/11. Sums: 15 / 86 / 71.

Mechanism of the failure mode (see the trace file): the model emits a calculator call (operation + operand references), the calculator executes it exactly and returns the right number as a result token, but the model's own emitted number token afterwards frequently is a different number (`emitted_numeric_ID` vs `calculator_numeric_ID` in the trace). Causal explanation is unproved.

## Files
`outputs/`
- `EVAL-OBSERVATIONS.jsonl` - the 128 raw saved outputs, one JSON row per (checkpoint, question): `arm`, `condition`, `seed`, `id`, raw generated token ids (`MODEL_raw_generate_ids`, `MODEL_generated_ids_with_observed_EOS`), `predicted_trace` (parsed calculator call and result), `routing`, EOS/contract flags, per-row timing/memory in `performance`. Token ids only; the tokenizer is not included.
- `GENERATED-CLOSED.json` - closure receipt for the generation run (counts, hashes).

`questions_and_scoring/`
- `QUESTION-ONLY-v2-UNFROZEN.json` - the 16 question texts with ids and pair ids.
- `NATIVE-v2-EVAL-INPUTS-UNFROZEN.json` - tokenized inputs and numeric registries (operand literals with char spans) per question.
- `GOLD-PRIVATE-v1.json` - gold per question: operation, operands, canonical numeric target, target token ids (`labels`), case type (carry etc.). Consumed gold.
- `SCOPED-SCORING-PROTOCOL-v3.json`, `ENDPOINTS-v1.json` - the pre-registered scoring protocol and endpoint definitions.
- `SCORE-REQUEST-v1.json`, `SCORE-v1.json` - the scoring request (with pinned hashes) and the full per-row scoring result (`results[].answers[]`: `operation_correct`, `equivalent_task_call_correct`, `combined_correct`, decoded answer, mechanical validity; plus comparative decisions and matched contrasts).

`summaries/`
- `TERMINAL-FRESH-SCORED-TABLE-v1.tsv`, `DEREK-RESULT-TABLE-v1.tsv` - the 8-row endpoint tables.
- `DEREK-SAVED-128-ROW-NUMERIC-TRACE-v1.tsv` - per-row: expected, emitted value, executed operation/operands, calculator value, outcome (`correct`, `correct_call_wrong_final`, `wrong_call_wrong_final`). Note: the first 3 columns after `seed` in this file cover seed 1 rows at the top; check the `seed` column for the rest.
- `DEREK-SAVED-FRESH-RESULT-DIAGNOSIS-v1.json`, `DEREK-SAVED-FRESH-RESULT-DIAGNOSIS-v2.py` - saved diagnosis and the script that produced it (CPU only, reads the saved files).
- `DEREK-ALL128-SAVED-PERFORMANCE-v1.json` - latency/memory summary.
- `INDEPENDENT-POSTGOLD-RECOUNT-v1.json` - separate recount that matches the totals above.
- `SAVED-OUTPUT-ROLE-TABLE-v2.tsv`, `SAVED-OUTPUT-CONCENTRATION-ROLE-DIAGNOSIS-v2.json` - breakdown by question role (add-needed vs sub-needed) and output concentration.

`pipeline_code/` (copied unchanged from `scripts/cap256_launch/`; several are hash-pinned by the scorer, so do not edit)
- `calculator_tools.py` - parses/validates the numeric-literal registry (`build_registry`) and executes calls (`execute_integer_call`: actions NONE/ADD/SUB, up to 4 calls, integers <= 1,000,000, results appended to the registry). No generated code is executed; no model is called.
- `calculator_runtime_depth_compare.py` - `CalculatorPath`: the model-side module that turns the core's output into a call and feeds the calculator result back into the four-loop forward.
- `fresh_core_calculator_constructor.py` - builds the calculator-equipped core variants.
- `eval_terminal_fresh_windows_v2.py` - generation runner for the 128 outputs (native greedy decode, calls calculator tools per row; no gold access).
- `score_terminal_fresh_approved_v3.py`, `fresh_terminal_eval_schema_v1.py`, `audit_fresh_core_comparison.py` - the CPU scorer (opens gold only after all 128 raw rows are verified) and its schema/arithmetic helpers.
Some of these modules import other repo modules (and a Windows-side tokenizer/torch environment) that are not included; they are here for reading, not for running.

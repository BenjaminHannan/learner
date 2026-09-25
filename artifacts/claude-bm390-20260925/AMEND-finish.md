# bm-390 amendment 3: finish the arms that did not run (benchmarks thread, 2026-09-25, registered before they run)

Updates AMEND-winnl2.md. PASSMARKS.md, the sealed code (SEAL-code.sha256.txt, 8 lines) and the scorer are unchanged.

## Where bm-390 stands (VERIFY-bm390.md)
The third attempt on BensPC finished P (0.1), P_bare, Rb and P's MMLU-Redux and GSM8K. M1 against Rb is a FAIL
(-22.07 points), which PASSMARKS makes final for 0.1. T ran out of GPU memory on its first question; C, Q2, L12 and
every plain general test did not finish. So M4 (no harm) is unjudged and there is no same-harness number yet for
the plain 1B with the whole chat or for either rival. Every later build (bm-391 on) needs those numbers as its bar.

## What runs now, and what does not
Runs once, on a rented RTX 5090 (Linux), which is bm-390's registered rental route (rent-bm390.md): T, C, Q2, L12 on
LoCoMo, and T, Q2, L12 on MMLU-Redux-300 and GSM8K-300, with the registered commands, into a NEW folder run2/.
P, P_bare, Rb and P's general tests are NOT rerun; their BensPC files stand. The plain arms are greedy, so the
machine can change only floating-point detail, not the method; the report names both machines.

## The one possible difference: how attention is computed for long prompts
T's crash (RESULTS-benspc3.md) came from the kernel PyTorch picked, not from the model: transformers 5.x hands
grouped-query attention to PyTorch (enable_gqa=True) whenever there is no mask; without the flash kernel PyTorch
falls back to the math kernel, which builds the full heads x L x L score matrix (a whole LoCoMo chat is 13,758 to 26,557 tokens, measured with each model's tokenizer).
Before any registered command, a check (scripts/claude_bm390_longctx.py, a made-up diary about fictional people,
at least 27,000 tokens, longer than the longest chat, 4 generated tokens) records peak GPU memory for the plain 1B:
- peak at most 8 GiB with the registered code path: every command runs exactly as registered;
- otherwise the check runs again under scripts/claude_gqa_wrap.py (transformers repeats the key/value heads itself,
  so PyTorch can use the memory-efficient kernel); if that is at most 8 GiB, EVERY plain command in this job runs
  under the wrapper, the same way for all arms; if not, nothing runs (LONGCTX-FAIL).
The wrapper computes the same attention. Evidence (Linux CPU, Python 3.11, transformers 5.17.0, MiniCPM5-1B
@87179e5c): with the wrapper the model makes 0 grouped-query calls instead of 72 on a 7,864-token prompt, and the
greedy reply to a 2,438-token made-up prompt is identical with and without it. The check then runs for Q2 and L12
in the chosen mode; a rival above 12 GiB or failing the check is NOT RUN.

## Data on Linux
fetch must print the Linux form of BensPC's samples: mmlu300_sha256 e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049
and gsm8k300_sha256 df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949 (with "\n" -> "\r\n" these
are exactly BensPC's 1a44e304...3850 and 073acc01...555b; VERIFY-bm390.md).

## Scoring
run/ (BensPC) and run2/ (rental) are copied into one folder and scored once with the sealed scorer:
`--primary P --baselines T,Rb,Q2,L12 --report C,P_bare`, then a blind recount. M1 stays FAIL whatever these arms
show. M4 is judged against T. The rivals' numbers become the bar for bm-391.

## Predictions for the new arms (before they run)
- F1: T's categories 1-4 F1 is 15 to 35 (P390.1); Rb (25.06) is within 5 points of T (P390.5); C is at most 8
  (P390.4); Q2 and L12 each score above P's 2.98.
- F2: M4 FAILS: T scores at least 3 points above P on MMLU-Redux-300 (P 28.33%) or on GSM8K-300 (P 9.67%).
- F3: the registered code path fits on the 5090 (the flash kernel handles grouped-query attention on Linux), so
  the wrapper is not needed.

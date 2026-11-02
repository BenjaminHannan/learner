# Probe-5: Probe-4 rerun on LFM3-1.7B (the new small tier)

Fixed 2026-10-27 ~22:10Z, before any LFM3 try, test or training run. Ben (19:45Z Oct 27) made LFM3-1.7B the small tier
in place of K2-Horizon-3.7B. Probe-4 (PASS on K2: 12 tries + K2's trained tests 66.7% vs one try 50.0%) is rerun with
LFM3. One change from Probe-4: the backbone. Same 96 frozen tasks (`creative/probe4/tasks_new.jsonl`, sha256
b6c23113...27ab), same sandbox, tool list, system prompt, pickers, metric and pass marks.
Small card experiments and the village model are not involved. Labels: shown / suggested / untested.

## Model and serving (Ben's M3)
- LFM3-1.7B BF16 GGUF (official LiquidAI/LFM3-1.7B-GGUF) on llama.cpp built from source with LFM3 support,
  `llama-server --jinja`, thinking off (`enable_thinking=False`; any text up to `</think>` is cut). BF16 rather than
  the app's QAD-Q4_0 because QAD weights differ ~7% from the bf16 weights the LoRA is trained on; a Q4 check is later.
- Tries: T0.7, top_p 0.95, up to 6 turns, 12 per task (as Probe-4).
- Test-writer LoRA: the Probe-3 recipe on LFM3 (same 449/49 Haiku train/val sets from 372 non-target tasks, r16 /
  alpha 32 / dropout 0.05, lr 1e-4 cosine, 2 epochs, effective batch 16) on the LFM3 target regex (attention q/k/v/o,
  conv in/out, feed-forward w1/w2/w3), torch + peft on MPS with a vendored copy of LiquidAI's model file (no remote
  code fetched), converted with `convert_lora_to_gguf.py` and served with `--lora`. Fixed before training: keep the
  last checkpoint (no picking by test score).

## Pickers (as Probe-4)
FIRST, RAND, VOTE, SELF (LFM3 P(yes) judge), TEST-B (untuned LFM3 tests, Probe-2 prompt with start state, 4 samples,
ties by SELF), TEST-T (primary: LFM3 + LoRA tests, same prompt and settings, ties by SELF). ORACLE as the ceiling.

## Pass marks (fixed now, same as Probe-4)
- E1: TEST-T >= FIRST + 10 points. E2: TEST-T >= SELF + 5. E3: TEST-T >= TEST-B + 5.
PASS = E1-E3. PROVED WRONG: TEST-T <= FIRST + 3 points. Otherwise INCONCLUSIVE.
Also reported: traps vs non-traps; tokens per picker; wall time on the M3; LFM3 vs K2 per picker (descriptive only,
no pass mark, different backbones).

## Validity gates (checked before reading any picker result)
- Replay gate: replaying each try's tool calls reproduces its success on >= 99% of tries.
- Tool-call parse: >= 90% of tries contain at least one parsed tool call or a final reply (no format collapse).
- LoRA: val loss after training below val loss before; TEST-T empty-sample share <= 10%.
If a gate fails the run is INVALID (not a result), the fault is fixed and the run repeated once.

## Cost
Free (M3). Estimate: training 1-3 h (MPS speed for LFM3 is unmeasured), tries + tests + SELF 2-4 h.

## Next (not part of this test)
Probe-6, the trick-job fix: on Probe-4's pools, winning trap tries end with a question 122/137 times, losing
non-trap tries that ask 112/122 (shown, K2). So a "should I ask first?" judgment gating an ask-preferring pick could
close most of the 31.6 -> 60.5 gap. Its own prereg comes after Probe-5.

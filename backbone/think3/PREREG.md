# Think-3 preregistration: copy the written reasoning into silent laps (CODI-style), K2-Horizon-3.7B, Ben's PC

Written and sealed 2026-10-25 ~22:00Z, before any Think-3 code or run, and before the Think-2 verdict.
Labels: shown / suggested / untested. Ben's rule: runs only on BensPC (RTX 5070 Ti 16 GB).

## The one question
Can K2-Horizon-3.7B, with thinking off, learn to do in a few silent laps what it does when it thinks in words?
Recipe (CODI, arXiv 2502.21074): one model plays teacher (writes its reasoning) and student (silent laps), and the
student is graded on matching the teacher's hidden state at the token just before the answer, not on the answer alone.
Evidence (shown, other labs, short math traces): 67-97% of the written-reasoning gain kept; dropping the hidden-state
match costs ~19 points. Risk (shown): on long, wordy traces it falls apart (Qwen-1.5B: 53% written vs ~13% silent).

## Task and data
Village task, same splits as Think-1/2 (train depth <= 3; validation 8,675 rows to depth 6; the sealed test is never read).
Teacher traces: K2-3.7B with thinking ON at reasoning_effort "low" (short traces, per the warning above) on training rows;
keep only traces whose final answer is exactly right. Thinking OFF uses swap/templates/k2_nothink.jinja.

## Gate 0 (cheap, ~1-2 h, decides whether there is anything to copy)
Score base K2-3.7B thinking-on (low) and thinking-off on the first 1,000 validation rows.
- G0 passes if on - off >= 8 points. Otherwise STOP: report, no Think-3 training.
- Also record on's mean thinking tokens per answer (T_on) and how many training traces come out correct.

## Arms (seed 0, all LoRA r=16 on the same layers, same steps N, same batch order)
| arm | what it is |
|---|---|
| off | thinking-off LoRA on answers only (the control) |
| codi | thinking-off + K = 6 silent laps: the last hidden state goes back in as the next input through a 2-layer MLP + residual; loss = student answer CE + teacher CE on its own correct trace (same weights, teacher-forced) + L1 match of all layers' hidden states at the token before the answer (teacher side stop-grad), as in CODI |
N is set from Gate 0's traces and timing before the arms start, and recorded in RUNLOG before any arm result.

## Scores (validation, 8,675 rows, greedy exact match)
S_off, S_codi; S_on = base thinking-on (low) on all 8,675 rows (the ceiling). Lesions on codi: K = 0 laps; swap (row reads another
story's latents); mean latents.

## Pass marks (fixed now)
- **P1 gap:** (S_codi - S_off) / (S_on - S_off) >= 0.50.
- **P2 beats control:** S_codi - S_off >= +3.0, paired bootstrap 95% interval excluding 0.
- **P3 latents used:** S_codi - S_codi(swap) >= +2.0.
- **P4 cost:** codi's generated positions (6 laps + answer tokens) <= 20% of thinking-on's mean generated tokens.
All four needed to call it a pass. A pass means: 2 more seeds on the PC, then a speed test on the Mac before any v2 use.

## Wrong-if
S_codi - S_off < +1.0, or the swap lesion costs < 1.0, or K = 0 scores within 1 point of codi (the laps carry nothing).
Any of these: drop silent-lap reasoning for v2 and say so.

## Known risks, stated in advance
- K2-3.7B in bf16 is ~10 GB; training on 16 GB needs gradient checkpointing and small micro-batches (untested on this PC).
- The teacher pass doubles the work per step, so codi costs more per step than off; matched on steps, not compute (favours codi).
- One seed: a pass is a signal to expand, never a result.
- Think-2 (G-STS on Qwen3.5-0.8B) is a different mechanism; its verdict does not decide Think-3, but Gate 0 does.

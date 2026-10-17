# Funding bid SC-1 (to the coordinator)

Status: BID. Nothing is booked.
**Ruling (Q22, 2026-10-17):** Stage 0 is YES in principle, with a hard stop at $0.50, on an on-demand box only.
It books ONLY after the Q20 code review passes and `span_cards.py` is committed. The overhead placeholder below
is filled from the Stage 0 measurement itself. Stages 1 and 2 are NOT booked: Stage 1 waits for the Stage 0
report (projected ≤ $18, branch-point check identical, smoke finite), a sealed card and the coordinator's
queue call. Stage 2 waits for Stage 1's G1-G4 and next week's cap. If Stage 0 projects Stage 1 above $18,
stop and re-bid (no seed cut). $0 work (design, code, tests, run card, local data pilots) is done under the
standing pre-approval. **No training rental starts until the coordinator gates it**, one stage at a time.

## Ask, in one line
Stage 0 (≤ $0.50) now; after it reports, Stage 1 (≤ $18) this week; Stage 2 (≤ $18) next week, only if Stage 1's
guards pass. Total ceiling $36.50 over two weeks, never more than $18.50 in one week (37% of the $50/week cap).

## What each stage buys

| Stage | Work | Buys | Cap | Gate to continue |
|---|---|---|---|---|
| 0 | One verified single-GPU box (3090 ≈ $0.16-0.20/h or 4090 ≈ $0.40/h, read-only price query 2026-10-17), ≤ 45 min: build the label-free v2 caches, measure seconds/step for LINE and SPAN in gold/teacher/own on real 52k-token batches, run the branch-point identity check and a 200-step SpanTrainer smoke on GPU | the real cost of Stages 1-2 (the one unknown below) and a GPU check of the code | $0.50 | projected Stage 1 cost ≤ $18, branch-point check identical, smoke finite |
| 1 | Parents P_0..P_2 (5% of F each) + Cell A: LINE and SPAN × 3 seeds × 95% of F; DEV economy reports | P1-P3 and guards G1-G5 on today's data: is SPAN safe on the ruler, and does the gate move at all | $18 | G1-G4 pass for SPAN (else Stage 2 is not requested) |
| 2 | Cell B: LINE and SPAN × 3 seeds × 95% of F on reflowed train data, from the same parents | P4-P6: does a learned layout beat per-line cards when line breaks stop matching facts (Ben's question) | $18 | none (final) |

Sealed held-out scoring (E1, E3) is the coordinator's; it is inference only (12 models), well under $0.50 at the
same box rate, and is included in the Stage 1/2 caps.

## Cost model (measured parts marked)
- D full (2,102,228 params): **measured** 0.91e12 FLOPs per teacher batch and 1.36e12 per own batch on a real
  label-free 52k-token batch (41 visits, 422 questions; `flops.measure_mini`, this session). Curriculum-weighted
  ≈ 1.2e12 per step, so a full run at F ≈ 3.15e16 (design/06 §4) is **≈ 26,000 steps / ≈ 1.35B tokens**.
- Plan size: 0.15 (parents) + 5.7 (Cell A) + 5.7 (Cell B) = 11.55 full-run equivalents.
- SPAN overhead vs LINE: **to be filled from the Stage 0 GPU measurement (Q22).** CPU pre-measure, for
  context only and not used for costing: about +15% wall per own-mode step (27.7 s vs 24.2 s, one sample).
- **Unknown: GPU seconds per step.** The think loop is Python-level (up to 8 loops × per-question gathers), so D
  is launch-bound, not FLOP-bound; nothing in the repo measures it on a GPU. CPU (4 threads) is 23 s/step.
  Assuming 0.3-1.0 s/step: 2.2-7.2 h per full run, Stage 1 ≈ 13-42 GPU-h, Stage 2 the same.
  At $0.40/h (4090): Stage 1 ≈ $5-17; at $0.18/h (3090, if comparable speed) ≈ $2.5-8. The caps sit at the
  top of the 4090 range; Stage 0 replaces this range with a measurement before any real spend.
- If Stage 0 projects Stage 1 above $18, I stop and re-bid (options: the BensPC 5070 Ti at $0 if it is free, or a
  smaller F applied identically to both arms, stated before sealing). I do not cut seeds: the family rule needs 3.

## What it displaces
Stage 1 takes up to $18.50 of this week's $50, leaving ≥ $31.50 for other queued work. I cannot see the
coordinator's queue (the newest dated plan in the repo is 2026-09-30), so the trade is the coordinator's call.
Stage 2 is deliberately pushed to next week so it never stacks with Stage 1.

## What it does not buy
No architecture change to the main line (only Ben approves those), no claim beyond the run card's predictions,
and no tuning: the four SpanConfig numbers (max_span 64, newline_prior 8, base_logit −4, w_rate 0.03) are fixed
in the card and are not searched.

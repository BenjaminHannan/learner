# P2 zero-GPU far diagnostics. Marks written before any scoring, Wed Oct 14, 2026, 2:27 AM ET (the scoring jobs started 2:29 AM ET)

Thread "Far transfer (ultracode)". Free cloud CPU only, scoring of saved checkpoints, nothing trained, no sealed panel row read
(probe rows only: far-transfer/diag/sheet-probe.jsonl, cells F4-two and F5-far, 420 rows each).
Labels: **shown** = measured, **suggested** = reasoned, **untested** = never run.
Source of the questions: Ben's merged action list (10-14 2:16 AM ET), P1 config lookups and P2 diagnostics.

Seed rule (Ben's tiered rule): every checkpoint below is ONE training run, so every headline here is UNPOWERED (screening at best).
Row-level uncertainty (420 rows, bootstrap 95% interval) is shown, but it does not stand in for seeds. No best-of-anything.
Quarantined, not used: all join-last figures (L10, L12 and their A1 audits). The pieces-multiplied argument is withdrawn in its strong form.

## What a "join" and a "piece" are here

A joined question is `grid ; =K+J` or `grid ; =(K)*(J)`. The tool (domain.tools.sheet) gives the working: K's steps, then J's, then the
join call (the 7-round call cap is never exceeded: F4-two has 3-7 steps, F5-far 3-7, shown). The model writes each call as text, the
calculator outside the model returns the result, and the entry `add 12 5 = 17` goes on the tape the model reads (custom_io/models/tool.py
docstring). So piece results come back as tape tokens written by the calculator, not by the model; the model only copies them into the
next call or the answer.

- **Alone**: the piece asked by itself on the same grid (`grid ; =K`).
- **In context**: the same piece inside the whole question, scored from the model's own calls on the whole question, in order:
  K_ctx = its first nK calls equal the tool's K steps (add/mul/min/max either operand order), J_ctx = the next nJ calls equal J's steps,
  join_ctx = the last call equals the join step.

## Checkpoints (all kept in the scratchpad; each ONE run, step 4000)

Baselines with no join practice: parent T1SDR s200, L8-LB, L8-LA64 (the mode's own makers). Join-practised: L9-LB, L9-LA64 (whole-formula
joins), L7-LB (hand-made joins, unguarded, old skills wrecked). Guarded join-practised: L11 (soft 1 + 10x KL), L13 (soft 10 + 10x KL),
L14 (hard + 30x KL). Not scored: L12 (join-last, quarantined).

## Measures (fixed now)

1. **W** whole question right, the probe's own score (`accepted` list). **W_norm** the same with the answer normalised (strip, `+`, leading
   zeros, trailing `.0`, thousands commas; numeric equality). **W_calls** all calls equal the tool's, in order.
2. **Ladder** (nested, in order): R1 first call right; R2 K done (first nK calls); R3 K and J done; R4 all calls right; R5 final answer right.
   Same ladder with calls compared **order-free** (a multiset of normalised calls), to price reordering.
3. **Alone**: K_alone, J_alone, P = both (value right, as A1), and call-level K_alone_calls. **Combine** T/P: the model's join of its own two piece
   answers (an outside splitter's score T, as A1).
4. **Conditioned piece accuracy** (the one number): K_ctx rate, J_ctx given K_ctx, join_ctx given K_ctx and J_ctx, each with n, against K_alone_calls.
5. **Taxonomy** of every failed whole row, by the first differing call (round r, in order): none (no calls), stopped early, extra calls,
   wrong op, reordered (the call is a later valid step of the tool's working), wrong operand read from the prompt (a prompt number that is
   not the right one), wrong intermediate (an earlier result used wrongly), operand not found anywhere (composed), plus where it sits
   (round 0 / inside K / inside J / join call) and pair type.

## Marks

| Question | Yes | No |
|---|---|---|
| Q1 the whole score is an eval artifact (answer format) | W_norm - W >= 3 points on any non-quarantined checkpoint | W_norm - W < 1 everywhere |
| Q2 combining is the failure ("real combine rate") | K_ctx >= 0.8 x K_alone_calls and join_ctx given K_ctx, J_ctx < 50% | join_ctx given K_ctx, J_ctx >= 80% |
| Q2b in-context piece loss is the failure | K_ctx < 0.5 x K_alone_calls on the baselines | K_ctx >= 0.8 x K_alone_calls |
| Q3 the 10% dissolution rule fires | corrected join baseline >= 10% on a baseline checkpoint (definitions below) | below 10% on all |
| Q4 first-step routing (round 0) is the main first error | round-0 share of first wrong calls >= 50% on F4-two and F5-far of the baselines | < 50% |
| Q4b round-0 errors are ordering, not wrong work | reordered share of round-0 errors >= 30% | < 10% |

### Definitions for Q3 (the roadmap does not define "corrected join baseline"; all three are computed, the first is the one applied)

- **D1 artifact-corrected whole score** (same protocol, same model, only the scorer corrected): W_norm. This is the literal reading and the one
  applied to the rule. "Baseline" = parent, L8-LB, L8-LA64; "joins" = F4-two, "far" = F5-far.
- **D2 splitter score T**: the model's own piece answers, the model's own join of them, an outside piece splitter. A different protocol, so
  reported, flagged, NOT applied to the rule (deployable autonomy: the splitter was dropped on 10-12). If D2 is at or over 10% the line says so.
- **D3 ladder mean**: reported as partial credit, not a pass rate, so not comparable to 10%.

## Predictions (suggested, written now)

W_norm - W under 1 on every checkpoint. On the baselines K_ctx is 20-35% of F4-two rows against 70-90% alone (A1 saw 310 of 407 first errors in K
on L8-LB), join_ctx given both pieces right in context at 90% or more. D1 about 3-4% on F4-two and about 1% on F5-far, so the rule does
not fire on D1; D2 about 40-45% on F4-two (over 10%) and 9-12% on F5-far (at the line). Round 0 about 60-65% of first wrong calls, and
part of it will be the model doing the second piece first (reordering), which would make the K-wrong count of the old A1 table too high.
What would prove this wrong: K_ctx close to K_alone (then pieces survive the join and the join step is what fails), or W_norm over W by
3 or more (then the scorer hides skill).

Plain-language line for Ben: a joined question is two small sums stuck together. We ask: does the model get each small sum right when
it sits inside the big question, or only when asked alone? And is the 4% just us marking answers too harshly?

# Skill-Sleep 2: a longer night, harder bad examples, and asking kept alive

Preregistered 2026-10-26, before any run. It follows Skill-Sleep 1 (RESULTS.md): +3 points, inside the noise. The night
barely moved the model (54 steps, probe NLL -2%), and the 33 good/bad pairs saturated within 10 steps.

## Same as Skill-Sleep 1
K2-Horizon-3.7B bf16, thinking off, vLLM serving, tau2 retail (cc1df47 + Haiku judge patch), Haiku 5.5 as the customer.
Day = retail train split x 2 tries. Test = retail test split (40 tasks) x 4 trials, airline test x 2, ARC-Easy 200.
Fix stage: a Sonnet critique as a hint and up to 3 retries, kept only when the check passes. The critiques now go through
the Message Batches API. LoRA r16, lr 1e-4, accumulation 4, clip 1.0, DPO beta 0.1, DPO/KTO weight 0.2, anchor KL 0.1.

## What changes
1. Night x4: EPOCHS 8 instead of 2, on the same data, for every trained arm.
2. Near-miss fork pairs (arm C3 only). At decision tokens in day runs (turn start, tool name, argument value) where the
   model was confident (p1 >= 0.9) but a runner-up had p2 >= 0.005, force the runner-up, let the model finish that turn,
   then let tau2 play the rest of the conversation and check it. Up to 6 forks per run, on failed and passing runs alike.
   A fork whose outcome differs from its parent gives a pair that shares everything up to the fork. The DPO loss counts
   only tokens after the fork point.
3. Asking guard, in every trained arm. Skill-Sleep 1 trained on whole conversations, so authentication and "please
   confirm" questions were already SFT targets. This run measures that share and the ask rate (below). The Ask-once test
   showed that action-only nights can erase asking (57/420 to 0/420).

## Arms (2 training seeds each, except A0)
- A0: no sleep (the base model; its test is run once on its own GPU).
- C1: good only, night x4.
- C2: good + bad (the Skill-Sleep 1 A2 recipe), night x4.
- C3: C2 + near-miss fork pairs, night x4.

## Pass marks (fixed now)
Retail test pass rate, mean of 2 seeds, paired over the 40 tasks with a sign-flip permutation test (per-task means across
seeds and trials).
- Q1 longer night helps: C2 >= A0 + 6 points, p < 0.05.
- Q2 bad examples help at dose: C2 >= C1 + 4 points, p < 0.05 (a gap of 4 or more with p >= 0.05 counts as "suggested").
- Q3 near-miss pairs help: C3 >= C2 + 4 points, p < 0.05 (same "suggested" rule).
- Q4 pairs are not saturated: in C3, DPO accuracy stays below 0.95 for at least the first half of training. Label only.
- Harm (each trained arm): airline >= A0 - 7.5 points; ARC-Easy >= A0 - 2 points; ask rate >= half of A0's.
  Ask rate = the share of write tool calls (cancel, modify, return, exchange, address and payment changes) that come
  right after an agent message to the user ending in "?" with a user reply in between. The number of agent questions per
  conversation is also reported.
- Wrong if: C2 <= A0 (a longer night does nothing), or C3 < C2 - 4 (fork pairs hurt).
- Seeds: a win must hold in both seeds (each seed's delta > 0).

## Not claimed
Haiku stands in for a real person. The day is one store. The q4 base and the big tier come after a pass.

## Compute
Ben's two RTX 4090s through the GPU queue ("Keep the two 4090s busy all week"). The Anthropic key runs Haiku (customer and
judge, live) and the Sonnet critiques (batched). Ben OK'd the key on rented GPUs on Oct 25 at 12:36Z.

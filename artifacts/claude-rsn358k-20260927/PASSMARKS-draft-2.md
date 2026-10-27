# rsn-358k DRAFT 2 for the Thread manager (sleep research thread, 2026-09-27 13:48:57 UTC; not sealed; the dev pilot is running)

This replaces DRAFT 1's marks section. It adds the Thread manager's 6 review points (12:50 UTC) and the 3 problems the code check found (A, B, C). Code: scripts/claude_rsn358k_run.py (e8a1d5be6, draft; its docstring lists every design choice). The world layout, arms and task are as in DRAFT 1 unless stated here.

**Scope** (Thread manager, 12:51 UTC): read-only fact cards, filled from outside, with look-alike decoys and chaining. Sol's numbers task tests a different thing: a writable scratch store on make-24, where the net writes its own partial results. Seeds, folders and machines are kept apart.

## What the code check changed
- **A. Answers alone cannot show choosing.** The soft top-4 read returns 4 cards per call, and a name sits on at most 4 cards. So a key that matches only the name always brings the asked card in, and the layers can pick it by place. G1 on answers could pass with keys that never learned both fields. **Fix:** choosing is graded on the top-1 read, a new mark G1k (below). Top-1 means the card with the highest read weight, scored by code against the known asked card. It is a measurement only, never a training signal.
- **B. Card type leaked a hint.** A reader using name plus type got 0.481 on q1 (0.756 on q2), against 1/3 by name alone. **Fix:** every look-alike of a chain card now shares its type (selftest checked). On 20,000 fresh non-test worlds, name plus type is now 0.333 on every kind. Place alone is 0.24-0.25. Place plus type is 0.24 on q1 and 0.29 on q2 and q2c3. So the one-field ceiling for a top-1 read is 1/3 (100 of 300).
- **C. The no-store arm has equal weights but not equal training.** In no-store the NULL card always gets weight 1, so the store's query, pool and key weights get exactly zero gradient. The weight counts are exactly equal (1,717,670 in each arm; the store parts are 101,956 of them). This is built into the comparison, and it is disclosed here.

## Thread manager points
1. **Report-only 3-card chains (q2c3), 300 items, never practised.** They show whether chaining carries past the practised length; the 09-18 toy broke on new two-hop (14/189).
2. **Which card each call read, per round:** scored by code against the known chain cards. The top-1 and the top-4 are reported per round (rounds 1-8 and the loop's own stop) as counts of: the asked card, the next cards on the chain, NULL, same name, same place, other. It is report only, except G1k.
3. **Pasted-cards arm (report only, 2 seeds).** The same net with the 16 cards in the input and no calls. **Written now:** if pasted >= store on the q1 and q2 means, the conclusion is "at 16 cards, the store does not beat reading every card". That holds even if the store PASSes. A store earns its place only where the cards do not fit in the input, which is a later test.
4. **Why the loop is 2 x d256 (358i3 was 2 x d512):** this tests whether answer loss alone can teach card keys. It is not a size comparison with 358i3. d256 is 358e's small CPU net, and d512 would cost about 4x per step on CPU. Weights: store = no-store = pasted = 1,717,670. Pasted leaves the store parts unused, so 1,615,714 are active.
5. **Practice/test overlap:** each run logs how many practice worlds' 16-card sets hash-match a test world (tests/world-hashes.txt, 1,200 hashes). It must be 0. It was 0 of 12,800 in every smoke run.
6. **Dev pilot:** dev world seeds only. It sets --steps only. Batch 64, lr 1e-3 with 100 warm-up steps, weight decay 0.1 and a cosine schedule are fixed now, from 358e's small nets. The marks below do not move after the pilot. Its steps, and the minutes per 100 steps, go into the sealed plan.

## Marks (fresh sealed test worlds, 300 items per kind, answer at the loop's own stop; store and no-store, seeds 17-20)
| mark | pass |
|---|---|
| V leak | no-store <= 15/300 on q1 and on q2, on every seed. Otherwise INCONCLUSIVE. |
| G1 answers | store q1 mean >= 240/300, and >= 200 on at least 3 of 4 seeds. |
| G1k keys choose | store q1: the asked card is the top-1 read at round 1 (the call made from the question alone). Mean >= 200/300, and >= 150 on at least 3 of 4 seeds. 200 is double the one-field ceiling (100). |
| G2 chaining | store q2 mean >= 150/300, and >= 100 on at least 3 of 4 seeds. |
| G3 uses the rounds | on q2, store right at its own stop >= store right at a fixed 1 round + 50 (mean over seeds). |

**PASS = V, G1, G1k, G2 and G3.** Anything else with V met is a FAIL, and it stays a FAIL.
**Proved wrong** (for "answer loss alone teaches the store's keys to choose, at this size"): V met and the G1k mean <= 100/300, i.e. no better than matching one field.
**Report only:**
- q2: the pointer as top-1 at round 1, and the target as top-1 at round 2. A chaining claim beyond answers needs the round-2 count >= 150; otherwise RESULTS says "chains in its answers, not shown in its reads".
- q3, q2c3, the pasted arm, and each key head's attention on the name vs the place token (the 09-18 collapse measure).
- The practice/test overlap, steps_block_nograd, torch version and minutes per run.

**Predictions** (made before any full run, after the 200-step smokes only): V 95%; PASS 25%; proved wrong 35%. They are lower than DRAFT 1 because G1k now needs the keys themselves to choose, and the 09-18 toys never learned that from answer loss.
**Cost and place:** $0, CPU in this container, 1-2 threads per run. Store and no-store take about 94-101 s per 100 steps (200-step smokes); pasted takes about 302 s. 8 graded runs plus 2 pasted runs; the hours depend on the pilot's steps.
**A PASS is a test result only.** Putting a card store into the build is an architecture change and needs Ben's yes.

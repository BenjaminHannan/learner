# Transfer diagnostic: reuse a canonical lookup, and make the intermediate entity explicit

20 September 2026 UTC. Track A toy only. B is the ordered-evidence token-memory recipe; C is its scaled-initialization, 6,000-update variant. These labels are unrelated to candidates A/B in design notes 14–15.

**Shown.** The saved models already answer the terminal question extremely well when it is presented as an ordinary one-hop query about the true endpoint: **507–512/512 held-out answers and 503–512/512 edited pairs**, across all six checkpoints. This is a strong positive localisation result. It supplies the correct endpoint and resets the query, so it is **not autonomous two-hop transfer**. No weights were trained or changed.

**Shown.** The proposed universal diagnosis, “hop 1 transfers; only terminal relation binding fails,” is false at the requested final-question-row attention measurement. B0, B2, C0 and C2 already lose the first link read when REL becomes held-out. C1 instead locates the link in 512/512 cases and fails later; B1 is intermediate. The failures are heterogeneous. Finding a line does not establish that its entity has been encoded into a usable intermediate state.

**Suggested.** Replace the continuous two-hop state interface with **two calls to the exact same canonical one-hop operator, passing a predicted entity token and resetting all query state between calls**. Start in the token-memory successor. This addresses both the early terminal-REL interference and the later failure to reuse an existing skill. It is one proposed replacement design with disclosed grammar and intermediate-label privileges, not a demonstrated learned solution.

**Shown — registration and custody.** [Original predictions](../../artifacts/astra-transfer-diagnostic-20260920/PREDICTIONS.md) were written before loading panels/checkpoints or reading their saved per-seed results; the pasted handoff's results were known. Its SHA-256 is `4b864c3920800738cac958f4e71c13dbdba2a74d27837a5ba5dcad847b90b20f`. The [95-file manifest](../../artifacts/astra-transfer-diagnostic-20260920/manifest.json), hash `0349a82d2928491e31fabba09012e98b6a791900891441684a67678a2ff07354`, freezes the harness, tests, registered source closures, plans, checkpoints and input panels. The matched-REL extension was separately [registered](../../artifacts/astra-transfer-diagnostic-20260920/FOLLOWUP-PREDICTIONS.md) **after B0's initial result** and before any matched-twin run. It is a prospective follow-up, not part of the original preregistration.

**Shown.** Existing plan loaders passed. Each of the six jobs exactly reproduced every registered fresh-evaluation prediction, unit-correctness flag, count and checkpoint fingerprint before diagnosis. Passive tracing and passive hooks preserved logits bit-for-bit. Checkpoint file hashes and model tensor fingerprints were unchanged afterward; the frozen source and panel hashes still match. Only the six existing fresh validation/development panels, seeds 202609201001–1006, were loaded. No test.pt, training, optimizer calls, installations, GPU, SSH, paid compute, credential inspection or external messaging were used. Python ran with `-B`, one Torch compute thread and one inter-op thread per process. Six primary jobs and the six-checkpoint follow-up completed on their first attempts; five instrumentation tests passed on their first attempt. Logs are retained, including negative hypothesis results. This does not erase earlier experiments' failures.

**Shown — native replay.** Every denominator below is 512; c4–c6 count an entire pair only when both questions are correct, with answer invariance also required in c6. None of these six saved checkpoints passes all six native thresholds.

| Seed | c1 | c2 | c3 | c4 pairs | c5 pairs | c6 pairs |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | 506 | 474 | 40 | 3 | 8 | 29 |
| B1 | 512 | 512 | 103 | 29 | 73 | 107 |
| B2 | 512 | 512 | 46 | 0 | 14 | 61 |
| C0 | 503 | 476 | 31 | 1 | 0 | 24 |
| C1 | 512 | 512 | 31 | 5 | 17 | 37 |
| C2 | 512 | 512 | 46 | 1 | 14 | 56 |

**Shown — evidence localisation.** Sum token attention into its original story line, at the final non-padding question row; average the four heads, then choose the highest individual line (including NULL). “Top” is a raw question count, not the largest pooled category. All 512 c2 and 512 c3 questions are included for every seed.

| Seed | Cell | Answers | Link top, step 1 | Link mass, step 1 | Endpoint top, step 2 | Endpoint top, step 3 | Endpoint mass, step 3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | c2 | 474 | 501 | 0.9394 | 477 | 470 | 0.8375 |
| B0 | c3 | 40 | 83 | 0.1624 | 8 | 4 | 0.0131 |
| B1 | c2 | 512 | 512 | 0.9980 | 512 | 512 | 0.9965 |
| B1 | c3 | 103 | 453 | 0.8561 | 31 | 241 | 0.4366 |
| B2 | c2 | 512 | 512 | 0.9983 | 512 | 512 | 0.9980 |
| B2 | c3 | 46 | 69 | 0.1404 | 15 | 17 | 0.0341 |
| C0 | c2 | 476 | 509 | 0.9802 | 477 | 469 | 0.8909 |
| C0 | c3 | 31 | 208 | 0.4264 | 4 | 1 | 0.0030 |
| C1 | c2 | 512 | 512 | 0.9987 | 512 | 512 | 0.9991 |
| C1 | c3 | 31 | 512 | 0.9889 | 6 | 25 | 0.0454 |
| C2 | c2 | 512 | 512 | 0.9995 | 512 | 512 | 0.9996 |
| C2 | c3 | 46 | 356 | 0.6715 | 19 | 21 | 0.0420 |

**Shown.** B0, B2, C0 and C2 meet the preregistered first-read-failure criterion: fewer than 80% first-link top lines or more than a 20-point loss versus c2. B1 has 453/512, missing the early-transfer pass mark of 461/512 and losing 59 cases versus c2; it does not meet the stronger first-read-failure criterion. C1 meets the first-read pass and has only 6/512 endpoint top lines at step 2. All six show a large later endpoint-location deficit. This rules out one common terminal-only explanation across the population; it does not show six different internal circuits or identify the content of a hidden entity register.

**Shown — complete line-category mass.** Entries are mean probability mass, rounded to six decimals. “Endpoint other relation” pools the endpoint person's two other attribute lines. “Other fact” contains the remaining eligible link/attribute lines; filler means filler-only lines, not filler tokens on fact lines. NULL is separate. These additions make the requested categories exhaustive. Full-precision sums, per-head means, and all raw top-line counts are retained in each result.json, [TABLES.md](../../artifacts/astra-transfer-diagnostic-20260920/TABLES.md), [per-head.csv](../../artifacts/astra-transfer-diagnostic-20260920/per-head.csv), and compressed per-question records. Rounded zero does not mean mathematical zero.

| Seed | Cell | Step | link | endpoint | decoy | endpoint_other_relation | filler | other_fact | null |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | c2 | 1 | 0.939448 | 0.000000 | 0.000000 | 0.000320 | 0.000000 | 0.060231 | 0.000000 |
| B0 | c2 | 2 | 0.000201 | 0.848046 | 0.029573 | 0.000214 | 0.000001 | 0.121965 | 0.000000 |
| B0 | c2 | 3 | 0.000539 | 0.837474 | 0.035320 | 0.000043 | 0.000000 | 0.126624 | 0.000000 |
| B0 | c3 | 1 | 0.162435 | 0.031400 | 0.005742 | 0.000797 | 0.000000 | 0.799626 | 0.000000 |
| B0 | c3 | 2 | 0.013130 | 0.020362 | 0.004181 | 0.130861 | 0.000002 | 0.831464 | 0.000000 |
| B0 | c3 | 3 | 0.034217 | 0.013058 | 0.003951 | 0.129050 | 0.000129 | 0.819595 | 0.000000 |
| B1 | c2 | 1 | 0.998028 | 0.000026 | 0.000082 | 0.000143 | 0.000000 | 0.001721 | 0.000000 |
| B1 | c2 | 2 | 0.000016 | 0.997487 | 0.000159 | 0.000296 | 0.000000 | 0.002042 | 0.000000 |
| B1 | c2 | 3 | 0.000015 | 0.996463 | 0.000305 | 0.000421 | 0.000000 | 0.002796 | 0.000000 |
| B1 | c3 | 1 | 0.856064 | 0.001678 | 0.000398 | 0.008896 | 0.000000 | 0.132963 | 0.000000 |
| B1 | c3 | 2 | 0.003646 | 0.097620 | 0.002841 | 0.786455 | 0.000000 | 0.109438 | 0.000000 |
| B1 | c3 | 3 | 0.003742 | 0.436554 | 0.010701 | 0.443327 | 0.000000 | 0.105674 | 0.000000 |
| B2 | c2 | 1 | 0.998337 | 0.000021 | 0.000000 | 0.000050 | 0.000000 | 0.001591 | 0.000000 |
| B2 | c2 | 2 | 0.000013 | 0.999045 | 0.000080 | 0.000148 | 0.000000 | 0.000714 | 0.000000 |
| B2 | c2 | 3 | 0.000061 | 0.997958 | 0.000223 | 0.000111 | 0.000000 | 0.001647 | 0.000000 |
| B2 | c3 | 1 | 0.140361 | 0.043253 | 0.067797 | 0.000000 | 0.000000 | 0.748589 | 0.000000 |
| B2 | c3 | 2 | 0.045986 | 0.028795 | 0.008514 | 0.147311 | 0.000100 | 0.769293 | 0.000000 |
| B2 | c3 | 3 | 0.011301 | 0.034071 | 0.009010 | 0.184001 | 0.000854 | 0.760763 | 0.000000 |
| C0 | c2 | 1 | 0.980235 | 0.000392 | 0.000050 | 0.000071 | 0.000000 | 0.019252 | 0.000000 |
| C0 | c2 | 2 | 0.000108 | 0.910519 | 0.010297 | 0.000706 | 0.000000 | 0.078370 | 0.000000 |
| C0 | c2 | 3 | 0.000002 | 0.890896 | 0.016514 | 0.000017 | 0.000000 | 0.092572 | 0.000000 |
| C0 | c3 | 1 | 0.426436 | 0.001932 | 0.139310 | 0.000047 | 0.000256 | 0.432019 | 0.000000 |
| C0 | c3 | 2 | 0.000000 | 0.007654 | 0.001641 | 0.273695 | 0.000000 | 0.717008 | 0.000000 |
| C0 | c3 | 3 | 0.000000 | 0.003042 | 0.001503 | 0.277756 | 0.000001 | 0.717698 | 0.000000 |
| C1 | c2 | 1 | 0.998713 | 0.000008 | 0.000000 | 0.000045 | 0.000000 | 0.001234 | 0.000000 |
| C1 | c2 | 2 | 0.000002 | 0.999435 | 0.000112 | 0.000001 | 0.000000 | 0.000450 | 0.000000 |
| C1 | c2 | 3 | 0.000002 | 0.999119 | 0.000174 | 0.000007 | 0.000000 | 0.000698 | 0.000000 |
| C1 | c3 | 1 | 0.988891 | 0.002236 | 0.000001 | 0.000061 | 0.000000 | 0.008812 | 0.000000 |
| C1 | c3 | 2 | 0.000002 | 0.014879 | 0.000001 | 0.691315 | 0.000032 | 0.293771 | 0.000000 |
| C1 | c3 | 3 | 0.000004 | 0.045384 | 0.000001 | 0.601134 | 0.000973 | 0.352504 | 0.000000 |
| C2 | c2 | 1 | 0.999450 | 0.000004 | 0.000004 | 0.000010 | 0.000000 | 0.000532 | 0.000000 |
| C2 | c2 | 2 | 0.000001 | 0.999795 | 0.000025 | 0.000005 | 0.000000 | 0.000174 | 0.000000 |
| C2 | c2 | 3 | 0.000003 | 0.999596 | 0.000048 | 0.000012 | 0.000000 | 0.000342 | 0.000000 |
| C2 | c3 | 1 | 0.671511 | 0.015203 | 0.053178 | 0.000000 | 0.000000 | 0.260109 | 0.000000 |
| C2 | c3 | 2 | 0.004546 | 0.041239 | 0.000536 | 0.268061 | 0.000000 | 0.685617 | 0.000000 |
| C2 | c3 | 3 | 0.036811 | 0.041953 | 0.007449 | 0.243582 | 0.000541 | 0.669663 | 0.000000 |

**Shown — wrong-answer accounting.** Attribute values repeat across facts, so token matches cannot uniquely establish which fact caused an answer. The requested five classes also omit wrong value tokens that match neither the endpoint's other relations, the decoy, nor another person's requested relation. We therefore retain multi-membership flags and add (f), rather than force false labels. The exclusive precedence is **(c), (e), (b), (a), (d), (f)**; (e) here excludes the link-entity answers already counted in (c), while the raw inclusive non-value flag includes them. (d) excludes the asker and endpoint; (f) includes remaining value tokens, whether elsewhere in the story or absent. Correct tokens are excluded even when they also match a decoy. “Value overlaps” counts wrong predictions matching at least two of (a), (b), (d).

| Seed | Cell | Wrong | (a) person/right, REL/wrong | (b) decoy | (c) link entity | (d) other person/same REL | (e) other non-value | (f) other value | Value overlaps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | c2 | 38 | 4 | 5 | 0 | 14 | 0 | 15 | 3 |
| B0 | c3 | 472 | 90 | 26 | 0 | 111 | 0 | 245 | 30 |
| B1 | c2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| B1 | c3 | 409 | 316 | 35 | 0 | 17 | 0 | 41 | 107 |
| B2 | c2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| B2 | c3 | 466 | 125 | 36 | 0 | 99 | 0 | 206 | 48 |
| C0 | c2 | 36 | 4 | 4 | 0 | 19 | 0 | 9 | 5 |
| C0 | c3 | 481 | 146 | 26 | 0 | 60 | 0 | 249 | 49 |
| C1 | c2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| C1 | c3 | 481 | 297 | 45 | 0 | 32 | 0 | 107 | 94 |
| C2 | c2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| C2 | c3 | 466 | 150 | 37 | 0 | 68 | 0 | 211 | 50 |

**Shown.** Every wrong answer is a value token; no seed emits the link's entity or another non-value token on these panels. In four seeds, fewer than half of held-out errors even match the union of (a) and (b). B1 and C1 fit that proposed error signature; the population does not. These are matching-token classes, not proven causal provenance.

**Shown — causal routing intervention.** L restricts every head and question row to the correct link line at read 1. E restricts them to the correct endpoint line at reads 2–3. LE does both. Scores are re-softmaxed within the permitted line, retaining native within-line preferences, values, residuals, anchors and weights. Q resets the model with `[question] true_endpoint REL [answer]`, the same story and causal eligibility. Only these interventions receive evaluator-derived information. Native evaluation remains label-free. Counts and paired gains/losses are relative to the native answers on the same questions; every denominator is 512.

| Seed | Cell | Native | L (+gain/−loss) | E (+gain/−loss) | LE (+gain/−loss) | Q (+gain/−loss) |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | c2 | 474 | 494 (+24/−4) | 507 (+33/−0) | 512 (+38/−0) | 507 (+35/−2) |
| B0 | c3 | 40 | 24 (+15/−31) | 214 (+189/−15) | 176 (+160/−24) | 512 (+472/−0) |
| B1 | c2 | 512 | 512 (+0/−0) | 512 (+0/−0) | 512 (+0/−0) | 512 (+0/−0) |
| B1 | c3 | 103 | 128 (+37/−12) | 488 (+386/−1) | 512 (+409/−0) | 512 (+409/−0) |
| B2 | c2 | 512 | 512 (+0/−0) | 512 (+0/−0) | 512 (+0/−0) | 512 (+0/−0) |
| B2 | c3 | 46 | 76 (+60/−30) | 199 (+163/−10) | 282 (+248/−12) | 512 (+466/−0) |
| C0 | c2 | 476 | 480 (+4/−0) | 512 (+36/−0) | 512 (+36/−0) | 502 (+33/−7) |
| C0 | c3 | 31 | 40 (+28/−19) | 509 (+479/−1) | 510 (+480/−1) | 507 (+476/−0) |
| C1 | c2 | 512 | 512 (+0/−0) | 512 (+0/−0) | 512 (+0/−0) | 512 (+0/−0) |
| C1 | c3 | 31 | 34 (+4/−1) | 512 (+481/−0) | 512 (+481/−0) | 512 (+481/−0) |
| C2 | c2 | 512 | 512 (+0/−0) | 512 (+0/−0) | 512 (+0/−0) | 512 (+0/−0) |
| C2 | c3 | 46 | 52 (+12/−6) | 322 (+288/−12) | 348 (+313/−11) | 512 (+466/−0) |

**Shown.** L gives no seed a 20-point rescue; its net changes on c3 are −16, +25, +30, +9, +3, +6. E alone reaches 488, 509 and 512 for B1, C0 and C1, but only 214, 199 and 322 for B0, B2 and C2. Even LE leaves those latter seeds at 176, 282 and 348. Correct line access is therefore not sufficient for the full population. In contrast, on practised controls, E loses no native-correct answer and LE gets every answer right in every seed. L loses four practised answers in B0; this individual harm is retained.

**Suggested.** C1 is the cleanest later-routing case: first-link location is already perfect, L barely helps, E repairs all 481 native errors. B1 is mostly later routing with some early errors. C0 has early failures, but giving the endpoint bypasses them successfully. B0, B2 and C2 also require something beyond this particular routing correction. The successful reset re-query implicates query/state/interface dependence. It does not separate token selection inside the correct line, residual contamination, decoder conditioning, or inadequate intermediate binding. An oracle clamp is an out-of-distribution intervention; its failure does not prove useful information is absent from the model.

**Shown — canonical re-query on changed facts.** Q uses each twin's own endpoint derived from its visible link, then scores the ordinary one-hop model. Changed-link Q therefore receives a changed entity in its question: it bypasses the very link-following operation that autonomous inference must learn. Changed-value Q must still read the new attribute value. These are oracle-interface sufficiency results, not six-cell model gate passes.

| Seed | c2 | c3 | c4 pairs | c5 pairs | c6 pairs |
| --- | --- | --- | --- | --- | --- |
| B0 | 507 | 512 | 511 | 511 | 512 |
| B1 | 512 | 512 | 512 | 512 | 512 |
| B2 | 512 | 512 | 512 | 512 | 512 |
| C0 | 502 | 507 | 503 | 509 | 510 |
| C1 | 512 | 512 | 512 | 512 | 512 |
| C2 | 512 | 512 | 512 | 512 | 512 |

**Shown.** The original P4 passes in all six seeds. Five seeds answer every held-out canonical query correctly; C0 gets 507/512. All edited-pair scores exceed the preregistered 461/512 threshold, with B0 at 511/511/512 and C0 at 503/509/510. This is stronger than ordinary training accuracy: existing weights handle these held-out endpoint queries and the value edits correctly after the interface rewrite. It still leaves autonomous entity prediction untested.

**Shown — original predictions, including failures.** P1 required early-link transfer and later endpoint failure; P2 required at least half of c3 errors to match (a) or (b); P3 required a small L effect but E and LE to gain at least 154 answers and reach 410/512; P4 required canonical c3 ≥487/512 and each edited-pair score ≥461/512. The numerical rules are unchanged. P1–P3 fail as universal B-population predictions.

| Seed | P1 first/late pattern | P2 (a) or (b) ≥half errors | P3 routing rescue | P4 canonical re-query |
| --- | --- | --- | --- | --- |
| B0 | FAIL | FAIL (116/472) | FAIL | pass |
| B1 | FAIL | pass (351/409) | pass | pass |
| B2 | FAIL | FAIL (161/466) | FAIL | pass |
| C0 | FAIL | FAIL (172/481) | pass | pass |
| C1 | pass | pass (342/481) | pass | pass |
| C2 | FAIL | FAIL (187/466) | FAIL | pass |

**Shown — matched-REL follow-up.** Only the terminal REL token changes between the three questions; story, asker, LINK, question length, slot and eligibility are identical. Thus the correct first link line and its endpoint are identical. Gain/loss counts compare first-link top-line decisions with r2 on the same 512 worlds. The follow-up M1 required both practised variants ≥461/512 and each to beat r2 by at least 103/512, in every seed.

| Seed | r0 link top | r1 link top | r2 link top | r0 gain/loss vs r2 | r1 gain/loss vs r2 | M1 |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | 496 | 506 | 83 | +414/−1 | +423/−0 | pass |
| B1 | 512 | 512 | 453 | +59/−0 | +59/−0 | FAIL |
| B2 | 512 | 512 | 69 | +443/−0 | +443/−0 | pass |
| C0 | 510 | 511 | 208 | +302/−0 | +304/−1 | pass |
| C1 | 512 | 512 | 512 | +0/−0 | +0/−0 | FAIL |
| C2 | 512 | 512 | 356 | +156/−0 | +156/−0 | pass |

**Shown.** M1 passes in B0, B2, C0 and C2, fails in B1 and C1, and therefore fails as a universal prediction. In the four passing seeds, replacing only the terminal REL changes first-link location by a large amount. B1 has a smaller 59-case effect; C1 has no first-link top-line change. This is direct input-intervention evidence of terminal-relation interference with early evidence location, not an effect of different c2/c3 story samples. It does not isolate a specific neuron or prove that all question rows share the measured failure.

**Shown.** Across all c3 inputs, changing the adapter's question line to any of the four trailing question slots produces exactly identical memory, question, owner and eligibility tensors. The token model has no prior-question input or global question-slot embedding. Therefore the original wire's reported question-block-slot shortcut cannot explain this successor under the tested adapter. This is not a fresh audit of the original model; its slot-sensitive reader and age/context effects remain a separate question.

**Suggested — what the evidence changes in Fable's reading.** Available information and gradient paths are not sufficient for compositional reuse. The evidence does not show they are irrelevant to every remaining failure: useful evidence selection is visibly wrong, and oracle routing helps some seeds enormously. “One circuit per practised combination” remains an interpretation, not a measured circuit decomposition. “The break is only in the terminal lookup” is too narrow for four seeds. “Held-out accuracy barely changes under memory removal, so the model barely uses the story” also overreaches: chance-like correctness can coexist with systematic use of wrong story facts. The defensible statement is poor *correct* grounding on native unseen combinations. The strong commonality is that the canonical terminal operation works, while its composition interface does not reliably preserve that ability.

**Untested — one recommended replacement, an explicit canonical lookup operator.** Keep the token-memory module's existing 79,316 parameters, width 48, four heads, three internal read steps, embeddings and full 68-token output. Define a canonical query with exactly the same four-token structure for either an attribute or LINK:

```text
q(x, s)              = [question, x, s, answer]
p_theta(t | M,x,s)   = softmax(E · answer_norm(h_theta(M,q(x,s))) + b)[t]
F_theta(M,x,s)       = argmax over all 68 tokens p_theta(t | M,x,s)

one-hop:  y_hat      = F_theta(M,a,r)
two-hop:  b_hat      = F_theta(M,a,LINK)
          y_hat     = F_theta(M,b_hat,r)
```

**Untested mechanism.** Reset the question encoding, anchor and recurrent state for each call. Share *all* operator parameters; pass only the predicted entity token between calls. Reuse story memory and its projections if caching is numerically verified. There is no original-asker residual, full original-question anchor, depth embedding, special hop-2 head, or latent donor state available to the second call. The first call cannot depend on terminal REL because it never receives it. With a correct predicted endpoint, the second call is literally the one-hop computation, not a separately conditioned branch merely encouraged to resemble it. This is a stronger constraint than weight tying recurrent read blocks, which the failed model already does.

**Untested training specification.** Use training worlds only. Each ordinary one-hop question gives one canonical attribute example. Each practised two-hop question gives two canonical training examples: `(a, LINK) -> b` and `(b, r) -> v`. With the current two one-hop plus two two-hop questions per visit, this is six canonical examples per visit. The intermediate entity and supporting line come from training evidence. Relation 2 stays absent from the practised two-hop-derived examples and remains present in ordinary one-hop examples. No held-out two-hop target is introduced. Apply the same operator and objective to every example:

```text
L = mean_(M,x,s,t,l) [ -log p_theta(t | M,x,s)
                      - (0.5/3) sum_(j=1..3) log attention_mass_theta(j, l) ]
```

**Untested training detail.** For LINK, `t` is its entity object and `l` its sole link line; for an attribute, `t` is its value and `l` its sole attribute line. This retains the successful ordered-evidence coefficient while making every operator call a one-hop task. The canonical link examples and explicit entity targets are new training supervision. Teacher-forced entity input in training is disclosed; evaluation uses the operator's own full-vocabulary prediction. Do not silently substitute the gold entity when prediction fails. No end-to-end gradient through argmax, straight-through estimator, auxiliary alignment loss, extra lexical classifier, cap, or larger network is part of this first candidate.

**Untested cost and privileges.** **+0 learned parameters; 79,316 total** if implemented with this exact module. The controller supplies fixed toy grammar parsing, operation order, an entity-token interface, and a reset; it must be declared as architectural structure. Training supplies intermediate entity targets plus existing evidence supervision. Inference supplies neither correct entities nor gold cards. Two-hop inference executes two four-token queries with three reads each; this costs more question/read computation than one five-token three-read query, although story encoding can be reused. Six training examples replace four questions per visit, so matching update counts does not match compute. Charge actual FLOPs and wall time; do not claim a benefit from equal compute or autonomous discovery of the decomposition.

**Untested predictions.** The candidate should remove the particular first-call REL sensitivity by construction and retain ordinary one-hop competence at the terminal call. The substantive prediction is **c3, c4, c5 and c6 each ≥461/512 in every prospective seed**, while c1/c2 each remain ≥487/512. A changed link must alter the predicted intermediate entity; a changed endpoint value must alter the terminal value; an irrelevant edit should preserve the final value. Existing Q results motivate this prediction but do not establish it after training the new LINK output, which may interfere with the same shared weights.

**Suggested quantitative caution.** If link error probability is at most epsilon_L and error of the canonical terminal call with the true entity is at most epsilon_R on the relevant marginal distribution, single-question failure is bounded by epsilon_L+epsilon_R. For a pair, sum the four side-specific error probabilities; no independence assumption is needed. At 1% per operation, this would give at least 98% single accuracy and 96% pair accuracy. Those are conditional bounds, not measured autonomous performance. The looser individual diagnostic thresholds below alone do not guarantee the paired pass; the actual pair gate must be met.

**Untested — strongest counterexample.** The new link-output task learns a spurious entity predictor, or its gradients destroy the attribute competence of the shared operator. With teacher-forced entities the terminal call remains excellent, but autonomous predictions pass the wrong entity and c4 collapses. Even a 95% link operator and 95% terminal operator can fail the pair gate badly; errors may be correlated across edited worlds. Giving each call the entire story also leaves room for frequency and irrelevant-fact shortcuts. A reset removes an architectural route for depth-specific conditioning; it does not force a correct learned lookup on all worlds. This is the strongest immediate falsifier, before claims about unseen names or deeper chains.

**Untested — cheapest decisive next test, not executed or authorized by this eval-only turn.** Freeze a separate three-seed CPU screen, seeds 0,1,2, at most 6,000 updates with 16 training visits/update, the six-example conversion and loss above, the existing optimizer and scaled initialization, and a fixed stream/checkpoint policy. Count its actual compute, disclose that this is an absolute sufficiency screen rather than a matched-compute superiority experiment, and freeze a hard resource cap before launch. Before any training output, freeze new 512-unit validation panels, for example seeds **202609202001–2006**, not these reused diagnostic panels. No test split or checkpoint selection. Score once at the fixed final update; incomplete jobs are failures.

**Untested required answer.** In **every** seed: c1/c2 ≥487/512; c3/c4/c5/c6 ≥461/512, with autonomous intermediate tokens, both twins correct, and no oracle substitution. Also report link-token accuracy and canonical terminal accuracy with gold entities, each ≥487/512 on all relevant question marginals, plus native joint entity/answer outcomes. Require identical first-call inputs and outputs across matched REL twins and identical terminal logits for an equivalent direct one-hop query when its input entity agrees. A low link score, loss of terminal competence, or failure of any edited-pair gate rejects this first candidate even if loss or training accuracy improves. Keep all seeds and failures; no silent extension beyond 6,000 updates or tuning against the validation panel. Passing earns a narrow structured-operator toy result, not G_cert or a broad reliability estimate. A later causal comparison can separate the value of the controller, new labels and extra compute; this screen cannot.

**Suggested — is the toy impossible at 80k?** No such impossibility follows. A fixed exact symbolic lookup-and-compose program solves this distribution with no learned parameters, showing that storing/computing the rule does not inherently require a large neural parameter budget. That is an existence argument with supplied structure, not proof that this training process can discover the rule. The training data also admit functions that agree on practised cases and differ on the held-out cell; inductive bias is needed. Here the same 79k-weight networks already perform the terminal one-hop task on those endpoints. Keep the current toy as a sharp composition test, disclose any supplied program structure, and leave vocabulary remapping, learned parsing, unseen names and new depths to separately registered extensions. Success here says nothing about the village/Track B setting.

**Suggested — disposition of earlier proposals.** “Dead” below means no longer an evidence-supported next transfer proposal, not a theorem that every related implementation must fail.

| Earlier proposal | Evidence status and decision |
| --- | --- |
| More access, more heads, better gradient connectivity, or more recurrent reads as a sufficient transfer fix | **Shown:** the saved successor and earlier six-read stress results do not solve transfer. **Suggested:** retire the sufficiency claim; more capacity alone is not the next hypothesis. These experiments are not a general transformer comparison. |
| Note 14 candidate A: practised-only hop-2/one-hop query alignment | **Untested as a trained intervention. Suggested:** superseded as the first fix. Its exact held-out-branch counterexample survives; low alignment loss on r0/r1 does not require reuse at r2. The useful principle is direct reuse, now enforced at the input/state interface. |
| Notes 14–15 candidate B: lexical typing plus shared relation residual | **Untested as a complete trained recipe. Suggested:** defer. It shares relation content but leaves an original two-hop state and entity binding path; it cannot be accepted as sufficient from this evidence. Our all-evidence clamps still fail in three seeds. This does not prove a supervised type module could never help. |
| W → WG → WGC ladder | **Shown in the saved original-model replay:** WG missed its first-LINK/answer mechanism gate and its mean no-harm gate; the .25 cap harmed working checkpoints. **Suggested:** the admitted sequence is dead; do not inherit a WG/WGC or combined-B launch. .50 passing its preservation eligibility screen is not demonstrated improvement over W. This is consistent with the separate post-A3 rulings in note 16-post-a3-wire-slot-rulings. |
| Longer teacher window / Q3 evidence-loss normalization | **Shown for the saved A3 report:** learned-gate attainment improved, but held-out G_pair went 1→0 and the stage was not accepted under its safeguards. **Untested for Q3. Suggested:** these remain separate optimization questions; they are not selected transfer fixes. |
| Shuffle original question slots | **Suggested:** retain as an original-model confound-removal experiment if its proposed population audit confirms the effect. **Shown here:** token successor input is invariant across the four trailing slots, so this cannot repair the failure demonstrated here. The small historical wire probe does not establish population-wide slot dependence. |

**Suggested — where to implement.** Test the canonical-operator replacement in the **token-memory successor first**, as an additive new model/runner with its own contract. Its one-hop competence, current oracle re-query result and slot invariance make it the cleaner mechanism test. The principle is relevant to both architectures, but porting into original hard-retrieval Premonition would additionally require an entity-output interface, episode reset, legitimate card-store reuse and control of its slot/prefix confound. Do not implement both at once or describe the original architecture as repaired. A later original-model version needs its own retrieval-budget, ASK, role-privilege and gate accounting; soft-memory evidence is not a hard-card certificate.

**Suggested — what Fable should audit.**

1. Check the original prediction file and hashes precede the first model run; keep P1–P3's failures and the later status of M1 visible. Verify every replay against the saved predictions, not merely counts.
2. Reconstruct compact-token-to-line identities and the final question-row index. Check all four heads, NULL, zero padding and causal eligibility; confirm category sums and top-individual-line counts. Inspect [the arithmetic audit](../../artifacts/astra-transfer-diagnostic-20260920/arithmetic-audit.json) and the five fixture tests rather than trusting the summary alone.
3. Confirm routing restrictions affect all question rows at exactly the declared steps, preserve within-line scores, and leave no hook/state behind. Check that the Q rewrite preserves story/eligibility, resets state, and uses a true endpoint only in the explicitly oracle diagnostic.
4. Check collision precedence and uncovered value tokens. Do not read answer matches as unique fact provenance. Confirm paired Q scores require both sides correct and use each edited story's own endpoint.
5. Attack the new candidate at its boundary: can terminal REL, depth, the original asker, a previous anchor, a saved hidden state, or gold intermediate content leak into either canonical call? Check full-vocabulary intermediate argmax, no failure fallback, no hidden held-out two-hop training targets, and the exact +0 parameter claim.
6. Insist on autonomous changed-link and changed-value pairs in the next screen. A perfect gold-entity terminal score alone is a failed demonstration of composition. Audit added supervision and compute rather than calling this an isolated weight-sharing effect.

**Shown — reproduction and retained artifacts.** [Main harness](../../scripts/astra_transfer_diagnostic.py), [fixture tests](../../tests/test_astra_transfer_diagnostic.py), [matched follow-up](../../scripts/astra_transfer_twins.py), and [model-free report/audit](../../scripts/astra_transfer_report.py) are new files. Primary B/C seed folders contain parity.json, result.json and c2/c3 records with every head's attention mass for every line and read step; each intervention prediction is retained per question. Follow-up JSONs retain all three REL variants for every world. The arithmetic audit independently recomputed 6,144 question records and all 144 step/head summary vectors. Reproduction must use a new output location because existing run and manifest files are intentionally not overwritten. No registered runner/model/plan/panel/checkpoint, original contributor file or ledger was edited.

**Shown — source scope.** New numerical claims above come from the six primary result files and six matched follow-up files in [the artifact directory](../../artifacts/astra-transfer-diagnostic-20260920/). Historical statements come from [the successor comparison](../../artifacts/codex-token-memory-20260920/COMPARISON.md), [wire replay summary](../../artifacts/claude-wire-replay-20260919/summary/summary.txt), [teacher-delay report](../../artifacts/claude-teacher-delay-20260919/report/report.txt), [note 14](14-relation-fix.md), [note 15](15-relation-fix-review.md), and [post-A3 rulings](16-post-a3-wire-slot-rulings.md). Those historical experiments were not rerun here. There is no new village result, no parameter-scaling result, and no claim of general intelligence.

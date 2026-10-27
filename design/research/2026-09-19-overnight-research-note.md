# Overnight research note — what blocks reasoning in Premonition, and what to try next

Run `ovn-20260918-235851`, 2026-09-18 23:59 to 2026-09-19 08:00 EDT. Written by Opus (research and execution lead
for the night). Local Mac only, $0 rental. Experiment details: `reviews/opus-overnight-2026-09-19-ovn-20260918-235851.md`.
Labels: **tested tonight** (with run evidence), **read in the primary source**, **hypothesis** (untested).
Everything below is on synthetic toys (synthetic vocabulary). "Supplied cards" results are privileged
gold-evidence diagnostics.

## For Ben, in plain words

Think of the model as a student with index cards of facts (the card store), a scratchpad (the Think rows) and a
pen that writes the answer (the decoder).

1. **Each index card has room for only one idea.**
   - A card should say two things: *who and what it is about* ("Mira's colour") and *what it says* ("blue").
   - Tonight's probes show that each card's single summary keeps only one of the two.
   - If the model is first trained mostly to *find* cards, the cards remember "Mira's colour" and forget "blue". It
     can find the card but not read the answer off it.
   - If it is first trained mostly to *answer*, the cards remember "blue" and forget whose colour it was. It can
     read one card but can't tell cards apart.
   - Which one wins depends on the random start: two runs with the same settings went opposite ways.
   - The model still *reads* every word of the line correctly. The loss happens only when the line is squeezed
     into the card's one summary: that summary learns to look at one or two words and ignore the rest.
   - This one bottleneck explains most of tonight's failures.
2. **Copying the answer from the right card works** when the card still holds the answer (1024/1024 in milestone
   2; 512/512 tonight).
3. **Choosing among similar cards never worked from answer practice alone.** The cards had forgotten who they
   were about, so there was nothing to choose with.
4. **The search skill (ASK) chains two lookups only for combinations it practised.** Asked about a new
   combination of steps it knows, it finds the first card but almost never the second.
   - At the second step it asks for the wrong kind of fact: always one it practised as a second step, never the
     one the question names.
5. **The thinking scratchpad damages facts it is allowed to rewrite.** Facts should be read-only while thinking.

**Best next step:** give every card two separate slots, one for "who/what" and one for "the answer", and check
that finding and reading then both learn, on several seeds.

## 1. The capability ladder: where the evidence stands

| Ability | Status | Evidence (exact counts) |
|---|---|---|
| Read one supplied fact | **Solved** when the card keeps the value | m02: 1024/1024 test, 2 variants × 2 seeds. Ladder: 512/512, 341/341, 171/171 |
| Choose among decoys with no retrieval, answer-only | **Not learned** | ≤ 171/512 validation, ≤ 182/512 test (the question-blind ceiling is 53.7%). Probes: card person 116/2048 (chance) |
| Find the fact yourself (ASK, evidence-supervised) | **Partial, seed-dependent** | 1-hop own retrieval 356/512 on test (K4; s0, 4000 steps). Seed 1 at 1500 steps: finds 390/512 but reads 27/512 |
| Combine two facts (2-hop) | **Partial for practised combinations** | Test: 154/323 (both cards fetched in 166) |
| Reuse familiar steps in a new combination | **Fails** at retrieval hop 2 | Test: 14/189, both cards fetched in 1/189. Validation (1500 steps): first hop 139/171, second 0/171 |
| Learn a new procedure, keep old ones | Not testable yet | Nothing is learned reliably enough to measure retention |

## 2. Primary sources read tonight

- **PairNorm** (Zhao & Akoglu, ICLR 2020) —
  [ar5iv 1909.12223](https://ar5iv.labs.arxiv.org/html/1909.12223).
  - What it does: centres node features across the graph and rescales them to a fixed total spread, which stops
    deep GNNs smoothing every node to the same vector.
  - Limits: a small drop for shallow networks, and no gain where shallow suffices.
  - Tested tonight as a row-centred Think update: it removed the shared collapse, but reading did not return.
- **ContraNorm** (ICLR 2023) — [ar5iv 2303.06562](https://ar5iv.labs.arxiv.org/html/2303.06562).
  - Distinguishes complete collapse from dimensional collapse, and adds a uniformity step after attention.
  - Limits: small gains, a tuned scale, a slight drop at shallow depth.
  - Not tested.
- **End-To-End Memory Networks** (Sukhbaatar et al., 2015) —
  [ar5iv 1503.08895](https://ar5iv.labs.arxiv.org/html/1503.08895).
  - The question-derived query reads memory over several hops.
  - They needed a "linear start", noise, and the best of 10 random restarts (chosen by training error).
  - The strongly supervised version (supporting-fact labels) stayed better on several tasks. So learning *which*
    memory to read from answers alone was fragile there too.
- **Key-Value Memory Networks** (Miller et al., 2016) —
  [ar5iv 1606.03126](https://ar5iv.labs.arxiv.org/html/1606.03126).
  - Addressing uses the *key* encoding and reading uses a *different value* encoding. With a knowledge base, key =
    subject + relation and value = object.
  - The separation lets matching and answering use different features.
  - The features were hand-designed, and a gap remained between documents and a curated knowledge base.
  - Direct prior art for candidate A.
- **Set Transformer, PMA** (Lee et al., 2019) — [ar5iv 1810.00825](https://ar5iv.labs.arxiv.org/html/1810.00825).
  - Pooling with k learned seed vectors gives k summaries of a set, for problems needing several outputs.
  - Prior art for pooling a line into more than one vector.
- **TRM** (Jolicoeur-Martineau, 2025) — [arXiv 2510.04871](https://arxiv.org/html/2510.04871v1).
  - Deep supervision means up to 16 detached improvement steps, each predicting the answer.
  - The paper cites the ARC Prize analysis crediting deep supervision for most of HRM's gain. Full backprop
    through recursion beat a 1-step gradient (87.4% vs 56.5%, Sudoku-Extreme).
  - Limits: fixed-size, supervised puzzles.
  - Evidence *against* final-loop-only supervision. Tonight's test could not check this: Think contributed
    almost nothing (the gate stayed near 0), so final-loop-only made no difference.
- **Looped Transformers for Length Generalization** (Fan et al., 2024) —
  [arXiv 2409.15647](https://arxiv.org/html/2409.15647v2).
  - Re-injecting the input at every loop helped, but training used ground-truth step counts (a privilege).
- **ESBN** (Webb, Sinha & Cohen, ICLR 2021) — [ar5iv 2012.14601](https://ar5iv.labs.arxiv.org/html/2012.14601).
  - A controller that sees only keys, bound to content values, generalizes rules to unseen objects where
    transformers, LSTMs and NTMs do not.
  - Limits: simple tasks; the strict split may limit which rules it can learn.
  - Supports identity/content separation (candidate A) and pointer-built queries (candidate B).
- **Perceiver IO** (Jaegle et al., 2021) — [ar5iv 2107.14795](https://ar5iv.labs.arxiv.org/html/2107.14795).
  - Latents read the inputs and never rewrite them. Cost is linear in input size, with a latent bottleneck.
  - Prior art for candidate C.
- **Vision Transformers Need Registers** (Darcet et al., 2023) —
  [ar5iv 2309.16588](https://ar5iv.labs.arxiv.org/html/2309.16588).
  - High-norm "artifact" tokens are hijacked as global scratch space, and dedicated registers remove them.
  - Related to, but not the same as, our all-row collapse. D already has registers.
- **Binding IDs** (Feng & Steinhardt, 2023) — [arXiv 2310.17191](https://arxiv.org/abs/2310.17191). *Abstract
  only.*
  - Language models tie attributes to entities with binding-ID vectors (causal swaps). Context for "facts must
    stay attached to their people".
- **CLEAR, experience replay** (Rolnick et al., 2019) — [ar5iv 1811.11682](https://ar5iv.labs.arxiv.org/html/1811.11682).
  - About 50/50 new data and replay nearly removed forgetting (RL). Small buffers sufficed, and task boundaries
    were not needed.
- **Grokked Transformers are Implicit Reasoners** (Wang et al., 2024) —
  [ar5iv 2405.15071](https://ar5iv.labs.arxiv.org/html/2405.15071).
  - On two-hop composition over a synthetic knowledge graph, in-distribution composition is eventually learned
    through grokking. Out-of-distribution composition stays at zero even after 2M steps.
  - Circuit analysis: the second hop is done by upper layers. Facts never used as a second hop in training are
    not stored there.
  - Remedy: they call for cross-layer memory sharing. Sharing parameters (Universal-Transformer style) gave only
    slow, partial out-of-distribution gains.
  - Relevance: the closest published analogue of our held-out 2-hop failure. It bears on candidate B.
- **Compositional Attention** (Mittal et al., ICLR 2022) —
  [ar5iv 2110.09419](https://ar5iv.labs.arxiv.org/html/2110.09419).
  - Multi-head attention rigidly pairs each head's search (query–key) with its retrieval (value). Decoupling S
    searches from R retrievals, with a learned selection, improved out-of-distribution results on several
    synthetic and relational tasks.
  - Costs: time within about 10%, similar parameters.
  - Limitation stated by the authors: with no explicit bottleneck, retrievals sometimes fail to specialize.
  - Prior art for separating "how a memory is found" from "what it returns" (A), and a caution for A.
- **Preventing Attention Entropy Collapse** (Zhai et al., 2023) —
  [ar5iv 2303.06296](https://ar5iv.labs.arxiv.org/html/2303.06296).
  - Very low attention entropy accompanies training instability. σReparam (spectral norm with a learned scale)
    keeps entropy bounded.
  - The authors say the causal link is unclear.
  - Relevant only as a possible competitor: an entropy floor on the pool. In our case sharpness is not an
    instability; a sharp value pool is *needed* to read the value token.
- **Loss of Plasticity in Deep Continual Learning** (Dohare et al., 2024) —
  [ar5iv 2306.13812](https://ar5iv.labs.arxiv.org/html/2306.13812).
  - Across thousands of tasks, standard backprop gradually loses the *ability to learn new tasks*. This is
    separate from forgetting old ones.
  - Adam made it worse, and dropout did not help. L2 and Shrink-and-Perturb eased it. Continual backprop
    (reinitialising low-utility units) maintained it.
  - Limitation: the utility measure is heuristic.
- **Tiny episodic memories** (Chaudhry et al., 2019) — [ar5iv 1902.10486](https://ar5iv.labs.arxiv.org/html/1902.10486).
  - In single-pass continual learning, replaying even one stored example per class beat regularisation methods
    (EWC, A-GEM).
  - Training on new tasks acts as a regulariser against overfitting the tiny memory.
  - Limitation: supervised, single-pass benchmarks.
- **Token Superposition Training** (arXiv 2605.06546 v2), read from the LaTeX source.
  - It averages input embeddings in groups and predicts the next token bag, then returns to normal training.
  - The authors state it is algorithmically identical to earlier patch-level training (Shao et al., 2025).
  - Limits stated by the authors:
    - It trades data for compute.
    - The smallest model had 270M parameters (untied embeddings).
    - No repeated runs.
    - Output-only superposition beat the baseline without extra data.

## 3. What tonight's experiments add

- **Exp 1: read, choose, combine, with supplied cards.**
  - Reading is solved.
  - Choosing and combining are not learned by the no-Think, bypass, gated, centred or final-loop-only variants,
    or with the question-aware read. The no-cards control stays at chance.
  - Probes show that answer-only training strips the person and relation out of every card: person 116/2048,
    relation 656/2048, value 2048/2048. The no-Think reader's question query still encodes both (512/512).
- **Exp 2: D's own evidence-supervised retrieval (top-1) with a read-only reader.**
  - **Default curriculum.** Cards keep person and relation (1893/2048, 2048/2048) but lose the value (125/2048).
    Retrieval learns; reading never does (32/512).
  - **Long reading phase, seed 0.** The value wins (2048/2048) and the person is lost (134/2048). Reading
    learns; retrieval is poor.
  - **Long reading phase, seed 1.** Identity wins (1818/2048) and the value is lost (143/2048). Retrieval learns
    better; reading never does (27/512).
  - **Long reading phase, seed 0, 4000 steps.** A partial compromise (person 657/2048, value 2048/2048).
    End-to-end results on test (K4): 356/512 one-hop and 154/323 practised two-hop. Held-out two-hop: 14/189.
  - **Memory control.** D-noask with 4000 steps of the same training stays at chance (41/512).
- **Where the single pool looks** (eval-only probe, validation, 4608 attribute lines).
  - Softmax mass on [marker, person, relation, value, fillers + newline]:

    | Checkpoint | Pool mass |
    |---|---|
    | Init | [.18 .17 .16 .17 .33] |
    | Answer-only | [.004 .004 .004 .979 .008] |
    | Exp 2 default | [.04 .18 .71 .02 .06] |
    | Long reading s0 | [.07 .02 .42 .43 .06] |
    | Long reading s1 | [.08 .26 .47 .05 .14] |
    | 4000 steps | [.02 .02 .56 .38 .02] |

  - The reader keeps everything in every checkpoint. Probes read the person from the person-token state at
    2304/2304, and the value from the value-token state at 2304/2304.
  - The value-token state does not carry the person, even at init (125/2304). So a single pool must choose which
    token to summarise.
  - Losing the unchosen fact therefore happens in the pool, not in the reader.
- **Test split, Exp 1** (checkpoints chosen on validation beforehand).
  - Reading 512/512, 323/323 and 189/189 for the no-Think, gated and final-loop-only models.
  - Choosing: 166/512, 182/512 and 181/512 respectively.
  - The no-cards control scores 40/512.

## 4. Shortlist (three candidates), with criticism

### A — Two-channel cards: separate "who/what" and "what it says" pooling

- **Plain example.** Every index card gets a header line ("Mira — colour") and a body line ("blue"). Finding
  uses the header; answering copies the body.
- **Mechanism.**
  - D's card writer pools a line's reader states with **one** learned attention score, then computes both the
    key and the value from that single pooled vector. Replace it with **two** scores: `p_k` for the key and
    `p_v` for the value. This is PMA with two seed vectors.
  - Optionally, give the decoder's card row the key as well, so answer-path choosing can use identity.
  - Everything else stays D.
- **Classification.** Known elsewhere: key-value memories with separate key/value encodings (KV-MemNN,
  hand-designed features), multi-seed attention pooling (PMA), the ESBN key/content split. New to this project.
  - The mechanism is measured tonight: pool mass plus reader-state probes, §3.
  - The fix is an **untested hypothesis**: that separate pools remove the race.
- **Bottleneck addressed.** The measured race (§3). It explains:
  - Exp 1's choosing failure;
  - Exp 2's reading failure under the default curriculum;
  - the seed-dependence of reading, 1 of 2 seeds at 1500 steps.
- **Costs.** One extra d-vector per writer (+33 parameters at d = 32). The pooling work per line roughly doubles,
  which is negligible. The same card memory is used.
- **Extra teacher information.** None beyond D's (evidence labels for L_ask).
- **Simplest fair competitors.**
  1. Single-pool D with the same curriculum and seeds.
  2. A **fixed uniform (mean) pool**: no learned pooling, so nothing can concentrate.
     - It is the simplest possible cure.
     - Tonight's reader states under a uniform mean still carry the person (1998–2300/2304).
     - But in the two runs where identity won, they carried only part of the value (1211/2304 and 1590/2304).
     - So a mean pool may keep too little of the answer.
- **Support.** Under D's default curriculum on the ladder, on every seed run (at least 2, and a third if budget
  allows; see the handoff):
  - pure reading ≥ 486/512;
  - end-to-end 1-hop K4 accuracy ≥ 90% of the gold-fetched count;
  - key-probe person ≥ 90%;
  - value-probe value ≥ 90%.
- **Abandon or postpone.** Probes show both pools collapse onto the same tokens. Or reading and retrieval still
  race (one fails on some seeds). Or the cure does not survive real village lines (several people per line).
- **Criticism.**
  - Compositional Attention reports that decoupled retrievals sometimes fail to specialize. Both pools could
    still settle on the same tokens: check pool mass per pool.
  - Two pools fit the toy's short lines, where identity and value tokens are separate. Village lines can hold
    several facts, and more seeds (k > 2) or line-local encoders may be needed.
  - An entropy floor on the single pool (after Zhai et al.) is an in-between competitor, but a floor would also
    blur the value read.
  - It fixes retrieval-then-read, but not choosing inside the answer path, unless the key also reaches the
    decoder.
  - A fix for the race is not a fix for composition (see B).

### B — Compositional multi-step queries built from name pointers

- **Plain example.** For "the colour of Mira's friend", first look up the friend. Then use the *same* colour
  lookup the model already uses for "the colour of X", aimed at the friend.
- **Mechanism.** The next ASK query is `q = W_e · slot(e_new) + W_r · rel(question)`. `e_new` is the entity slot
  the binder just filled from the fetched link card. `W_r` is shared with 1-hop questions (`e` = the asked
  person).
- **Classification.** Known elsewhere: factorised key-value lookups, neural module networks, tensor-product
  binding. New here. Untested hypothesis: factorising queries by pointer and relation makes hop 2 transfer to
  unseen combinations.
- **Bottleneck addressed.** On validation (1500 steps), hop 2 reaches 0/171 on held-out combinations while hop 1
  reaches 139/171. On test (4000 steps), only 1/189 held-out questions fetch both cards.
  - Eval-only classification of the second fetch: on held-out questions it asks for the question's relation 0/171
    times (default s0), or 9/171 (4000 steps). On practised questions it does so 341/341 and 293/341 times.
  - Its relation comes from habit (relations seen at hop 2), not from the question.
  - The right person is found only about 42% of the time even when practised (144/341), so the friend pointer is
    also weak.
  - B targets both: the question's relation, and the friend's pointer.
- **Costs.** Two small linear maps.
- **Extra teacher information.** As D.
- **Simplest fair competitor.** D's register-0 query (Exp 2).
- **Support.** Held-out hop-2 recall at least about 80% of trained-combination hop-2 recall.
- **Abandon.** Held-out hop-2 recall stays near 0.
- **Prior evidence and a caution.**
  - Wang et al. (2024) trace out-of-distribution 2-hop failure to facts missing from the circuit that does the
    second hop. Their sharing remedy helped only slowly.
  - In D all hops already read one shared card store, so fact storage is not our bottleneck. The hop-2 *query*
    is: tonight the link card is fetched 139/171 times but the second card 0/171 times.
  - B applies the same "share across hops" idea to the query builder. Their partial result suggests expecting
    partial gains, not a clean fix.
- **Criticism.**
  - It builds in structure that mirrors the toy (one-token relations, one pointer per person).
  - "Which slot is new" relies on binder bookkeeping.
  - It depends on A: the link card must still say *who* the friend is.

### C — Read-only facts, writable scratchpad ("register-only Think")

- **Plain example.** The student may write on the scratchpad but never on the index cards.
- **Mechanism.** Only register rows receive Think updates. Question, slot and card rows are keys and values only.
  The decoder reads registers plus untouched evidence.
- **Classification.** Known elsewhere: Perceiver IO latents, the MemN2N controller state. New here, untested.
- **Bottleneck addressed.** Think rewriting destroyed evidence rows: shared collapse in milestone 2, row-specific
  swamping (spread 8.2) tonight.
- **Costs.** Cheaper: 4 query rows instead of 76, so attention work falls about 19×. No new parameters.
- **Simplest fair competitor.** The bypass (a milestone-2 variant), and a trained no-Think model.
- **Support.** A register-only Think adds 2-hop ability over the no-Think control once cards keep identity (A).
- **Abandon.** No gain over the no-Think control.
- **Criticism.** Tonight every soft-attention read trained only from the answer failed to learn choosing. The
  cards' lost identity is the likely reason, so C should be tested only after A.

**Ranking.** A, then B, then C. A is cheapest, is directly supported by probes and training dynamics, and is
upstream of both others.

## 5. Rejected or postponed

**Tested tonight and rejected in their current form**
- **Row-centred Think update.** It removed the shared vector but blocked reading (64/512) through row-specific
  swamping.
- **Final-loop-only answer supervision.** No change (164/512 choosing and 127/341 combining, against 169/512 and
  121/341). This is uninformative while Think contributes almost nothing. Keep D's per-loop supervision
  (TRM/HRM).
- **The gate as a reasoning enabler.** α reached at most 0.042 with no gain. Keep it only as a stability tool.
- **The question-aware read alone.** It helps reading: without a curriculum at 1200 steps, 264/512 against
  179/512 for the no-Think model without it. But it gives no choosing, because the cards had lost identity. It is
  a cheap reading aid only.
- **"Several fetched cards cause the milestone-2 own-retrieval failure."** Refuted: top-1 fetching with no
  distractors fails the same way. The cause is the value being erased from cards (§3).
- **"No answer loss when evidence is missing" (early_ans 0).** No effect.

**Postponed**
- **Relevance supervision for the answer path.** Likely unnecessary if retrieval chooses and cards keep identity.
  Keep it as a fallback.
- **TST.** It targets language-model pretraining throughput at 270M+ in compute-bound regimes, and it is the same
  algorithm as patch-level training. Our bottleneck is memory binding.
  - Revisit after a working baseline. Compare with output-only superposition (no extra data) and with
    contextualise-then-pool. D's cards already pool contextual states.
- **Continued-learning pilots.** Nothing is learned reliably enough yet to measure retention.
  - Design for later:
    1. Teach 1-hop, then a new 2-hop procedure.
    2. Compare naive fine-tuning, CLEAR-style 50/50 replay and simulator-chosen failing cases, at equal updates.
    3. Test on fresh facts after clearing cards.
  - Measure **both** failure modes:
    - *forgetting*: old skills after new training;
    - *plasticity*: how fast the model learns the Nth new procedure compared with the first (Dohare et al.).
  - Tiny replay buffers may suffice (Chaudhry et al.). Add a plasticity arm, such as Shrink-and-Perturb, only if
    learning speed decays.
- **ContraNorm or PairNorm rescaling, input injection, linear start.** Not addressed to the measured bottleneck.

## 6. Surviving hypotheses, ranked by evidence

1. **The single shared pool per card forces a race between identity and content.** Evidence:
   - card probes on 6 checkpoints (§3);
   - pool mass concentrated on the winning tokens, while reader states keep everything;
   - the training outcome follows the probe winner in every case;
   - the seed-dependence of reading.
2. **Choosing among similar facts cannot be learned from the answer while cards lack identity.** Evidence:
   - Exp 1 (every variant ≤ 33% on validation, ≤ 36% on test);
   - probes: card person at chance after reading is learned.
3. **Reasoning updates that rewrite evidence destroy it.** Evidence: milestone 2, and Exp 1's centred arm.
4. **Learned retrieval queries do not compose to new combinations of familiar steps.** Evidence: Exp 2 held-out
   hop 2. Located: the hop-2 query never asks for the held-out relation (0/171 and 9/171), falling back to
   relations practised at hop 2.
5. **D's default 5% supplied-card phase under-trains reading at this scale.** Evidence: Exp 2. It is probably a
   symptom of (1), not a separate cause.

## 7. Suggestions for Ben's long-term vision (for Ben to decide)

- **Keep:** reasoning first, separate factual memory, continued learning.
- **Add to the memory design:** each stored fact needs a separate *address* ("whose, what kind") and *content*
  ("the value"). This is a concrete refinement of "separate factual memory", measured tonight. It also matters
  for continued learning: an address that drifts would detach facts from people.
- **Treat multi-step reasoning as repeated use of one lookup** built from name pointers and relations. New
  combinations of familiar steps can then be tested exactly.
- **Keep facts read-only during thinking.**
- **Postpone language-efficiency tricks and continual-learning machinery** until the core can find, read and
  chain facts on several seeds.
- **When continued learning starts, track two things.** Does it keep old skills (forgetting)? Does it stay able
  to learn new ones (plasticity)? Published work shows they fail separately.

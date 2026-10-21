# Premonition on a big open model: design brief

2026-10-21. A $0 desk design. Nothing here was run: no GPU, no rental, no training, no tests.
Ben asked for this track; the coordinator (session_018Ybowk1FLjHVsZsWFonjEk) speaks for Ben within his standing rules.

**GATE (Ben, ledger 2026-10-21 ~01:40Z):** no GPU spend on this track until the mechanisms are shown end to end on the small village model. After that it bids against the $50/week budget like everything else. Anything over the caps, any 10M-parameter run and the Modal budget are Ben's call.

**Labels.** Every claim is **shown** (a result in a file I read, or a fact I fetched today), **suggested** (reasoning or literature, nothing run here) or **untested**. The small card experiments and the village model are kept in separate sections (§2.1 vs §2.2) and are never pooled into one claim.

---

## 0. Bottom line

1. **"Qwen 3.8 27B" exists.** It is `Qwen/Qwen3.8-27B` on Hugging Face (shown, §1). No newer or better model of that size turned up. Keep it, and re-check at the moment the gate opens.
2. **The mechanisms do not port equally.** Of the three, the sleep / anti-forgetting fix is the closest to ready: the repo already runs LoRA nights with a KL anchor on a pretrained 1B model. Card memory is the weakest: it is not yet shown on the village model, and a 27B with a 262K-token window may not need it (§2.1, risk 1). The creative line comes last.
3. **Cost is small per run, but the stack is unproven.** A 27B QLoRA run costs about $1 to $2 a run on a 48 GB card at today's Vast prices (suggested). The real cost risk is setup failure: 6 of the 7 rentals booked Oct 20-21 ended before any training (ledger, shown).
4. **The first test (§4) asks one question:** does a *trained* card retriever beat plain BM25 retrieval, on the same LoRA'd Qwen, on questions about text that fell out of its short window? If not, the card store adds nothing here and we stop.

---

## 1. Which model? (item d, checked today, 2026-10-21)

### 1.1 Does "Qwen 3.8 27B" exist?

**Yes (shown).** I fetched the Hugging Face API directly rather than trust blog posts:

| Fact | Value | Source |
|---|---|---|
| Repo | `Qwen/Qwen3.8-27B`, public, ungated | `huggingface.co/api/models/Qwen/Qwen3.8-27B` (fetched today) |
| Created / last modified | 2026-08-05 / 2026-08-14 | same |
| License | Apache-2.0 | same |
| Downloads / likes | about 7.6 million / about 18,000 | same |
| Type | image-text-to-text; architecture class `Qwen3_5ForConditionalGeneration`, text model `qwen3_5_text` | `config.json` |
| Size and shape | 27B dense; hidden 5120; 64 layers; 24 attention heads, 4 KV heads, head_dim 256; MLP 17,408; vocabulary 248,320 | `config.json` |
| **Layer mix** | **48 "linear attention" layers and 16 full-attention layers (every 4th layer is full attention)** | `config.json` `layer_types` |
| Context | 262K native (about 1M with extension) | press and blog sources (secondary) |
| Thinking mode | switchable; defaults to a very long "xhigh" effort, which Simon Willison calls a poor default (22,276 reasoning tokens for one SVG) | [simonwillison.net, 2026-08-16](https://simonwillison.net/2026/Aug/16/qwen-38-27b/) |

Two things to know:
- Blog sources disagree about the Qwen3.8 line (some call the 27B "delayed", one reports only a 2.4T model). The Hugging Face record settles it for the 27B: it is out. The 2.4T-A95B and a 180B "Flash-Next" (license "other") are separate, much larger releases from the same family (shown, HF listing).
- The repo already uses this model: the handoff runs `Qwen3.8-27B-UD-IQ4_XS.gguf` on BensPC as the ear's YES/NO checker (`handoff/HANDOFF.md`, shown). So Ben's own setup has already downloaded and run it, for inference only.

### 1.2 Is anything newer or better at a similar size?

**No clear winner found (suggested; the comparisons are vendor and blog claims).**

| Model | Date | Size / license | Verdict |
|---|---|---|---|
| Qwen3.8-27B | Aug 2026 | 27B dense, Apache-2.0 | **Keep.** Newest in its family at this size; no Qwen3.9 or Qwen4 repo exists (HF search, shown). |
| Meta Muse-Glimmer-30B | repo created 2026-08-09, updated 2026-10-20 | about 30B dense, multimodal, Apache-2.0 (HF tags, shown) | Closest rival. Meta's table compares it with Gemma 4 31B and Qwen3.6-27B, **not** with Qwen3.8-27B, and I found no independent score (secondary reports). Watch it; do not switch on a vendor table. |
| Gemma 4 31B | mid-2026 | 31B dense, Apache-2.0 | Older. One blog puts it far below Qwen3.8-27B on the Artificial Analysis index (19 vs 34); blog figures conflict, so treat as suggested. |
| Qwen3.6-27B | Apr 2026 | 27B, Apache-2.0 | Older sibling, same `qwen3_5` architecture. Useful as a cheaper stand-in if tooling is easier. |
| Kimi K3, GLM-5.3, DeepSeek V4.1-Flash (552B), Muse Spark Open (816B), Qwen3.8-2.4T | Aug-Oct 2026 | hundreds of billions to trillions of parameters | Stronger in the roundups but far too big to fine-tune on rented single GPUs. Not candidates. |

**Rule for switching (suggested):** switch only if a model of at most about 32B dense parameters, with an Apache-2.0 or MIT license, beats Qwen3.8-27B on an independent leaderboard *and* has working QLoRA support. Re-check at gate-open time (Ben has not said yes to a scheduled monthly check; the ledger says it is "noted, not scheduled").

### 1.3 Why the architecture matters here (shown from config; consequences suggested)

- Only **16 of 64 layers** have ordinary attention with a KV cache. A "cross-attention to card vectors" adapter has natural homes only in those 16 layers. The other 48 layers carry state in a fixed-size recurrent form, so there is nothing to attend *from* in the usual way (untested).
- Standard LoRA targets (`q_proj, k_proj, v_proj, o_proj`) exist only in the 16 full-attention layers. The 48 linear-attention layers use different projection names, so a "target all linear layers" LoRA is needed to touch most of the model (untested; check the exact module names on first load).
- The vocabulary is 248,320 tokens, which makes a full-vocabulary KL term memory-heavy (§2.3).
- Training support for this architecture in `transformers`, `peft`, `bitsandbytes` and any fast linear-attention kernels is **untested**. It is the biggest unknown in the stack.

---

## 2. How each mechanism maps onto a pretrained transformer (item a)

### 2.1 Card memory

**What it is in the small model (shown, `design/06-premonition-mini-spec.md`).** Village model D is about 2.0M parameters. A reader writes one *card* per non-question line: a 64-dim unit key, a 128-dim value, the line index and the line's token ids (a "diary pointer"). At each question, a query from a register scores every card (`κ·q·k + age bias`) and the top 4 are fetched into the think space. Training signal: `L_ask`, a set cross-entropy that rewards putting probability on the gold cards (the cards on the question's evidence lines). The store is rebuilt per visit and holds no trained weights. Names become pointers (`ENT` ids) so a fresh name is copied, not generated.

**Status on the small experiments (shown; I did not recompute any number).**
- Village end to end: **I found no sealed result showing D beating the plain-transformer baselines on village questions in the files I read.** The ledger lists the gate as open. The spec itself says D vs contender E (pointers without the store) is the test of whether the store earns its keep (`06-premonition-mini-spec.md` §0).
- Card-memory sub-results in the ledger: S2, S5 and S6 passed on a toy with d = 32 only; S3 and S4 failed ("mechanism not engaged"); a village count showed 70.6% of told questions name no person, so person-match cues do not carry over to the village as built; the decoder reader-KV line failed Stage 0 and is closed (all `handoff/coordinator/funding-ledger.md`).
- Separate model line (the Director's reasoner, not the village): the card store "proved wrong for lookup" (G1k 17.5 of 300; `design/research/sleep-design-2026-09-28/MAP.md`, `handoff/director-board.md`). That is a different model and is **not** evidence about the village model or a big model; I note it only because it is the same idea failing once.

**Three ways to put cards on a pretrained transformer** (all suggested, none tried):

| | Write | Read | Touches the model? |
|---|---|---|---|
| **M1: learned retriever, cards as text** | Each card keeps its original line as text, plus a key vector from a small writer reading the model's own mid-layer hidden state at the line end. | A small ASK head (query from the hidden state at the question) scores the keys, trained with D's `L_ask` set loss. The top-k lines are pasted into the prompt as ordinary text. | LoRA only (plus the small ASK head). The pretrained model reads text it already understands. |
| **M2: cross-attention adapter** | Same cards, stored as vectors. | Gated cross-attention (Flamingo-style, tanh gate starting at zero) added to the 16 full-attention layers, attending to the card vectors. | New trained modules inside the network; riskier for forgetting and for this hybrid architecture. |
| **M3: compressed soft tokens** | A writer squeezes each line to 1-4 vectors (gist or Perceiver-style). | The vectors are prepended as input embeddings. | New writer; the model must learn to read embeddings it never saw. |

**Recommendation (suggested): start with M1.** It is the closest to what the village model already does (the "diary pointer" card *is* the original text), it changes the pretrained network least, and it is the cheapest to debug. Try M2 or M3 only if M1 works but the context budget is the bottleneck.

**Mapping notes:**
- *Names as pointers:* a 27B pretrained model already copies unseen names well (suggested). Drop the `ENT` machinery at first and keep it as a control only if names turn out to be a failure source.
- *Episode scoped vs persistent:* D's store is rebuilt per visit. The reason to use a store on a big model is a store that **persists across sessions**. The first test (§4) deliberately uses the episode-scoped form, as the village spec does, so the two stay comparable.
- *The honest baseline problem:* Qwen3.8-27B can read 262K tokens in its prompt (secondary source). A card store only earns its place where the story is **longer than the window we give the model**, or where reading the whole history each time costs too much. This is why §4 limits the model's window on purpose and includes a "whole visit in context" arm as a ceiling. If the ceiling is simply the best, the practical answer for a big model may be "use a long prompt", and the card store is justified only by cost and persistence (suggested).
- *Contender C already in the repo:* BM25 retrieval of earlier lines into the window (`06-premonition-mini-spec.md` §5). That is the fair comparison for M1 and is arm B2 in §4.

### 2.2 Sleep and anti-forgetting (village model vs card experiments vs the 1B LoRA line)

Three separate bodies of evidence exist. Keep them apart.

**(i) The 1B LoRA "nights" line (shown; model is MiniCPM5-1B with LoRA r16 on q,k,v,o; `artifacts/claude-dl*-2026092*`).** This is the nearest precedent, because it is LoRA on a pretrained model, and its harness (`scripts/claude_dl1_nights.py`, `claude_dl4_anchor.py`, `claude_blurt2.py add_lora`) can be reused.
- dl-2: a week of nights on copy-practice lifted lucky guesses on fresh puzzles from 64 to 237 and 249, but the model lost 26 of 200 general items it used to get right (`claude_dl4_anchor.py` docstring).
- dl-3: replaying the base's single greedy answers did **not** cut losses and roughly doubled drift (KL 0.28 vs 0.13-0.17). Registered FAIL.
- dl-4 (**the KL anchor**): add `KL(base || current)` over the full vocabulary on base-written general questions. The "base" is the same network with every LoRA scale set to 0, so no second model is held in memory. Drift on general replies stayed near base (KL 0.031-0.035 vs 0.175-0.186 without the anchor, shown). But forgetting counts were not cut enough: items lost 25 vs 33, against a bar of half (16.5). **Registered FAIL** on F1 and F2; F3, F4 and F5 passed; not proved wrong (`artifacts/claude-dl4-20260926/RESULTS-gpu.md`).
- dl-7: an arm labelled F cut losses to 7 vs 26 (passing F1 and F2) but missed the learning bar by 13 (gain 263 vs 276). Registered FAIL on F3 (`claude-dl7-20260926/VERIFY.md`).
- dl-9: a separate expert adapter with a learned on/off switch: **registered PASS** (`claude-dl9-20260926/RESULTS-gpu.md`).
- dl-6 found that forgetting tracks the total amount trained (`dl9 PASSMARKS.md`, quoting dl-6).

**(ii) The reasoner sleep line (shown on the Director's loop reasoner, not the village; `design/research/sleep-design-2026-09-28/MAP.md`).** A long night at full step size only tied a short one on sums and lost the grid gain (-33 to -94 of 400); the fix being tested spreads the same total change thinly at a small learning rate. Distilling from the current model in sleep: +4.5 of 200, short of a bar of 20, "not proved wrong". Facts live in the notebook; only skills are protected by sleep.

**(iii) "G1" (Brain).** The task text and ledger name a "G1" replay-plus-KL configuration, kept by Ben after an Opus xhigh review (ledger 2026-10-20 ~00:30). **I could not find G1's exact definition in the files on `main` or in the ledger**, so this brief maps the dl-4 recipe above and does not claim to port G1. Read G1's config from the Brain branch before the first sleep run on the big model (open item).

**How it maps onto Qwen3.8-27B (suggested):**
- **The night's update = one LoRA adapter** on the 4-bit base. The reference model for KL is the base with the adapter switched off (`peft`'s `disable_adapter`): no second 27B in memory.
- **Replay** = a small mix of (a) the day's new skill items and (b) a rehearsal store of old skill items, chosen by code, as in the reasoner line. Do not replay the base's greedy answers (dl-3 FAIL).
- **KL anchor** = the dl-4 loss on general text the *base wrote itself*. With a 248,320-token vocabulary, computing the full-vocabulary KL for every answer position is memory-heavy: compute it in chunks of positions, or restrict to the base's top-k tokens plus a remainder bucket. The top-k version is **untested** as a substitute for the full KL that dl-4 used.
- **Small steps:** spread the update thinly (low learning rate, short nights), per the H6 and dl-6 findings.
- **Facts go to cards, not weights.** Sleep trains skills only, as in the notebook design.
- **Guard panel:** a short general-knowledge panel the base gets right (dl-4's "HARM" measure: lost = right at base, wrong now) is the forgetting readout.

Because dl-4 **failed** its registered forgetting bar on a 1B, there is no basis to expect the KL anchor to pass on a 27B. This is a "suggested, untested" mapping, not a plan with a known outcome.

### 2.3 The creative line (later; shown only on a 1B, on puzzles)

Design (`design/v3/30-modes/creative-roadmap-2026-09-25.md`): the model blurts many wild tries, a checker keeps the lucky ones, and a sleep step practises the wins so later blurts get luckier.
- Shown on MiniCPM5-1B puzzles: blurt-3 PASS (the guesser's luck doubled after sleeping on its own hits, 63 to 131 of 1,980); blurt-2, 2p and 2b (greedy-solve loops) FAIL; idea-judging by the model itself was weak (top pick good 2/10, AUC 0.691).
- On a 27B (suggested): the generator is natively much stronger, so the "luck" is easier to see; keep puzzles with an exact checker first, because ideas need a judge and the judge is the open problem.
- Not in the first test. It needs the sleep step (§2.2) working first.

---

## 3. Fine-tune method, GPUs and cost (item b)

### 3.1 Method (suggested)
**QLoRA**: the base in 4-bit NF4, small LoRA adapters in bf16 trained on top. Full fine-tuning is out of reach (27B needs hundreds of GB for weights, gradients and optimizer state). Load the language model only (the config has a `language_model_only` field, and the vision tower is not needed). Gradient checkpointing on, short sequences (2,048 tokens), batch size 1 with accumulation.

### 3.2 Memory (estimates are mine: suggested; ranges from sources are shown)

| Item | Estimate |
|---|---|
| Weights in 4-bit | 27B × 0.5 byte = 13.5 GB raw; sources give about 14-16 GB loaded and a 17 GB Q4_K_M file ([yottalabs](https://www.yottalabs.ai/post/qwen-3-8-27b-specs-hardware-requirements-how-to-run-2026), Willison) |
| bf16 weights (for reference) | about 56 GB, so plain bf16 LoRA needs an 80 GB card |
| LoRA weights + Adam state, rank 16, all linear layers | about 2-3 GB (my arithmetic; depends on the module list) |
| Activations at 2K tokens, checkpointing on | about 4-8 GB (my estimate) |
| **Total to train** | **about 22-30 GB (untested)** |

Consequences: a 24 GB card (RTX 4090 or 3090) is too tight. A **32 GB** card (RTX 5090) is feasible. A **48 GB** card (RTX A6000, A40, RTX 6000 Ada) is comfortable. BensPC's RTX 5070 Ti has 16 GB, which is enough to *load* the 4-bit model for inference (it already does) but not to train it.

### 3.3 Today's Vast prices (shown; one read-only API query, 400 cheapest verified on-demand offers, 1 GPU, reliability above 0.95, download above 200 Mbps)

| GPU | VRAM | Offers in sample | Cheapest $/h | Median $/h |
|---|---|---|---|---|
| RTX 3090 | 24 GB | 24 | 0.16 | 0.31 |
| RTX 4090 | 24 GB | 21 | 0.42 | 0.56 |
| A100 SXM4 | 40 GB | 4 | 0.44 | 0.52 |
| **RTX A6000** | **48 GB** | 5 | **0.40** | 0.40 |
| A40 | 48 GB | 5 | 0.47 | 0.54 |
| RTX 6000 Ada | 48 GB | 4 | 0.54 | 0.60 |
| RTX PRO 5000 | 48 GB | 6 | 0.59 | 0.67 |
| **RTX 5090** | **32 GB** | 4 | **0.60** | 0.67 |

The sample was the cheapest 400 offers, so 80 GB H100/A100 cards did not appear. Third-party pages list an undated Vast H100 median of about $1.67/h ([Vast pricing table via search](https://vast.ai/pricing/gpu/A100-SXM4) and a March 2026 guide give $2-3.50); I did not verify those. For comparison, the ledger's recent real bills were $0.42-0.69/h for 4090/5090 boxes including storage. The ledger also says every rental needs Ben's own click in the renting session.

### 3.4 Cost per experiment (estimates: suggested; throughput is untested)

Assumptions: a 48 GB card at about $0.45/h; training speed 500-1,500 tokens per second for 4-bit LoRA on a 27B (my guess; the first step must measure it); about 55 GB of bf16 weights to download (7-40 minutes depending on the host's bandwidth); the 4-bit conversion happens on load.

| Piece | Time | Cost |
|---|---|---|
| Setup, download, load, smoke check | 0.5-0.7 h | $0.20-0.35 |
| One training run, 3M tokens | 0.6-1.7 h | $0.30-0.80 |
| Evaluation of the arm (a few hundred questions, generation) | 0.2-0.4 h | $0.10-0.20 |
| **One arm, one seed** | | **about $0.6-1.4** |
| Failure allowance (ledger: 6 of 7 recent boxes failed before training; each cost $0.05-0.85) | | add 50-100% |

So the **first test in §4** (3 trained arms × 3 seeds = 9 runs, sharing setup on one box where possible) comes to about **$8-18** (suggested), and the full sleep ladder after that perhaps $15-40. This is consistent with the low end of Ben's rough $50-500 guess; the high end would need a much longer training budget, a bigger context, or an 80 GB card. Because only the first step of §4 can measure the real throughput, treat every figure here as a bid to be replaced by a measured quote, as the ledger already does for its other runs.

---

## 4. The first small test (item c)

**Prerequisites (suggested; the gate itself is Ben's/the coordinator's call):**
1. **Gate:** the village model shows card memory end to end. A concrete reading, taken from the village spec: D beats contender E (pointers, no store) and contender C (BM25 lookup) on far and multi-hop village questions at equal compute, on at least 2 of 3 seeds, with bars sealed before the run. If this is not met, this track stays at $0.
2. **Rung 0, $0 plumbing (needs a coordinator ruling, because the gate says "no GPU spend"; BensPC is Ben's own and costs no dollars):** build the §4 harness and run it end to end on the 1B model the repo already uses (MiniCPM5-1B), so the 27B rental only repeats a debugged script. Steal the LoRA and eval code from `scripts/claude_dl*.py`.

**Question.** On text that fell outside the model's short window, does a *trained* card retriever beat plain BM25 retrieval, with everything else identical? (Memory *at all* vs no memory is a separate, earlier row, not the claim.)

**Data.** Long village visits (at least 4,000 tokens), questions on lines *before* a short window (512 tokens), including multi-hop questions that need 2-3 earlier lines; held-out name pool and held-out rule family (R9), as the village design already requires (`design/05-village-v0.md` §3). Exact-match grading by the village oracle. Grading never uses a model judge.

**Arms (all Qwen3.8-27B in 4-bit, the same LoRA recipe, the same number of steps and tokens, 3 seeds):**

| Arm | Sees | Trained? | Role |
|---|---|---|---|
| B0 | window only | no (base, LoRA off) | floor |
| B1 | window only | LoRA on village format | control: LoRA teaches format, not memory |
| **B2** | window + BM25 top-k earlier lines | LoRA | **the comparator** (contender C analogue) |
| **B3** | window + top-k lines chosen by the trained ASK head | LoRA + ASK head | **the one change vs B2: the retriever** |
| U | whole visit in the prompt | LoRA | ceiling only, not a contender |

One change at a time: B1→B2 adds retrieval; B2→B3 changes only the retriever. The claim below is B3 vs B2 only.

**Pass marks, fixed before any run (draft; see the calibration note):** on at least 2 of 3 seeds, on far and multi-hop questions (at least 300 per seed):
- **M1:** exact match of B3 minus B2 is at least `max(5 points, 2×SE)`, paired over the same questions.
- **M2:** the ASK head's recall@4 of the gold cards is at least 0.80 and at least 0.10 above BM25's recall@4 on the same questions.
- **M3 (guard, forgetting):** B3 loses at most 10 of 200 on the general-knowledge panel (lost = right at base, wrong now), and no more than B1 plus 5.
- **Void, not a failure:** the run is void if U is below 80% (the model cannot do the task even with everything visible), or if B2 is already at 90% or above (no headroom), or if B1 and B0 differ by under 2 points because LoRA never learned the format.

**The result that would prove the idea wrong:** B3 minus B2 is at or below 0 on **all three** seeds. Then a learned card retriever adds nothing over BM25 on a big pretrained model, and the card line stops here. We keep plain BM25 retrieval, which needs no training. A second proves-wrong reading: if M2 passes (the right cards are found) but M1 fails, retrieval is not the bottleneck and reasoning over the cards is; the next test would then concern reading, not memory.

**Calibration note (the same discipline the Director's marks self-check uses; `TESTS.md` item 1).** The bars above (5 points, 0.80, 10 of 200) are placeholders. Before sealing, measure the noise floor by running B2 twice with different seeds and set M1 to no less than the larger of the two spreads. A bar chosen after seeing a score is not allowed.

**Cost:** about $8-18 (§3.4), booked as a sealed bid to the coordinator, with the renting session's click.

**After this test, one change at a time (not yet specified further):**
1. **Sleep rung:** add the nightly LoRA update with a KL anchor against the same LoRA without the anchor. Registered pass in the style of dl-4: items lost with the anchor at most half of those without, on each seed, with the learning gain kept at 80% or more. Proves wrong: the anchor loses at least as many items on both seeds. Given dl-4's FAIL on a 1B, the odds are not favorable (suggested).
2. **Cards plus sleep together** (facts in cards, skills in weights).
3. **Creative line.**

---

## 5. Risks (the three biggest first)

1. **The long-context problem (card memory).** A 27B reads a whole village visit in its prompt, so learned cards may add nothing. The card line has also failed or stalled repeatedly at small scale (S3, S4, the decoder reader-KV line, G1k), and the village end-to-end result is not on file. If U beats B3, the honest outcome is "use a long prompt".
2. **The stack and the setup.** The model is a hybrid, with 48 of 64 layers linear-attention, a 248K vocabulary and a new architecture class. QLoRA, LoRA module names, kernels and the KL memory are all untested. In the last two days 6 of 7 booked rentals ended before training (ledger). Expect to burn part of the first rental on setup, and plan rung 0 on the 1B to reduce it.
3. **The forgetting fix is unproven even small.** dl-4's KL anchor failed its registered forgetting bar on the 1B; the other passes there (the expert switch, dl-9) are a different mechanism. The "G1" definition is not on `main`. Whatever sleep result we got on a 27B could be a model effect, not a mechanism effect.

Smaller risks: model churn (a better model may appear while the gate is open, so re-check before spending); the big model's built-in thinking mode (set it to off or low for the tests, or the token counts will not be comparable); the licence on any model we switch to (Qwen3.8-27B, Muse-Glimmer and Gemma 4 are Apache-2.0; the 180B Qwen3.8 Flash-Next is not).

## 6. Open items for the coordinator / Ben

- Read G1's exact definition from the Brain branch before any sleep run.
- Approve rung 0 (the $0 rehearsal on MiniCPM5-1B on BensPC) or keep the track fully frozen until the gate opens.
- Decide whether to schedule a monthly "is there a better model" check (needs Ben's yes).
- Seal the §4 bars only after the noise-floor measurement.

---

## 7. Plain-language summary (for a high-school senior)

**What this is.** Ben's project, Premonition, is a tiny model with a notebook for remembering things and a "sleep" step so it does not forget old skills when it learns new ones. The question is whether we can bolt those ideas onto a big, already-trained model instead of training from scratch.

**The model Ben named is real.** Qwen 3.8 27B came out on August 14, 2026. It is free to use (Apache 2.0). I checked the real download page, not just news posts. I found nothing newer and clearly better at that size; Meta's Muse-Glimmer 30B is the closest rival, but only Meta's own charts say it is good.

**Can we do it cheaply?** Yes, we would not retrain the whole thing. We would freeze it and train a thin "add-on layer" (called LoRA) while the main model is stored in a squashed 4-bit form so it fits on one rented graphics card with 32 to 48 GB of memory. Those cards rent for about 40 to 60 cents an hour today. One practice run costs roughly a dollar or two, and the first real test maybe $8 to $18. Those numbers are my estimates; nobody has timed it yet.

**What might go wrong.** First, a big model can already read a huge amount of text at once, so a notebook may not help it at all, and the first test is built to find that out fast. Second, this model is built differently from most, so the tools may break and setup costs could eat some money (6 of the last 7 rentals failed before they even started training). Third, even on a small model, our "don't forget" trick has not passed its test yet.

**What happens next.** Nothing costs money until the small village model shows the notebook working from start to finish. After that, the first test asks one question: does a smart, trained notebook search beat a plain keyword search? If the answer is no, we stop and save the money.

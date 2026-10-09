# Literature addendum (10-08 evening): Haiku verification of `LIT.md` and a gap sweep

Made by a Haiku-only workflow (36 agents, every agent capped at 6 web searches and 2 page fetches, so none got near 100k tokens). I read and condensed the results;
I did not open the papers. "Seen" labels are the Haiku agents' own: **abstract/page seen** = they fetched it, **snippet only** = a search excerpt, which can be wrong.
Raw results: `lit-workflow-result.json` in this folder.

## 1. Verification of the 18 papers cited in `LIT.md`

All 18 exist, and authors, year and arXiv id are right as cited. Verdict on the attributed claim: **supported** (abstract says it): Saxena 2022, LAMOL, STaR, van de Ven & Tolias,
GEM, LoRA-learns-less. **Partly** (the abstract supports part of it, the rest not seen, so treat as unchecked): Muennighoff, Verwimp, Chaudhry (tiny episodic memories), Ibrahim,
WiSE-FT, task arithmetic, DreamCoder, Mirzadeh, CLS-ER, Marek, Tadros, Kosson.
Corrections made in `LIT.md`: Marek 2026's title; Chaudhry's two titles; Muennighoff's and Verwimp's wording. Other notes: DreamCoder's second author is Catherine Wong (the PLDI page has a typo);
Saxena 2022 and Tadros 2022 have no arXiv id (do not add one); van de Ven & Tolias is an arXiv preprint (no peer-reviewed venue seen); Kosson et al. is arXiv 2410.23922.

## 2. New papers from the five gap questions (Haiku-reported; none read by me)

**Mix ratio (new vs replayed old data per batch).**
- Ibrahim et al. 2024 (arXiv 2403.08763), abstract seen: replay + lr re-warm/re-decay matched retraining on all data; the replay grid (about 1% to 50%) comes from search snippets that disagree.
- Spiegelhalter et al. 2025, "Balancing Synthetic Data and Replay for Enhancing Task-Specific Capabilities", arXiv 2510.11842, snippet only: sweeps token budget and replay ratio on a narrow task; the closest match to our mix-ratio question.
- TiC-LM benchmark (arXiv 2504.02107), abstract seen: replay matters most for generic web data; a fixed 1/2 new-data mix beat a decaying schedule (snippet).
- "Forget Forgetting" (arXiv 2502.07274), snippet only (images): replay with abundant memory lowers plasticity on novel information. "Revisiting Replay and Gradient Alignment for Continual Pre-Training" (arXiv 2508.01908), snippet only.
- Takeaway (Haiku): larger replay shares cost new-skill learning at fixed compute; no source seen measures this at 3.3M parameters.

**Fixed small buffer vs fresh/augmented replay.**
- Zhang et al. 2022, "Repeated Augmented Rehearsal", NeurIPS, arXiv 2209.13917, snippet: repeating the buffer with augmentation beats vanilla rehearsal in online CL (9% to 17%).
- Bonicelli et al. 2022, LiDER, NeurIPS, arXiv 2210.06443, snippet: replaying a small buffer repeatedly overfits it; a Lipschitz regulariser helps.
- Huang et al. 2024, "Self-Synthesized Rehearsal", ACL, arXiv 2403.01244, snippet: model-generated rehearsal data at least as good as real replay with less data.
- ADRM (arXiv 2405.11829), snippet: adversarially perturbed copies counter memory overfitting.

**Training on self-generated, checker-verified data.**
- Marek et al. 2026 (2605.26097), abstract seen: self-generated replay nearly eliminates forgetting; low learning rates reduce forgetting but need many more steps.
- ReST-EM (Singh et al. 2023, arXiv 2312.06585), abstract seen: sample, keep what a binary checker accepts, fine-tune, repeat a few rounds.
- Yuan et al. 2023, rejection-sampling fine-tuning (arXiv 2308.01825), snippet: GSM8K 49.3% vs 35.9% for SFT on LLaMA-7B.
- "Talking to Yourself" (arXiv 2602.20162), snippet: self-generated dialogues mixed with task data keep performance close to the original model.
- A verifier-filtered fine-tuning preprint (arXiv 2609.23367), snippet: verified data limited to deterministic tasks collapsed open-ended ability, so the data mix matters.

**Self-chosen stopping from the model's own probes.**
- Vins, Delanois, Bazhenov 2025, "When to Learn and When to Stop: Quitting at the Optimal Time" (student abstract), abstract seen: stop training on a new task when the mean validation accuracy across ALL tasks (old and new) stops rising; paired with sleep-style replay. This is the one source close to our stop rule.
- Wang 2025 (arXiv 2512.20634), abstract seen: a real-time detector separates spurious forgetting from true loss and triggers mitigation (3B to 32B models).
- Class-wise forgetting detector (Pham, Liew, Wang), snippet: switches to replay when forgetting appears; needs labels per class.
- Haiku found no source that uses a model's own held-out old-task probes for stopping at small scale.

**Positive backward transfer, and how papers separate it from extra practice.**
- GEM (Lopez-Paz and Ranzato 2017), abstract seen: "allowing beneficial transfer of knowledge to previous tasks". MER (Riemer 2019): replay + gradient alignment to raise transfer, snippet.
- Pretrained VLA models (arXiv 2603.03818), abstract seen: simple replay sometimes gives zero forgetting.
- "Layerwise Proximal Replay" (arXiv 2402.09542), snippet: replay raises the number of iterations that touch past data, which is the compute confound a control must match.
- Haiku found no paper that runs a matched-steps, old-data-only control arm. Our `rp` arm is that control.

**Gaps a Haiku critic named (it did not search; unchecked):** parameter regularisation (EWC, LwF) as a replay-free control; interference-targeted replay selection (Aljundi et al. 2019, "Maximally Interfered Retrieval");
orthogonal-subspace or adapter isolation; synaptic homeostasis during sleep (Tononi and Cirelli 2014); the complementary-learning-systems template (McClelland et al. 1995).

## 3. What this changes, if anything (suggestions, untested here)

- *Suggested:* our stop rule uses only the held practice fit rate (the new skill). Vins et al.'s rule counts old and new together. A stop rule that also watches the model's own held skills rows is the nearest literature-supported change, and it is cheap, since both checks already exist. Not tested.
- *Suggested:* the mix-ratio question has a direct literature match (Spiegelhalter et al.; Ibrahim et al.), and both say the answer depends on compute and domain.
- *Not changed:* the pre-registered confirm. Nothing here was used to alter a mark.

# G: Latent multi-hop reasoning, Coconut, and bridge-entity layers

Labels: **shown** = number or claim read in an abstract/page during this search; **suggested** = interpretation by me or a secondary source; **untested** = implication for our village task, not checked.

Note: I read abstracts and summary pages only (arXiv HTML/PDF full text was too large for one fetch in one case). Numbers below should be re-checked in the full paper before they go into a write-up.

## 1. Latent (no-CoT) multi-hop limits

- **Yang et al., "Do LLMs Latently Perform Multi-Hop Reasoning?" arXiv 2402.16837 (ACL 2024).** **shown:** first hop (recalling the bridge entity) is well supported; a clear scaling trend with model size for hop 1, but not for hop 2; hop 2 and full traversal are only moderately supported on average; pathway use varies strongly by relation type and prompt type (">80%" for some relations). Implication: one hop of latent recall is reliable; two-hop composition is where it breaks.
- **Balesni, Korbak, Evans, "The Two-Hop Curse," arXiv 2411.16353.** The v1 result (fine-tuned models on facts in separate documents fail completely at two-hop no-CoT, chance accuracy) was **revised**. The v4 paper, retitled "Lessons from Studying Two-Hop Latent Reasoning" (Nov 2025), **shown:** models fail to compose two *synthetic* facts but succeed when one fact is synthetic and the other is natural (Llama 3 8B and GPT-4o tested). Their conclusion: latent two-hop is possible, but how it scales with model size is unclear. Cite v4, not the "curse" framing.
- **Yao et al., EMNLP 2025 (from a search summary; I did not fetch the paper).** Models trained from scratch on k-hop tasks: data needed grows exponentially in k; layers needed grow linearly in k; curriculum cuts data need but does not remove it. Status: **secondary-source summary, not verified.**
- **Yang et al., ACL Findings 2025 (SOCRATES dataset, from a search summary).** **shown in summary:** best models reach ~80% latent composability when the intermediate answer is a country, but ~5% when it is a year. Status: **secondary, verify.**
- **arXiv 2509.21199 (Fano-style bound on single-pass multi-hop QA).** A theoretical per-pass information-capacity argument with an "accuracy cliff" as hops grow. **suggested:** a useful framing for "how many hops fit in one forward pass," but I did not verify its numbers.
- **Entity state tracking.** Kim & Schuster, arXiv 2305.02363 (**shown:** only GPT-3.5 models, pretrained on code, track entity state through operation sequences well; fine-tuned T5 is non-trivial but drops on harder splits; text-only pretraining alone is not enough). The page gives no layer or numeric detail. Feng & Steinhardt, "How do LMs bind entities in context?" arXiv 2310.17191 (ICLR 2024): **shown:** a "binding ID" mechanism appears in all sufficiently large Pythia and LLaMA models; binding vectors form a continuous subspace. Relevance: entity-to-attribute binding is a plausible mechanism for "which item belongs to which person," which our task needs. **suggested**, not tested on our setup.

**Hop count answer (suggested, not settled):** Evidence supports roughly one latent hop per forward pass in pretrained models, with two hops only sometimes and deeper chains poorly. Extra latent tokens (Coconut-style) are the expected way to get 3-6 hops, but no paper I found measures a hard latent hop limit for a 3.7B pretrained model.

## 2. Coconut on ProsQA / ProntoQA

- **Coconut, Hao et al., arXiv 2412.06769 (GPT-2 base).** **shown in secondary coverage (The Decoder, TDS; abstract confirms the direction):** ProsQA 97% (Coconut) vs 77.5% (CoT); ProntoQA 99.8% vs 98.8%; GSM8k CoT is higher (42.9% vs ~34%; sources disagree on 34.1 vs 34.9). Token counts roughly 14 vs 49 on ProsQA and ~9 vs 92 on ProntoQA. Check these against the paper's Table 1 before quoting.
- **Why it wins on ProsQA (shown in abstract):** Continuous thoughts can encode several alternative next steps at once, so the model can search breadth-first instead of committing to one path. The abstract says "BFS"; the word "superposition" is a secondary paraphrase, not the paper's wording.
- **Training:** a multi-stage curriculum (ProsQA max depth 6 steps); at test time the number of latent thoughts k can be varied from 0 to 6 with shared weights. This is directly the knob we want: k latent tokens per hop.

**Implication (suggested):** Coconut's gain is largest on search-heavy graph tasks, where a BFS-like frontier helps. Our village chains (1-6 hops, mostly chain-like, with "where was X" lookups) are closer to a chain than a search, so the gain may be smaller. Untested. Our curriculum should match hop count to latent-token count, as Coconut does.

## 3. Which layer holds the bridge entity; back-patching

- **Biran et al., "Hopping Too Late," arXiv 2406.12775 (EMNLP 2024).** **shown:** the bridge entity is resolved at the first-hop token in *early* layers (Patchscopes decodes it in 41-78% of cases across models). The second-hop target is resolved at the final token in *mid-to-upper* layers (decoded in 71-86% of correct cases, 33-65% of incorrect ones). Information moves from first-hop token to final token mainly in *middle* layers (71-97% of cases).
- **Back-patching (shown):** copy a hidden state from a later layer into the same position at an earlier layer, then continue the forward pass. Tested on ~82k Wikidata two-hop queries. Fix rates on previously wrong cases (first-hop token / final token):
  - LLaMA 2 7B: 41.0% / 42.5%
  - LLaMA 2 13B: 32.4% / 36.1%
  - LLaMA 3 8B: 38.8% / 47.2%
  - LLaMA 3 70B: 57.3% / 57.8%
  - Pythia 6.9B: 66.3% / 56.4%
  - Pythia 12B: 63.2% / 61.8%
  Correct cases stay at 100%. The paper says it is **not a practical inference method**, because only certain source-target layer pairs work.
- **Layer-Order Inversion, arXiv 2601.03542 (2026).** **shown in abstract:** in multi-hop queries, later-hop answers can become decodable before bridge entities, which contradicts the hop-aligned circuit hypothesis; the effect grows with total hop count. Proposed mechanism: broad recall in shallow MLPs, then selective extraction in deeper attention layers. Abstract gives no model names or numbers. **suggested:** this weakens the "bridge at layer L, then hop 2 at layer L+k" picture that back-patching assumes, and it argues that back-patching works partly by compensating for weak shallow recall. Full text needed.

**Implications for our distillation (suggested, untested):**
- Recycling state: the bridge (hop-1) state is most decodable in early-to-middle layers, so a latent token that recycles the mid-layer hidden state (not just the final layer) is the closest match to the evidence.
- Matching layers in distillation: match the teacher's hop-1 and hop-2 states at early-middle and mid-upper layers respectively, rather than only the final logits. The Hopping Too Late numbers suggest these are the layers where the entity and the target are represented.
- Back-patching is a diagnostic here, not a training method. Running it on our 3.7B model (no training) would show which source-target pairs are fixable, which is cheap to test.

## Caveats
- Several numbers come from search summaries, not the papers themselves (Yao et al.; Yang SOCRATES; Coconut GSM8k and token counts).
- Balesni et al. v1 and v4 disagree; cite v4.
- Nothing above measures a 3.7B model on a village-style task.

## Suggested next checks (untested)
1. Read Coconut Table 1 and Section 5 directly for ProsQA numbers and the BFS analysis.
2. Read 2601.03542 full text for model list and the back-patching claim.
3. Run a Patchscopes/logit-lens probe on our model for hop-1 entity layer on 20 village questions, with pass mark: hop-1 entity decodable at a single layer in >=70% of cases.

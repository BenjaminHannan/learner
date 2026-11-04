# Known ideas: card write rule and entity binding

Built before any evolve run (Stage 0). It is used in two places:
- `KNOWN_SHORT.md`, a short version, goes into the mutation prompt as "do not reproduce these".
- This full file goes to the novelty judge with every finalist.

The project's own ideas were harvested by skimming the headings of `design/research/`, `reviews/` and `design/v3/` (about 45 of about 740 files sampled). Each source is given beside its entry. "TRIED" means the project has a result.

## A. This project's own ideas (write rule, eviction, binding)

1. **Single attention-pool writer (the seed).** One softmax pool over the line; key = W_k p and value = W_v p. Measured: 0.979 of the pool sits on the value token, so the person is lost. Sources: `premonition/model.py` CardWriter, `premonition/card_pools.py`.
2. **Two-pool writer.** Separate softmax pools for the key and the value. TRIED, FAIL on the ladder (gold fetched −0.11 to −0.17). Sources: `premonition/card_pools.py`, `reviews/opus-next-2026-09-19-two-pool-cards.md`.
3. **Mean-pool writer.** A uniform mean over the line. TRIED, FAIL. Same sources.
4. **Separate key pool (key-pool variant).** Source: `scripts/premonition_key_pool.py`. Stuck runs: 1/40 vs 7/40 (`design/v3/10-fixes.md`).
5. **Wire / relation-shortcut writer.** Source: `design/v3/10-fixes.md`. Stuck runs: 17/40.
6. **Key and value from different line positions or role-block slices.** Source: broad-sweep #29.
7. **Address-keyed selection.** The key is person+relation; the value is read separately. TRIED: choose went from 164 to 503/512, but only with structural help. Sources: `reviews/opus-milestone-03-address-keys-results.md`, `design/v3/00-decisions.md` D23–D24 ("the address excludes the value").
8. **Dual-state cards with an identity vector trained contrastively.** Source: broad-sweep #51.
9. **Role or identity tags on card and slot writes; a typed card row holding entity ids plus a key.** Source: broad-sweep #12, #4.
10. **HRR role×filler binding; barcode keys made from identity tokens.** Sources: broad-sweep #98, #63; `design/v3/20-undercovered-brain-mechanisms.md` §3.
11. **Sparse keys from entity pointers.** Source: novel-mechanisms S6.
12. **Slot knock-out with shuffled slot order,** so that identity lives only in pointers. Source: novel-mechanisms #1.
13. **Entity-slot gated binding** (`Think.bind`: s ← s + σ·(tanh − s)). Measured as unused. Source: `premonition/model.py`.
14. **Name pointerizer** (each new name gets the next ENT id in a random order per visit); a mutual-exclusivity bit for new names. Sources: `premonition/pointer.py`, broad-sweep #83.
15. **Owner pointer credited for any copy of the name.** Source: `reviews/chat-prompt-vread-name-credit-2026-09-28.md`.
16. **Token-level ColBERT-style addresses kept until the question arrives.** Source: `final-sweep-2026-09-19/02-memory.md` P1.
17. **Factorised query (who and relation fields); a tiny discrete codebook on the relation.** Source: broad-sweep #11, #64.
18. **Supervise choosing with hard negatives.** Source: broad-sweep #9.
19. **Write gating:**
    - learned surprise gate plus reconstruction loss (broad-sweep #67);
    - predict-before-store;
    - confidence-threshold save gate;
    - certified write thresholds (several `design/v3/30-modes` files).
20. **Error-correcting delta write (DeltaNet style).** Source: `final-sweep 02-memory.md` P3.
21. **Append-only versioned records; source tags (WORLD/SUPPOSE/BELIEF).** Sources: novel-mechanisms S1 and S7, track B.
22. **Eviction rules:**
    - FIFO ring;
    - LRU;
    - reservoir;
    - two memory strengths;
    - "forget the key, not the fact".

    Sources: track B, novel-mechanisms S4 and S6.

## B. Standard literature methods for turning a token set into a key/value, or for binding

Pooling and set encoders:
- mean pooling, max pooling, sum pooling;
- GeM / power-mean pooling;
- softmax attention pooling; the CLS token;
- multi-head / multi-query attention pooling (PMA, Set Transformer, Lee et al. 2019);
- Perceiver latent cross-attention;
- self-attention layers over the tokens before pooling;
- Deep Sets (φ then sum then ρ);
- NetVLAD / VLAD;
- bilinear / second-order (covariance) pooling;
- sparsemax / entmax pooling, top-k token selection, Gumbel-softmax hard attention;
- entropy regularisation of pool weights; temperature-scaled pooling.

Key/value design:
- Key-Value Memory Networks (Miller 2016): separate key and value encodings;
- End-to-End Memory Networks;
- Neural Turing Machine / DNC content addressing and write heads;
- product-key memory;
- VQ / discrete codebook keys;
- contrastive (InfoNCE) key training;
- modern Hopfield networks;
- Kanerva sparse distributed memory;
- locality-sensitive hashing keys.

Binding:
- Tensor Product Representations (Smolensky): role ⊗ filler;
- Holographic Reduced Representations (Plate): circular convolution;
- vector-symbolic architectures (MAP / BSC: elementwise multiply, permute);
- fast weights / outer-product memory (Ba 2016; Schlag 2021, linear transformers);
- the DeltaNet delta rule;
- Recurrent Entity Networks (Henaff 2017): per-entity gated slots;
- slot attention (Locatello 2020): competition between slots;
- capsule dynamic routing;
- relation networks (pairwise g(o_i, o_j) then sum);
- gated / multiplicative interactions: GLU, FiLM, hypernetwork-generated weights;
- bilinear binding of two token states (x_i^T W x_j);
- pointer networks;
- role-specific projections learned from token content ("type-aware pooling");
- MoE / routing over tokens;
- a recurrent (GRU/LSTM) line encoder; a 1-D convolution line encoder;
- LayerNorm, whitening or orthogonalisation of keys;
- learned positional binding.

## C. How to use this list

A finalist is "known" if its core mechanism is one of the items above or a direct combination of two of them. Examples: multi-head pooling plus a gate; outer-product binding of the two highest-pool tokens; Deep Sets with a pairwise term.

A finalist is "not found" only if the judge, after its literature search, cannot name a published or project method with the same core operation. In that case the judge states the closest one.

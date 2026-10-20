# ShinkaEvolve trial, Stage 2 report: evo1 (card write rule)

Date: 2026-10-20. Sealed card: `research/shinka/CARD.md`, sealed at commit 6996899. One dated amendment (section 6 clarifications) was committed before finalist selection.

Claim labels:
- **shown**: measured in this trial.
- **suggested**: inferred from what was measured, not tested directly.
- **untested**: not checked at all.

## Verdict

**The trial failed by its own sealed rule (shown).** No finalist was both BETTER on the 2 fresh seeds and judged NOT KNOWN.

| group | finalists |
|---|---|
| both (WINNER) | none |
| better but known | **6a-1 `transport_quota_key`** (gen 19) |
| novel but not better | none |
| neither | 6b-1 (gen 13), 6b-2 (gen 5), 6a-2 (gen 14), 6a-3 (gen 15), 6a-4 (gen 9; NOT JUDGED for budget, so it counts as known) |

## What ran (shown)

- **Evolve run:**
  - 20 generations (20 children plus the seed on 2 islands), ended by ShinkaEvolve's cost cap;
  - 25 Opus 5.5 calls, 15 of 20 children correct;
  - best evolution-seed score 0.759 (gen 19).
- **Code-novelty rejection:** 0 rejections and 15 acceptances. Every proposal stayed below the 0.95 code-similarity threshold.
- **Strange slot:** fired 6 times. It picked gen 1 (4 times) and the seed (2 times), because few programs existed when it fired.
- **Fresh-seed confirmation:** seeds 1001 and 1002, CPU only, no API spend. It ran the baseline, multi-head and all 6 finalists, with no errors.
- **Novelty judge:** Opus 5.5 with web search, in the sealed order. 5 finalists were judged. 6a-4 was NOT JUDGED: $0.54 of the judge budget was left, and a first turn's worst case was $0.636.

## Dollars (shown, from `results/TRIAL_LEDGER.jsonl`)

| item | calls | USD |
|---|---|---|
| smoke tests (sine example, first plumbing test) | 3 | 0.021 |
| Opus plumbing test | 2 | 0.134 |
| evo1 evolve run | 25 | 2.175 (ShinkaEvolve cap 2.025; the extra came from proposals already in flight, which the card allows) |
| novelty judge | 5 | 1.060 |
| **total** | 35 | **3.389** (against the $4.50 stop and the $5.00 limit) |

## Fresh-seed scores (shown, `confirm.json`)

| program | score s1001 / s1002 | Δ vs baseline | Δ vs multi-head | acc familiar | acc novel | person-lost errors (novel) | BETTER? |
|---|---|---|---|---|---|---|---|
| baseline (seed) | 0.411 / 0.471 | | | 0.495 / 0.566 | 0.327 / 0.376 | 0.439 / 0.400 | |
| multi-head pool (known) | 0.743 / 0.740 | | | 0.969 / 0.961 | 0.517 / 0.520 | 0.483 / 0.463 | |
| 6b-1 gen13 | 0.565 / 0.649 | +0.154 / +0.178 | −0.177 / −0.091 | 0.775 / 0.844 | 0.355 / 0.454 | 0.493 / 0.460 | no (novel accuracy below multi-head) |
| **6a-1 gen19** | **0.715 / 0.740** | +0.304 / +0.269 | −0.028 / −0.000 | 0.942 / 0.915 | **0.487 / 0.564** | 0.440 / **0.316** | **yes** |
| 6b-2 gen5 | 0.572 / 0.593 | +0.161 / +0.122 | −0.170 / −0.147 | 0.780 / 0.818 | 0.364 / 0.368 | 0.507 / 0.591 | no |
| 6a-2 gen14 | 0.697 / 0.684 | +0.286 / +0.213 | −0.046 / −0.056 | 0.894 / 0.891 | 0.500 / 0.478 | 0.416 / 0.449 | no |
| 6a-3 gen15 | 0.685 / 0.684 | +0.274 / +0.212 | −0.058 / −0.057 | 0.908 / 0.908 | 0.462 / 0.459 | 0.474 / 0.487 | no |
| 6a-4 gen9 | 0.705 / 0.676 | +0.294 / +0.205 | −0.038 / −0.064 | 0.908 / 0.897 | 0.502 / 0.455 | 0.420 / 0.456 | no |

What the table shows:
- Every finalist beats the baseline by more than 0.06 on both seeds (shown).
- Only 6a-1 also has a novel-name accuracy sum above multi-head's: 1.051 against 1.037 (shown).
- That margin is 0.014 summed over two seeds, which is inside seed noise. So 6a-1 being better than multi-head on novel names is **not** established (suggested).
- No finalist beats multi-head overall by the 0.045 "better than best known" mark. 6a-1 ties it on seed 1002 and loses by 0.028 on 1001 (shown).
- 6a-1 has the lowest person-lost error rate on seed 1002 (0.316, against 0.46–0.48 for multi-head) but not on seed 1001 (shown). Whether it binds the person better is untested beyond these 2 seeds.

## Finalists: plain-language mechanism and the judge's verdict

Code and diffs against the seed are in `results/evo1/finalists/*.py` and `*.diff`. All 6 were read by hand for sandbox evasion and none was found (shown). Every verdict below is the judge's verdict line, quoted from `judge.jsonl`.

**Shared ingredient (shown).** All 6 finalists, and the lineage they descend from, are built on **"deflation pursuit"**:
- one attention pool picks a direction in the line;
- that direction is removed from every word;
- the next pool must find something else.

This is attention-weighted matching pursuit. The idea showed up in generation 1 and the population never left it. Code-novelty rejection never fired, because each rewrite was new code expressing the same core idea (shown). Code-level novelty is not idea-level novelty (suggested).

### 6b-1 `novelty_cued_residual_atom` (gen 13; strange-slot pick, distance 6.38)
**Mechanism:** up to 4 rounds of "pool, then remove what was pooled". After them comes a final pool that favours words whose leftover energy lies outside a learned 12-dimensional "familiar" subspace. The aim is to catch the unusual word, hoped to be the person.

**Judge:** KNOWN. It names multi-query attention pooling (PMA) plus matching-pursuit deflation (Mallat & Zhang 1993), plus a PCA reconstruction-error novelty pool. Under KNOWN.md §C this is a direct combination of known items.
- My check: the judge says the value comes from a separate pool. In the code, the value uses the same pool weights applied to the original states. This is a minor slip and does not change the verdict.

### 6a-1 `transport_quota_key` (gen 19) — better but known
**Mechanism:** the key is built from several different summaries of the line:
- (a) 2 deflation-pursuit pools;
- (b) a pool of words that the learned familiar subspace explains badly;
- (c) a pool of words unlike the other words in the line;
- (d) the product of (b) and (c);
- (e) a few learned prototype slots, each forced to take an equal share of the line's words through entropic optimal transport (Sinkhorn: every slot must "buy" its quota of words);
- (f) fixed random projections of (c), (d) and (e), added onto the key as an "echo".

The value is a learned mix of the pursuit pools.

**Judge:** KNOWN. It names multi-query attention pooling (PMA) plus optimal-transport prototype pooling (OTKE, Mialon et al. 2021), with separate key-side pools. The deflation and novelty scores count as reweightings of standard attention pooling. Under §C this is a direct combination.
- I agree. The quota-transport slots are the newest-looking part, and OTKE is a close match.

### 6b-2 `matching_pursuit_deflation_writer` (gen 5; strange-slot pick, distance 5.93)
**Mechanism:** the plainest form of deflation pursuit: up to 4 pools, each removing its direction before the next.

**Judge:** KNOWN, as matching-pursuit / Gram-Schmidt deflation applied to multi-head softmax attention pooling.
- Caveat from the judge itself: its web search hit its usage limit before returning anything, so this verdict rests on what the model already knew.

### 6a-2 `conjunctive_novelty_echo` (gen 14)
**Mechanism:** deflation pursuit, plus a "not explained by the familiar subspace" pool and a "unlike the other words in the line" pool. A pool weighted by the product of those two ("unusual AND locally distinct") is added to the key through fixed random projections.

**Judge:** KNOWN, as a product of experts of two attention-pooling distributions. KNOWN.md §C names "multi-head pooling plus a gate" as known.

### 6a-3 `ridge_leverage_echo_pursuit` (gen 15)
**Mechanism:** deflation pursuit, plus a novelty pool, plus a pool whose scores get a bonus equal to each word's ridge leverage within the line. Leverage is a standard statistic for how much of an outlier a point is.

**Judge:** KNOWN, as softmax attention pooling with a hand-made salience bias (ridge leverage, a standard outlier statistic) stacked with multi-head pooling orthogonalised by deflation.

### 6a-4 `distinctive_echo_isometric_key` (gen 9)
**Mechanism:** 6a-2 without the product pool: deflation pursuit, a novelty pool, and a "distinct within the line" pool echoed into the key.

**Judge:** NOT JUDGED (budget), which counts as KNOWN.
- My own reading: it is a strict subset of 6a-2's parts, which was judged KNOWN, so I would expect the same verdict (suggested).

## What the trial does and does not show

- **Shown:** under these rules, ShinkaEvolve with Opus 5.5 produced writers that beat PremonitionMini's single-pool writer by a large margin on this toy: +0.12 to +0.30 on fresh seeds.
- **Shown:** none of them beat the known multi-head pool, and every finalist was judged KNOWN, or counts as known because it was not judged.
- **Shown:** the main reusable idea it found, deflation pursuit, is known: matching pursuit applied to attention.
- **Suggested:** with about 20 generations, the search settled on one family early. The strange slot had few programs to choose from when it fired. A longer run might explore more, at more cost (untested).
- **Untested:** whether any of these writers would help PremonitionMini itself on the ladder or the village. That would need a separate pre-registered run under `premonition/`.

## Plain-language summary for Ben

We asked an AI-driven "evolution" program to invent a new way for your model to write its memory cards: a way that remembers *who* a fact is about, not just the fact. To keep it honest, every invention was:
- scored on a small test that reproduces your model's real weakness;
- checked again on two fresh test runs it never trained on;
- shown to a separate AI judge that searched the literature for anything similar.

It made about 20 attempts and spent $3.39 of the $5 budget. Every one of its 6 best ideas beat your model's current card-writer by a lot, roughly from 45% to as much as 74% right on our test. But none beat a well-known existing method (multi-head pooling). The judge recognised each idea as a combination of known techniques. The main trick it kept reusing was "look at the line, take out what you just noticed, then look again", which is called matching pursuit.

So the honest result is: **better than what your model has now, but not new.** By the rules we set in advance, the trial counts as a failure: no idea was both new and better. The useful takeaway is that your current card-writer is easy to improve, and that a known method (multi-head pooling) already does most of that improvement. Trying a known method like that in the real model could be worthwhile, as a separate, pre-registered test.

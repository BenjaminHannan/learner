# 71 — Fable-Edit-200 baselines (experiment 66, Muse, 2026-09-21)

Three registered baseline arms for Fable-Edit-200, so bench65's notebook arm
(doc 70) can be compared against something fair. The notebook arm feeds
triples to a hard-coded hop loop; these arms instead give a same-size
open-weight model (SmolLM2-360M-Instruct, Apache-2.0) the ORIGINAL ENGLISH
teaching sentences and see what it does. Same 200 items, same scoring rules,
same machine class (Mac CPU, OMP_NUM_THREADS=1).

## Arms (script `scripts/fable_bench66_baselines.py`, seed 6601)

All arms are fed only the item's original English teaching sentences and the
question. The gold answer never enters any prompt or any training text — it
is used only for scoring after generation (K4 holds by construction, not by
promise).

1. **IN-CONTEXT** — every teaching sentence of the item in one prompt
   ("Facts:\n- ...\nQuestion: ..."), system line "Answer the question with a
   short phrase. If the answer is not known, say unknown.", greedy decode,
   ≤ 16 new tokens.
2. **RAG-lite** — same prompt shape, but only the top-3 sentences by Okapi
   BM25 (k1=1.5, b=0.75) scored against the question. BM25 is implemented in
   numpy inside the script; no new packages. This mimics the retrieval
   baseline that doc 63's scout says beats parameter editors on prose
   benchmarks.
3. **FINE-TUNE** — per item: reset to base weights, train ONLY the final 2
   transformer blocks + lm_head (18.5% of params) for a fixed 20 Adam steps
   at lr 1e-4 on the item's teaching sentences (next-token loss, one
   sequence per sentence), then ask the question ZERO-SHOT (no sentences in
   the prompt). This asks the 2026 question directly: does 20 steps of
   gradient descent install the taught facts into a 360M model? Full
   fine-tuning would take hours per item on CPU; the pre-registered cut is
   to the first 60 items (fixed order) if the projection from the first 3
   items exceeds 40 min.

## Scoring (fixed in the sealed PASSMARKS)

Normalise: lowercase, strip punctuation and articles, collapse spaces.
Correct = normalised answer equals a normalised gold or alias (exact match);
'contains gold' recorded separately. Abstain = answer contains 'unknown' /
"i don't know" / 'not' AND contains no gold. WRONG = non-abstaining and not
gold — on the 50 abstain items (gold empty) this is the wrong-answer count
K2 tracks.

## Data

`data/open/bench65/fable_edit_200.jsonl` (built by bench65, doc 70):
100 MQuAKE-Remastered CF-3k two-hop single-edit, 50 reversal (25 fictitious
facts × both directions, both sentences taught), 25 abstain-absent + 25
abstain-broken (gold empty). Sentences are taken from `taught[].sentence_en`;
gold lists and aliases from `gold` + `gold_aliases`.

## Sealed predictions (PASSMARKS.md, hashed in SEAL.sha256.txt)

K1 integer counts per arm × type; K2 per-arm abstention wrong-answer count
reported; K3 total wall < 45 min; K4 no gold at inference. P66.1 in-context
exact ≤ 30% (p 0.70); P66.2 RAG-lite ≥ in-context (p 0.60); P66.3 reversal
≤ 20% everywhere (p 0.75); P66.4 ≥ 1 arm guesses on an abstain item (p
0.80); P66.5 K3 holds (p 0.85); P66.6 fine-tune ≤ in-context on mquake2hop
(p 0.70). These are predictions ABOUT a weak baseline, not bars we want it
to pass; a PASS means the measurement completed.

## Deviations

- The script pre-dated the data file; on first sight of bench65's real
  schema it was adapted (sentences from `taught[].sentence_en`, gold as a
  list + aliases, type names `mquake-twohop`/`abstain-absent`/
  `abstain-broken` mapped to the canonical four). Logic unchanged.
- A 3-item timing/schema probe ran before the registered run (declared; not
  scored).
- Ledger numbering: P66.1–P66.6 was used before noticing another agent's
  experiment (doc 66) also claims P66; outcomes are labelled
  "P66.x bench66-baselines" to disambiguate.
- Waited for bench65's file rather than falling back to the synthetic
  stand-in; the stand-in path stays in the script, unused.

## What it means

If K1–K4 hold, we get a leak-free, honestly-timed baseline table (arms ×
types, correct/abstain/wrong) on the exact items bench65's notebook arm
answers from triples — the fair comparison point for "does the notebook
actually beat a same-size model that reads English?".

## What it does not mean

Nothing here tests the notebook itself; these arms are SmolLM2 only. Low
baseline scores do not prove the notebook would win on English input — that
arm parsed no English at all — and high abstention-wrong counts do not prove
our structural abstention is better; they only show what a small greedy
decoder does when taught and asked the same questions.

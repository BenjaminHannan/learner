# bm-393b RESULTS: the ep-382 store's recall() on LoCoMo practice (after using LoCoMo for development)

Run 2026-09-25 ~20:20 UTC, cloud CPU, 2 min 1 s, $0, sealed code at main 1319cb5b8. Self-test EP382-SELFTEST PASS
(9 of 9). Counts only.

## Evidence found in the top 10 (any / all evidence turns), and any at 20
| Category (questions) | fused | minilm | bm25 |
|---|---|---|---|
| 1 multi-hop (281) | 55.9% / 11.4%, @20 68.0% | 48.4% / 8.9%, @20 65.8% | 41.3% / 6.4%, @20 53.0% |
| 2 temporal (320) | 71.6% / 64.4%, @20 76.9% | 53.4% / 46.9%, @20 62.8% | 64.1% / 57.2%, @20 70.3% |
| 3 open-domain (89) | 39.3% / 21.3%, @20 58.4% | 41.6% / 19.1%, @20 49.4% | 34.8% / 18.0%, @20 42.7% |
| 4 single-hop (841) | 64.4% / 62.4%, @20 75.4% | 52.6% / 50.8%, @20 61.6% | 61.2% / 59.1%, @20 69.9% |
| **1-4 (1,531)** | **62.9% / 51.1%, @20 73.4%** | 51.3% / 40.4%, @20 61.9% | 56.6% / 46.6%, @20 65.3% |

## Predictions
- S1 (fused any@10 at least 62%): right, 62.9%.
- S2 (fused above both single modes on any@10 and all@10): right (62.9 vs 51.3 and 56.6; 51.1 vs 40.4 and 46.6).
- S3 (store's minilm within 3 points of bm-393's 56.3%): **wrong**, 51.3% (-5.0). The only differences are the row
  text ("Wren: text [shared caption]" here, 'Wren said, "text"' plus " and shared caption." in bm-393) and nothing
  else in the MiniLM path, so the row format costs MiniLM about 5 points; on multi-hop 48.4% vs 59.1%. Inferred,
  not tested separately. BM25 went the other way (56.6% vs 51.7%): here it indexes speaker names and uses the bare
  question instead of bm-390's query with the category-2 date hint.

## Decision (registered use)
S1 and S2 hold, so recall() keeps fused as its default. The S3 miss points at one more single change, the row
format, tested next as bm-393c before the store is fixed for ep-382's GPU test.

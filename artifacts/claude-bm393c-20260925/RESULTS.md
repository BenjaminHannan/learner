# bm-393c RESULTS: store version 2 on LoCoMo practice (after using LoCoMo for development)

Run 2026-09-25 ~19:45 UTC, cloud CPU, ~2 min, $0, sealed at main cd9048ccf. Self-test PASS. Counts only.
One change from bm-393b: rows ranked as '<speaker> said, "<text>"'.

| Categories 1-4 (1,531 questions) | fused | minilm | bm25 |
|---|---|---|---|
| any evidence in top 10 | **65.9%** (393b 62.9%) | 57.5% (393b 51.3%) | 57.0% (393b 56.6%) |
| all evidence in top 10 | 53.7% | 45.4% | 47.0% |
| any in top 20 | 75.3% | 69.0% | 65.3% |

Per category, fused any@10 (all@10): multi-hop 59.8% (13.5%), temporal 73.8% (67.2%), open-domain 40.4% (22.5%),
single-hop 67.7% (65.3%).

Predictions: C1 (minilm at least 54.3%) right, 57.5%. C2 (fused at least 64.0%) right, 65.9%.
Decision (registered use): version 2 (scripts/claude_ep382_store_v2.py, fused default) is the store for ep-382's GPU
test and month-end's join. No further retrieval changes are tried on LoCoMo before that test.

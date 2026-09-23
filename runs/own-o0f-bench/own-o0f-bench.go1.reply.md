Sealing a blind 2,500-world benchmark — first the rules and plan.
Plan §7 and rules read. Now checking the relation inventory for person-valued relations to build chains from.
Inventory confirmed (96 person-valued relations). Writing the sealed benchmark generator now — blind to all model code, fictional names only.
All green. Quick sub-count audit, then sealing.
**Verdict: PASS** — own-O0f sealed comparison benchmark built, verified, sealed. Stopping; the panel is TEST-ONLY and no model was run on it.

Marks table (integer counts):

| Mark | Bar | Got |
|---|---|---|
| Pown0f.1 500 worlds per family | 5 × 500 | 500 two_hop + 500 reversal + 500 abstention + 500 mquake_edit + 500 long_chain = 2500 worlds, 3000 questions |
| Pown0f.2 checker re-derives every gold | 0 mismatches | 0 mismatches / 3000; 0 ungrounded facts; 0 over-budget conversations |
| Pown0f.3 cross-family name-set independence | 0 shared | 0 shared name sets |

Every move / sub-count: abstention 167 untaught + 167 never-mentioned + 166 broken-chain; long_chain 250 × 3-hop + 250 × 4-hop; mquake_edit 500 chain + 500 unaffected; templates per family teach 49, ask 32 (bar ≥ 30 each); max conversation 605 chars ≈ 151 tokens (bar 900; per-family max 286/210/292/605/478). Misses: none. Deviations: none.

What it means (plain high-school English): there are now 2,500 locked fictional test worlds with known answers that later models can be fairly graded on.

What it doesn't mean: it says nothing about any model's score — no model was run, and the seal only stays fair if nobody trains on or edits these files. Sealed 7 files (`SEAL.sha256.txt` in `artifacts/claude-own-bench-20260923/`); ledger lines Pown0f.1–3 appended. PUSH paths for the watcher: `artifacts/claude-own-bench-20260923` `scripts/claude_own_o0f_bench.py` `artifacts/fable-predictions-ledger.md`.

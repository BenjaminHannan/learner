# own-O0f sealed comparison benchmark — RESULTS

**TEST-ONLY: ownbench-20260923.** This panel is TEST-ONLY from the moment it is
sealed. Never read it item by item, never tune on it, never quote it. It may be
run only where a task says so, once.

Verdict: **PASS** — all three marks met (counts below).

Generator (sealed, blind to all model code, CPU only):
`scripts/claude_own_o0f_bench.py` (`generate` writes, `verify` re-derives).
Relation names from `artifacts/claude-smolear257-20260922/relation_table_v2.json`
(96 person-valued relations). Fictional fantasy names only, globally unique.
Fresh wordings (no plan example reused); noise: lowercase, missing apostrophes,
missing "?" on questions.

## Marks table (integer counts)

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| Pown0f.1 500 independent worlds per family (two_hop, reversal, abstention, mquake_edit, long_chain) | 5 x 500 | 500, 500, 500, 500, 500 (2500 total; 3000 questions: mquake 2/world) | yes |
| Pown0f.2 rule-based checker re-derives every gold from the conversation facts | 0 mismatches | 0 mismatches over 3000 questions; 0 ungrounded facts; 0 over-budget conversations | yes |
| Pown0f.3 no world shares a name set with another family's world | 0 shared | 0 shared pairs (names globally unique by construction) | yes |

Detail counts: abstention subtypes untaught 167 / never-mentioned 167 / broken-chain
166; long_chain 250 x 3-hop + 250 x 4-hop; mquake_edit 500 main + 500 unaffected.
Templates per family: teach 49, ask 32 (bars: >= 30 each).
Token budget (900 tokens ~ 4 chars each, i.e. <= 3600 chars/conversation):
max chars per family two_hop 286, reversal 210, abstention 292, mquake_edit 605,
long_chain 478. **Max overall 605 chars ~ 151 tokens**, far under budget.

Moves: none (benchmark construction, no model run). Misses: none.
Deviations: none — generated and verified in one sitting, sealed, stopped.

## What it means (plain English)

We now have 2,500 fresh fictional test worlds, locked and hashed, that future
models can be graded against without ever having seen them during training.

## What it doesn't mean

It says nothing about how any model scores — no model was run here. A locked
test only stays fair if nobody trains on it or edits it after the seal.

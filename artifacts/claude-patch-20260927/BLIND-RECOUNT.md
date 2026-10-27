# Blind recount

UTC: 2026-09-28 05:40:48 UTC
Checks SHA-256: `095c48e649eb9035c7998f0c34897b500c9d63a9578dd5052d73b0601bf89b81`

**Shown:** Weight inventory and instantiated shapes agree. Patch 1,652,767; loop 1,645,726; plain 1,646,693. Patch is 0.428% from own loop.

**Shown:** 20 of 20 matrix gradients have a finite, positive norm in raw checks; inventory agrees. This audits the recorded gradient norms; it does not rerun backpropagation.

**Shown:** Independently graded raw panels:

- `artifacts/claude-patch-20260927/loop-927401/dev-raw.jsonl`: sums 300 of 300, grids 285 of 300, sorting 295 of 300, reversing 295 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/loop-927401/verify-raw.jsonl`: sums 300 of 300, grids 274 of 300, sorting 293 of 300, reversing 295 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/loop-927402/dev-raw.jsonl`: sums 298 of 300, grids 262 of 300, sorting 294 of 300, reversing 290 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/loop-927402/verify-raw.jsonl`: sums 298 of 300, grids 272 of 300, sorting 298 of 300, reversing 292 of 300, counting 299 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/loop_meta-927401/dev-raw.jsonl`: sums 300 of 300, grids 284 of 300, sorting 297 of 300, reversing 291 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/loop_meta-927401/verify-raw.jsonl`: sums 300 of 300, grids 282 of 300, sorting 297 of 300, reversing 292 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/loop_meta-927402/dev-raw.jsonl`: sums 300 of 300, grids 244 of 300, sorting 299 of 300, reversing 291 of 300, counting 297 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/loop_meta-927402/verify-raw.jsonl`: sums 300 of 300, grids 260 of 300, sorting 298 of 300, reversing 291 of 300, counting 297 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/patch-927401/dev-raw.jsonl`: sums 300 of 300, grids 281 of 300, sorting 293 of 300, reversing 291 of 300, counting 297 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/patch-927401/verify-raw.jsonl`: sums 300 of 300, grids 278 of 300, sorting 297 of 300, reversing 289 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/patch-927402/dev-raw.jsonl`: sums 300 of 300, grids 271 of 300, sorting 298 of 300, reversing 289 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/patch-927402/verify-raw.jsonl`: sums 300 of 300, grids 272 of 300, sorting 296 of 300, reversing 293 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/plain-927401/dev-raw.jsonl`: sums 297 of 300, grids 183 of 300, sorting 298 of 300, reversing 298 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/plain-927401/verify-raw.jsonl`: sums 295 of 300, grids 164 of 300, sorting 297 of 300, reversing 299 of 300, counting 299 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/plain-927402/dev-raw.jsonl`: sums 292 of 300, grids 166 of 300, sorting 299 of 300, reversing 299 of 300, counting 298 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/plain-927402/verify-raw.jsonl`: sums 292 of 300, grids 160 of 300, sorting 300 of 300, reversing 297 of 300, counting 299 of 300, brackets 300 of 300; PASS
- `artifacts/claude-patch-20260927/qualification/dev-raw.jsonl`: sums 300 of 300, grids 287 of 300, sorting 300 of 300, reversing 296 of 300, counting 300 of 300, brackets 300 of 300; PASS

**Shown:** Practice gate fail; patch comparisons use both loop and loop_meta with a maximum gap of 9 of 300.

**Untested:** Race outcome and sleep absorption require later raw records.

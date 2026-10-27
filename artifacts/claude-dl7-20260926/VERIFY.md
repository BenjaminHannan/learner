# dl-7b VERIFY (Fix-sleep thread, 2026-09-26T20:13:49Z)

**Registered verdict: FAIL** (F3 fails; F1, F2, F4, F5 pass; not INCONCLUSIVE; not proved wrong). A FAIL stays a FAIL.
Blind recount (separate agent, read-only, recomputed every night from harm_items vs base_harm_items and the per-night
TEST records before reading RESULTS-gpu.md) agrees with the builder's marks block on every marked number.

| arm/seed | lost per night 1-7 | TEST lucky per night 1-7 | reached n7 | gained n7 | KL n7 |
|---|---|---|---|---|---|
| S 12 | 4,3,6,12,8,11,11 | 122,142,146,200,235,329,273 | 58 | 47 | 0.153 |
| S 13 | 8,8,12,11,9,11,15 | 95,140,138,201,177,212,204 | 60 | 50 | 0.176 |
| F 12 | 0,7,4,5,8,8,3 | 101,110,145,184,207,200,179 | 52 | 14 | 0.018 |
| F 13 | 2,0,0,0,4,3,4 | 82,103,172,211,205,217,216 | 53 | 20 | 0.013 |

Base: L0 66, reached 35, greedy 2, panel right 200/300. Pool: asked 3000, questions 1479, answered 1282, shaky 427.
- F1 PASS: F lost 3+4 = 7 <= 13 (half of S's 11+15 = 26); each F seed below each S seed.
- F2 PASS: 0 of 14 F nights lost > 10 (the code's variable says "over_15" but tests > 10, the registered bar).
- F3 FAIL: F lucky 179 and 216 >= 132, but F's gain 263 < 276 (0.8 x S's gain 345), short by 13.
- F4 PASS: 0 of 14 F nights dropped > 15% (worst -10.5%). F5 PASS: reached 52, 53 >= 35.
- Proved wrong (F lost >= S on both seeds): no.

Addendum 1 premise check (report-only): 22 of S's 26 night-7 lost items (84.6%; unique items 16 of 19) sit in the
base's least-confident third of its right panel items (bar 60%). Premise SUPPORTED on fresh seeds: nights mostly knock
over the base's shaky facts.

One builder error, report-only: RESULTS-gpu.md says the training anchor KL ran 0.008-0.035; the JSON's
last_batch_anchor_kl runs 0.0093-0.1134 (four values above 0.035, two above 0.1). No mark uses it.

What it means (plain): replaying the base's shaky facts cut forgetting by about three quarters (26 -> 7) and kept 76%
of the learning (263 of 345). The bar was 80%, so it FAILS by 13 lucky guesses. Report-only comparison, not tested:
dl-6's lighter nights cut forgetting only by as much as they cut learning; the anchor's trade is better than that.
Cost: about $0.60 of the $1.00 (builder; one 5090 rental, destroyed).

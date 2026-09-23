# 107 — Reading behind the gate: what rung-2 ears actually read (Muse, diagnostic)

Exp 106 found rung-2 ears propose STATE frames on 276–306 of 400 real
Simple English Wikipedia sentences but execute nothing (gate 0.88–0.95).
This doc asks what those frames contain. Answer: mostly wrong readings
(~3% exact), ranked wrong-first by confidence — but wrong in a systematic,
namespace-shaped way.

## 1. Method (one paragraph)

Same frozen checkpoints (4701/4702/4703), same panel, same normaliser as
exp 106; the only change is dropping the gate: one `S47.decode` per
sentence/seed, and every `act == "STATE"` frame is scored against that
sentence's gold triple set as exact-correct / relation-right-span-wrong /
wrong-relation / invented (gold empty). Confidence is the decoder's own
min-of-softmaxes score. Per seed, never averaged. No threshold is fit,
moved, or certified; the exp-47 gate stands.

## 2. Findings

- **Mostly wrong, all seeds.** Exact: 9/11/10 of 276/306/288 raw STATE
  frames (3.3/3.6/3.5%). Wrong-relation is the biggest error bin
  (110/112/108), invented next (124/155/139 — 45/51/48% of raw STATE).
- **Confidence is inverted.** Correct frames peak at 0.50–0.59 (median
  ~0.17); wrong frames reach 0.68–0.73. The single highest-confidence
  frame is wrong in every seed, so the best achievable point is 0 correct
  at ≤ 1% wrong AND at ≤ 5% wrong. A lower gate buys wrong writes first.
- **The errors have a shape.** Proposed top relations: `unsure`
  (93/103/103 — the head's own abstention leaking into STATE frames),
  `country` (90/97/87), `country of citizenship` (20/22/23). Gold top:
  `located in…` (137), `occupation` (44). The ears map "X is a town in
  France" → `country`, "American writer" → `citizenship`: WebRED's
  relation namespace, not the panel's inventory. Spans are often right
  (28–33 rel-right-span-wrong per seed) while the relation label is off.
- **Not special subsets.** The 87 rung-1-unencodable sentences give
  2/4/4 exact of 68/70/71 STATE — the same mix, so rung-2's failure is
  not about "hard" sentences rung-1 can't even encode.
- **Seeds agree.** The top wrong frames are the same sentences in the
  same order across seeds (El Alamein, Saint-Paul-en-Jarez, Tom Whedon…).

## 3. What this suggests (not claims)

The head points at the right entities with the wrong relation words. That
pattern — right spans, systematically mismatched relations, plus `unsure`
leaking as a STATE relation — points at the training-label interface
(WebRED → our 8-relation-plus inventory mapping) rather than at span
perception. Any future rung-3 attempt should first fix the relation
namespace (closed-list mapping / label audit on real sentences) before
touching thresholds: no threshold can sort a list whose top is wrong.

## 4. Limits

Single-frame-per-sentence scoring; direction ignored; missing object → "";
`relation-right` is string equality on normalised relations, so near-miss
wordings count as wrong-relation. The ≤1%/≤5% sweep is descriptive.

## 5. Reproduce

`scripts/fable_read107_behind_gate.py --snapshot <scibert-snapshot> --out
artifacts/fable-read107-20260921/fable_read107_results.json` (Mac CPU,
OMP=1, ~40 s). Sealed PASSMARKS + SEAL.sha256.txt in that folder.

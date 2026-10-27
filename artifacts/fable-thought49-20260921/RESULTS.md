# RESULTS — fable-thought49-20260921 (thought format v2)

Agent 2 of 7, parallel build brief 48. Plain software only: no models, no training, no GPU, no installs, no commits. Files added (prefix `fable_thought49_`): `scripts/fable_thought49_schema.py`, `scripts/fable_thought49_notebook.py`, `scripts/fable_thought49_conformance.py`; doc `design/v3/30-modes/49-thought-format-v2-opus.md` (≤1,500 words). Existing files untouched — verified by the control run below. All three of Ben's questions (2026-09-21) were answered "go with yours" and are implemented and tested (§ Rulings).

## Marks (integer counts)

| mark | what ran | result | bar |
|---|---|---|---|
| W-CONTRACT | contract lifecycle suite through the v2 wrapper | 32 / 32 pass | all pass |
| CONTROL | contract lifecycle suite through the unmodified `Notebook` | 32 / 32 pass | all pass |
| NAIVE-CONTRACT | contract suite through last-write-wins dict | 28 / 32 fail | ≥ 15 fail |
| W-V2 | 33 new v2 sequences through the wrapper | 33 / 33 pass | all pass |
| NAIVE-V2 | same 33 sequences through naive v2 dict | 20 / 33 fail | ≥ 15 fail |
| SELFTEST | all five marks above in one command | **PASS** | PASS |

Naive-v2 failures (20): n09 restart, n11 paper-never-answers, n12/n13 promote rules + qualifier gate, n14/n15 two-papers-both-kept, n16 taught-beats-paper, n17 CONFLICT, n18 supersede-keeps-old, n22 degraded native rows, n23 tamper, n24 AMBIGUOUS, n25 quarantine gates, n26 idempotence, n27 inferred-vs-taught, n28 chain-survives-restart, n30 proposed-paper-promote, n31 qualifier gate, n32 loser-mark, n33 relation-id suggest. Naive-v2 passes (13): pure schema/adapter sequences (n01–n08, n10, n19–n21, n29) — a foil can carry one row in memory; it cannot carry history, gates, marks, or restarts.

Coverage of the brief's required themes: numbers n01–n03/n17–n19/n27; qualifiers n08–n10/n29/n31; two papers conflicting — both kept, neither promoted n14, one promoted keeps the other n15; "claimed by paper never answers as fact until promoted" n11→n12 and n30.

## Rulings adopted (Ben, "go with yours")

1. **Qualified rows never answer bare questions.** `ask(name, relations, qualifiers=dict|list|None)` drops qualified rows whose conditions the question doesn't match; empty hop → `MISSING_FACT, reason=qualified`. Unqualified rows unchanged (contract's 32 sequences still 32/32). Tests: n12, n31.
2. **Mark the promotion loser.** Successful promote appends a `THOUGHT_MARK` event (`superseded-by-promotion`, `by=<taught fid>`) on each different-valued active paper/web claim for the same subject+relation; same-value claims unmarked; row never deleted; mark survives restart. Unknown event kind passes through the contract's hash chain untouched. Tests: n32.
3. **Suggest relation ids, keep raw.** `suggest_relation_id()` = exact normalized match against WebRED's 521 names; explicit ids win; no match → None; raw string always stored, asked, and projected. No semantic mapping (never guesses). Tests: n33.

## Hand-map (doc §5–6)

| set | clean | needs qualifier | cannot represent | total |
|---|---|---|---|---|
| WebRED dev (real rows, line-numbered) | 11 | 6 | 13 | 30 |
| arXiv abstract sentences (API, 2026-09-21) | 6 | 10 | 4 | 20 |
| **total** | **17** | **16** | **17** | **50** |

Representable (clean+qualifier): **33 / 50**. Not representable: **17 / 50** (12 WebRED negatives where the label is not stated — ears must NO_FACT; 4 arXiv link/metadata or multi-claim sentences needing a split).

Reproduce exactly:

```
uv run --offline --no-project --python 3.12 python -B scripts/fable_thought49_conformance.py --selftest
```

## What it means

- A paper sentence with an open relation, a number+unit, conditions, and a non-believed source now has a real row: it stores, restarts, survives tamper checks inside the same hash-chained `events.jsonl`, and its provenance says who claimed it and which sentence it came from.
- Every existing module keeps working unchanged: the wrapper passes all 32 contract lifecycle sequences; `to_v1()`/`from_v1()` round-trip exactly when the embedded record is present (n21).
- Ben's abstain rule holds end to end: conditioned claims never answer a bare question (n12/n31); two disagreeing papers both persist, neither answers, promotion is the only path and it visibly marks the loser without deleting it (n14/n15/n32); a taught fact still beats any paper (n16/n17/n27); relation ids help grouping without ever rewriting what was said (n33).
- Both naive last-write-wins dictionaries fail both suites, so these tests are testing something.

## What it does not mean

- It does not mean papers are "understood": fit labels are one reader's hand-mapping of 50 sentences, not an agreement statistic, and no ears/encoder was involved.
- Qualifier matching is exact (string/number/bool equality), not semantic — a differently-worded question abstains rather than guesses, per the contract.
- Confidence is recorded, not calibrated. `None` means "not recorded", never a guessed number.
- Marks are wrapper view-metadata, not contract state; the contract's own reads ignore `THOUGHT_MARK`.
- It does not change the contract: no file other than the three new scripts and the two docs was written.

## Deviations from plan

1. The contract suite has **32** sequences (c31–c32 exist); the brief said 30. All 32 run through the wrapper — no cases skipped.
2. `ask()` and `promote()` are re-expressed inside the wrapper (qualifier gate; loser marks; promoted rows keep typed value + qualifiers) rather than delegated; refusal rules, statuses, details and hop limits match the contract, and the contract file was not edited. `THOUGHT_MARK` is a new event kind the contract passes through unexamined.
3. Papers/documents without a URL mirror to v1 as `proposed`, not `web-quarantine` (contract demands a URL; a paper id is not a URL). Both never answer, both promote identically.
4. Naive v2 foil passes 13 adapter-level cases by design (threshold counts storage/gate semantics, which it fails 20 times).
5. No PASSMARKS/seed ledger: no registered model run — deterministic software conformance.

## Questions for Ben

None open — all three original questions answered and implemented above.

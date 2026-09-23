# 49 — Thought format v2

Status: built, conformance-tested; plain software, no model. Prefix `fable_thought49_`; files `scripts/fable_thought49_{schema,notebook,conformance}.py`; artifacts `artifacts/fable-thought49-20260921/`. Three Ben rulings adopted (§8).

## 1. Problem

Notebook holds person–relation–person over 8 relations. "Method X improves accuracy on Y by 12% when Z" has an open relation, a number+unit, and two conditions — nowhere to put it. v2 widens the row; contract guarantees unchanged.

## 2. The v2 row (`ThoughtV2`)

| field | type | note |
|---|---|---|
| subject | `E####` | stable id; names stay aliases |
| relation | open string | raw string, never rewritten |
| relation_id | optional string | suggested: exact match vs WebRED's 521 names |
| value | entity \| number+unit \| date \| text \| boolean | date = `YYYY[-MM[-DD]]`; one kind per row |
| qualifiers | list of (open relation, typed value) | "when Z", "on dataset Y" |
| provenance | document (id/URL), sentence, claimed_by, url, promoted_from | claimed_by ∈ `taught` \| `paper:P` \| `web-quarantine` \| `system:<source>` |
| confidence | 0–1 or None | None = not recorded (legacy); never guessed |
| source | v1 tag, unchanged | only taught/inferred/sleep-derived/web-verified answer |
| mark, marked_by | optional strings | view marks from append-only THOUGHT_MARK events |
| rule_id, deps | inferred only | contract requirement |

Construction validates structure (kind fit, date format, confidence range); `validate(strict=True)` adds contract rules at write.

## 3. Guarantees kept

| v1 guarantee | how v2 keeps it |
|---|---|
| append-only hash chain | one log: v2 rows embedded under `provenance.thought_v2`; chain, fsync, torn tail, tamper detection inherited |
| stable ids + aliases | subject is `E####`; `ensure_entity` reuses a match, returns AMBIGUOUS on collision, never merges |
| source tags | `source` unchanged; `claimed_by` added |
| supersede not delete | same contract path; corrections supersede, old row stays |
| inferences never overwrite taught | unchanged source priority |
| AMBIGUOUS never guesses | load never re-parses a literal — degrade to text, `confidence=None` |
| web/paper never answers pre-promotion | paper→`web-quarantine` (URL) or `proposed` (no URL); outside ANSWERING_SOURCES; only Ben's `promote()` writes taught |

## 4. Storage, adapters, wrapper

`to_v1()` returns a legal `assert_fact()` payload (subject, relation, bare value, source, provenance, url, quoted_span, claimed_by, confidence, embedded `thought_v2`). Lossy: **qualifiers are not projected**. `from_v1(fact)` is exact with the embed, degraded otherwise (text value, no qualifiers, `confidence=None` — never guessed).

`ThoughtNotebook` wraps contract `Notebook` by composition (no edit): `add_thought`, `get_thought`, `thoughts_for`, `ensure_entity`; all else delegates **except `ask()` and `promote()`**, re-expressed by the wrapper — same statuses/details/hops, contract file untouched:

- **Ask gate (ruling 1).** Drops qualified rows whose conditions the question doesn't match; empty hop → `MISSING_FACT, reason=qualified`. Bare question + qualified fact never answers. Question side: `ask(name, relations, qualifiers=dict|list|None)`.
- **Promote marks (ruling 2).** After promotion, each different-valued active paper/web claim for the same subject+relation gets a `THOUGHT_MARK` event: `superseded-by-promotion`, `by=<taught fid>`. Unknown kind passes the contract's chain untouched; marked row stays, never deleted. Same-value claims unmarked.
- **Relation ids (ruling 3).** `add_thought` suggests `relation_id` on exact match vs WebRED's 521 names; explicit ids win; no match → None. Raw string always stored, used by `ask()`, returned by `to_v1()`.

| claimed_by | URL | mirrored as | actor |
|---|---|---|---|
| taught | — | taught | listening |
| paper:P / web-quarantine | yes | web-quarantine | thinking |
| paper:P / web-quarantine | no | proposed | thinking |

WebRED frames carry no row URL and a paper id is not a URL; no-URL forms never answer, both promote identically.

## 5. WebRED dev hand-map (30)

All rows: claimer `web-quarantine`, source `proposed`, doc `webred:dev:<line>`. Fit: **C** clean, **Q** needs qualifier(s), **N** cannot represent (ears must NO_FACT).

| # | line | fit | v2 row |
|---|---|---|---|
| 1 | 3602 | C | father: Heather Bresch→E(Joe Manchin) |
| 2 | 2533 | C | child: Joe Manchin→E(Heather Bresch) |
| 3 | 2709 | C | spouse: Martha Jefferson→E(Thomas Jefferson) |
| 4 | 516 | C | employer: Barry Lee Myers→E(AccuWeather) |
| 5 | 2020 | C | place of birth: Steve Riggs→t"Louisville" |
| 6 | 338 | Q | educated at: Saraju Mohanty→E(USF), Q(degree=PhD, year=2003) |
| 7 | 1848 | C | sibling: Joel Myers→E(Barry Lee Myers) |
| 8 | 2215 | C | date of birth: Dean Hopkins→d"1959-06-06" |
| 9 | 909 | C | capital of: Panjim→E(Goa) |
| 10 | 150 | Q | member of sports team: Brad Stevens→E(Celtics), Q(role=coach) |
| 11 | 3287 | Q | founded by: PCRM→E(Barnard), Q(role=founding president) |
| 12 | 658 | Q | diplomatic: USA→E(Soviet Union), Q(event=U-2 swap, date=1962-02-10) |
| 13 | 2887 | N | maintained by: citation fragment only |
| 14 | 1243 | Q | official language: Quebec→t"French", Q(jurisdiction, law=Bill 101) |
| 15 | 70 | Q | owner of: Wikimedia→E(Wikipedia), Q(claim=trademark) |
| 16 | 3806 | C | inception: Global Times→d"1993" |
| 17 | 1442 | C | place of birth: Cyndee Peters→t"Granite Falls" |
| 18 | 3755 | C | date of death: Wayne Estes→d"1965-02-08" |
| 19 | 2136 | N | citizenship: not stated (name clash) |
| 20 | 1989 | N | contains: not stated (works in Texas) |
| 21 | 1155 | N | HQ: title fragment |
| 22 | 592 | N | border: sales-tax text |
| 23 | 1027 | N | capital: club-membership text |
| 24 | 851 | N | country: holiday quote |
| 25 | 1107 | N | HQ: publisher byline only |
| 26 | 1470 | N | diplomatic: economics tables |
| 27 | 3573 | N | capital: fort location only |
| 28 | 439 | N | border: survey percentages |
| 29 | 3382 | N | border: geology text |
| 30 | 2510 | N | diplomatic: chart legend |

## 6. arXiv abstract hand-map (20)

All rows: claimer `paper:<id>`, source `web-quarantine`, doc `https://arxiv.org/abs/<id>`, confidence 0.5–0.8 until promoted. Fetched via arXiv API 2026-09-21.

| # | arXiv | fit | v2 row |
|---|---|---|---|
| 1 | 2511.20102 | C | introduces: SSA, training framework (sparse+full attention) |
| 2 | 2508.02124 | C | introduces: trainable dynamic mask sparse attention |
| 3 | 2605.24518 | C | is bottleneck for: self-attention complexity→t"long sequences" |
| 4 | 2605.24518 | C | introduces: Grammatically-Guided Sparse Attention |
| 5 | 2508.02124 | C | proposes: community→t"sparse attention" |
| 6 | 2508.02124 | C | obstructs gradients: mask+sparse weights→b"false" |
| 7 | 2506.04108 | Q | delivers speedup: ReSA→n"2.42 x", Q(when=decoding, at=256K, hedge=up to) |
| 8 | 2605.24518 | Q | accuracy: hard→n"0.82", soft→n"0.8165" (2 rows), Q(task=SST-2) |
| 9 | 2502.11089 | Q | speedup: NSA→t"substantial", Q(vs=Full Attention, len=64k, phases) |
| 10 | 2502.11089 | Q | maintains-or-exceeds: NSA→E(Full Attention), Q(ref=Figure 1) |
| 11 | 2505.00315 | Q | reduces complexity: MoSA→t"O(k²+T)", Q(from=O(T²)) |
| 12 | 2508.02124 | Q | Pareto advantage: DMA→b"true", Q(over=sparse baselines, hedge=up to 10x) |
| 13 | 2106.01087 | Q | increases interpretability: sparse attention→b"true", Q(status=hearsay) |
| 14 | 2505.00315 | Q | leads to efficiency: content sparsity→t"more efficient attention", Q(status=hypothesis) |
| 15 | 2502.11089 | Q | offers direction: sparse attention→t"promising", Q(hedge=promising) |
| 16 | 2505.00315 | Q | suffers inferior performance: subquadratic→t"in practice", Q(comparator=unstated) |
| 17 | 2511.20102 | N | SSA sota+adapts+superior: needs sentence split |
| 18 | 2508.02124 | N | "three key innovations" list — one row cannot hold it |
| 19 | 2506.04108 | N | "Code is available at https://…" — metadata, not a fact |
| 20 | 2508.02124 | N | "kernel open-source at https://…" — metadata |

## 7. Honest scope

Counts: WebRED 11 C / 6 Q / 13 N; arXiv 6 C / 10 Q / 4 N. **33/50 representable, 17/50 not.** "Cannot" = no faithful single row (label absent, link/metadata, multi-claim needing a split); ears must NO_FACT or split first.

Does not mean: confidence recorded ≠ calibrated. Fit labels are one reader's judgement. Marks are view metadata, not contract state — the contract's own reads ignore them.

Deviations: contract suite has 32 cases (brief said 30); all pass through wrapper. Naive v2 foil fails 20/33 (threshold 15); 13 pure-adapter cases pass on the foil by design. `ask()`/`promote()` re-expressed in wrapper (contract untouched); `THOUGHT_MARK` passes through unexamined. Papers without URLs mirror as `proposed`. No PASSMARKS — no registered model run.

## 8. Rulings adopted (Ben, 2026-09-21)

1. **Qualified rows never answer bare questions** — matching qualifiers required, else `MISSING_FACT`. Ask gate; tested n12, n31.
2. **Mark the promotion loser** — `superseded-by-promotion`, append-only, never delete; same-value unmarked. Tested n32.
3. **Suggest relation ids, keep raw** — exact WebRED match only, explicit ids win, no semantic mapping. Tested n33.

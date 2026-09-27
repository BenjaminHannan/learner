# novelty-19 data side — independent adversarial audit

**Auditor:** independent agent, read-only on all pre-existing files. Nothing outside
`artifacts/fable-novelty19-replay-20260920/audit/` was created or modified. No commits.
No `test.pt` was loaded. Registered seeds 1900/1901/1902 were **not** run; all stream /
memory / buffer evidence comes from disposable seed **9991**.

**Date:** 2026-09-20 · **Python:** CPython 3.12.14 (macos-aarch64) · **torch:** 2.14.0 ·
`OMP_NUM_THREADS=1`

**Files under audit**

| file | sha256 | note |
| --- | --- | --- |
| `scripts/fable_novelty19_data.py` | `66eef57ca3c75696d2fc91d559a4374232e6180ee35a27c30479ca0280bd8bcb` | **matches the expected `66eef57c` prefix** |
| `tests/test_fable_novelty19_data.py` | `9cfccf3cf2a032c8753042410fbc0f8cebe025442cf60f384f1c8b71e95cb430` | read, **not** trusted; all checks below are my own |
| `design/v3/19-…-preregistration-draft.md` | — | the authority |
| frozen operator `astra_canonical_operator_seed-1/final.pt` | `e7e5b6f3a6bfecf3890538bd0a14af7f5189b1565329e5cf411b52dd4d4dfbec` | **matches the value the spec quotes** (§2) |

**My instruments** (all in this folder, all re-runnable)

| script | what it does |
| --- | --- |
| `independent_checks.py` | decodes the on-disk blocks **itself** (own `rows`/`row_count`/`question` parser, own op-string parser, own 6×6 recount). It never calls the builder's `decode_block`, `op_names`, `composite_r10`, `generation_gate` or `r10_exposure`. Frozen project code used only for grammar/interpreter (`V3.interpret`, `V1.walk`, `A.visible_signature`, `CP.world_signature`). |
| `adversarial_probes.py` | forces every guard and lockout to fire or fail. |
| `world_overlap.py` | world-signature-level disjointness (the spec asks for worlds; the builder only checks questions). |
| `operator_history.py` | reconstructs the frozen operator's **entire** historical training corpus without model forwards, and intersects it with everything. |

Outputs: `independent-checks-9991.json`, `adversarial-probes.json`, `world-overlap.json`,
`operator-history.json`.

---

## Verdict table

| # | Item | Verdict |
| --- | --- | --- |
| 1a | No composite relation-10 question in awake / memory / R / G / U | **PASS** |
| 1b | No `(c=4 or 5, r=10)` in any buffer | **PASS** |
| 1c | Dev N/E cells excluded from all training material by question **type** | **PASS** |
| 1d | Dev N/E cells excluded by **world signature** | **PASS (measured), but never enforced in code** |
| 1e | Dev panels disjoint from the legacy exclusion union | **PASS** |
| 1f | Frozen operator's historical training signatures absent from the union | **PASS in fact — and now cheaply closable (21 s).** Was "disclose as unverified"; no longer necessary. |
| 1g | Confirmation panels exclude training / candidate-generation / replay **worlds** | **FAIL — must fix** |
| 1h | `audit` subcommand reports `passed: true` with the leakage checks silently absent | **FAIL — must fix** |
| 2a | 6×6 counts come only from awake strings, no smoothing | **PASS** |
| 2b | `P(LINK→LINK)≈1/3`, `P(BOS→LINK)≈2/3`, `P(LINK→10)=0` | **PASS** |
| 2c | G's accepted length distribution matches what the counts imply | **PASS** (expected ≈ 207 `c=4` / ≈ 69 `c=5`; the "200 / 65" figure in the brief is slightly low) |
| 2d | Labels come only from the interpreter, never a model | **PASS** |
| 3 | Arm fairness: identical world bytes/order/sizes, one shared offline order, U uniform with the r=10 exclusion, fallbacks counted | **PASS** |
| 4 | Generation gate — "≥16 distinct questions" | **AMBIGUOUS — needs a ruling.** Reading A passes with 2.3× margin; reading B fails on 2 of 4 structures and is near-impossible to pass. |
| 5a | Stratification `12 + index % 16` cannot leak the answer to a model | **PASS** |
| 5b | Answer balance / chance level per cell | **PASS** (16 values × exactly 4 units; chance 4/64 = 6.25 %) |
| 5c | Distinct-people rule, pair-cell edit rules, L cells `c=6..8` in 16-person worlds | **PASS** |
| 6a | Same seed twice → identical bytes; chunked == unchunked; resume == uninterrupted | **PASS** |
| 6b | What is not portable across machines | **PASS with flags** (torch serialization, CPython version, `runtime.local.json`, timestamps in every manifest) |
| 7 | Judgment calls and the `registered_cells()` `V3.CELLS` mutation | **PASS** (exception-safe, collision-guarded, no legacy behaviour change) — with one fragility note |
| 8 | Confirmation lockout | **AMBIGUOUS / weak — must fix** |

---

## 1 — Leakage

### 1a / 1b — composite relation-10

My own parser re-derives every operation string from the raw `question` tensor
(`question[2:-1]`, entity names stripped), never from the builder's `ops` field.

Awake stream, seed 9991, 100 updates = 1,600 worlds / 6,400 questions:

```
types: {"8":730, "9":637, "10":709, "LINK 8":1072, "LINK 9":1060,
        "LINK LINK 8":1117, "LINK LINK 9":1075}
malformed: 0   composite_r10_count: 0   c45_r10_count: 0
```

Memory (1,024 worlds / 4,096 questions) and all three buffers (4,096 questions each):
`composite_r10_count = 0`, `c45_r10_count = 0`, `malformed = 0`. Full cell histograms in
`independent-checks-9991.json → buffers.census`.

Structurally this is guaranteed, not lucky: the empirical table has
`LINK→10 = 0` and `10→10 = 0`, so `propose_string` cannot reach a composite 10 at all;
and `uniform_string` hard-codes 8/9 for `c≥2`. The only `r=10` in any buffer is `c=1`
(G: 445, U: 265, R: 450), which §5 explicitly permits.

**The guard is therefore never exercised in the registered run.** I forced it. With a
poisoned count table (`LINK→10 = 70`), `propose_string` happily emits
`LINK 10`, `LINK LINK 10`, `LINK LINK LINK 10`, `LINK LINK LINK LINK 10` — 3,964 of
4,000 valid draws. `propose_for_world` then rejects all of them
(`rejected_reasons: {"composite_r10": 62}`), accepts zero, and falls back to awake
questions. The quarantine lives one level above the sampler and it works.

I also forced the buffer-side collision abort: seeding the exclusion union with a real
memory question's signature produces
`RuntimeError: buffer-R world 0 slot 0 collides with the exclusion union; run invalid`.
And `B1.training_items` raises `RuntimeError: training/panel semantic overlap; run
invalid` on a forbidden collision — it does not skip.

### 1c / 1d — dev N/E cells excluded by type and by world signature

*By type:* N is `(c=4/5, r=10)`, E is `(c=5, r=10)` pairs. No composite-10 string exists
anywhere in awake, memory or any buffer (above), so the type exclusion holds globally
across entity names and worlds — not as a hash exclusion.

*By world signature:* the builder never checks this. I did, computing
`CP.world_signature` myself from each artifact's visible rows (`world_overlap.json`):

```
dev-panel worlds 2240   awake worlds 1600   memory worlds 1024   buffer worlds 1024 each
dev ∩ awake = 0    dev ∩ memory = 0    dev ∩ buffer-{R,G,U} = 0
memory ⊆ awake = true    buffer worlds == memory worlds (all three arms) = true
```

Question-level: `dev ∩ awake = 0`, `dev ∩ buffers = 0`.

Note the awake stream here was built **without** `--dev-panels`, so this zero is the
natural base rate, not the effect of the abort. Good news for the design; see 1h for the
operational risk.

### 1e — legacy union

`build_exclusion_union()` = 26,880 signatures from the five registered sources
(sha256 `5a51fd4b08a502dd568972c27dbebe24e4c92f3c5ee43509febbfcbb9db90955`). All five
files exist; a missing one aborts. Dev-panel overlap with the union: **0**.

The superseded `fable-dispatcher-pilot-20260920` panels (640 signatures) are deliberately
excluded from the union. I measured their overlap with the dev panels, the awake stream
and the buffers: **0, 0, 0**. Harmless in practice; add `--extra-exclusion` if the owner
wants belt-and-braces.

### 1f — the frozen operator's historical training signatures

The builder says these are not in the union. That was true, and §7 says to disclose it as
unverified if provenance cannot be recovered. **It can be recovered, and it costs 21
seconds.** Provenance, from `scripts/astra_canonical_operator_run.py:worker` and
`…_seed-1/training.json`:

* one sequential stream, `rng = random.Random(1101)`, independent of the model seed
* 6,000 updates × `A.training_batch(rng, 16, forbidden)`
* each batch = 16 × `toy_ladder.visit(spec, rng, training=True)` then `rng.randrange(1<<30)`
* `training.json`: `canonical_records 576000 = 6000·16·6`, `monolithic_records 192000`

I verified my cheap replay consumes the RNG identically (`rng.getstate()` hashes equal
after 40 updates against the real `A.training_batch` path), then ran the full 6,000:

```
distinct_training_worlds               96000
distinct_training_question_signatures 732586
world_union_sha256  0730f99e6e627fa00db03cef5919b814599dfacb3a299a8ded440d28f0dc900a
seconds 20.7   (no model forwards)

overlap with the 32×64 development panels : worlds 0, questions 0
overlap with awake/memory/R/G/U (seed 9991): worlds 0, questions 0
```

**How much it matters:** the confound is real for D but only world-level. During native
scoring D calls the frozen operator with one-call questions
(`[QUESTION, p, LINK, ANSWER]`, `[QUESTION, p, 10, ANSWER]`) — exactly the operator's
canonical training shape. A panel world that appeared in operator training would mean the
operator had memorised those facts. Question-level collision is structurally impossible
for N/E/P/L (their questions are 7–10 tokens; the operator only ever saw 4- and 5-token
questions), so the world check is the one that matters — and it is zero.

**Important:** the dev panels are **seed-free** (`astra-novelty19-dev-v1:<cell>:<unit>:<attempt>`),
and I confirmed rebuilds are byte-identical. So this zero is a **definitive result for the
registered panels**, not a rehearsal. What remains is the 21-second rerun against the three
registered awake streams and, later, the confirmation panels.

### 1g — confirmation panels do not exclude training / replay worlds — **FAIL**

`build_dev_panels(confirmation=True)` builds its exclusion set from
`legacy_exclusion_paths(extra_exclusion)` only. It does **not** include:

* the new development panels (unless someone remembers `--extra-exclusion`),
* the awake stream, the replay memory, or the R/G/U buffers — **for which no
  `forbidden-semantics.json` is ever written**. `awake_signatures()` exists as a function
  but nothing persists its output.

§7 requires: *"Exclude all training, candidate-generation and replay worlds, not merely
accepted training questions."* That is a **world-level** requirement, and nothing in the
code does world-level exclusion anywhere — `dev_unit` only tests `V3.unit_signatures`
(question-level `visible_signature` / `tensor_signature`).

### 1h — the `audit` subcommand under-reports — **FAIL**

`--dev-panels` is optional on `awake-stream`, `buffers` **and** `audit`. Run without it,
the audit silently drops six checks and still prints `"passed": true`:

```
with    --dev-panels : 23 checks, passed true
without --dev-panels : 17 checks, passed true
missing: awake_disjoint_from_dev_panels, memory_disjoint_from_dev_panels,
         buffers_disjoint_from_dev_panels, dev_panel_hashes,
         dev_panel_cell_count, dev_panel_answer_stratification
```

A green audit therefore does not mean leakage was checked. Likewise, omitting
`--dev-panels` on `awake-stream`/`buffers` removes the collision abort entirely.

---

## 2 — Generator fidelity

### 2a — counts come only from awake strings, unsmoothed

I recomputed the 6×6 table from the memory block's raw `question` tensors, with my own
BOS/EOS framing, and compared to `transition-counts.json`:

```
counts_match_my_recount            : true
counts_are_integers                : true   (no smoothing, no pseudocounts)
no_smoothing_total_matches         : true   (Σcounts = Σ(len(ops)+1) = 12366)
memory questions ⊆ awake stream    : true
distinct world signatures          : 1024 / 1024
```

Recomputed table, rows `BOS, LINK, 8, 9, 10, EOS`:

```
BOS  [   0, 2781,  454,  411,  450,    0]
LINK [   0, 1393, 1418, 1363,    0,    0]
8    [   0,    0,    0,    0,    0, 1872]
9    [   0,    0,    0,    0,    0, 1774]
10   [   0,    0,    0,    0,    0,  450]
EOS  [   0,    0,    0,    0,    0,    0]     <- the only empty row; terminates generation
```

Nonzero edges: `BOS→{LINK,8,9,10}`, `LINK→{LINK,8,9}`, `{8,9,10}→EOS`. Every nonzero edge
is traced to a specific awake question by the builder, and the builder raises if any edge
lacks a trace.

### 2b — the three probabilities

```
P(BOS→LINK)  = 0.678955   (≈ 2/3 ✓)
P(LINK→LINK) = 0.333733   (≈ 1/3 ✓)
P(LINK→10)   = 0.000000   (exactly 0 ✓)
P(LINK→8)    = 0.339722   P(LINK→9) = 0.326545
P(BOS→10)    = 0.109863   P(10→EOS) = 1.0
```

### 2c — accepted length distribution vs. what the counts imply

I derived the accept probability per `(c, r)` analytically from the counts, applying the
spec's rules myself (start at BOS, at most 7 draws after BOS, reject `>5` calls,
LINK-terminated, or empty; never repair):

| cell | expected (iid, given accept) | observed in buffer-G |
| --- | --- | --- |
| c=1 | 1316.2 | 1299 |
| c=2 | 1854.7 | 1847 |
| c=3 | 619.0 | 652 |
| **c=4** | **206.5** | **221** |
| **c=5** | **69.0** | **77** |

Rejected probability mass 0.000938. Both `c=4` and `c=5` sit at ≈ +1.0 binomial SD
(σ ≈ 14 and 8.2). To rule out a systematic bias from the duplicate-signature rule
(which runs *before* the quota check and so preferentially discards short, low-variety
strings), I re-ran the same RNG streams with duplicate rejection disabled and also drew a
pure iid sample:

```
actual buffer-G (dup rejection ON) : c1 1299  c2 1847  c3 652  c4 221  c5 77
same streams,   dup rejection OFF  : c1 1274  c2 1904  c3 633  c4 212  c5 73
pure iid sample of 4096 valid draws: c1 1304  c2 1854  c3 630  c4 217  c5 65
```

The duplicate rule moves `c=4` by ≈ 9 and `c=5` by ≈ 4 — real but immaterial. **PASS.**

*Correction to the brief:* the expected counts are ≈ **207** `c=4` and ≈ **69** `c=5`, not
200 / 65. The 200 / 65 figures come from `p·4096` without renormalising by the acceptance
probability.

The builder's own rejection accounting for G (65,536 candidates) is consistent:
`too_many_calls 360`, `overrun 199`, `duplicate_signature 6384`, `after_quota_filled 54497`,
`fallbacks 0`. Rejected types are `LINK×5 {8,9}`, `LINK×6 {8,9}`, `LINK×7` — thrown away
whole, never truncated. `max candidate index actually used = 6`, i.e. the 64-attempt
budget is nowhere near strained.

### 2d — labels

`make_buffer_item` → `label_question` runs `V3.interpret` **and** `V1.walk` and raises if
they disagree. I relabelled all 12,288 buffer questions myself with both interpreters and
compared to the stored `answer`, `people`, `ops`, `chain_result`:

```
R: answer_mismatches 0, chain_mismatches 0
G: answer_mismatches 0, chain_mismatches 0
U: answer_mismatches 0, chain_mismatches 0
```

No model is consulted anywhere in the data path.

---

## 3 — Arm fairness — **PASS**

Compared the three `buffer-*.pt` files tensor-by-tensor:

```
rows / row_count / owner / world_signature identical  R vs G : true, true, true, true
                                                       R vs U : true, true, true, true
namespaces identical                                   true (both)
sizes                                                  R 4096, G 4096, U 4096
each arm's stories == the memory worlds                true, true, true
one shared offline-order.json                          2000 updates × 16 visits
offline order reproducible from the namespace          true (I regenerated it)
```

U's curriculum, decoded from its questions (not from its config):

```
c histogram : 1→811, 2→816, 3→815, 4→844, 5→810      (uniform over 1..5 ✓)
r=10 at c≥2 : 0                                      (same exclusion ✓)
c=1 split   : r8 283, r9 263, r10 265                (all three at one call ✓)
```

Fallbacks: R 0, G 0, U 0, all counted and logged (`fallback_log`, `fallback_types`). G's
fallback path is exercised and correct under the poisoned-counts probe (4 fallbacks, drawn
from that world's own awake questions in source order).

---

## 4 — Generation gate — **AMBIGUOUS, needs the design owner's ruling**

§5: *"G must produce and accept at least 16 distinct questions in at least 16 distinct
worlds for each of the four structures."*

The builder reads "distinct question" as a distinct `(world, question)` instance
(**reading A**), and says so in a comment. The alternative is distinct raw question token
sequences (**reading B**). Both, on disposable seed 9991:

| structure | A: `(world, question)` instances | B: distinct raw questions | distinct worlds | A | B |
| --- | --- | --- | --- | --- | --- |
| c=4, r=8 | 118 | 16 | 113 | pass | pass |
| c=4, r=9 | 103 | 16 | 96 | pass | pass |
| **c=5, r=8** | 37 | **15** | 37 | pass | **FAIL** |
| **c=5, r=9** | 40 | **15** | 38 | pass | **FAIL** |

All four have `awake_instances = 0`, confirmed against the entity-stripped awake corpus.

**Why reading B is not a counting test but a coverage test.** A question of structure
`(c, r)` is `[QUESTION, person, LINK×(c-1), r, ANSWER]` — the only free token is the
subject, and there are exactly 16 entity IDs. So "≥16 distinct raw questions" means
"every one of the 16 entity IDs must be bound at least once", and 16 is the ceiling, not a
floor with headroom.

Binding is marginally uniform over the 16 IDs (`bind.choice(sorted world people)`, the 6
people being a uniform 6-subset of 16). Coupon-collector for the observed instance counts:

```
n =  37  P(all 16 bound) = 0.170   E[missing] = 1.47
n =  40  P(all 16 bound) = 0.243   E[missing] = 1.21
n = 103  P(all 16 bound) = 0.979
n = 118  P(all 16 bound) = 0.992
P(all four structures cover all 16, one seed) ≈ 0.040
P(3/3 registered seeds)                       ≈ 6e-5
```

Under reading B the gate is essentially unpassable, and failing it would be an artefact of
the 16-ID vocabulary rather than of the proposal mechanism. Under reading A the gate
passes with ≈ 2.3× margin on the binding structures (`c=5`, ~37–40 vs. 16, ≈ 3.5 σ).

**Recommendation for the owner:** ratify reading A explicitly in an amendment *before*
launch, keeping `distinct_bound_subjects` as a reported diagnostic (the builder already
reports it). Do not leave the wording to be settled after the counts are seen.

---

## 5 — Development panels — **PASS**

All 32 cells built (seed-free namespace, so these are the registered panels), 64 units
each, 2,240 semantic signatures = 2,240 tensor signatures = 2,048 singles + 192 pair
b-sides. Every number below is recomputed by me from the panel JSON, re-interpreting each
question with `V3.interpret`.

### 5a — can `target_answer = 12 + index % 16` leak through the unit index?

No. The model never sees the index. The evaluator packs a unit with
`V3.pack_side`, whose entire body reads exactly three fields:

```python
A.data.pack([unit[side]['memory']], [unit[side]['question']], list(range(len(units))),
            [unit[side]['where']])
```

`memory`, `question`, `where` — nothing else. `B1.pack_batch` reads only
`owner`, `question`, `chain`, `support` (the latter two are targets); `answer`, `hops`,
`terminal` never reach the packer at all. The panel unit does carry `index`,
`target_answer`, `namespace`, `cell`, `kind` at top level, and `target_answer` always
equals `a['answer']` — but these are metadata, not model inputs. **PASS.**

*Residual risk (note only):* because the answer is a deterministic function of position in
the file, any future consumer that takes a **prefix or subset** of a cell's units
(`units[:32]`, a split-by-unit-range scoring wave) gets a biased answer distribution. §9
explicitly contemplates "split scoring by frozen cell/unit ranges". A scoring wave must
either take whole cells or recombine ranges before computing rates.

### 5b — balance and chance

Every one of the 32 cells: 16 distinct answer values, exactly 4 units each, i.e.
`answer_counts == [4]`, `answer_values == 16`, chance level `4/64 = 6.25 %` in every cell.
`answer_equals_12_plus_index_mod_16` is true for all 2,048 single sides. No cell deviates.

### 5c — structure

Recomputed per cell from the questions and the interpreter, across all 32 cells:

```
hop_mismatch 0   terminal_mismatch 0   repeated_people 0   answer_mismatch 0
```

* distinct-people rule holds for **every** unit in every cell, including `c=6/7/8`.
* pair cells: `E-c5-link` 64/64 answer changed, `E-c5-value` 64/64 changed,
  `E-c5-irrelevant` 64/64 unchanged — exactly the spec's requirement; and the builder
  additionally enforces the token-diff count (1 for link, 2 for value/irrelevant), question
  invariance, `distinct` preservation after the edit, and value-inventory preservation.
* N cells: `c=4/5 × people 6/16`, terminal fixed to 10 — 4 cells. ✓
* E cells: `c=5`, 16 people, terminal 10, three edits — 3 cells. ✓
* F: 7 cells (`c=1` × r8/r9/r10, `c=2/3` × r8/r9), 6 people. ✓
* P: 8, H: 4, L: 6 (`c=6/7/8` × {balanced 8/9, 10}, 16 people). ✓ Total 32, asserted at
  import.
* "balanced 8/9" is implemented as `PRACTISED_RELS[index % 2]` → exactly 32/32.

---

## 6 — Determinism

### 6a — reproducible on this machine — **PASS**

```
same seed, same chunking, two runs         : awake chunk sha256 IDENTICAL
chunked (3×8) vs unchunked (1×24)          : block-level content IDENTICAL
resume (0..8 then 8..24) vs single pass    : chunk bytes IDENTICAL
memory rebuilt                             : worlds.pt + transition-counts.json IDENTICAL
buffers rebuilt                            : buffer-R/G/U.pt + offline-order.json IDENTICAL
dev panels rebuilt (twice)                 : every cell JSON + forbidden-semantics IDENTICAL
```

`save_chunk` and `write_new` both refuse to overwrite (`path.exists()` raise / `open('x')`),
and `build_dev_panels` uses `mkdir(exist_ok=False)`. Every RNG is `random.Random(<string>)`
over a frozen namespace, so nothing depends on `PYTHONHASHSEED` or dict iteration order;
all set-derived output is `sorted()` first; all JSON is `sort_keys=True`.

### 6b — what is *not* portable — **flags, not failures**

1. **`torch.save` serialization.** Every `.pt` sha256 (awake chunks, `worlds.pt`,
   `buffer-*.pt`) is a hash of torch's archive format. A different torch build can change
   those bytes without changing a single token. Pin `torch 2.14.0` in the launch manifest,
   or hash the decoded tensors instead of the file.
2. **CPython version.** `random.Random(str)` seeding and `sample`/`choice`/`randrange`
   are stable across platforms but have changed between CPython minor versions
   historically. Pin `3.12.14` explicitly.
3. **`runtime.local.json`.** `astra_canonical_operator` puts eleven
   `~/.cache/uv/archive-v0/<hash>` directories on `sys.path`; torch is **not** importable
   without it. Those are machine-local paths. A GPU box must reproduce that file, and the
   manifest should record the resolved versions, not the paths.
4. **Timestamps inside the manifests.** `index.json`, `memory/manifest.json`,
   `buffers/manifest.json`, `buffers/audit.json` and the panel `manifest.json` all embed
   `created_unix` and `seconds`, so **their own sha256 is not reproducible** even when
   every data byte is identical (verified: two identical buffer runs differ only in
   `created_unix`, `seconds`, and the cascading `memory.manifest_sha256`). §9 item 4 wants
   a manifest of hashes frozen before any run; a reviewer can re-derive the **data** hashes
   but not the manifest hashes. Either hash only the data files, or split the timestamp
   into a sidecar.
5. **Panel subset builds.** `taken_semantic`/`taken_tensor` accumulate across cells in
   `DEV_CELL_ORDER`, so a 3-cell build is not *guaranteed* to equal the corresponding cells
   of a 32-cell build. In practice it does (I checked: byte-identical), because collisions
   never occur. But `--cells` subsets are not a safe way to split a registered panel build,
   and there is no resume path (`mkdir(exist_ok=False)` + the `--budget` abort tells you to
   delete and restart) — which is the right conservative choice.

---

## 7 — Judgment calls and `registered_cells()`

### `registered_cells()` — **PASS**

I attacked it directly (`adversarial-probes.json`):

```
cells before 25 → inside 57 → after 25
restored exactly after an exception raised inside the with-block : true
V3.CELL_ORDER untouched, before/inside/after                     : true
name-collision guard fires before any mutation                   : RuntimeError, CELLS unchanged
re-entrant use                                                   : RuntimeError (collides with itself),
                                                                   CELLS still restored
```

The `clash` check runs **before** `V3.CELLS.update`, so a collision leaves the table
untouched; the `finally` pops on any exception. No key is ever shadowed, so `pop` is a
faithful restore.

Effect on legacy behaviour: I grepped every consumer. `fable_baseline_transformer`,
`fable_baseline_length_eval` and `fable_confirmation_panels` index `V3.CELLS[name]` from an
explicit list or from `V3.CELL_ORDER`; `fable_dispatcher.py:394`'s
`for cell, cfg in CELLS.items()` is **V1's** table, not V3's. The one place that iterates
V3's table wholesale is `fable_dispatcher_v3.py:596` — `cells=len(CELLS)` in v3's own
panel-build summary. Nothing in the novelty-19 path calls that inside the with-block, so
no legacy behaviour changes. **Note only:** it is fragile by construction; the project
already has the cleaner pattern (`fable_confirmation_panels.operator_cell` explicitly says
"no module global is mutated" and threads the config through instead). Threading a `cells`
argument into `V3.audit_unit`/`audit_side` would remove the hazard permanently.

One consequence the training/scoring agent must know: **`V3.audit_unit` and `V3.audit_side`
look the cell up in `V3.CELLS`, so the scoring wave must also run inside
`registered_cells()`.** It fails loudly (`KeyError`) if forgotten — I triggered it by
accident. That is the right failure mode, but it belongs in the handoff.

### Judgment calls

The builder's own list of 14 is not in the repo, so I enumerated the discretionary
decisions I could find in the source. Each is defensible; the starred ones are the ones
the owner should actually sign off on.

1. ★ "distinct questions" in the generation gate = distinct `(world, question)` instances → **item 4, needs a ruling**.
2. ★ Confirmation exclusion = legacy panels only → **must-fix (1g)**.
3. ★ `--dev-panels` optional on `awake-stream` / `buffers` / `audit` → **must-fix (1h)**.
4. ★ Confirmation lockout keyed on mere file existence → **must-fix (item 8)**.
5. `registered_cells()` mutating `V3.CELLS` rather than threading a `cells` argument.
6. All 64 candidates are always drawn; valid ones arriving after the quota are logged as `after_quota_filled`, not as type rejections. Faithful, and it makes the proposed histogram describe the whole schedule.
7. `MAX_DRAWS_AFTER_BOS = 7` counts the EOS draw, so `c=6` is *generated* and then rejected by the ≤5 rule, while `c≥7` overruns. Matches "a maximum of seven draws after BOS suffices to detect a valid ≤5-call string plus EOS or an overrun".
8. The duplicate-signature test runs **before** the quota test, so a duplicate consumes an attempt even once four slots are full. Immaterial (measured, item 2c).
9. Zero-padding is reversible because token 0 is unused by the grammar. Verified: rows use 3/7/8–11/12–27/28–51/52–67, questions 4/5/8–11/52–67; 0 appears nowhere. My decoder round-trips 22,016 questions with 0 malformed.
10. Memory de-duplication uses `CP.world_signature` (sorted eligible fact tuples), so row order and filler are ignored — exactly what §3 asks. 0 duplicates in 64 updates; the log file exists regardless.
11. The R arm is *reconstructed* from `(start, names)` and re-labelled rather than copied verbatim from the awake item. I verified the result is identical to the awake question and that R's type histogram exactly equals memory's.
12. `distinct=True` on **every** cell including `c=6..8` (v3's k6..k8 precedent), so no cell tolerates a cycling chain.
13. L's "balanced 8/9 ending group" = `index % 2`, giving exactly 32/32 rather than a random balance.
14. `operator_chain_hits` deliberately omitted from panels (it is a model forward; panels stay pure data).
15. The superseded pilot panels are outside the registered union (measured overlap: 0).
16. `decode_block` infers questions-per-world by integer division `len(items) // len(stories)`. Exact for every artifact this file produces; it would silently mis-shape `memories` (and so `where`) if a block ever had an uneven count. Not a live bug; worth an assertion.

---

## 8 — Confirmation lockout — **AMBIGUOUS / weak, must fix**

What holds:

```
confirm namespace without the --confirmation flag : BLOCKED ("needs the explicit --confirmation flag")
--confirmation with no DEV-PASSED.json            : BLOCKED
dev vs confirm namespace produce different units  : true (different world and question)
```

What does not:

```
--confirmation with an EMPTY, unvalidated DEV-PASSED.json : ALLOWED, panels built
--n 512 under the DEV namespace, no flag at all           : ALLOWED, 512-unit suite built
```

The flag file's **contents are never read**. Nothing checks that development actually
passed, which seeds passed, that the recipe was unchanged, or — as §7 requires — that
*"final checkpoint hashes are locked"*. Any process that touches the path unlocks
confirmation. Combined with 1g (confirmation does not exclude training/replay worlds),
the confirmation suite is the weakest part of the data side.

The `--n 512 --namespace astra-novelty19-dev-v1` path is not a lockout bypass in the strict
sense — those units differ from the confirmation units — but it does let an unlimited number
of 512-unit panel suites be built before development is declared, which is exactly the
selection surface §6/§7 try to close.

---

## Must fix before freezing

1. **Persist training/replay signatures and exclude them from confirmation.** Write a
   `forbidden-semantics.json` (question-level) **and** a `forbidden-worlds.json`
   (world-level, from the `world_signature` tensor the blocks already carry) for the awake
   stream, memory and all three buffers of each registered seed, and make
   `build_dev_panels(confirmation=True)` consume them. §7 asks for *worlds*, and no
   world-level exclusion exists anywhere in the code today. (1f/1g)
2. **Make `--dev-panels` mandatory** on `awake-stream`, `buffers` and `audit`, or have
   `audit` report `passed: false` when a disjointness check could not be run. A green
   audit must not be achievable by omitting a flag. (1h)
3. **Rule on the generation gate wording** in an additive amendment, before launch.
   Reading A passes at ≈ 2.3× margin; reading B has ≈ 4 % chance of passing one seed and
   ≈ 6e-5 of passing three, because it is a 16-entity coverage test in disguise. (item 4)
4. **Harden the confirmation lockout:** validate `DEV-PASSED.json` contents — the three
   seeds, the per-cell marks, the endpoint checkpoint SHA-256s and the data-side manifest
   hash — and refuse if the recorded fingerprint differs from the running one. (item 8)
5. **Run the operator-history reconstruction in the launch wave** (21 s, no model forwards,
   `operator_history.py` does it) against the three registered awake streams and, later, the
   confirmation panels, and record `world_union_sha256`
   `0730f99e6e627fa00db03cef5919b814599dfacb3a299a8ded440d28f0dc900a` in the manifest. The
   development-panel result is already definitive (0 / 0) and the §7 "disclose as
   unverified" fallback is no longer needed. (1f)
6. **Pin the execution profile in the manifest:** CPython 3.12.14, torch 2.14.0, and the
   resolved `runtime.local.json` import roots — every `.pt` sha256 depends on the torch
   serialization format. (6b-1/2/3)

## Note only

* Manifest/index/audit JSON embed `created_unix` and `seconds`, so their own hashes are not
  reproducible; the data-file hashes they contain are. Hash the data files, not the
  manifests. (6b-4)
* The composite-r10 quarantine is structurally unreachable in the registered run
  (`LINK→10 = 0`). I forced it with poisoned counts and it works — keep that as a
  preflight fixture so it is not merely dead code.
* `registered_cells()` is exception-safe and collision-guarded, but it mutates a frozen
  module global. Threading a `cells` argument into `V3.audit_unit`/`audit_side` would be
  strictly safer. The scoring wave must also run inside the context manager (fails loudly
  if not) — put that in the handoff.
* Answer is a deterministic function of unit index. Safe for the model, unsafe for any
  scoring wave that takes a **prefix/subset** of a cell. Score whole cells, or recombine
  ranges before computing rates.
* The superseded pilot panels (640 signatures) are outside the registered union; measured
  overlap with dev panels, awake stream and buffers is 0. Add `--extra-exclusion` only if
  the owner wants the union to be maximal.
* `--n 512` under the development namespace is buildable at any time. Not a lockout bypass,
  but it is an unbounded panel-generation surface; consider capping `--n` unless
  `--confirmation` is set.
* `decode_block` infers questions-per-world by integer division. Add an assertion.
* Corrected arithmetic for the prediction ledger: expected ≈ **207** `c=4` and ≈ **69**
  `c=5` questions per 4,096-question G buffer (the brief and `FABLE-PREDICTIONS.md` say
  200 / 65; the difference is renormalisation by the 0.99906 acceptance probability).
  Measured on seed 9991: 221 and 77, both ≈ +1.0 σ.

---

## Reproducing this audit

```bash
cd <worktree>
export OMP_NUM_THREADS=1
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
A=artifacts/fable-novelty19-replay-20260920/audit
S=$A/scratch

$PY -B scripts/fable_novelty19_data.py awake-stream --seed 9991 --updates 100 --chunk 100 --out $S/awake9991 --quiet
$PY -B scripts/fable_novelty19_data.py memory      --seed 9991 --stream $S/awake9991 --out $S/mem9991
$PY -B scripts/fable_novelty19_data.py buffers     --seed 9991 --memory $S/mem9991  --out $S/buf9991
$PY -B scripts/fable_novelty19_data.py dev-panels  --out $S/dev32 --quiet

$PY -B $A/independent_checks.py --stream $S/awake9991 --memory $S/mem9991 \
        --buffers $S/buf9991 --dev-panels $S/dev32 --json $A/independent-checks-9991.json
$PY -B $A/adversarial_probes.py  > $A/adversarial-probes.json
$PY -B $A/world_overlap.py       > $A/world-overlap.json
$PY -B $A/operator_history.py 6000        # ~21 s, writes operator-history.json
```

Wall clock for the whole rehearsal + audit: well under 2 minutes, excluding the 21 s
operator reconstruction. The bulky `.pt` and panel-JSON scratch files were deleted after the
measurements above were recorded; re-running the four build commands recreates them
byte-identically.

---

# Re-check 2 — 20 September 2026

Re-audit of `scripts/fable_novelty19_data.py` after the builder's patch, against (a) my six
must-fix items, (b) rulings 1–6 of `design/v3/19-rulings-1.md`, (c) the protected API the
trainer consumes.

**Identities measured, not quoted**

| file | sha256 | size |
|---|---|---|
| `scripts/fable_novelty19_data.py` | `6e5c8f70c9351135e7498032d4c41146245b37df1e3c209d345e3b53781e5d89` | 2,426 lines |
| frozen `design/v3/19-rulings-1.md` | `af4cc0d4…` | 53 lines |

Disposable seed 9991 only. Nothing under `scratch2/` is a registered artifact. My checkers
are `data_recheck_a.py` … `data_recheck_d.py` in this folder; they parse the on-disk
outputs with my own task-1 parser (`independent_checks.py`) and use the frozen project
modules only for the grammar/interpreter (`fable_confirmation_panels.world_signature`,
`fact_tuples`).

## (a) The six must-fix items

| # | item | status | evidence |
|---|---|---|---|
| 1 | persist training/replay signatures; exclude **worlds** from confirmation | **CLOSED** | §R2-1 |
| 2 | `--dev-panels` mandatory; `audit` fails when a check is absent | **CLOSED** | §R2-2 |
| 3 | rule on the generation-gate wording | **CLOSED** (ruling 1, reading A = "instances") | §R2-3 |
| 4 | harden the confirmation lockout (validate contents) | **CLOSED on the data side**; still open on the trainer — see `TRAIN-AUDIT.md` must-fix 1/2 | §R2-4 |
| 5 | run the operator-history reconstruction and record `world_union_sha256` | **CLOSED** | §R2-5 |
| 6 | pin the execution profile | **CLOSED** (stronger than asked) | §R2-6 |
| 7 | *new this pass* — consumed exclusion files are never hash-checked | **OPEN — must fix (small)** | §R2-7 |

### R2-1 — world-level exclusion for confirmation

`write_forbidden` now publishes `forbidden-semantics.json` (questions) and
`forbidden-worlds.json` (worlds) from every artifact folder, and
`build_dev_panels(confirmation=True)` consumes both through `confirmation_exclusions`.

I built a real confirmation suite (4 cells × 64 units = 256 units, 320 world signatures)
against a full seed-9991 experiment folder and recomputed every panel world signature
myself from the rows each question can actually see:

| overlap | count |
|---|---|
| confirmation × training worlds (awake ∪ memory ∪ buffers, 1,600 signatures) | **0** |
| confirmation × development-panel worlds | **0** |
| development × training worlds | **0** |

The confirmation manifest records the union it applied: 15,749 questions / 3,840 worlds from
`stream_9991`, `memory_9991`, `buffers_9991`, `dev_panels`, plus
`operator_history.world_union_sha256 = 0730f99e…`.

I also attacked the identity definition itself. The exclusion is built from
`CP.fact_tuples(story)` over **all** rows, while a panel question sees only rows before
`where` — if those differed, a training world could slip past. Measured per item over all
22,784 items of the three artifacts: `where < row_count` in **0** items, the full-row and
visible-row signatures are equal for **22,784 / 22,784**, and the `world_signature` tensor
the blocks now publish equals my independent recomputation for **22,784 / 22,784**. So the
two identities coincide and the exclusion is sound.

Negative control: with one artifact folder present but its exclusion files absent, the
confirmation build refuses (`missing forbidden-question file at …`), so a silently narrowed
union cannot arise from a forgotten publish step.

### R2-2 — mandatory flags and the audit roster

`--stream`, `--memory`, `--buffers`, `--dev-panels`, `--operator-history` are all required
arguments of `audit`; `--dev-panels` is required on `awake-stream` and `buffers`.
`audit` on the seed-9991 fixture runs **36 / 36** `EXPECTED_AUDIT_CHECKS`, `checks_absent: []`,
`passed: true`. Injecting one extra expected name into the roster (in my own process) makes
the same run report `passed: false`, `failures: ["expected_checks_absent"]`. A green audit
can no longer be obtained by omitting a source.

### R2-3 — ruling 1, the generation gate

Recounted from the G buffer with my own code: for each of the four registered structures I
counted distinct `(world signature, raw question tokens)` pairs over **sampled, non-fallback**
items only, using the world signature I recomputed from the stored rows rather than the
memory index.

| structure | my distinct instances | my distinct worlds | module's figures | awake instances |
|---|---|---|---|---|
| c=4, r=8 | 118 | 113 | 118 / 113 | 0 |
| c=4, r=9 | 103 | 96 | 103 / 96 | 0 |
| c=5, r=8 | 37 | 37 | 37 / 37 | 0 |
| c=5, r=9 | 40 | 38 | 40 / 38 | 0 |

Every figure agrees exactly; all four pass the ≥16-instances **and** ≥16-worlds requirement
with zero awake instances; `GATE_READING = 'instances'`; `memory_worlds_distinct` is a
separate conjunct, so ruling 1's "a memory index is an equivalent key only after memory-world
uniqueness is verified" is honoured. The module's `ruling` field cites the frozen file.

### R2-4 — the DEV-PASSED lockout (data side)

`validate_dev_passed` was given eleven flags. All ten bad ones are refused and only the
fully-valid one is accepted:

| flag | result |
|---|---|
| missing / empty / not-JSON / `{}` | refused |
| wrong `schema` | refused |
| `seeds = [1900,1901,1902]` when scoring 9991 | refused |
| `report_sha256` removed | refused |
| `dev_panels.manifest_sha256` ≠ the manifest on disk | refused |
| only 1 of 2 awake checkpoints | refused |
| checkpoint values not 64-hex | refused |
| complete and consistent | **accepted** |

It re-hashes the dev-panel manifest **on disk** rather than trusting the recorded value, and
checks all 2 awake + 6 offline checkpoint keys for the seed set it is asked about. This
closes must-fix 4 for the data module. It does **not** close it for the trainer:
`fable_novelty19_train.guard_confirmation` still only calls `Path.exists()` and never calls
`validate_dev_passed` — see `TRAIN-AUDIT.md`.

### R2-5 — operator history (ruling 2)

`operator-history/manifest.json` carries
`world_union_sha256 = 0730f99e6e627fa00db03cef5919b814599dfacb3a299a8ded440d28f0dc900a`,
the value my task-1 reconstruction produced, and the confirmation manifest carries it
forward. `load_operator_history` refuses a manifest with `complete: false`, refuses `None`,
and `build_dev_panels` refuses `require_full_history=False` for both `NS_DEV` and
`NS_CONFIRM` with *"a partial operator history may never back a registered namespace; use a
fixture namespace for that"*. Ruling 2's "an incomplete reconstruction remains an unresolved
freeze prerequisite" is therefore enforced in code, not only in prose.

### R2-6 — execution profile

Every manifest (`awake/index.json`, `memory`, `buffers`, `dev-panels`, `operator-history`)
carries `execution_profile`: python 3.12.14, CPython, torch 2.14.0, macOS-27.0-arm64,
`script_sha256`, **and the sha256 of all eight imported project modules plus the canonical
operator**. The resolved `runtime.local.json` import roots are not recorded, but recording
the sha of every module actually imported is strictly stronger than recording where they were
found, so I count this closed.

### R2-7 — NEW: the published exclusion files are never hash-checked when consumed

`read_signature_file` validates shape (non-empty JSON list of 64-hex strings) but never
compares the file against the `published_exclusions.*_sha256` its own artifact manifest
recorded. I truncated `bufB/forbidden-worlds.json` from 1,024 entries to 5 and the
confirmation build **accepted it** and produced panels; the only trace is the count in the
confirmation manifest (`buffers_9991: worlds 5`), which no code compares to anything.

Impact is bounded — in the registered layout the buffers reuse the memory worlds, so
truncating that file is largely covered by `memory_9991`; truncating the **stream's** file is
the dangerous one because its 1,600 worlds are unique to it. Severity is "defence-in-depth
defeated by a file edit", not an active leak, but the entire world-level guarantee added in
must-fix 1 rests on these files.

*Fix:* have `artifact_exclusions` read the artifact's `manifest.json` and refuse when
`sha(file) != published_exclusions.<kind>_sha256`, and record each source file's sha256 in
the confirmation manifest's `training_exclusion.sources`.

## (b) Rulings 1–6 implemented exactly

* **Ruling 1** — see §R2-3. **Implemented.**
* **Ruling 2** — see §R2-5. **Implemented.**
* **Ruling 3 (fixed-slot fallback)** — the registered rehearsal produces 0 fallbacks in all
  three arms, so I forced the path by rejecting proposals inside my own process. With k = 0
  and k = 2 accepted, for both **G** and **U**: slots `0..k−1` keep the sampled questions,
  slot `j ≥ k` takes awake question `j` verbatim (operation string **and** start entity both
  match `awake_items[j]`), `sampled=False`, `candidate=None`, each fallback is logged with
  `duplicates_accepted`, and the k=2 G case did produce a fallback duplicating an accepted
  question — kept and flagged, not replaced. The attempt budget is a fixed
  `range(CANDIDATES_PER_WORLD)` loop that the fallback code cannot re-enter. The gate skips
  `sampled=False` items. **Implemented exactly.**
* **Ruling 4 (world identity)** — memory admits 1,024 distinct signatures, `duplicates: 0` on
  this fixture, and my per-item recomputation (§R2-1) confirms the signature is the canonical
  question-free fact set with entity IDs retained and row order/filler ignored.
  **Implemented.**
* **Ruling 5 (distinct people, including L)** — checked over **2,240 sides** (all 32 cells,
  both sides of all three E pair cells). For every side the visited set — the start person
  plus the person each of the `c−1` LINK calls reaches — has exactly `c` distinct members.
  **0 violations.** L cells reach the full 6 / 7 / 8. **Implemented.**
* **Ruling 6 (answer stratification + ending schedule)** — `target_answer(i) = 12 + (i mod 16)`
  holds for every unit of every cell; every cell has 16 answer values × exactly 4 units.
  The mixed-ending cells are `L-c6-prac`, `L-c7-prac`, `L-c8-prac`; in each,
  `r(i) = 8 + (floor(i/16) mod 2)` gives every (answer, ending) pair exactly twice —
  answer parity vs ending is 16/16/16/16, answer half vs ending is 16/16/16/16, and knowing
  the answer predicts the ending at exactly **0.500**, i.e. chance for two endings. The
  `answer_ending_balanced` manifest flag agrees with my recomputation in all 32 cells.
  **Implemented exactly; the parity shortcut is gone.**

### Shortcut sweep beyond ruling 6

I scanned all 32 cells × 10 model-visible or index-derived features (terminal relation, start
entity, visible row count, `where`, people visited, call count, distinct people in the story,
question length, the last visible row's subject, and `index mod 2` as a control that the
model cannot see). Statistic: weighted purity `Σ_f (n_f/N)·max_a P(a|f)`, compared with 400
answer shuffles holding the feature fixed. **131 tests, 2 flagged at α = 0.01**, both the same
underlying quantity (row count ≡ `where`) in one cell, `F-c3-r9`.

A deeper 20,000-shuffle test gives raw p = 0.0008, i.e. **Bonferroni p = 0.10 over 131 tests
— not significant**, and the two sibling cells `F-c3-r8` and `F-c2-r9` show nothing
(p = 0.99, p = 0.88). Even taken at face value the feature predicts the answer with
**18.75 %** accuracy against an F-family mark of **61/64 = 95.3 %**, so it cannot move a gate.
**No usable index-driven shortcut found.** (My first pass flagged `answer_from_start_entity`
in all 32 cells; that was an artefact of 16 singleton-ish groups, and it is at chance under
the permutation null — recorded here because I reported it before testing it properly.)

## (c) The protected API is unchanged in behaviour

I rebuilt the exact task-1 fixture (seed 9991, 100 updates) with the new module and re-ran my
own task-1 parser over it:

* awake census **byte-identical** to my task-1 record;
* memory census **byte-identical**; memory counts match my independent recount; 1,024 distinct
  memory worlds, as before;
* the chunk sha256 moved `762311363565…` → `210eadc4b15d…`, which is **expected and benign**:
  the block schema gained the `world_signature` tensor that must-fix 1 required. The decoded
  stories, questions, labels, owner vectors and ordering are unchanged, which is what the
  trainer consumes.

Manifests are hash-reproducible: the same command into the same path twice gives identical
bytes for every panel and exclusion file; into a *different* path only `manifest.json` differs,
because it stores absolute paths. Wall-clock has moved out of the documents into
`<name>.meta.json` sidecars — no `created_unix` / `seconds` key remains in any manifest.

---

## FREEZE-READY (data side): **YES, with one small fix**

Rulings 1–6 are implemented exactly as written, and five of my six must-fix items are
genuinely closed with measured evidence rather than assertion. The sixth (lockout content
validation) is closed inside the data module; the remaining half of it lives in the trainer.

The one outstanding data-side item is **R2-7**: hash-check the `forbidden-*.json` files
against the artifact manifests when consuming them, and record their shas in the confirmation
manifest. It is a ~10-line change, it does not alter any registered byte, and I would freeze
on it. If the owner prefers to freeze the module as it stands, R2-7 must instead become a
launch-procedure step: re-verify each artifact's `published_exclusions.*_sha256` by hand
immediately before the confirmation build.

**Data side: FREEZE-READY = YES conditional on R2-7 (code fix or written launch step).**
The training side is a separate verdict — see `TRAIN-AUDIT.md`.

## Reproducing Re-check 2

```bash
cd <worktree>/artifacts/fable-novelty19-replay-20260920/audit
export OMP_NUM_THREADS=1
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
$PY -B data_recheck_a.py    # protected API, audit roster, manifest stability   (~40 s)
$PY -B data_recheck_b.py    # lockout matrix, confirmation worlds, rulings 1/6  (~5 s)
$PY -B data_recheck_c.py    # per-item world identity, permutation null         (~3 s)
$PY -B data_recheck_d.py    # rulings 3/4/5, execution profile                  (~5 s)
```

Outputs: `data-recheck-{a,b,c,d}.json`. The `scratch2/` fixture (≈ 105 MB, mostly the
operator-history exclusion JSON and the 32 dev panels) was deleted after these measurements;
re-running the four scripts after the four build commands at the top of this file recreates
it.

---

# Re-check 3 — final confirmation pass (data side)

Subject: `scripts/fable_novelty19_data.py` sha256 `ef1df0e149aa4741a22f7185fadb9eaeb054b072d50c09a1ad2a196a998ae9de`
(2,575 lines), tests `102caaf22432283cedf71cd108e869e188bc9bd14b40fc0ed577276550805d94`.
Both shas reproduced locally with `shasum -a 256`; they match what the builder reported.
All work on disposable seed 9991 under `audit/scratch3/`. My own checkers
(`data_recheck_e.py`, `data_recheck_f.py`) parse the on-disk artifacts and drive the
module's own command line as a black box; the builder's tests were not consulted.

## 1. R2-7 is closed — the tamper matrix

Re-check 2's finding was that a consumer read a published exclusion list without ever
hashing it, so truncating `bufB/forbidden-worlds.json` from 1,024 entries to 5 was
accepted silently. The patch routes every consumer through `read_signature_file`, which
checks sortedness+distinctness, the manifest's recorded count, and the manifest's recorded
sha256.

I attacked four exclusion files (`awakeB/forbidden-worlds.json`, `bufB/forbidden-worlds.json`,
`ophist/forbidden-worlds.json`, `dev/forbidden-semantics.json`) with five variants each —
**truncated** (the original R2-7 attack, 1,024 → 5), **same-count-tampered** (one signature
swapped for `'a'*64`, length preserved), **duplicate-padded** (5 real entries padded back to
full length by repeating one), **unsorted**, **emptied** — against three consumers
(awake-stream build, buffers build, dev-panels build / `audit`).

- **45 / 45 cases refused**, `accepted: []` (`data-recheck-e.json`, `tamper_matrix`).
- Each refusal names the right cause, e.g. truncation → *"holds 5 entries but … records 1600;
  refusing a truncated or padded exclusion file"*; same-count tamper → *"hashes to a21b566f…
  but … records 9e2a7a97…; refusing a tampered exclusion file"*; duplicate-pad and unsorted →
  *"is not a sorted list of distinct signatures; refusing a rewritten exclusion file"*.
- Baseline before tampering: all four consumers returncode 0.

## 2. Manifest attacks

Three ways to remove the thing the hash is checked against, both consumers each:

| attack | result |
|---|---|
| `manifest.json` deleted | refused — *"no artifact manifest … an exclusion file without the manifest that produced it cannot be verified"* |
| `published_exclusions` block stripped | refused — *"records no published_exclusions; its exclusion files cannot be verified and may not be consumed"* |
| `questions_sha256` blanked inside the block | refused — *"published_exclusions has no questions_sha256; the exclusion files cannot be verified"* |

`manifest_all_refused: true`. There is no "unverified" path left: I grepped every call site of
`artifact_exclusions` and none passes `verify=False`.

## 3. The confirmation consumer — the original R2-7 attack site

Same five variants × four files driven through a real confirmation-panel build
(`data-recheck-f.json`): **20 / 20 refused**, `accepted: []`, and the clean control still
builds after every file is restored.

Clean confirmation build (2 cells, `NS_CONFIRM`, seed 9991):

- 64 confirmation worlds; **overlap with the 1,600 training worlds = 0**; overlap with the
  2,240 development worlds = 0.
- Union actually applied: 15,749 forbidden questions, 3,840 forbidden worlds.
- Four sources, **every one `verified: true` and carrying a sha**: `stream_9991`
  (`9e2a7a97…` worlds), `memory_9991` (`de3a5cae…`), `buffers_9991` (`de3a5cae…`),
  `dev_panels` (`e7709aed…` worlds, `64a082da…` questions).
- `consumed_exclusions` present in the panel manifest, as required.
- `operator_history.world_union_sha256` = `0730f99e6e627fa00db03cef5919b814599dfacb3a299a8ded440d28f0dc900a`
  (unchanged).

The awake-stream and buffers manifests carry the same verified shas under
`exclusion.dev_panel_source` and `primary_world_exclusion.source`. `load_operator_history`
refuses all five tampered variants of its own list.

## 4. Audit roster

`audit` now expects **37** checks (36 + the five exclusion-verification checks, minus the
consolidation the builder made): the run reports 37/37 present and passing, and the roster
count is asserted, so a silently-dropped check still fails the command.

## 5. Generated bytes unchanged apart from embedded script shas

The `.pt` chunk sha necessarily moves (`210eadc4…` → `911bb493…`) because the chunk metadata
embeds `execution_profile.script_sha256` — i.e. the module hashes itself into its own output.
Content equality was therefore checked by decoding:

- awake and memory censuses byte-identical old vs new;
- all 32 × 10 per-cell purity values identical;
- ruling-6 ending-schedule tables identical;
- 1,024 memory worlds identical;
- `memB/forbidden-worlds.json` sha `de3a5cae32b893cff6f967b8c860b7392a373fc68a21974dc3bbed9ec55092a9`
  **byte-identical across module versions**.

No behavioural change to the protected API.

## Reproduce

```bash
cd <worktree>/artifacts/fable-novelty19-replay-20260920/audit
export OMP_NUM_THREADS=1
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
$PY -B data_recheck_e.py    # 45-case tamper matrix + 3 manifest attacks + audit roster
$PY -B data_recheck_f.py    # confirmation consumer: 20 cases, provenance, world overlap
```

Outputs `data-recheck-e.json`, `data-recheck-f.json`. The `scratch3/` fixture (≈ 110 MB) was
deleted after these measurements.

**Data side: FREEZE-READY = YES.** All six original must-fix items and R2-7 are closed with
measured evidence; no new data-side must-fix.

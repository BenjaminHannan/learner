# M0 -- Notebook demo v0: results

Generated 2026-09-20T23:08:34.089983+00:00. Evaluation only; nothing was trained.
RNG namespace `fable-notebook-m0-v1`; 64 scripted teaching sessions, facts taught one at a time; every seed reported separately, never averaged.

## Checkpoints (frozen, read-only)

| operator seed | parameters | updates | sha256 | path |
|---|---|---|---|---|
| 0 | 79316 | 6000 | `db40c2452ea31fe9e4df90b6864ffe68631c2196c7309f1408cec5c8be04022c` | `/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/fable-operator-grow-blind-20260920/astra_canonical_operator_seed-0/final.pt` |
| 1 | 79316 | 6000 | `c02c12d64319aae5e9984b0e7e4c9ac08976a463ecf3dfd3e641e236a532290a` | `/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/fable-operator-grow-blind-20260920/astra_canonical_operator_seed-1/final.pt` |
| 2 | 79316 | 6000 | `ed498799fba6ce82052413d860fcba878fb70dc80b4a05ec3106429d3b8ee32d` | `/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/fable-operator-grow-blind-20260920/astra_canonical_operator_seed-2/final.pt` |

## Growth: accuracy at each notebook size (raw counts)

### operator seed 0

| notebook rows | one-hop correct/n | one-hop % | two-hop correct/n | two-hop % |
|---|---|---|---|---|
| 1 | 64/64 | 100.00% | 0/0 | n/a |
| 2 | 128/128 | 100.00% | 64/64 | 100.00% |
| 4 | 256/256 | 100.00% | 69/69 | 100.00% |
| 8 | 512/512 | 100.00% | 102/102 | 100.00% |
| 16 | 512/512 | 100.00% | 254/254 | 100.00% |
| 32 | 512/512 | 100.00% | 507/507 | 100.00% |
| 64 | 512/512 | 100.00% | 512/512 | 100.00% |

**Corrections** (two per session: one attribute, one friend link; asked after the correction is appended). The old-answer rate is over the questions whose old answer differs from the new one.

| question | n | new answer | old answer | neither |
|---|---|---|---|---|
| attribute one-hop | 64 | 64/64 (100.00%) | 0/64 (0.00%) | 0 |
| link one-hop | 64 | 64/64 (100.00%) | 0/64 (0.00%) | 0 |
| two-hop through the corrected link | 192 | 192/192 (100.00%) | 0/174 (0.00%) | 0 |
| **all** | 320 | 320/320 (100.00%) | 0/302 (0.00%) | 0 |

**Untouched facts unchanged**: 1024/1024 probe answers identical before and after the corrections.

**Kill-and-reload**: 8/8 sessions re-instantiated from disk in a fresh process gave byte-identical rows, predictions and answer logits.

**Descriptive, no mark -- untaught questions** (notebook of 16 rows; none of these is answerable from the notebook):

| question kind | n | mean confidence | confidence >= 0.9 | answered with a value token | with an entity token | with neither |
|---|---|---|---|---|---|---|
| known person, relation never taught | 256 | 0.924 | 200 | 204 | 52 | 0 |
| person never mentioned in the notebook | 496 | 0.901 | 356 | 254 | 242 | 0 |

**Descriptive, no mark -- wipe test** (empty notebook, 8 questions): predicted tokens [58, 13, 13, 13, 63, 26, 13, 26], confidence [0.3727, 0.4353, 0.805, 0.3276, 0.5793, 0.3073, 0.2683, 0.3788]. an empty notebook is presented as one all-padding row; the operator still emits a token, which is the honest baseline failure

**Marks**

| mark | verdict |
|---|---|
| one_hop@1 | PASS |
| two_hop@1 | n/a (no answerable question at this size) |
| one_hop@2 | PASS |
| two_hop@2 | PASS |
| one_hop@4 | PASS |
| two_hop@4 | PASS |
| one_hop@8 | PASS |
| two_hop@8 | PASS |
| one_hop@16 | PASS |
| two_hop@16 | PASS |
| one_hop@32 | PASS |
| two_hop@32 | PASS |
| one_hop@64 | PASS |
| two_hop@64 | PASS |
| correction_new_answer | PASS |
| correction_old_answer | PASS |
| untouched_unchanged | PASS |
| kill_and_reload | PASS |
| ALL | PASS |

### operator seed 1

| notebook rows | one-hop correct/n | one-hop % | two-hop correct/n | two-hop % |
|---|---|---|---|---|
| 1 | 64/64 | 100.00% | 0/0 | n/a |
| 2 | 128/128 | 100.00% | 64/64 | 100.00% |
| 4 | 256/256 | 100.00% | 69/69 | 100.00% |
| 8 | 512/512 | 100.00% | 102/102 | 100.00% |
| 16 | 512/512 | 100.00% | 254/254 | 100.00% |
| 32 | 512/512 | 100.00% | 507/507 | 100.00% |
| 64 | 512/512 | 100.00% | 512/512 | 100.00% |

**Corrections** (two per session: one attribute, one friend link; asked after the correction is appended). The old-answer rate is over the questions whose old answer differs from the new one.

| question | n | new answer | old answer | neither |
|---|---|---|---|---|
| attribute one-hop | 64 | 64/64 (100.00%) | 0/64 (0.00%) | 0 |
| link one-hop | 64 | 64/64 (100.00%) | 0/64 (0.00%) | 0 |
| two-hop through the corrected link | 192 | 192/192 (100.00%) | 0/174 (0.00%) | 0 |
| **all** | 320 | 320/320 (100.00%) | 0/302 (0.00%) | 0 |

**Untouched facts unchanged**: 1024/1024 probe answers identical before and after the corrections.

**Kill-and-reload**: 8/8 sessions re-instantiated from disk in a fresh process gave byte-identical rows, predictions and answer logits.

**Descriptive, no mark -- untaught questions** (notebook of 16 rows; none of these is answerable from the notebook):

| question kind | n | mean confidence | confidence >= 0.9 | answered with a value token | with an entity token | with neither |
|---|---|---|---|---|---|---|
| known person, relation never taught | 256 | 0.839 | 146 | 193 | 63 | 0 |
| person never mentioned in the notebook | 496 | 0.833 | 284 | 296 | 200 | 0 |

**Descriptive, no mark -- wipe test** (empty notebook, 8 questions): predicted tokens [61, 19, 25, 18, 21, 25, 25, 25], confidence [0.298, 0.3592, 0.2044, 0.2394, 0.1388, 0.4016, 0.6375, 0.223]. an empty notebook is presented as one all-padding row; the operator still emits a token, which is the honest baseline failure

**Marks**

| mark | verdict |
|---|---|
| one_hop@1 | PASS |
| two_hop@1 | n/a (no answerable question at this size) |
| one_hop@2 | PASS |
| two_hop@2 | PASS |
| one_hop@4 | PASS |
| two_hop@4 | PASS |
| one_hop@8 | PASS |
| two_hop@8 | PASS |
| one_hop@16 | PASS |
| two_hop@16 | PASS |
| one_hop@32 | PASS |
| two_hop@32 | PASS |
| one_hop@64 | PASS |
| two_hop@64 | PASS |
| correction_new_answer | PASS |
| correction_old_answer | PASS |
| untouched_unchanged | PASS |
| kill_and_reload | PASS |
| ALL | PASS |

### operator seed 2

| notebook rows | one-hop correct/n | one-hop % | two-hop correct/n | two-hop % |
|---|---|---|---|---|
| 1 | 64/64 | 100.00% | 0/0 | n/a |
| 2 | 128/128 | 100.00% | 64/64 | 100.00% |
| 4 | 256/256 | 100.00% | 69/69 | 100.00% |
| 8 | 512/512 | 100.00% | 102/102 | 100.00% |
| 16 | 512/512 | 100.00% | 254/254 | 100.00% |
| 32 | 512/512 | 100.00% | 507/507 | 100.00% |
| 64 | 512/512 | 100.00% | 512/512 | 100.00% |

**Corrections** (two per session: one attribute, one friend link; asked after the correction is appended). The old-answer rate is over the questions whose old answer differs from the new one.

| question | n | new answer | old answer | neither |
|---|---|---|---|---|
| attribute one-hop | 64 | 64/64 (100.00%) | 0/64 (0.00%) | 0 |
| link one-hop | 64 | 64/64 (100.00%) | 0/64 (0.00%) | 0 |
| two-hop through the corrected link | 192 | 192/192 (100.00%) | 0/174 (0.00%) | 0 |
| **all** | 320 | 320/320 (100.00%) | 0/302 (0.00%) | 0 |

**Untouched facts unchanged**: 1024/1024 probe answers identical before and after the corrections.

**Kill-and-reload**: 8/8 sessions re-instantiated from disk in a fresh process gave byte-identical rows, predictions and answer logits.

**Descriptive, no mark -- untaught questions** (notebook of 16 rows; none of these is answerable from the notebook):

| question kind | n | mean confidence | confidence >= 0.9 | answered with a value token | with an entity token | with neither |
|---|---|---|---|---|---|---|
| known person, relation never taught | 256 | 0.804 | 118 | 183 | 73 | 0 |
| person never mentioned in the notebook | 496 | 0.806 | 240 | 259 | 237 | 0 |

**Descriptive, no mark -- wipe test** (empty notebook, 8 questions): predicted tokens [67, 15, 15, 17, 17, 15, 17, 17], confidence [0.1788, 0.4052, 0.4343, 0.3852, 0.1007, 0.2745, 0.3345, 0.7608]. an empty notebook is presented as one all-padding row; the operator still emits a token, which is the honest baseline failure

**Marks**

| mark | verdict |
|---|---|
| one_hop@1 | PASS |
| two_hop@1 | n/a (no answerable question at this size) |
| one_hop@2 | PASS |
| two_hop@2 | PASS |
| one_hop@4 | PASS |
| two_hop@4 | PASS |
| one_hop@8 | PASS |
| two_hop@8 | PASS |
| one_hop@16 | PASS |
| two_hop@16 | PASS |
| one_hop@32 | PASS |
| two_hop@32 | PASS |
| one_hop@64 | PASS |
| two_hop@64 | PASS |
| correction_new_answer | PASS |
| correction_old_answer | PASS |
| untouched_unchanged | PASS |
| kill_and_reload | PASS |
| ALL | PASS |


# 67 — Thought format v3: groups + no-value rows (wrapper over v2)

Status: built, conformance-tested; plain software, no model. Prefix `fable_thought62_`; files `scripts/fable_thought62_{schema,conformance}.py`; artifacts `artifacts/fable-thought62-20260921/`. Implements doc 56's extensions 1–2 only (comparison kind deferred — doc 56's extension 3, not needed for 17/17).

## 1. Problem

Doc 49's v2 holds 33/50 hand-mapped sentences. The other 17 fail two ways: the sentence states no usable value (fragment, wrong-topic negative, URL-only metadata), or one claim needs several rows (multi-claim, list, table). Ears must NO_FACT those today, and the notebook cannot even record *why*. V3 records the why and the bundle.

## 2. The v3 row (`ThoughtV3`)

Everything in v2, plus:

| field | type | note |
|---|---|---|
| value | v2 kinds + `link` + `empty` | link = url + reason; empty = reason only |
| reason | `fragment \| absent \| metadata` | why there is no usable value |
| group_id | optional string | shared by 2+ rows that form one claim |
| source | v1 tag, unchanged | link/empty rows MUST be `proposed` |

Construction validates structure; `validate(strict=True)` adds contract rules at write. Link/empty rows with any other source fail at construction, not just at write.

## 3. Guarantees kept

| v1/v2 guarantee | how v3 keeps it |
|---|---|
| append-only hash chain | one log: v3 rows embedded under `provenance.thought_v2`; tamper still raises `LogCorrupt` (tested g18) |
| taught-only answerability | no-value rows are `proposed` forever — promote refuses them (tested g08); the contract's `current()` already excludes `proposed`, and the wrapper gate skips them explicitly |
| qualified rows need matching questions | unchanged v2 gate; group members keep their own qualifiers, and `ask_group` requires every member's qualifiers to match |
| supersede-not-delete, marks, relation ids | inherited from the v2 wrapper by composition |
| old behaviour unchanged | 32/32 contract cases pass (T1); ungrouped `to_v1()` byte-identical to v2 (T5, 8/8) |

## 4. The group gate

A group answers only through `ask_group(name, group_id, qualifiers)`: OK with a `; `-joined per-member answer iff at least 2 members are active, every active member is either answering-source with matching qualifiers or covered by its identical taught promotion — else `MISSING_FACT, reason=partial_group`. Plain `ask()` on a member's relation abstains with `partial_group` (it never answers half a claim). A proposed original left over after promotion does not block its own group. Groups are single-subject: table groups hang off a document entity (e.g. "survey paragraph") with one row per cell.

## 5. Adapters

`to_v1()`: link/empty raise (dropped by `project_to_v1`); grouped members project as ordinary rows tagged `[group <id>]` in the raw source string plus `provenance["group_id"]`; ungrouped rows delegate exactly. v2-only readers see ungrouped rows natively, grouped rows as ordinary rows (extra key ignored), no-value rows not at all.

## 6. The 17 gold rows

10 empty (W13 fragment, W19/W20/W22/W23/W24/W27 absent, W21/W25/W30 fragment), 2 link (A19/A20 metadata), 5 groups (W26 2 cells, W28 2 cells with shared qualifier, W29 2 cells, A17 3 claims, A18 3 list items with list-index qualifiers). 17/17 rescued; per-extension counts in RESULTS.md. A19/A20 link URLs point at the paper pages — exact code targets were not fetched offline, and the quotes say so.

## 7. Honest scope

Fit labels are one reader's judgement against the real WebRED dev lines and the doc-49 abstract notes. Group promotion is all-or-nothing per member: promoting 1 of 3 leaves the group unanswerable by design. The comparison kind (doc 56 extension 3) is not built — W28's percentages are plain numbers with qualifiers, which the gate already handles.

## What it means / What it does not mean

It means absence is now data (a reason, not silence) and multi-row claims answer atomically or not at all — the two moves every surveyed system in doc 56 uses, with the smallest code that holds all 17. It does not mean the notebook believes anything new: no-value rows never answer, groups answer only fully promoted, and a gold row records what a sentence states, never whether it is true.

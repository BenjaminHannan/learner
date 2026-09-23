# 56 — Scientific claim rows: what others do, what rescues our 17 (research scout)

Source docs: thought-row schema `scripts/fable_thought49_schema.py`; hand-map in `design/v3/30-modes/49-thought-format-v2-opus.md` §5/§6 (33/50 representable, **17/50 not**: WebRED dev N=13 — #13 fragment, #19–#30 minus Q/C rows — plus arXiv N=4: #17 multi-claim, #18 "three key innovations" list, #19–#20 code-URL metadata). Rules per brief 48: additive only, no commits, Mac CPU, claims ≤ evidence.

## 1. Survey (row shape, conditions/comparisons/lists, licence)

**SciFact** (Wadden et al. 2020). Row = `{id, claim: atomic sentence, evidence: {doc_id: [{sentences, label SUPPORT|CONTRADICT}]}, cited_doc_ids}` — claim stays plain text; structure lives in the evidence links. Compound claims must be split ("travel 6 feet" / "remain 3 hours" = two rows). Lists/conditions/comparisons: split, never nested. Sources: paper https://aclanthology.org/2020.emnlp-main.609, schema https://github.com/allenai/scifact/blob/master/doc/data.md, HF https://huggingface.co/datasets/allenai/scifact. Licence: claims+annotations **CC BY 4.0**, abstracts **ODC-By 1.0**, code Apache-2.0 (https://raw.githubusercontent.com/allenai/scifact/master/LICENSE.md).

**Nanopublications.** Row = 4 named RDF graphs: head + assertion (1+ triples, the claim) + provenance (method, attribution, time) + publication info. Conditions go in extra assertion triples or provenance; comparisons are reified associations (CoreKB gene–cancer facts published as 197,511 nanopubs). Sources: https://arxiv.org/pdf/1809.06532v1, https://ceur-ws.org/Vol-3643/paper2.pdf, schema https://github.com/Nanopublication/Guidelines/blob/master/nschema.html. Licence: varies by dataset; CoreKB paper is CC BY 4.0; base spec licence not found.

**Super-pattern + AIDA** (Bucur et al. 2021–2023). Claim = one AIDA sentence (Atomic, Independent, Declarative, Absolute) + 5-slot formalization: context, subject, qualifier/modal, relation, object. Conditions live in the **context** slot — the direct ancestor of our qualifiers. Sources: https://arxiv.org/pdf/2109.12907, https://peerj.com/articles/cs-1159, https://arxiv.org/abs/2203.01608. Licence: papers OA (PeerJ CC BY / arXiv); ontology licence not found.

**Wikidata statements.** Row = item–property–value + **qualifiers** (restrictive: point-in-time P585, applies-to-jurisdiction P1001; non-restrictive: determination-method P459) + references + rank; plus explicit **no-value / unknown-value**. Lists = multiple statements; comparisons = qualifiers on one statement. Closest to our v2. Sources: https://www.wikidata.org/wiki/Help:Qualifiers, https://www.wikidata.org/wiki/Wikidata:Data_model. Licence: **CC0 1.0** (data); statement text not found as separate licence — data CC0 per Wikimedia.

**Evidence Inference** (Lehman/DeYoung 2019–2020). Row = **ICO prompt** (Intervention, Comparator, Outcome) + label (increase/decrease/no-difference) + evidence span. The only schema with comparison as a first-class slot — our v2 has no equivalent. Sources: https://evidence-inference.ebm-nlp.com/, https://github.com/jayded/evidence-inference, https://aclanthology.org/2020.bionlp-1.13. Licence: code **MIT** (repo); annotation licence not found.

**SciClaim fine-grained graphs** (Magnusson & Friedman 2021). Row = reified **association node** + factor entities + fine-grained attributes (causal, comparative, predictive, statistical, proportional) over 901 sentences / 12,738 labels. Handles comparisons/hedges/stats without splitting. Source: https://arxiv.org/abs/2109.10453v1. Licence: not found (repo https://github.com/siftech/SciClaim gives no licence file I could verify).

**ORKG templates + Comparisons.** Row = Paper → Contribution → template slots (problem, method, dataset, metric, result); a **Comparison** table aligns one template across dozens of papers (e.g. algorithm scores). Lists/conditions/comparisons are native (multi-slot rows, tabular compare). Sources: https://orkg.org/about, https://arxiv.org/pdf/1901.10816. Licence: published data **CC0 1.0**, code **MIT** (https://orkg.org/page/license).

**S2ORC / SemOpenAlex / OpenAlex.** Not claim rows: paper-level metadata + structured full text + citation contexts (S2ORC 81.1M papers / 8.1M full texts). Useful as the *sentence source*, not the row. Sources: https://arxiv.org/abs/1911.02782, https://arxiv.org/pdf/2308.03671. Licence: SemOpenAlex + OpenAlex **CC0** (https://openalex.org, https://explore.openalex.org/about); S2ORC abstract-corpus licence not found (mixed publisher rights) — do not ingest blindly.

**SciTLDR / TLDRs** (Cachola et al. 2020). Row = `{source sentences, paper_id, target: [author-tldr, reviewer-tldrs...], title}` — extreme summary, no structure, no conditions slot. Source: https://github.com/allenai/scitldr, https://aclanthology.org/2020.findings-emnlp.428. Licence: code **Apache-2.0** (repo LICENSE); dataset card licence field **unknown** (https://huggingface.co/datasets/allenai/scitldr) — treat as not-found, do not train on it.

**2024–2026 claim-extraction work (verified).** All keep the claim as **plain text** plus labels — none proposes a structured row richer than Wikidata/ORKG: SciClaims 2025 end-to-end Llama-3-8B extract→retrieve→verify with SUPPORT/REFUTE/NEI + rationale (https://arxiv.org/abs/2503.18526); Context24 2024, 585 claims grounded to figures/tables/method snippets (https://aclanthology.org/2024.sdp-1.3/); NSF-SciFy 2025, 2.8M zero-shot-extracted claims (https://aclanthology.org/2025.newsum-main.13); SciClaim-Dataset 2025, 2,391 sentences Claim/Evidence/Neither, **CC BY-NC 4.0** (https://github.com/Lynnnx/SciClaim-Dataset).

## 2. Map: which idea holds each of our 17

- A17 (SSA "sota + adapts + superior" multi-claim): SciFact atomic split; nanopub bundle; SciClaim association nodes. → needs **group**.
- A18 ("three key innovations" list): ORKG multi-slot template; Wikidata multi-statements; SciFact 3 atomic rows. → needs **group**.
- A19/A20 (code-URL metadata): nanopub pubinfo graph; Wikidata reference, never a claim. → needs **link/non-claim kind**.
- W13 fragment / W21 title fragment / W25 byline-only: Wikidata **no-value**; nanopub requires quote-or-nothing. → needs **no-value**.
- W19/W20/W22/W23/W24/W27/W30 (relation absent — name clash, sales-tax, club, holiday, publisher, fort, legend): Wikidata no-value + rank deprecated; SciFact NEI. Ears must NO_FACT today; a no-value row records *why*. → needs **no-value**.
- W26/W28/W29 (economics tables, survey %, geology text): ORKG Comparison (one row per table cell, grouped); Evidence Inference ICO for W28's percentages. → needs **group** (+ comparison for W28).

## 3. Smallest extensions, ranked (rescue counts, overlaps noted)

1. **`metadata` value kind + `no_value` flag (12/17).** New value kinds `link` (URL-only sentence) and `empty` with reason (`fragment | absent | metadata`), mirrored as `proposed`, never answering. Rescues W13, W19–W25, W27, W30 (10) + A19, A20 (2). Idea from: Wikidata no-value, nanopub pubinfo, SciFact NEI.
2. **`group_id` linking rows into one claim (5/17).** Optional string shared by 2+ rows; ask-gate requires all members to match (borrow: nanopub head graph, SciFact atomic split, ORKG Comparison). Rescues A17 (3 rows), A18 (3 rows), W26/W28/W29 (table → cell rows). Overlaps #1 on W28 only as alternative.
3. **`comparison` value kind (3/17).** `{baseline, metric, direction, delta?}` — borrow Evidence Inference ICO + SciClaim comparative attribute. Rescues A17's "superior" arm, W28's percentages, W22's tax comparison (alternative to no-value where a real comparison exists). Smallest code: one new Value kind + qualifier convention.

## 4. One sealed-mark experiment (plain software, Mac CPU)

Gold-hand-split A17/A18/W26/W28/W29 into grouped rows + mark all 12 no-value cases; write PASSMARKS.md (≥4/5 groups byte-identical on re-split; 0 answers from no-value/link rows through `ask()`; `to_v1()` unchanged for ungrouped rows), `shasum -a 256 PASSMARKS.md > SEAL.sha256.txt`, then run one offline splitter once, report per-case rescue counts. No training, no installs.

## What it means / What it does not mean

It means: every surveyed system either splits multi-claims (SciFact), bundles rows (nanopubs/ORKG), or marks absence explicitly (Wikidata no-value) — our v2 needs the same three moves, and the ranking above says which to build first. It does not mean any of these schemas is endorsed for import: several licences are not found or non-commercial (SciClaim-Dataset CC BY-NC, SciTLDR unknown), and none replaces our taught-only answerability or append-only chain.

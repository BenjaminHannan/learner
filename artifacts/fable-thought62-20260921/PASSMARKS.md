# PASSMARKS — Experiment 62: thought v3 groups + no-value rows (sealed BEFORE the run)

Wrapper `scripts/fable_thought62_schema.py` imports v2, never edits it.
Conformance `scripts/fable_thought62_conformance.py`. One offline run, Mac CPU.

| mark | bar (must meet) | what is counted |
|---|---|---|
| T1 | 32/32 contract lifecycle cases pass through the wrapper | `fable_notebook_contract.run_suite` via wrapper factory, integer count |
| T2 | >= 20/20 new wrapper cases pass | new cases: empty/link never answer; partial group abstains; full group answers; to_v1 round trip; hash chain intact |
| T3 | rescued >= 15/17 sentences representable (count per extension) | gold rows for W13, W19–W30, A17–A20; per-row verdict + which extension (empty/link/group) or still-not-representable + why |
| T4 | 0 answers from empty/link rows | every ask/ask_group over an empty/link row returns MISSING_FACT, never OK |
| T5 | v1 adapter unchanged on ungrouped rows | wrapper `to_v1()` byte-identical to v2 `ThoughtV2.to_v1()` on all ungrouped v2 conformance rows |

Verdict rule: PASS iff all five bars met. A registered FAIL stays a FAIL (never re-run into a pass).
Seeds: none (plain software, deterministic; content hashes asserted, not seeds).

What it means: the wrapper adds absence-marking and claim-bundling without weakening any v2 guarantee.
What it does not mean: it does not claim the gold rows are factually true — they record what the sentence does or does not state.

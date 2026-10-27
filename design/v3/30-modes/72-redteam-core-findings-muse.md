# 72 — Red-team core findings (2026-09-21, redteam67, read-only probe)

Red-team pass over the plain-software core before a human talks to it. Probed: the notebook contract, listening M1, reasoner50 + qual56, thought49/62 row wrappers, the agent-loop glue. Method: 69 adversarial ACTION SEQUENCES (full log in `artifacts/fable-redteam67-20260921/probe-results.json`, runner `scripts/fable_redteam67_probe.py`). Nothing was fixed; this doc only ranks what to fix.

## Integer summary

cases 69 | OK 64 | BUG 3 (critical 1, high 0, medium 2, low 0) | UNCLEAR 2

## Finding 1 (critical) — ThoughtNotebook.ask breaks doc-56 rule 2

Setup: non-functional relation, one unqualified taught row and one qualified taught row both active for the same subject+relation, question carries the matching qualifier. Doc 56 rule 2: the unqualified row always wins, even for a qualified question. qual56 obeys (answers "Ana"); `ThoughtNotebook.ask` returns multi "Mira, Ana", serving the conditioned claim as unconditioned fact. Silent wrong answer content with status OK — the worst kind before a human reads it. Suggested direction: apply rule-2 priority inside `ThoughtNotebook._gate` (drop qualified rows whenever an unqualified taught row is present), so both readers share one gate. Reproducer (12 lines, repo root):

    import sys; sys.path.insert(0, 'scripts')
    import fable_qual56_reasoner as Q56
    from fable_thought49_notebook import ThoughtNotebook
    from fable_thought49_schema import ThoughtV2, Value, Qualifier, Provenance
    tnb = ThoughtNotebook('scratchpad/rt66mini'); nb = tnb.nb
    nb.declare_relation('r', 'friend', False)
    t = nb.new_entity('e1', 'Tom').detail['entity_id']; a = nb.new_entity('e2', 'Ana').detail['entity_id']; m = nb.new_entity('e3', 'Mira').detail['entity_id']
    mk = lambda v, qs=(): tnb.add_thought(ThoughtV2(subject=t, relation='friend', value=Value.of_entity(v), provenance=Provenance(document='d', sentence='s', claimed_by='taught'), qualifiers=qs, source='taught'), event_id='q'+v)
    mk(a); mk(m, (Qualifier('when', Value.of_date('2019')),))
    print(tnb.ask('Tom', ['friend'], qualifiers={'when': '2019'}).detail.get('answer'))  # Mira, Ana (wrong per doc 56)
    print(Q56.QualifierAwareReasoner().answer({'name': 'Tom', 'relations': ['friend'], 'qualifiers': {'when': '2019'}}, nb)['fields'].get('answer'))  # Ana

## Finding 2 (medium) — qual56 can never match a boolean qualifier given as bool

Same boolean-qualified row, question `{"open": True}`: ThoughtNotebook answers OK, qual56 abstains MISSING_FACT. Root cause: `value_equals` compares `str(True)` (`"True"`) against the stored literal `"true"` — never equal, so boolean qualifiers are dead input through qual56 although the question format explicitly allows bools. Wrong status code in one of two shipped readers. Suggested direction: give `value_equals` the same bool branch `_value_matches` already has, plus a shared conformance pair both wrappers must pass. Reproducer (11 lines):

    import sys; sys.path.insert(0, 'scripts')
    import fable_qual56_reasoner as Q56
    from fable_thought49_notebook import ThoughtNotebook
    from fable_thought49_schema import ThoughtV2, Value, Qualifier, Provenance
    tnb = ThoughtNotebook('scratchpad/rt65mini'); nb = tnb.nb
    e = nb.new_entity('e', 'Mira').detail['entity_id']
    tnb.add_thought(ThoughtV2(subject=e, relation='city', value=Value.of_text('Lisbon'), provenance=Provenance(document='d', sentence='s', claimed_by='taught'), qualifiers=(Qualifier('open', Value.of_boolean(True)),), source='taught'), event_id='q')
    print(tnb.ask('Mira', ['city'], qualifiers={'open': True}).status)  # OK
    print(Q56.QualifierAwareReasoner().answer({'name': 'Mira', 'relations': ['city'], 'qualifiers': {'open': True}}, nb)['status'])  # MISSING_FACT

## Finding 3 (medium) — last-line edits evade the hash chain

The contract docstring claims editing is detected on load; middle-line edits are (LogCorrupt, verified). But the newest line has no successor verifying its hash, so rewriting its value loads silently and is answered (`HACKED`). Precondition is filesystem write access — and anyone with that can already append valid-looking events — so this is a docstring overclaim plus a small integrity gap, not an exploitable hole. Suggested direction: one sentence in the docstring scoping tamper detection to non-tail lines, or a `verify_full` that re-hashes every line against its successor at startup. Reproducer (13 lines):

    import sys, json; sys.path.insert(0, 'scripts')
    import fable_notebook_contract as C
    nb = C.Notebook('scratchpad/rt49mini'); nb.declare_relation('r', 'city', True)
    e = nb.new_entity('e', 'Mira').detail['entity_id']
    nb.assert_fact('f', 'listening', 'taught', e, 'city', {'literal': 'Lisbon'})
    p = 'scratchpad/rt49mini/events.jsonl'
    lines = [l for l in open(p).read().split(chr(10)) if l.strip()]
    d = json.loads(lines[-1]); d['value'] = {'literal': 'HACKED'}
    lines[-1] = json.dumps(d, sort_keys=True, ensure_ascii=False)
    open(p, 'w').write(chr(10).join(lines) + chr(10))
    print(C.Notebook('scratchpad/rt49mini').ask('Mira', ['city']).detail.get('answer'))  # HACKED, no error

## Explicit non-findings (held under attack)

Corrections/supersede chains, CONFLICT gating, alias AMBIGUOUS-never-merge, self-reference and 2-cycles terminate, 8-hop OK / 9-hop BAD_REQUEST, quarantine/proposed never answer, promote rights, inferred invalidation on dep retract, taught-beats-inferred/sleep-derived, 2-domain web-verified rule with spoken suffix, retract-then-reteach, unicode/500-char/case-folded names, torn-tail repair, reasoner50 == contract on all parity frames including cache invalidation, bare-question qualifier abstention (`reason=qualified`, both wrappers), 10k facts with intact chain (write 5.7 s, load 0.1 s, query 1.7 ms). Unclear, not bugs: empty literals are stored+answered (contract silent); the loop's FakeEars refuses 4-hop questions (declared stub scaffolding).

## What it means / does not mean

Means: the M1 contract core is trustworthy as probed; fix Finding 1 before any human sees qualified multi-answers, and Findings 2–3 are cheap. Does not mean the system is safe end to end: English ears, mouth wording, and sleep mining were out of scope and unprobed.

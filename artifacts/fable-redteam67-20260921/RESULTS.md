# RESULTS — redteam67 adversarial probe of the plain-software core (2026-09-21)

Result first: 69 adversarial action-sequences, 64 OK, 3 real bugs (1 critical, 2 medium), 2 unclear. The notebook contract itself is solid; all 3 bugs sit in the layers around it (qualifier wrappers x2, hash-chain tail x1). Nothing was fixed (red-team rules).

## Integer summary

cases 69 | OK 64 | BUG 3 (critical 1, high 0, medium 2, low 0) | UNCLEAR 2

## What was tested

`scripts/fable_redteam67_probe.py` drives the real modules (never English): contract writes/reads, corrections, retracts, promotes, inferred/sleep/web rows, aliases, cycles, 0/8/9-hop edges, tamper + torn-tail, 10,000 facts, reasoner50-vs-contract parity frames, ThoughtNotebook-vs-qual56 qualifier agreement, listening doorway, agent-loop roundtrip. Each case states the expected rule from the contract docstring, then records observed + verdict.

## BUG-1 (critical): qualified claim leaks into an unconditioned answer — ThoughtNotebook.ask

Non-functional relation with an unqualified taught row AND a qualified taught row both active, question carries the matching qualifier. Doc 56 rule 2 says the unqualified row always wins, even then. qual56 obeys it (answers "Ana"); `ThoughtNotebook.ask` returns a multi answer "Mira, Ana", presenting the conditioned claim as fact. Silent wrong answer content.

Reproducer (run from repo root, 12 lines):

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

## BUG-2 (medium): qual56 can never satisfy a boolean qualifier passed as bool

Same boolean-qualified row, question `{"open": True}`. ThoughtNotebook answers OK; qual56 abstains MISSING_FACT. Cause: `value_equals` stringifies the bool (`str(True)` = `"True"`) and compares to the stored literal `"true"` — never equal, so bool qualifiers are dead through qual56. Wrong status code in one wrapper.

Reproducer (11 lines):

    import sys; sys.path.insert(0, 'scripts')
    import fable_qual56_reasoner as Q56
    from fable_thought49_notebook import ThoughtNotebook
    from fable_thought49_schema import ThoughtV2, Value, Qualifier, Provenance
    tnb = ThoughtNotebook('scratchpad/rt65mini'); nb = tnb.nb
    e = nb.new_entity('e', 'Mira').detail['entity_id']
    tnb.add_thought(ThoughtV2(subject=e, relation='city', value=Value.of_text('Lisbon'), provenance=Provenance(document='d', sentence='s', claimed_by='taught'), qualifiers=(Qualifier('open', Value.of_boolean(True)),), source='taught'), event_id='q')
    print(tnb.ask('Mira', ['city'], qualifiers={'open': True}).status)  # OK
    print(Q56.QualifierAwareReasoner().answer({'name': 'Mira', 'relations': ['city'], 'qualifiers': {'open': True}}, nb)['status'])  # MISSING_FACT

## BUG-3 (medium): editing the LAST log line evades the hash chain

The docstring says editing is detected on load. True for middle lines (RT49a: LogCorrupt correctly raised). But the newest line has no successor checking its hash, so changing its value loads silently and is answered (`HACKED`). Precondition is filesystem write access (an attacker with that can also append valid events, so impact is limited) — still a docstring overclaim worth a sentence in the contract.

Reproducer (13 lines):

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

## Unclear (2, not bugs)

- RT40: empty-string literal is stored and answered (`''`); the contract is silent on emptiness. Design gap, no crash, no wrong status.
- RT68: the agent loop teaches/asks fine, but a 4-hop question is refused by the FakeEars 3-hop stub limit. Declared scaffolding, not the core; noted only.

## Strong passes (spot list)

Duplicate/correction/supersede chains, CONFLICT-then-correct, alias collisions (AMBIGUOUS, never merged), self-reference + 2-cycles terminate, 8-hop OK / 9-hop BAD_REQUEST, quarantine + proposed never answer, promote gating, inferred invalidation on dep retract, taught-beats-inferred/sleep, 2-domain web-verified rule with the spoken suffix, retract-then-reteach, unicode/500-char/case-folded names, torn-tail repair, reasoner50 == contract on every parity frame incl. cache invalidation, qualified bare-question abstention with reason `qualified` (both wrappers), 10,000 facts: chain intact, write 5.7 s, load 0.1 s, query 1.7 ms.

## What it means / what it does not mean

Means: the M1 contract core keeps every guarantee probed; the two qualifier implementations disagree in 2 spots and the tail-line edit is silent — fix those before a human trusts qualified answers. Does not mean: the system is safe end to end — English ears, mouth wording, and sleep mining were not probed here.

## Deviations

Two probe-side (not code) corrections during the run: RT42's event-count arithmetic fixed (1 FACT event, not 3); RT49 split into 49a (true middle line, detected) and 49b (tail line, silent) after realising a 3-event log has no true middle line.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_redteam67_probe.py` — full JSON in this folder (`probe-results.json`). Questions for Ben: none.

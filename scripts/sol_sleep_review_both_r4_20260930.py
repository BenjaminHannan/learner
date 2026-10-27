#!/usr/bin/env python3
"""Reuse r2 synthetic cases against pinned v1/v2; no model/data imports."""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pins = {
    'v1': '8f48c553f24147b697c98be8e396afdb96e0d2282dda47922fff138903f153b7',
    'v2': '1b011c35408b2db968d44c215c90818e6244563b5406e37983cd30c1f8bfbb2b',
}
fixture = ROOT / 'scripts/sol_sleep_review_contracts_r2_20260930.py'
template = fixture.read_text()
outputs = {}
normalized = {}
for version, pin in pins.items():
    path = ROOT / ('scripts/sol_sleep_ordered_' + version + '.py')
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == pin, 'source changed'
    tree = ast.parse(data)
    run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    start = next(i for i,n in enumerate(run.body)
                 if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "restored['ledger']")
    block = run.body[start:start+9]
    assert ast.unparse(block[-1]).startswith("write(out / 'night-ledger.json'")
    names = {'guard_decision','exact_sentence','validate_guard_rows','verify_files'}
    normalized[version] = [ast.dump(n, include_attributes=False) for n in tree.body
                           if isinstance(n,ast.FunctionDef) and n.name in names]
    normalized[version].append(ast.dump(ast.Module(body=block,type_ignores=[]),include_attributes=False))
    adapted = template.replace("'sol-ordered-night-v1'", repr('sol-ordered-night-'+version))
    adapted = adapted.replace('361 <= n.lineno <= 370', f'{block[0].lineno} <= n.lineno <= {block[-1].lineno}')
    adapted = adapted.replace("bad_label_mask, True)", "bad_label_mask, False)")
    extra_cases = """    case('empty labels reject eagerly', lambda f: f['after'][0].update(labels=[[]], label_mask=[[]]), False)
    case('all ignored labels reject eagerly', lambda f: f['after'][0].update(labels=[[-100]], label_mask=[[False]]), False)
    case('integer mask rejects eagerly', lambda f: f['after'][0].update(label_mask=[[1,1,0]]), False)
    case('Boolean target ID rejects eagerly', lambda f: f['after'][0].update(labels=[[True,2,-100]]), False)
    case('two label rows reject eagerly', lambda f: f['after'][0].update(labels=[[17],[2]], label_mask=[[True],[True]]), False)

"""
    adapted = adapted.replace('    # Execute only the new ledger', extra_cases + '    # Execute only the new ledger')
    env = {'__file__':str(fixture), '__name__':'synthetic_fixture'}
    exec(compile(adapted,str(fixture),'exec'),env)
    env.update(SOURCE=path, PIN=pin)
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture):
        env['main']()
    outputs[version] = json.loads(capture.getvalue())
assert normalized['v1'] == normalized['v2'], 'reviewed fix blocks differ'
receipt = {
    'pins': pins,
    'command': 'python3 -B scripts/sol_sleep_review_both_r4_20260930.py',
    'shared_guard_helpers_and_ledger_finalization_AST_identical': True,
    'F1': 'Resolved in both: actual finalization source with mocked storage produces equal resume/JSON ledgers; real torch serialization unrun.',
    'F2': 'Resolved in both: inflated noise, missing/modified repeat and honest CE regression rejected.',
    'F3': 'Original reproductions resolved in both: stale input hash, missing/duplicate/reordered guard IDs, changed plan and malformed input mask rejected.',
    'residual': 'RESOLVED in both: formerly accepted invalid label mask now rejects; empty/all-ignored labels, integer masks, Boolean token IDs and multiple label rows also reject eagerly.',
    'scope': '50 of 50 expected synthetic observations: 23 negative cases reject and 2 positive/mock-finalization cases succeed per version; no models/corpus/checkpoints, training or inference. Actual night not shown; queued25 still required.',
    'day_boundary': 'v2 day callback source inspected (pinned loader, bundle, IDs/origins). Day branch not executed: no day rows, model/data imports, or full release-binding validation. F1/F2/F3 plus residual only.',
    'results': outputs,
}
out = ROOT / 'artifacts/sol-sleep-review-20260930/recheck-both-r4.json'
with out.open('x') as f:
    json.dump(receipt,f,indent=2)
    f.write('\n')
print(json.dumps({k:v for k,v in receipt.items() if k != 'results'},indent=2))

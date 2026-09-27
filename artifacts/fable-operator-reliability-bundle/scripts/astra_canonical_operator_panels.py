"""Additive panel construction, label separation and overlap auditing."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import random
import time

import astra_canonical_operator as A
import premonition_memnn_compare as C

ROOT, torch, data = A.data.ROOT, A.torch, A.data
OUT = ROOT/'artifacts/astra-canonical-operator-screen-20260920'
NAMESPACE = 'canonical-operator-screen-v1'


def load(path):
    path = Path(path)
    if path.name == 'test.pt':
        raise ValueError('test.pt is prohibited')
    return torch.load(path, map_location='cpu', weights_only=False)


def chunks(panel):
    """Yield only visible Inputs plus evaluator-owned targets, in stable order."""
    import premonition_handoff_diag as H
    for chunk in panel['chunks']:
        if 'sides' in chunk:
            yield chunk['sides']
        elif 'inputs' in chunk:
            yield {'a': (chunk['inputs'], chunk['targets'])}
        else:
            yield {s: (data.from_batch(H._strip_labels(chunk[s])),
                       [m[f'answer_{s}'][0] for m in chunk['meta']])
                   for s in ('a', 'b') if s in chunk}


def generate(name, n=512, namespace=NAMESPACE, spec=None, extra_link=False):
    """Preserve existing single/pair generation semantics with a new RNG namespace."""
    data.bootstrap()
    import premonition_pair_suite as PS
    from premonition.toy_ladder import LadderSpec
    spec = spec or LadderSpec()
    cfg = PS.CELLS[name]
    seed = 202609202000 + cfg['cell']
    sides = ['a', 'b'] if cfg['kind'] == 'pair' else ['a']
    records, rejections = [], Counter()
    for i in range(n):
        rng = random.Random(f'{namespace}:{name}:{seed}:{i}')
        if len(sides) == 2:
            ra, rb, where, facts, rej = PS._make_pair(spec, rng, cfg['edit'])
            rows = {'a': ra, 'b': rb}
        else:
            ra, where, facts, rej = PS._make_single(spec, rng, cfg['hops'], cfg['relation'])
            rows = {'a': ra}
        rejections.update(rej)
        converted = {}
        for side, lines in rows.items():
            question = lines[where].tokens[:lines[where].tokens.index(A.ANSWER)+1]
            if extra_link:
                assert len(question) == 5
                question = question[:3]+[A.LINK]+question[3:]
            memory = [[] if line.question else list(line.tokens) for line in lines]
            converted[side] = (memory, question, where, lines[where].answer[0])
        if len(sides) == 2:
            xa, xb = converted['a'][0], converted['b'][0]
            assert [len(r) for r in xa] == [len(r) for r in xb]
            assert sum(a != b for la, lb in zip(xa, xb) for a, b in zip(la, lb)) == cfg['token_diffs']
            vals = lambda mem: sorted(r[3] for r in mem if len(r) >= 4 and r[0] == 3 and 8 <= r[2] <= 10)
            assert vals(xa) == vals(xb)
        records.append(converted)
    packed = []
    for start in range(0, n, 32):
        block = records[start:start+32]
        item = {}
        for side in sides:
            vals = [r[side] for r in block]
            x = data.pack([r[0] for r in vals], [r[1] for r in vals], list(range(len(vals))), [r[2] for r in vals])
            targets = [p[-1]['target'] for p in A.truth_paths(x)]
            if not extra_link:
                assert targets == [r[3] for r in vals]
            item[side] = (x, targets)
        if len(sides) == 2:
            same = [a == b for a, b in zip(item['a'][1], item['b'][1])]
            assert all(same) if cfg['invariant'] else not any(same)
        packed.append({'sides': item})
    return dict(name=name, n=n, kind=cfg['kind'], invariant=bool(cfg.get('invariant')),
                chunks=packed, namespace=namespace, seed=seed, rejections=dict(rejections))


def signatures(panel):
    semantic, tensors = [], []
    for side_group in chunks(panel):
        for x, targets in side_group.values():
            paths = A.truth_paths(x)
            assert [p[-1]['target'] for p in paths] == list(targets)
            memory = x.memory.tolist()
            for owner, valid, q in zip(x.owner.tolist(), x.eligible.tolist(), x.questions.tolist()):
                mem = [r for r, ok in zip(memory[owner], valid) if ok]
                semantic.append(A.visible_signature(mem, q))
                tensors.append(A.tensor_signature(mem, q))
    return semantic, tensors


def prepare():
    data.bootstrap()
    torch.set_num_threads(1)
    import premonition_pair_suite as PS
    folder = OUT/'astra_canonical_operator_panels'
    folder.mkdir(exist_ok=False)
    result, audit, all_sem, all_tensor = {}, {}, set(), set()
    for name, cfg in PS.CELLS.items():
        panel = generate(name)
        sem, ts = signatures(panel)
        assert len(set(sem)) == len(sem) and len(set(ts)) == len(ts), 'within-panel duplicate'
        assert not all_sem.intersection(sem) and not all_tensor.intersection(ts), 'new-panel overlap'
        all_sem.update(sem); all_tensor.update(ts)
        path = folder/f'{name}.pt'
        torch.save(panel, path)
        key = f'c{cfg["cell"]}'
        result[key] = dict(path=str(path), sha256=C.sha(path), cutoff=487 if cfg['cell'] <= 2 else 461,
                           n=512, fresh=True, namespace=NAMESPACE, seed=panel['seed'])
        audit[key] = dict(sides_audited=len(sem), interpreter_correct=len(sem), unique_semantics=len(set(sem)),
                         unique_tensor_inputs=len(set(ts)), answer_and_edit_audit=True)
    stress_manifest = ROOT/'artifacts/codex-token-memory-20260920/stress/manifest.json'
    stress = json.loads(stress_manifest.read_text())
    for name, row in stress['panels'].items():
        key = 's3' if name == 'three-hop-heldout' else f'p12-{name.split("-c")[1][0]}'
        assert C.sha(row['path']) == row['sha256']
        result[key] = dict(path=row['path'], sha256=row['sha256'], cutoff=487 if key in ('p12-1','p12-2') else 461,
                           n=512, fresh=False)
    historical = {}
    for name, row in json.loads((ROOT/'artifacts/codex-token-memory-20260920/plan.json').read_text())['fresh_panels'].items():
        historical[f'old-fresh/{name}'] = dict(path=row['path'], sha256=row['sha256'])
    old = json.loads(C.PANEL.read_text())
    for name, row in old['cells'].items():
        path = ROOT/row['file']
        historical[f'old-original/{name}'] = dict(path=str(path), sha256=row['sha256'])
    historical.update({k: v for k, v in result.items() if not v['fresh']})
    old_audit = {}
    for name, row in historical.items():
        assert C.sha(row['path']) == row['sha256']
        sem, ts = signatures(load(row['path']))
        overlap_s, overlap_t = len(all_sem.intersection(sem)), len(all_tensor.intersection(ts))
        assert overlap_s == overlap_t == 0, f'new/old panel overlap: {name}'
        old_audit[name] = dict(sides=len(sem), semantic_overlap=overlap_s, tensor_overlap=overlap_t,
                              path=row['path'], sha256=row['sha256'])
    # Include reused stress in the training exclusion set; targets are not saved here.
    for key, row in result.items():
        if not row['fresh']:
            sem, ts = signatures(load(row['path']))
            assert len(set(sem)) == len(sem) and not all_sem.intersection(sem)
            all_sem.update(sem)
            all_tensor.update(ts)
            audit[key] = dict(sides_audited=len(sem), interpreter_correct=len(sem), unique_semantics=len(set(sem)))
    excluded = folder/'forbidden-semantics.json'
    C.write_new(excluded, sorted(all_sem))
    report = dict(created_unix=time.time(), fresh=audit, historical=old_audit,
                  duplicate_or_overlap_failures=0, fresh_side_count=4608,
                  exclusion_count=len(all_sem), canonicalized_entities='literal existing entity IDs',
                  exclusion_path=str(excluded), exclusion_sha256=C.sha(excluded))
    C.write_new(OUT/'astra_canonical_operator_panel_audit.json', report)
    C.write_new(OUT/'astra_canonical_operator_panels.json', result)
    return dict(cells=list(result), exclusion_count=len(all_sem), all_passed=True)


if __name__ == '__main__':
    print(json.dumps(prepare()), flush=True)

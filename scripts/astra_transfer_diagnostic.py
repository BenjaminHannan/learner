"""Additive eval-only localisation of saved token-memory B/C checkpoints.

See PREDICTIONS.md for frozen hypotheses. Native inference imports unmodified
registered code. Oracle interventions change only attention eligibility or the
visible question in a reset forward; they are never presented as native scores.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import gzip
import json
from pathlib import Path
import platform
import sys
import time
import traceback

import premonition_token_memory as T
import premonition_token_memory_run as R
import premonition_token_evidence_run as ER
import premonition_token_scaled_run as SR
import premonition_memnn_compare as C

torch, data = T.torch, T.data
ROOT = data.ROOT
OUT = ROOT / 'artifacts/astra-transfer-diagnostic-20260920'
REFERENCE = ROOT / 'artifacts/codex-token-memory-20260920'
ARMS = {'B': ROOT / 'artifacts/codex-token-evidence-20260920',
        'C': ROOT / 'artifacts/codex-token-scaled-20260920'}
CATEGORIES = ['link', 'endpoint', 'decoy', 'endpoint_other_relation', 'filler', 'other_fact', 'null']
ERRORS = ['c_link_entity', 'e_other_nonvalue', 'b_decoy', 'a_endpoint_other_relation',
          'd_other_person_same_relation', 'f_other_value']


def write_new(path, value):
    C.write_new(path, value)


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def configure():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    data.bootstrap()


def load_plan(arm):
    return (ER if arm == 'B' else SR).load(ARMS[arm])


def freeze():
    paths = {Path(__file__), ROOT / 'tests/test_astra_transfer_diagnostic.py',
             OUT / 'PREDICTIONS.md', ROOT / 'runtime.local.json'}
    for arm in ARMS:
        p = load_plan(arm)
        for key in ['sources', 'evidence_sources', 'scaled_sources']:
            paths.update(ROOT / name for name in p.get(key, {}))
        paths.add(ARMS[arm] / 'plan.json')
        for name in ['reference_plan', 'parent_plan']:
            if name in p:
                paths.add(Path(p[name]))
        paths.update(Path(row['path']) for row in p['fresh_panels'].values())
        for seed in range(3):
            paths.update(ARMS[arm] / f'seed-{seed}' / n for n in
                         ['model.pt', 'training.json', 'fresh-evaluation.json'])
    check(all(p.name != 'test.pt' for p in paths), 'test.pt is forbidden')
    manifest = {'created_unix': time.time(), 'preregistration_sha256': C.sha(OUT / 'PREDICTIONS.md'),
                'files': {str(p.relative_to(ROOT)): C.sha(p) for p in sorted(paths)},
                'python': sys.version, 'torch': torch.__version__, 'platform': platform.platform(),
                'threads': torch.get_num_threads(), 'interop_threads': torch.get_num_interop_threads(),
                'device': 'cpu', 'jobs': [[a, s] for a in ARMS for s in range(3)]}
    write_new(OUT / 'manifest.json', manifest)
    print(json.dumps({'frozen_files': len(paths), 'manifest_sha256': C.sha(OUT / 'manifest.json')}), flush=True)


def verify_manifest():
    m = json.loads((OUT / 'manifest.json').read_text())
    bad = [n for n, h in m['files'].items() if C.sha(ROOT / n) != h]
    check(not bad, f'Frozen inputs changed: {bad}')
    return m


def token_line_ids(x):
    """Independently reconstruct compaction identities; trailing column is NULL."""
    v, lines, width = x.memory.shape
    real = x.memory.ne(0).flatten(1)
    size = max(1, int(real.sum(1).max()))
    ids = torch.full((v, size + 1), -1, dtype=torch.long)
    source = torch.arange(lines).repeat_interleave(width)
    for owner in range(v):
        n = int(real[owner].sum())
        ids[owner, :n] = source[real[owner]]
    return ids[x.owner]


def line_attention(x, attention):
    """[question, step, head, line+NULL], last *question* row only."""
    q, steps, heads, _, tokens = attention.shape
    last = x.questions.ne(0).sum(-1) - 1
    read = attention.gather(3, last[:, None, None, None, None].expand(q, steps, heads, 1, tokens)).squeeze(3)
    ids = token_line_ids(x)
    check(ids.shape[-1] == tokens, 'compaction width mismatch')
    line_count = x.memory.shape[1]
    index = torch.where(ids >= 0, ids, line_count)
    result = read.new_zeros(q, steps, heads, line_count + 1)
    result.scatter_add_(-1, index[:, None, None, :].expand_as(read), read)
    check(torch.allclose(result.sum(-1), torch.ones_like(result[..., 0]), atol=2e-6), 'lost attention mass')
    invalid_padding = ids.lt(0)
    invalid_padding[:, -1] = False
    check(bool((read.masked_select(invalid_padding[:, None, None, :].expand_as(read)) == 0).all()), 'padding attended')
    return result


def parse_facts(x, q, spec):
    """Evaluation-only parse of visible tokens, cross-checked against panel metadata."""
    question = x.questions[q][x.questions[q] != 0].tolist()
    check(len(question) == 5 and question[2] == spec.link, 'expected two-hop visible question')
    asker, rel = question[1], question[3]
    attrs, links, kinds = {}, {}, {}
    for i, row in enumerate(x.memory[int(x.owner[q])].tolist()):
        if not bool(x.eligible[q, i]):
            continue
        if len(row) >= 4 and spec.vocab_size <= row[1] < 68 and row[2] == spec.link:
            links[row[1]] = (row[3], i)
            kinds[i] = 'link_fact'
        elif len(row) >= 4 and spec.vocab_size <= row[1] < 68 and row[2] in [spec.relation(r) for r in range(spec.relations)]:
            attrs[row[1], row[2]] = (row[3], i)
            kinds[i] = 'attr_fact'
        else:
            kinds[i] = 'filler'
    endpoint, link_line = links[asker]
    target, endpoint_line = attrs[endpoint, rel]
    decoy, decoy_line = attrs[asker, rel]
    other = [attrs[endpoint, spec.relation(r)] for r in range(spec.relations) if spec.relation(r) != rel]
    cats = ['ineligible'] * (x.memory.shape[1] + 1)
    for i, kind in kinds.items():
        cats[i] = 'filler' if kind == 'filler' else 'other_fact'
    cats[link_line], cats[endpoint_line], cats[decoy_line] = 'link', 'endpoint', 'decoy'
    for _, i in other:
        cats[i] = 'endpoint_other_relation'
    cats[-1] = 'null'
    return {'asker': asker, 'relation': rel, 'endpoint': endpoint, 'answer': target,
            'link_line': link_line, 'endpoint_line': endpoint_line, 'decoy': decoy,
            'endpoint_other_values': [v for v, _ in other],
            'other_person_same_relation_values': [v for (e, r), (v, _) in attrs.items()
                                                  if e not in (asker, endpoint) and r == rel],
            'line_categories': cats}


def error_class(prediction, facts, spec):
    if prediction == facts['answer']:
        return 'correct', [], False
    is_value = spec.value(0) <= prediction < spec.value(spec.values)
    flags = []
    if prediction == facts['endpoint']:
        flags.append('c_link_entity')
    if not is_value:
        flags.append('e_nonvalue_inclusive')
    if prediction == facts['decoy']:
        flags.append('b_decoy')
    if prediction in facts['endpoint_other_values']:
        flags.append('a_endpoint_other_relation')
    if prediction in facts['other_person_same_relation_values']:
        flags.append('d_other_person_same_relation')
    if 'c_link_entity' in flags:
        primary = 'c_link_entity'
    elif not is_value:
        primary = 'e_other_nonvalue'
    else:
        primary = next((key for key in ERRORS[2:-1] if key in flags), 'f_other_value')
    # The c/e overlap is definitional. Value collision count concerns b/a/d.
    collision = sum(key in flags for key in ERRORS[2:-1]) > 1
    return primary, flags, collision


@torch.no_grad()
def routed(model, x, facts, mode, *, return_trace=False):
    ids = token_line_ids(x)
    targets = {0: torch.tensor([f['link_line'] for f in facts]),
               1: torch.tensor([f['endpoint_line'] for f in facts]),
               2: torch.tensor([f['endpoint_line'] for f in facts])}
    call = 0
    def hook(module, args):
        nonlocal call
        step = call
        call += 1
        apply = (step == 0 and 'L' in mode) or (step > 0 and 'E' in mode)
        if not apply:
            return None
        query, keys, values, valid = args
        restricted = valid & ids.eq(targets[step][:, None])
        check(bool(restricted.any(-1).all()), 'oracle line not eligible')
        return query, keys, values, restricted
    handle = model.read.cross_attention.register_forward_pre_hook(hook)
    try:
        out = model(x, trace=return_trace)
    finally:
        handle.remove()
    check(call == model.steps, 'wrong number of read calls')
    return out


def requery(x, facts):
    # Retain only ordinary question/answer delimiters, substitute endpoint, drop LINK.
    questions = torch.tensor([[int(x.questions[i, 0]), f['endpoint'], f['relation'],
                               int(x.questions[i, int(x.questions[i].ne(0).sum()) - 1])]
                              for i, f in enumerate(facts)], dtype=torch.long)
    return replace(x, questions=questions)


def paired(native, changed, target):
    n = [p == t for p, t in zip(native, target)]
    c = [p == t for p, t in zip(changed, target)]
    return {'correct': sum(c), 'n': len(c), 'gains': sum(b and not a for a, b in zip(n, c)),
            'losses': sum(a and not b for a, b in zip(n, c)),
            'both_correct': sum(a and b for a, b in zip(n, c))}


def summarize(rows):
    n = len(rows)
    masses = torch.tensor([r['category_mass_by_step_head'] for r in rows], dtype=torch.float64)
    native = [r['prediction'] for r in rows]
    target = [r['answer'] for r in rows]
    top = [dict(Counter(r['top_category_by_step'][s] for r in rows)) for s in range(3)]
    errors = Counter(r['error_primary'] for r in rows)
    membership = Counter(k for r in rows for k in r['error_memberships'])
    return {'n': n, 'native_correct': errors.get('correct', 0),
            'error_counts': {k: errors.get(k, 0) for k in ['correct'] + ERRORS},
            'error_membership_counts': dict(membership),
            'ambiguous_value_errors': sum(r['value_collision'] for r in rows),
            'a_or_b_errors': sum(bool(set(r['error_memberships']) & {'a_endpoint_other_relation', 'b_decoy'}) for r in rows),
            'category_order': CATEGORIES, 'mass_mean_by_step_head': masses.mean(0).tolist(),
            'mass_sum_by_step': masses.mean(2).sum(0).tolist(),
            'mass_mean_by_step': masses.mean((0, 2)).tolist(),
            'top_line_categories_by_step': top,
            'top_line_categories_by_step_head': [[dict(Counter(r['top_category_by_step_head'][s][h] for r in rows))
                                                for h in range(4)] for s in range(3)],
            'native_joint_link1_endpoint3': sum(r['top_category_by_step'][0] == 'link' and r['top_category_by_step'][2] == 'endpoint' for r in rows),
            'interventions': {m: paired(native, [r['intervention_predictions'][m] for r in rows], target)
                              for m in ['L', 'E', 'LE', 'Q']}}


@torch.no_grad()
def run(arm, seed):
    start = time.monotonic()
    folder = OUT / f'{arm}-seed-{seed}'
    folder.mkdir(exist_ok=False)
    try:
        manifest = verify_manifest()
        plan = load_plan(arm)
        source_folder = ARMS[arm] / f'seed-{seed}'
        checkpoint = source_folder / 'model.pt'
        train = json.loads((source_folder / 'training.json').read_text())
        check(C.sha(checkpoint) == train['checkpoint_sha256'], 'checkpoint hash differs from training record')
        ckpt = torch.load(checkpoint, weights_only=False, map_location='cpu')
        check(ckpt['plan_sha256'] == C.sha(ARMS[arm] / 'plan.json'), 'checkpoint plan mismatch')
        check(ckpt['architecture'] == plan['architecture'], 'architecture mismatch')
        check(ckpt['seed'] == seed, 'checkpoint seed mismatch')
        model = T.TokenMemoryReasoner(**ckpt['architecture']).eval()
        model.load_state_dict(ckpt['state_dict'])
        before = C.fingerprint(model)
        check(before == train['final_fingerprint'], 'checkpoint tensor fingerprint mismatch')
        del ckpt
        panels = {}
        for name, row in plan['fresh_panels'].items():
            path = Path(row['path'])
            check(path.resolve().parent == REFERENCE.resolve() and path.name.startswith('fresh-'), 'non-fresh panel forbidden')
            check(C.sha(path) == row['sha256'], 'panel hash mismatch')
            d = torch.load(path, weights_only=False, map_location='cpu')
            check(d['seed'] == 202609201000 + d['cell'] and d['n'] == 512, 'wrong panel population')
            panels[name] = d
        # Run the exact registered scorer before reading/using any diagnostic outcomes.
        actual = R.score(model, panels, fresh=True)
        expected = json.loads((source_folder / 'fresh-evaluation.json').read_text())
        for name in panels:
            check(actual['cells'][name] == expected['cells'][name], f'full fresh parity failed: {name}')
        check(actual['fingerprint'] == expected['fingerprint'], 'registered fingerprint mismatch')
        write_new(folder / 'parity.json', {'all_predictions_and_units_exact': True,
                  'counts': {n: a['count'] for n, a in actual['cells'].items()},
                  'checkpoint_sha256': C.sha(checkpoint), 'fingerprint': before})
        print(json.dumps({'arm': arm, 'seed': seed, 'parity': 'exact'}), flush=True)
        import premonition_handoff_diag as H
        from premonition.toy_ladder import LadderSpec
        spec = LadderSpec()
        results, qresults = {}, {}
        for name, dataset in sorted(panels.items()):
            if dataset['cell'] == 1:
                continue
            rows, q_units, qraw = [], [], []
            for chunk_no, chunk in enumerate(dataset['chunks']):
                produced = {}
                for side in (('a', 'b') if dataset['kind'] == 'pair' else ('a',)):
                    x = data.from_batch(H._strip_labels(chunk[side]))
                    facts = [parse_facts(x, q, spec) for q in range(len(x.owner))]
                    for f, meta in zip(facts, chunk['meta']):
                        check(f['answer'] == meta[f'answer_{side}'][0], 'parsed target mismatch')
                        check([f['link_line'], f['endpoint_line']] == meta[f'gold_{side}'], 'parsed evidence mismatch')
                        check(f['endpoint'] == spec.vocab_size + meta[f'dest_{side}'], 'parsed endpoint mismatch')
                        check(f['asker'] == spec.vocab_size + meta['subject'], 'parsed asker mismatch')
                    qpred = model(requery(x, facts)).argmax(-1).tolist()
                    produced[side] = [[p, 2] for p in qpred]
                    if dataset['cell'] > 3:
                        continue
                    logits = model(x)
                    observed, attention = model(x, trace=True)
                    check(torch.equal(logits, observed), 'passive trace changed logits')
                    check(torch.equal(logits, routed(model, x, facts, 'N')), 'passive hook changed logits')
                    pred = logits.argmax(-1).tolist()
                    saved = actual['cells'][name]['predictions'][chunk_no][side]
                    check([[p, 2] for p in pred] == saved, 'native diagnostic predictions mismatch')
                    interventions = {mode: routed(model, x, facts, mode).argmax(-1).tolist() for mode in ['L', 'E', 'LE']}
                    interventions['Q'] = qpred
                    la = line_attention(x, attention)
                    for q, (f, meta) in enumerate(zip(facts, chunk['meta'])):
                        cats = f['line_categories']
                        mass = torch.stack([la[q, ..., [i for i, k in enumerate(cats) if k == cat]].sum(-1)
                                            for cat in CATEGORIES], -1)
                        check(torch.allclose(mass.sum(-1), torch.ones_like(mass[..., 0]), atol=2e-6), 'category mass missing')
                        primary, flags, collision = error_class(pred[q], f, spec)
                        tops = la[q].mean(1).argmax(-1).tolist()
                        head_tops = la[q].argmax(-1).tolist()
                        rows.append({'index': meta['index'], 'chunk': chunk_no, 'question': x.questions[q].tolist(),
                                     **f, 'prediction': pred[q], 'error_primary': primary,
                                     'error_memberships': flags, 'value_collision': collision,
                                     'line_attention_by_step_head': la[q].tolist(),
                                     'category_mass_by_step_head': mass.tolist(),
                                     'top_line_by_step': tops, 'top_category_by_step': [cats[i] for i in tops],
                                     'top_category_by_step_head': [[cats[i] for i in step] for step in head_tops],
                                     'intervention_predictions': {m: ps[q] for m, ps in interventions.items()}})
                targets = {s: [m[f'answer_{s}'] for m in chunk['meta']] for s in produced}
                units = C.score_predictions(produced['a'], targets['a'], produced.get('b'), targets.get('b'), dataset['invariant'])
                q_units.extend(units)
                qraw.append(produced)
            if rows:
                results[name] = summarize(rows)
                with gzip.open(folder / f'{name}-records.jsonl.gz', 'xt') as handle:
                    for row in rows:
                        handle.write(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n')
            native_units = actual['cells'][name]['per_unit']
            qresults[name] = {'correct': sum(q_units), 'n': len(q_units), 'per_unit': q_units, 'predictions': qraw,
                              'gains': sum(b and not a for a, b in zip(native_units, q_units)),
                              'losses': sum(a and not b for a, b in zip(native_units, q_units))}
            print(json.dumps({'arm': arm, 'seed': seed, 'cell': name, 'Q': sum(q_units),
                              'interventions': results.get(name, {}).get('interventions')}), flush=True)
        check(C.fingerprint(model) == before, 'diagnostics changed tensors')
        verify_manifest()
        load_plan(arm)
        result = {'arm': arm, 'seed': seed, 'seconds': time.monotonic() - start,
                  'parameters': model.parameters_count(), 'weights_unchanged': True, 'files_unchanged': True,
                  'passive_logits_exact': True, 'manifest_sha256': C.sha(OUT / 'manifest.json'),
                  'preregistration_sha256': manifest['preregistration_sha256'],
                  'native': {n: a['count'] for n, a in actual['cells'].items()},
                  'localisation': results, 'oracle_requery': qresults}
        write_new(folder / 'result.json', result)
        print(json.dumps({'completed': [arm, seed], 'seconds': result['seconds']}), flush=True)
    except BaseException:
        write_new(folder / 'failure.json', {'traceback': traceback.format_exc(), 'seconds': time.monotonic() - start})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'run', 'verify'])
    parser.add_argument('--arm', choices=list(ARMS))
    parser.add_argument('--seed', type=int, choices=[0, 1, 2])
    args = parser.parse_args()
    configure()
    if args.command == 'freeze':
        freeze()
    elif args.command == 'verify':
        verify_manifest()
        print('All frozen files unchanged')
    else:
        check(args.arm is not None and args.seed is not None, 'run requires arm/seed')
        run(args.arm, args.seed)

"""Prospectively registered matched-REL extension after B0's initial diagnostic."""
from __future__ import annotations
from collections import Counter
from dataclasses import replace
import json
import sys
import time

import astra_transfer_diagnostic as D

torch = D.torch
OUT = D.OUT / 'matched-rel-followup'


def freeze():
    D.verify_manifest()
    OUT.mkdir(exist_ok=False)
    paths = [D.ROOT / 'scripts/astra_transfer_twins.py', D.OUT / 'FOLLOWUP-PREDICTIONS.md', D.OUT / 'manifest.json']
    D.write_new(OUT / 'manifest.json', {'created_unix': time.time(), 'files': {str(p.relative_to(D.ROOT)): D.C.sha(p) for p in paths}})


def verify():
    D.verify_manifest()
    for n, h in json.loads((OUT / 'manifest.json').read_text())['files'].items():
        D.check(D.C.sha(D.ROOT / n) == h, 'followup input changed')


@torch.no_grad()
def run():
    start = time.monotonic()
    verify()
    import premonition_handoff_diag as H
    from premonition.toy_ladder import LadderSpec
    spec = LadderSpec()
    name = 'c3_own_heldout_two_hop'
    panel = torch.load(D.REFERENCE / f'fresh-{name}.pt', map_location='cpu', weights_only=False)
    for arm in D.ARMS:
        plan = D.load_plan(arm)
        for seed in range(3):
            ckpt = torch.load(D.ARMS[arm] / f'seed-{seed}/model.pt', map_location='cpu', weights_only=False)
            model = D.T.TokenMemoryReasoner(**ckpt['architecture']).eval()
            model.load_state_dict(ckpt['state_dict'])
            before = D.C.fingerprint(model)
            previous = json.loads((D.OUT / f'{arm}-seed-{seed}/result.json').read_text())
            rows = []
            for chunk in panel['chunks']:
                batch = H._strip_labels(chunk['a'])
                x = D.data.from_batch(batch)
                # q_line is the adapter's sole location input. The four trailing
                # question slots contain no eligible non-question rows between them.
                first = []
                for v in batch.q_visit.tolist():
                    slots = batch.line_is_question[v].nonzero().flatten()
                    D.check(len(slots) == 4, 'expected four trailing question slots')
                    first.append(int(slots[0]))
                for offset in range(4):
                    shifted = D.data.from_batch(replace(batch, q_line=torch.tensor(first) + offset))
                    D.check(all(torch.equal(getattr(x, field), getattr(shifted, field))
                                for field in ['memory', 'questions', 'owner', 'eligible']), 'slot changes model inputs')
                variants = {}
                for rel in [0, 1, 2]:
                    questions = x.questions.clone()
                    questions[:, 3] = spec.relation(rel)
                    twin = replace(x, questions=questions)
                    facts = [D.parse_facts(twin, q, spec) for q in range(len(twin.owner))]
                    logits, attention = model(twin, trace=True)
                    la = D.line_attention(twin, attention)
                    variant = []
                    for q, f in enumerate(facts):
                        cats = f['line_categories']
                        cm = torch.stack([la[q, ..., [i for i, cat in enumerate(cats) if cat == category]].sum(-1)
                                          for category in D.CATEGORIES], -1)
                        variant.append({'prediction': int(logits[q].argmax()), 'answer': f['answer'],
                                        'link_line': f['link_line'], 'endpoint': f['endpoint'],
                                        'first_link_top': int(la[q, 0].mean(0).argmax()) == f['link_line'],
                                        'first_link_mass': float(la[q, 0, :, f['link_line']].mean()),
                                        'category_mass_by_step_head': cm.tolist()})
                    variants[str(rel)] = variant
                for q, meta in enumerate(chunk['meta']):
                    row = {'index': meta['index'], 'variants': {r: vs[q] for r, vs in variants.items()}}
                    D.check(len({v['link_line'] for v in row['variants'].values()}) == 1, 'link target changed')
                    D.check(len({v['endpoint'] for v in row['variants'].values()}) == 1, 'person target changed')
                    rows.append(row)
            stats = {}
            for rel in ['0', '1', '2']:
                vs = [r['variants'][rel] for r in rows]
                base = [r['variants']['2'] for r in rows]
                stats[rel] = {'n': len(vs), 'answer_correct': sum(v['prediction'] == v['answer'] for v in vs),
                              'first_link_top': sum(v['first_link_top'] for v in vs),
                              'first_link_mass': sum(v['first_link_mass'] for v in vs) / len(vs),
                              'link_gains_vs_r2': sum(v['first_link_top'] and not b['first_link_top'] for v, b in zip(vs, base)),
                              'link_losses_vs_r2': sum(b['first_link_top'] and not v['first_link_top'] for v, b in zip(vs, base))}
            D.check(stats['2']['answer_correct'] == previous['native'][name], 'native replay mismatch')
            D.check(stats['2']['first_link_top'] == previous['localisation'][name]['top_line_categories_by_step'][0].get('link', 0), 'trace replay mismatch')
            D.check(D.C.fingerprint(model) == before, 'weights changed')
            D.write_new(OUT / f'{arm}-seed-{seed}.json', {'arm': arm, 'seed': seed, 'stats': stats, 'records': rows,
                        'weights_unchanged': True, 'all_four_slot_inputs_exactly_equal': True,
                        'M1_pass': all(stats[r]['first_link_top'] >= 461 and
                                       stats[r]['first_link_top'] - stats['2']['first_link_top'] >= 103 for r in ['0', '1'])})
            print(json.dumps({'arm': arm, 'seed': seed, 'stats': stats}), flush=True)
    verify()
    D.write_new(OUT / 'completion.json', {'seconds': time.monotonic() - start, 'files_unchanged': True})


if __name__ == '__main__':
    D.configure()
    if sys.argv[1] == 'freeze':
        freeze()
    elif sys.argv[1] == 'run':
        run()
    else:
        raise SystemExit('freeze or run required')

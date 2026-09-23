"""Model-free report tables and independent arithmetic audit of diagnostic records."""
from __future__ import annotations
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/astra-transfer-diagnostic-20260920'
CATS = ['link', 'endpoint', 'decoy', 'endpoint_other_relation', 'filler', 'other_fact', 'null']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---']*len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]) + '\n'


def main():
    results = [json.loads((OUT / f'{arm}-seed-{seed}/result.json').read_text()) for arm in 'BC' for seed in range(3)]
    audit = {'records': 0, 'jobs': 6, 'checks': [], 'primary_manifest_unchanged': True}
    for n, h in json.loads((OUT / 'manifest.json').read_text())['files'].items():
        assert sha(ROOT / n) == h, n
    tables = {}
    tables['native'] = table(['Seed', 'c1', 'c2', 'c3', 'c4 pairs', 'c5 pairs', 'c6 pairs'],
                             [[f"{d['arm']}{d['seed']}", *d['native'].values()] for d in results])
    compact, error_rows, mass_rows, top_rows, routing, qrows, predictions, matched = [], [], [], [], [], [], [], []
    head_rows = []
    for d in results:
        ident = f"{d['arm']}{d['seed']}"
        folder = OUT / f"{d['arm']}-seed-{d['seed']}"
        for cell, summary in d['localisation'].items():
            with gzip.open(folder / f'{cell}-records.jsonl.gz', 'rt') as handle:
                rows = [json.loads(line) for line in handle]
            assert len(rows) == 512
            assert [r['index'] for r in rows] == list(range(512))
            counts = Counter(r['error_primary'] for r in rows)
            assert dict((k, counts.get(k,0)) for k in summary['error_counts']) == summary['error_counts']
            assert sum(summary['error_counts'].values()) == 512
            assert counts['correct'] == sum(r['prediction'] == r['answer'] for r in rows)
            qp = [p[0] for chunk in d['oracle_requery'][cell]['predictions'] for p in chunk['a']]
            assert qp == [r['intervention_predictions']['Q'] for r in rows]
            for s in range(3):
                assert dict(Counter(r['top_category_by_step'][s] for r in rows)) == summary['top_line_categories_by_step'][s]
                for h in range(4):
                    assert dict(Counter(r['top_category_by_step_head'][s][h] for r in rows)) == summary['top_line_categories_by_step_head'][s][h]
                    observed = [0.] * 7
                    for r in rows:
                        raw = r['line_attention_by_step_head'][s][h]
                        assert abs(sum(raw) - 1) < 2e-6
                        recomputed = [sum(v for v, cat in zip(raw, r['line_categories']) if cat == c) for c in CATS]
                        declared = r['category_mass_by_step_head'][s][h]
                        assert max(abs(a-b) for a,b in zip(recomputed, declared)) < 2e-6
                        for i, v in enumerate(recomputed):
                            observed[i] += v / 512
                    assert max(abs(a-b) for a,b in zip(observed, summary['mass_mean_by_step_head'][s][h])) < 2e-6
                    head_rows.append([ident, cell[:2], s+1, h, *observed,
                                      *[summary['top_line_categories_by_step_head'][s][h].get(c,0) for c in CATS]])
                mass_rows.append([ident, cell[:2], s+1, *[f'{v:.6f}' for v in summary['mass_mean_by_step'][s]]])
                top_rows.append([ident, cell[:2], s+1, *[summary['top_line_categories_by_step'][s].get(c,0) for c in CATS]])
            for mode, a in summary['interventions'].items():
                native = [r['prediction'] == r['answer'] for r in rows]
                changed = [r['intervention_predictions'][mode] == r['answer'] for r in rows]
                assert sum(changed) == a['correct']
                assert sum(b and not n for n,b in zip(native,changed)) == a['gains']
                assert sum(n and not b for n,b in zip(native,changed)) == a['losses']
            compact.append([ident, cell[:2], summary['native_correct'],
                            summary['top_line_categories_by_step'][0].get('link',0),
                            f"{summary['mass_mean_by_step'][0][0]:.4f}",
                            summary['top_line_categories_by_step'][1].get('endpoint',0),
                            summary['top_line_categories_by_step'][2].get('endpoint',0),
                            f"{summary['mass_mean_by_step'][2][1]:.4f}"])
            e = summary['error_counts']
            error_rows.append([ident, cell[:2], 512-e['correct'], e['a_endpoint_other_relation'], e['b_decoy'], e['c_link_entity'],
                               e['d_other_person_same_relation'], e['e_other_nonvalue'], e['f_other_value'], summary['ambiguous_value_errors']])
            routing.append([ident, cell[:2], summary['native_correct'], *[f"{a['correct']} (+{a['gains']}/−{a['losses']})" for a in summary['interventions'].values()]])
            audit['records'] += len(rows)
        for name, a in d['oracle_requery'].items():
            units = []
            expected_original = 'codex-token-evidence-20260920' if d['arm'] == 'B' else 'codex-token-scaled-20260920'
            # Independent pair arithmetic against pre-recorded native per-unit data.
            native = json.loads((ROOT / f'artifacts/{expected_original}/seed-{d["seed"]}/fresh-evaluation.json').read_text())['cells'][name]['per_unit']
            assert sum(a['per_unit']) == a['correct']
            assert sum(b and not n for n,b in zip(native,a['per_unit'])) == a['gains']
            assert sum(n and not b for n,b in zip(native,a['per_unit'])) == a['losses']
        qrows.append([ident, *[a['correct'] for a in d['oracle_requery'].values()]])
        c2, c3 = list(d['localisation'].values())
        l2, l3 = c2['top_line_categories_by_step'][0].get('link',0), c3['top_line_categories_by_step'][0].get('link',0)
        early = l3 >=461 and l2-l3 <=51 and c3['mass_mean_by_step'][0][0]>=.75
        late = any(c3['top_line_categories_by_step'][s].get('endpoint',0)<=256 and
                   c2['top_line_categories_by_step'][s].get('endpoint',0)-c3['top_line_categories_by_step'][s].get('endpoint',0)>=103 for s in [1,2])
        p2 = c3['a_or_b_errors'] >= .5*(512-c3['native_correct'])
        p3 = (c3['interventions']['L']['correct']-c3['native_correct'] < 52 and
              all(c3['interventions'][m]['correct']-c3['native_correct'] >=154 and c3['interventions'][m]['correct']>=410 for m in ['E','LE']))
        p4 = list(d['oracle_requery'].values())[1]['correct']>=487 and all(a['correct']>=461 for name,a in d['oracle_requery'].items() if name[:2] in ['c4','c5','c6'])
        predictions.append([ident, 'pass' if early and late else 'FAIL',
                            f"{'pass' if p2 else 'FAIL'} ({c3['a_or_b_errors']}/{512-c3['native_correct']})",
                            'pass' if p3 else 'FAIL', 'pass' if p4 else 'FAIL'])
        twin = json.loads((OUT / f'matched-rel-followup/{d["arm"]}-seed-{d["seed"]}.json').read_text())
        st = twin['stats']
        matched.append([ident, *[st[r]['first_link_top'] for r in ['0','1','2']],
                        *[f"+{st[r]['link_gains_vs_r2']}/−{st[r]['link_losses_vs_r2']}" for r in ['0','1']],
                        'pass' if twin['M1_pass'] else 'FAIL'])
    tables['attention_key'] = table(['Seed','Cell','Answers','Link top, step 1','Link mass, step 1','Endpoint top, step 2','Endpoint top, step 3','Endpoint mass, step 3'],compact)
    tables['errors'] = table(['Seed','Cell','Wrong','(a) person/right, REL/wrong','(b) decoy','(c) link entity','(d) other person/same REL','(e) other non-value','(f) other value','Value overlaps'],error_rows)
    tables['mass'] = table(['Seed','Cell','Step',*CATS], mass_rows)
    tables['top'] = table(['Seed','Cell','Step',*CATS], top_rows)
    tables['routing'] = table(['Seed','Cell','Native','L (+gain/−loss)','E (+gain/−loss)','LE (+gain/−loss)','Q (+gain/−loss)'],routing)
    tables['requery'] = table(['Seed','c2','c3','c4 pairs','c5 pairs','c6 pairs'],qrows)
    tables['predictions'] = table(['Seed','P1 first/late pattern','P2 (a) or (b) ≥half errors','P3 routing rescue','P4 canonical re-query'], predictions)
    tables['matched'] = table(['Seed','r0 link top','r1 link top','r2 link top','r0 gain/loss vs r2','r1 gain/loss vs r2','M1'],matched)
    (OUT / 'tables.json').write_text(json.dumps(tables,indent=2)+'\n')
    with (OUT / 'per-head.csv').open('x', newline='') as handle:
        w=csv.writer(handle);w.writerow(['seed','cell','step','head',*[f'mass_{c}' for c in CATS],*[f'top_count_{c}' for c in CATS]]);w.writerows(head_rows)
    with (OUT / 'TABLES.md').open('x') as handle:
        handle.write('# Full diagnostic tables\n\n**Shown.** All count denominators are 512. Attention masses average heads at the final question row. No intervention score is native performance.\n\n')
        for key,t in tables.items():
            handle.write(f'**{key}**\n\n'+t+'\n')
    audit['checks'] = ['all primary manifest bytes unchanged', '6144 records indexed 0..511 per cell/job',
                       'raw line masses conserve probability', 'raw line-to-category aggregation matches summaries',
                       'all 144 step/head mean vectors and top-line counters independently recomputed',
                       'all exclusive error counts cover exactly correct+wrong=512',
                       'all routing gains/losses independently recomputed', 'all Q pair unit totals and gains/losses verified']
    audit['result_hashes'] = {str(p.relative_to(ROOT)): sha(p) for p in sorted(OUT.glob('*-seed-*/result.json'))}
    with (OUT / 'arithmetic-audit.json').open('x') as handle:
        json.dump(audit,handle,indent=2);handle.write('\n')
    print(json.dumps(audit,indent=2))


if __name__ == '__main__':
    main()

"""Model-free reconstruction of every reported screen outcome from raw records."""
from __future__ import annotations

import json
from pathlib import Path
import time

import astra_canonical_operator as A
import astra_canonical_operator_panels as P
import premonition_memnn_compare as C

OUT, ROOT = P.OUT, P.ROOT


def report():
    A.data.bootstrap()
    A.torch.set_num_threads(1)
    manifest = json.loads((OUT/'astra_canonical_operator_launch.json').read_text())
    for name, expected in manifest['files'].items():
        assert C.sha(ROOT/name) == expected, name
    keys = ['c1','c2','c3','c4','c5','c6','s3','p12-1','p12-2','p12-3']
    results, training, completion, failures = {}, {}, {}, []
    truth, cycles = {}, {}
    for key in keys:
        panel = P.load(manifest['panels'][key]['path'])
        truth[key] = []
        cycles[key] = []
        for sides in P.chunks(panel):
            paths = {s:A.truth_paths(x) for s,(x,_) in sides.items()}
            for i in range(len(paths['a'])):
                truth[key].append({s:[stage['target'] for stage in ps[i]] for s,ps in paths.items()})
                cycles[key].append({s:bool(len(ps[i])==3 and ps[i][1]['target']==ps[i][0]['entity']) for s,ps in paths.items()})
    rows_checked = 0
    for seed in range(3):
        folder = OUT/f'astra_canonical_operator_seed-{seed}'
        results[seed] = {}
        cp = folder/'completion.json'
        if cp.exists(): completion[seed] = json.loads(cp.read_text())
        else: failures.append(f'seed {seed}: incomplete; {folder / "failure.json"}')
        tp = folder/'training.json'
        if tp.exists(): training[seed] = json.loads(tp.read_text())
        for key in keys:
            path = folder/f'{key}.json'
            if not path.exists():
                failures.append(f'seed {seed}: missing {key}')
                continue
            r = json.loads(path.read_text())
            rc = mc = gain = loss = 0
            for idx, record in enumerate(r['records']):
                assert record['index'] == idx
                sides = record['sides']
                for side,row in sides.items():
                    t = truth[key][idx][side]
                    assert row['truth_path'] == t and row['target'] == t[-1]
                    assert row['asker_cycle'] == cycles[key][idx][side]
                    em, oracle = row['emitted'], row['oracle']
                    assert row['native_joint'] == int(em == t)
                    assert row['native_links'] == [int(j < len(em) and em[j] == t[j]) for j in range(len(t)-1)]
                    assert row['oracle_links'] == [int(oracle[j] == t[j]) for j in range(len(t)-1)]
                    assert row['terminal_oracle'] == int(oracle[-1] == t[-1])
                    rows_checked += 1
                ur = int(all(row['R'] == row['target'] for row in sides.values()))
                um = int(all(row['M'] == row['target'] for row in sides.values()))
                if key == 'c6':
                    ur &= int(len({row['R'] for row in sides.values()}) == 1)
                    um &= int(len({row['M'] for row in sides.values()}) == 1)
                assert record['correct'] == dict(R=ur,M=um)
                rc += ur; mc += um; gain += int(ur and not um); loss += int(um and not ur)
            assert (rc,mc,gain,loss) == (r['R'],r['M'],r['gain'],r['loss'])
            assert len(r['records']) == r['n'] == 512
            if key == 's3':
                for label,is_cycle in [('asker_cycle',True),('distinct_chain',False)]:
                    selected=[q for q in r['records'] if q['sides']['a']['asker_cycle']==is_cycle]
                    assert r['cycle_split'][label] == dict(n=len(selected),R=sum(q['correct']['R'] for q in selected),
                        M=sum(q['correct']['M'] for q in selected),native_joint=sum(q['sides']['a']['native_joint'] for q in selected))
            for side,d in r['diagnostics'].items():
                raw = [record['sides'][side] for record in r['records']]
                for category in ('native_links','oracle_links'):
                    assert d[category] == [sum(x[category][j] for x in raw) for j in range(len(raw[0][category]))]
                for category in ('terminal_oracle','native_joint'):
                    assert d[category] == sum(x[category] for x in raw)
            results[seed][key] = r
    all_complete = len(completion) == 3 and all(c['complete'] and c['updates'] == 6000 for c in completion.values())
    answers, r_gate, p2 = {}, {}, {}
    for seed in range(3):
        answers[seed] = {policy:all(len(results[seed]) == 10 and results[seed][key][policy] >= manifest['panels'][key]['cutoff']
                                  for key in keys) for policy in ('R','M')}
        diag_ok = len(results[seed]) == 10 and all(
            min(d['native_links']+[d['terminal_oracle']]) >= 487
            for r in results[seed].values() for d in r['diagnostics'].values())
        joint_ok = 's3' in results[seed] and results[seed]['s3']['diagnostics']['a']['native_joint'] >= 461
        r_gate[seed] = answers[seed]['R'] and diag_ok and joint_ok
        p2[seed] = r_gate[seed] and all(results[seed][key]['R']-results[seed][key]['M'] >= 52 for key in ('c3','c4','c5','c6','s3')) \
                    and all(results[seed][key]['M']-results[seed][key]['R'] <= 5 for key in ('c1','c2'))
        for policy in ('R','M'):
            for key,r in results[seed].items():
                if r[policy] < manifest['panels'][key]['cutoff']:
                    failures.append(f'{policy}{seed} {key}: {r[policy]}/512 < {manifest["panels"][key]["cutoff"]}')
        for key,r in results[seed].items():
            for side,d in r['diagnostics'].items():
                for j,count in enumerate(d['native_links']):
                    if count < 487: failures.append(f'R{seed} {key}/{side} native LINK {j+1}: {count}/512 < 487')
                if d['terminal_oracle'] < 487: failures.append(f'seed {seed} {key}/{side} terminal oracle: {d["terminal_oracle"]}/512 < 487')
        if not joint_ok: failures.append(f'R{seed}: three-hop native joint gate failed')
        if not p2[seed]: failures.append(f'seed {seed}: P2 substantial-policy-advantage prediction failed')
    R_pass = all_complete and all(r_gate.values())
    M_pass = all_complete and all(x['M'] for x in answers.values())
    reading = ('Incomplete comparison' if not all_complete else
               'Both pass' if R_pass and M_pass else
               'R passes, M fails' if R_pass else
               'R fails, M passes' if M_pass else 'Both fail')
    wave = json.loads((OUT/'astra_canonical_operator_wave/completion.json').read_text())
    lines = ['\n\n## Append-only execution addendum — 20 September 2026 UTC',
             '',f'**Shown.** Predeclared reading: **{reading}**. P1: **{"PASS" if R_pass else "FAIL"}**; '
             f'P2: **{"PASS" if all_complete and all(p2.values()) else "FAIL"}**. '
             'P3 implementation checks passed before launch; they are construction checks, not learned-transfer evidence.',
             '',f'**Shown.** Three common checkpoints supply six inference-arm rows. All-complete: {all_complete}. '
             f'The parallel model-execution wave took {wave["seconds"]:.3f} seconds; '
             'source/panel/checkpoint integrity and final-checkpoint-only evaluation were checked. '
             f'This independent model-free report reconstructed {rows_checked:,} side records against panel truth.',
             '', '| Arm/seed | '+' | '.join(keys)+' |', '| --- | '+' | '.join(['---']*10)+' |']
    for policy in ('R','M'):
        for seed in range(3):
            lines.append(f'| {policy}{seed} | '+' | '.join(str(results[seed][k][policy]) if k in results[seed] else 'MISSING' for k in keys)+' |')
    lines += ['', 'All denominators above are 512. c4–c6 count complete pairs. Raw thresholds: c1/c2/p12-1/p12-2 ≥487; all other answer cells ≥461. No averaging across seeds.',
              '', '**Shown — paired policy changes.** Each entry is R-only correct / M-only correct (net R−M).',
              '', '| Cell | Seed 0 | Seed 1 | Seed 2 |','| --- | --- | --- | --- |']
    for k in keys:
        vals=[]
        for s in range(3):
            r=results[s].get(k)
            vals.append(f'+{r["gain"]}/−{r["loss"]} ({r["R"]-r["M"]:+d})' if r else 'MISSING')
        lines.append(f'| {k} | '+' | '.join(vals)+' |')
    lines += ['', '**Shown — intermediate diagnostics.** Each side has 512 questions. L = autonomous LINK correct counts; O = gold-input LINK correct counts; T = gold-endpoint terminal correct; J = complete autonomous entity path and answer. These canonical diagnostics belong to the shared checkpoint; M has no native emitted path.',
              '', '| Seed | Cell/side | L | O | T | J |','| --- | --- | --- | --- | --- | --- |']
    for s in range(3):
        for k in keys:
            for side,d in results[s].get(k,{}).get('diagnostics',{}).items():
                fmt=lambda v: ', '.join(map(str,v)) if v else '—'
                lines.append(f'| {s} | {k}/{side} | {fmt(d["native_links"])} | {fmt(d["oracle_links"])} | {d["terminal_oracle"]} | {d["native_joint"]} |')
    lines += ['', '**Shown — three-hop asker-cycle split.**', '', '| Seed | Chain | n | R | M | Native joint |','| --- | --- | --- | --- | --- | --- |']
    for s in range(3):
        for label,d in results[s].get('s3',{}).get('cycle_split',{}).items():
            lines.append(f'| {s} | {label} | {d["n"]} | {d["R"]} | {d["M"]} | {d["native_joint"]} |')
    lines += ['', '**Shown — costs.** FLOPs count actual padded/compacted matmuls under the existing convention, validated against Torch instrumentation before training. Elementwise operations, optimizer arithmetic and file I/O are excluded from FLOPs. Policy seconds time their forwards; total job/wave time includes training, audits and I/O. Peak RSS is per process. Shared training is charged once.',
              '', '| Seed | Updates | Train seconds | Train FLOPs | Job seconds | Peak RSS bytes |','| --- | --- | --- | --- | --- | --- |']
    for s,t in training.items():
        cp=completion.get(s,{})
        lines.append(f'| {s} | {t["updates"]} | {t["seconds"]:.3f} | {t["flops"]} | {cp.get("seconds","MISSING")} | {cp.get("peak_rss_bytes","MISSING")} |')
    lines += ['', '| Seed | Policy | Seconds | FLOPs | Question calls | Batched forwards |','| --- | --- | --- | --- | --- | --- |']
    for s in range(3):
        for policy in ('R','M','oracle'):
            total={k:sum(r['costs'][policy][k] for r in results[s].values()) for k in ('seconds','flops','calls','batches')}
            lines.append(f'| {s} | {policy} | {total["seconds"]:.3f} | {total["flops"]} | {total["calls"]} | {total["batches"]} |')
    lines += ['', '**Shown — failures retained.**']
    lines += ['']+(['- '+f for f in failures] if failures else ['No registered gate failures.'])
    lines += ['', '**Suggested — interpretation.** '+{
        'R passes, M fails':'The supplied execution policy lets the common trained lookup meet every registered criterion. The monolithic control does not. This supports supplied-program sufficiency under matched weights and supervision; it does not demonstrate that the model learned the decomposition.',
        'Both pass':'The common training recipe supports both execution policies on the registered screen. The controller is not required to cross these thresholds; the added-label recipe is not isolated from every difference versus historical models.',
        'R fails, M passes':'Reject this recursive candidate under the fixed recipe and budget; the common trained weights satisfy the monolithic answer screen.',
        'Both fail':'Neither execution policy meets the complete registered screen. Retain any local successes without promoting them to full sufficiency.',
        'Incomplete comparison':'The planned screen failed to complete. Partial counts cannot establish a successful policy comparison.'}[reading],
        '', '**Untested.** Learned decomposition and the dispatcher remain untested. No dispatcher was built or run. No broad intelligence, equal-total-compute or certification claim follows.',
        '', 'Artifacts: [launch manifest](../../artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_launch.json), '
        '[pre-launch amendment](../../artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_PRE-LAUNCH-AMENDMENT.md), '
        '[raw seed folders and verification](../../artifacts/astra-canonical-operator-screen-20260920/).']
    text='\n'.join(lines)+'\n'
    dest=OUT/'astra_canonical_operator_RESULTS.md'
    with dest.open('x') as f:f.write(text)
    report_path=ROOT/'design/v3/17-canonical-operator-screen.md'
    assert report_path.read_bytes() == (OUT/'PRE-RUN-DESIGN.md').read_bytes(), 'report already modified'
    with report_path.open('a') as f:f.write(text)
    verification=dict(created_unix=time.time(),rows_checked=rows_checked,all_complete=all_complete,
                       R_pass=R_pass,M_pass=M_pass,P2=all_complete and all(p2.values()),reading=reading,
                       failures=failures,raw_results={str(p.relative_to(ROOT)):C.sha(p) for p in OUT.glob('astra_canonical_operator_seed-*/*.json')},
                       report_sha256=C.sha(report_path),new_result_sha256=C.sha(dest))
    C.write_new(OUT/'astra_canonical_operator_REPORT-VERIFICATION.json',verification)
    print(json.dumps({k:v for k,v in verification.items() if k not in ('raw_results','failures')}),flush=True)


if __name__ == '__main__':
    report()

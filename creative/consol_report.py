"""Consolidation sleep: measure saved snapshots and score the marks in creative/results/fastsleep/consol/MARKS.md. MEASURE only (C2 DEV, skills DEV).

  python3 -m creative.consol_report snaps --out ~/consol/A/s200 --arms rlc fd --steps 32 64 [--threads 1]
  python3 -m creative.consol_report screenA --root ~/consol/A --parents s200 s201

snaps: each DIR/<arm>/learner_s<k>.pt -> DIR/<arm>/snap_s<k>.json (C2 DEV right, by kind, per-question list; skills in_dist, pooled-5, harm_measure vs N
per row). The last saved step equals learner.pt, which `consol run` already measured (result.json / hits.json)."""
import argparse, json, os
import torch
from creative import c2_pilot, sleep
from creative.consol import SKILLS_DATA, _dump, measure
from creative.harm_look import harm_measure


def _nm(out):
    return json.load(open(os.path.join(out, 'N_measure.json')))['value']


def _harm(nm, hits, fams):
    return harm_measure(nm['skills']['hits'], hits, [{'family': f} for f in fams])


def snaps(out, arms, steps, skills_data=SKILLS_DATA, device='cpu'):
    nm = _nm(out)
    for arm in arms:
        for k in steps:
            p, sp = os.path.join(out, arm, f'learner_s{k}.pt'), os.path.join(out, arm, f'snap_s{k}.json')
            if os.path.exists(sp) or not os.path.exists(p):
                continue
            m, vocab, _ = sleep.load_parent(p, device)
            m.eval()
            lm = measure(m, vocab, device, skills_data)
            h = _harm(nm, lm['skills']['hits'], lm['skills']['families'])
            _dump(dict(step=k, c2_right=lm['c2']['right'], by_kind=lm['c2']['by_kind'], per_q_right=lm['c2']['per_q_right'], in_dist=lm['skills']['in_dist'],
                       pooled5=lm['skills']['pooled5'], hits=lm['skills']['hits'], harm_vs_N={x: h[x] for x in ('in_dist_a', 'in_dist_b', 'in_dist_drop', 'fired', 'passes')}), sp)
            print(out, arm, k, 'c2', round(lm['c2']['right'], 2), 'in_dist', round(lm['skills']['in_dist'], 2), 'drop', round(h['in_dist_drop'], 2), h['fired'], flush=True)


def point(out, arm, k, last):
    """-> dict(c2, per_q, in_dist, drop, fired, passes, hits) for arm at step k (snapshot, or the final learner when k == last)."""
    nm = _nm(out)
    if k == last:
        r = json.load(open(os.path.join(out, arm, 'result.json')))
        hj = json.load(open(os.path.join(out, arm, 'hits.json')))
        h = _harm(nm, hj['learner'], hj['families'])
        return dict(c2=r['learner']['c2_right'], per_q=r['learner']['per_q_right'], in_dist=h['in_dist_b'], drop=h['in_dist_drop'], fired=h['fired'], passes=h['passes'],
                    hits=hj['learner'], updates_done=r['sleep']['updates_done'], visits=r['sleep']['record_visits'], finds=r.get('finds'))
    s = json.load(open(os.path.join(out, arm, f'snap_s{k}.json')))
    hv = s['harm_vs_N']
    return dict(c2=s['c2_right'], per_q=s['per_q_right'], in_dist=hv['in_dist_b'], drop=hv['in_dist_drop'], fired=hv['fired'], passes=hv['passes'], hits=s['hits'])


def screen_a(root, parents, steps=(32, 64, 128), last=128, a1_steps=(64, 128), dev_bar=71.2):
    """Screen A's marks, exactly as MARKS.md states them."""
    res = dict(parents={}, marks={})
    for p in parents:
        out = os.path.join(root, p)
        nm = _nm(out)
        pr = dict(N=dict(c2=nm['c2']['right'], in_dist=nm['skills']['in_dist']), steps={})
        for k in steps:
            a, b = point(out, 'rlc', k, last), point(out, 'fd', k, last)
            d, lo, hi = c2_pilot.boot(b['per_q'], a['per_q'])
            sd, slo, shi = c2_pilot.boot(b['hits'], a['hits'])
            pr['steps'][k] = dict(rlc={x: a[x] for x in ('c2', 'in_dist', 'drop', 'fired', 'passes')}, fd={x: b[x] for x in ('c2', 'in_dist', 'drop', 'fired', 'passes')},
                                  fd_minus_rlc_c2=[d, lo, hi], fd_minus_rlc_in_dist=[sd, slo, shi])
        if os.path.exists(os.path.join(out, 'rp', 'hits.json')):
            rp, fd = point(out, 'rp', last, last), point(out, 'fd', last, last)
            pr['rp'] = dict(c2=rp['c2'], in_dist=rp['in_dist'], drop=rp['drop'], fired=rp['fired'], fd_minus_rp_in_dist=list(c2_pilot.boot(fd['hits'], rp['hits'])),
                            rp_minus_N_in_dist=list(c2_pilot.boot(rp['hits'], nm['skills']['hits'])), fd_minus_N_in_dist=list(c2_pilot.boot(fd['hits'], nm['skills']['hits'])))
        for arm in ('rlc', 'fd'):
            r = json.load(open(os.path.join(out, arm, 'result.json')))
            pr[arm + '_run'] = dict(finds=r.get('finds'), visits=r['sleep']['record_visits'], updates=r['sleep']['updates_done'], seconds=r['seconds'], checks=[{x: c[x] for x in ('step', 'held_fits', 'in_dist')} for c in r.get('checks', [])])
        res['parents'][p] = pr
    P = res['parents']
    a1 = all(P[p]['steps'][k]['fd']['drop'] <= P[p]['steps'][k]['rlc']['drop'] - 1.0 for p in parents for k in a1_steps)
    a2 = all(P[p]['steps'][k]['fd']['c2'] >= P[p]['steps'][k]['rlc']['c2'] - 2.0 for p in parents for k in a1_steps)
    wrong = all(P[p]['steps'][k]['fd']['drop'] >= P[p]['steps'][k]['rlc']['drop'] for p in parents for k in steps)
    ustar = None
    for k in steps:
        if sum(P[p]['steps'][k]['fd']['c2'] for p in parents) / len(parents) >= dev_bar and all(P[p]['steps'][k]['fd']['passes'] for p in parents):
            ustar = k
            break
    harmless = any(P[p]['steps'][last]['rlc']['drop'] < 2.0 for p in parents)      # MARKS.md fall-back rule: rlc shows little harm, so A1 cannot be tested
    fd_ok = all(P[p]['steps'][last]['fd']['passes'] and P[p]['steps'][last]['fd']['c2'] >= P[p]['steps'][last]['rlc']['c2'] - 2.0 for p in parents)
    res['fall_back'] = dict(rlc_harmless=harmless, fd_ok=fd_ok, confirm_uses=('fd' if fd_ok else 'rlc') if harmless else None,
                            rule='rlc drop < 2.0 at the last step on either parent -> A1 not testable; confirm uses fd if fd passes harm_measure on both and its C2 is >= rlc C2 - 2 (one-sided), else rlc')
    res['marks'] = dict(A1='not testable' if harmless else a1, A2=a2, passes=('not testable' if harmless else (a1 and a2)), proved_wrong=wrong, U_star=ustar,
                        rule='A1: fd in_dist drop <= rlc drop - 1.0 at 64 and 128 on both parents; A2: fd C2 >= rlc C2 - 2 there; wrong: fd drop >= rlc drop at every step on both; '
                             'U*: smallest step with two-parent mean fd C2 DEV >= 71.2 and harm passes on both (None -> rerun fd at 256)')
    return res


def holdout(out, arms, device='cpu'):
    """The research loop's C2 holdout (512, creative/data/c2rl), ONE greedy pass per saved learner, per-question list kept: DIR/<arm>/holdout.json. Refuses to run twice."""
    from creative import c2_stones, fastsleep as fs, rules_real as R
    rows = c2_stones._with_nums(R.load_split('creative/data/c2rl', 'holdout'))
    for arm in arms:
        hp = os.path.join(out, arm, 'holdout.json')
        if os.path.exists(hp):
            raise RuntimeError(f'{hp} exists: the holdout is read once per learner')
        m, vocab, _ = sleep.load_parent(os.path.join(out, arm, 'learner.pt'), device)
        m.eval()
        d, per = fs.dev_eval(m, rows, vocab, device)
        _dump(dict(right=100 * d['right'], by_kind={k: 100 * v for k, v in d['by_kind'].items()}, per_q_right=[int(x) for x in per], n=len(rows)), hp)
        print(out, arm, 'holdout', round(100 * d['right'], 2), flush=True)


def confirm(root, parents, b2_dir=None, skills_data=SKILLS_DATA, device='cpu', bar=71.3):
    """The confirm's marks, exactly as the last section of MARKS.md states them. root/<parent>/{fd,rp}/ from `consol run`; fd/holdout.json from `holdout`.
    Mark 1: mean fd holdout >= 71.3. Mark 2: updates_done <= 256 and <= 0.5 x (80 x (W + C) x 4 / 512) per parent. Mark 3: harm_measure passes per parent.
    Mark 4: pooled (parent-stacked) in_dist fd - N point > 0 and 95% interval lower end > 0; transfer label only if fd - rp (pooled) is above 0 with its interval above 0.
    Report only: harm vs the raw B2 (if b2_dir), C2 DEV, per kind, rp numbers."""
    import numpy as np
    res, ho, ah_fd, ah_n, ah_rp = dict(parents={}), [], [], [], []
    for p in parents:
        out = os.path.join(root, p)
        r = json.load(open(os.path.join(out, 'fd', 'result.json')))
        hj = json.load(open(os.path.join(out, 'fd', 'hits.json')))
        h = r['harm_vs_N']
        f = r['finds']
        half = 0.5 * (80 * (f['n_W'] + f['n_C']) * 4 / 512)
        pr = dict(c2_dev=r['learner']['c2_right'], by_kind=r['learner']['by_kind'], in_dist_N=h['in_dist_a'], in_dist_fd=h['in_dist_b'], harm_passes=h['passes'], fired=h['fired'],
                  updates_done=r['sleep']['updates_done'], half_research_loop_updates=half,
                  mark2=bool(r['sleep']['updates_done'] <= 256 and r['sleep']['updates_done'] <= half), seconds=r['seconds'])
        hp = os.path.join(out, 'fd', 'holdout.json')
        if os.path.exists(hp):
            pr['holdout'] = json.load(open(hp))['right']
            ho.append(pr['holdout'])
        ah_fd += hj['learner']; ah_n += hj['N']
        rpj = os.path.join(out, 'rp', 'hits.json')
        if os.path.exists(rpj):
            rh = json.load(open(rpj))
            assert rh['ids'] == hj['ids']
            ah_rp += rh['learner']
            pr['rp_in_dist'] = 100 * sum(rh['learner']) / len(rh['learner'])
        if b2_dir:
            from creative.harm_look import skills_hits
            m, _, _ = sleep.load_parent(os.path.join(os.path.expanduser(b2_dir), f'B2_{p}.pt'), device)
            m.eval()
            rows, hb, _, idb = skills_hits(m, skills_data, device)
            hv = harm_measure(hb, hj['learner'], rows)
            pr['vs_B2'] = dict(in_dist_B2=idb, in_dist_fd=hv['in_dist_b'], drop=hv['in_dist_drop'], fired=hv['fired'], passes=hv['passes'])
        res['parents'][p] = pr
    P = res['parents']
    d4 = c2_pilot.boot(ah_fd, ah_n)
    res['marks'] = dict(
        mark1_holdout_mean=(float(np.mean(ho)) if len(ho) == len(parents) else None), mark1_bar=bar, mark1=(bool(np.mean(ho) >= bar) if len(ho) == len(parents) else 'holdout not scored'),
        mark2=all(P[p]['mark2'] for p in parents), mark3=all(P[p]['harm_passes'] for p in parents),
        mark4_fd_minus_N=list(d4), mark4=bool(d4[0] > 0 and d4[1] > 0),
        c2_dev_mean=float(np.mean([P[p]['c2_dev'] for p in parents])))
    if ah_rp:
        t = c2_pilot.boot(ah_fd, ah_rp)
        r_n = c2_pilot.boot(ah_rp, ah_n)
        res['marks'].update(fd_minus_rp=list(t), rp_minus_N=list(r_n), transfer_label=('through transfer' if t[0] > 0 and t[1] > 0 else 'improved, not shown to come from the new skill'))
    fails = sum(not P[p]['harm_passes'] for p in parents)
    res['marks']['proved_wrong'] = bool(fails >= 3)
    return res


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('cmd', choices=('snaps', 'screenA', 'holdout', 'confirm'))
    a.add_argument('--out'); a.add_argument('--arms', nargs='+', default=['rlc', 'fd']); a.add_argument('--steps', nargs='+', type=int, default=[32, 64])
    a.add_argument('--root'); a.add_argument('--b2-dir'); a.add_argument('--parents', nargs='+', default=['s200', 's201', 's202', 's203', 's204', 's205']); a.add_argument('--threads', type=int, default=1)
    a = a.parse_args()
    torch.set_num_threads(a.threads)
    if a.cmd == 'snaps':
        snaps(os.path.expanduser(a.out), a.arms, a.steps)
    elif a.cmd == 'holdout':
        holdout(os.path.expanduser(a.out), a.arms)
    elif a.cmd == 'confirm':
        r = confirm(os.path.expanduser(a.root), a.parents, a.b2_dir)
        _dump(r, os.path.join(os.path.expanduser(a.root), 'confirm.json'))
        print(json.dumps(r['marks'], indent=1))
    else:
        r = screen_a(os.path.expanduser(a.root), a.parents)
        _dump(r, os.path.join(os.path.expanduser(a.root), 'screenA.json'))
        print(json.dumps(r['marks'], indent=1))
        for p, pr in r['parents'].items():
            for k, s in pr['steps'].items():
                print(p, k, 'rlc c2 %.1f drop %.2f %s | fd c2 %.1f drop %.2f %s' % (s['rlc']['c2'], s['rlc']['drop'], s['rlc']['fired'], s['fd']['c2'], s['fd']['drop'], s['fd']['fired']))

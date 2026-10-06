"""Test B1 analysis (design/B1-students.md section 5, PASS-MARKS.md addendum 3), computed exactly as written.
python3 -m custom_io.analyze_b1 [--results DIR ...] [--seeds 300,301] [--out-json F] [--out-md F] [--expect-teach SHA] [--expect-gen SHA]
Reads the RESULT.json of runs folded as b2t_sN (B2-M on TEACH), b2g_sN (B2-M on GEN), tft_sN (plain_tf-M on TEACH) under the results dirs, pairs them by
seed and writes results/B1-ANALYSIS.json and results/RESULTS-B1.md. diff_s = A_s - B_s on new kinds pooled (unrounded %); 'ahead on both seeds' = diff_s > 0 for
every seed. B1-a PASS: mean >= 15 and ahead on both; PROVED WRONG: mean < 5; else FAIL. B1-b PASS: mean donor exact (choice 9) <= 10 (printed
UNINFORMATIVE when b2t's mean intact new-kinds score is under 20). B1-c PASS: mean >= 3 and ahead on both. A mark is NOT JUDGED when a run it needs is missing or
invalid (status != ok, steps != 16000, recipe / cfg / size differs from choices 6-8, data MANIFEST.json sha256 differs from the one in PASS-MARKS addendum 3
or --expect-*; --skip-data-check turns only that last check off, for smoke runs)."""
import argparse, hashlib, json, os, re, sys
from custom_io.english import eval_sets, en_norm

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = {'b2t': ('ledger', 'teach'), 'b2g': ('ledger', 'gen'), 'tft': ('plain_tf', 'teach')}
SIZES = {'ledger': 10914681, 'plain_tf': 10782336}
CFG = {'ledger': dict(d=384, n_heads=6, reader_layers=2, blocks=3, n_loops=8, mlp=6.0, copy=True, span=True),
       'plain_tf': dict(d_model=384, n_layers=6, n_heads=6, max_ans=32)}
CFG_OK_EXTRA = dict(span_max=12, dk=64, w_noop=0.1, wpos=True, n_loops=1, place=False)          # defaults a cfg may spell out
RECIPE = dict(batch=256, lr=7e-4, warmup=500, bf16=True, max_ans=32, steps=16000, minutes=None, final_eval=True,
              grad_clip=1.0, order='shuffled')
SETS = ['fresh', 'new_r5', 'new_r6', 'new_pooled', 'gen_heldout', 'in_dist_heldout']
BARE = {'fresh': 75.0, 'new_r5': 67.7, 'new_r6': 77.6}          # the bare 1.2B 8-shot
SANDWICH = {'fresh': 92.2, 'new_pooled': 78.2}                   # today's sandwich
RUN = re.compile(r'^(b2t|b2g|tft)_s(\d+)$')


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def recorded_shas(passmarks):
    """{'teach': sha, 'gen': sha} from the lines of PASS-MARKS addendum 3 that name an arm and its 'manifest', one arm per line, arm first:
    '- teach MANIFEST.json sha256 <64 hex>' (table rows and two arms on one line are not read; analyze warns when fewer than 2 arms end up with a sha)."""
    out = {}
    if os.path.exists(passmarks):
        text = open(passmarks).read()
        text = text[text.find('Addendum 3'):] if 'Addendum 3' in text else text
        for line in text.splitlines():
            m = re.search(r'(?i)\b(teach|gen)\b[^\n]*manifest[^\n]*?\b([0-9a-f]{64})\b', line)
            if m:
                out[m.group(1).lower()] = m.group(2)
    return out


def find_runs(dirs):
    """-> {(arm, seed): path of RESULT.json} (the newest if a name occurs twice) and the list of duplicate names (analyze marks those runs invalid)."""
    found, dup = {}, []
    for d in dirs:
        for root, _, files in os.walk(d):
            m = RUN.match(os.path.basename(root))
            if m and 'RESULT.json' in files:
                key, p = (m.group(1), int(m.group(2))), os.path.join(root, 'RESULT.json')
                if key in found:
                    dup.append(f'{key[0]}_s{key[1]}')
                    if os.path.getmtime(p) < os.path.getmtime(found[key]):
                        continue
                found[key] = p
    return found, dup


def validate(arm, seed, res, expect, data_check=True):
    """-> list of reasons the run is invalid (empty = valid)."""
    model, which = ARMS[arm]
    c, why = res.get('config') or {}, []
    if res.get('status') != 'ok':
        why.append(f"status {res.get('status')!r} != 'ok'")
    if res.get('steps') != 16000:
        why.append(f"steps {res.get('steps')} != 16000")
    if c.get('model') != model:
        why.append(f"model {c.get('model')!r} != {model!r}")
    for k, v in RECIPE.items():
        if c.get(k) != v:
            why.append(f'recipe {k}: {c.get(k)!r} != {v!r}')
    if c.get('seed') != seed:
        why.append(f"seed {c.get('seed')} != {seed}")
    cfg = c.get('cfg') or {}
    want = CFG[model]
    bad = {k: (cfg.get(k), v) for k, v in want.items() if cfg.get(k) != v}
    extra = {k: v for k, v in cfg.items() if k not in want and CFG_OK_EXTRA.get(k, object()) != v}
    if bad or extra:
        why.append(f'cfg differs: {bad or ""} {("extra " + str(extra)) if extra else ""}'.strip())
    if res.get('n_params') != SIZES[model]:
        why.append(f"n_params {res.get('n_params')} != {SIZES[model]}")
    en = res.get('english')
    if not isinstance(en, dict) or g(en, 'intact', 'new_pooled', 'n') != 384 or g(en, 'intact', 'fresh', 'n') != 192:
        why.append('no english eval with 384 new-kinds-pooled and 192 fresh rows')
    if arm == 'b2t' and g(en, 'lesions', 'new_pooled', 'donor', 'exact') is None:
        why.append('no donor result (lesions.new_pooled.donor.exact) for B1-b')
    if data_check:
        want_sha, data = expect.get(which), c.get('data')
        mp = os.path.join(data, 'MANIFEST.json') if data else None
        if not want_sha:
            why.append(f'no recorded {which} manifest sha256 (PASS-MARKS addendum 3 / --expect-{which})')
        elif not mp or not os.path.exists(mp):
            why.append(f'data manifest {mp} not found')
        elif sha256(mp) != want_sha:
            why.append(f'data manifest sha256 {sha256(mp)[:12]} != recorded {want_sha[:12]}')
    return why


def metrics(res):
    en = res['english']
    m = {k: g(en, 'intact', k, 'exact') for k in SETS}
    m.update(n_params=res.get('n_params'), by_atype=g(en, 'intact', 'new_pooled', 'by_atype'),
             reachable={k: g(en, 'intact', k, 'reachable') for k in SETS}, lesions=en.get('lesions'),
             donor=g(en, 'lesions', 'new_pooled', 'donor'), donor_fresh=g(en, 'lesions', 'fresh', 'donor'),
             loops0=g(en, 'lesions', 'new_pooled', 'loops:0'), peak_mem_mib=res.get('peak_mem_mib'))
    return m


def diffs(runs, a, b, seeds, key=lambda m: m['new_pooled']):
    """-> per-seed diff a - b (None if either run is not valid), its mean, 'ahead' (diff > 0 on every seed)."""
    per = {}
    for s in seeds:
        x, y = runs.get((a, s)), runs.get((b, s))
        per[s] = None if not (x and y and x['valid'] and y['valid']) else key(x['m']) - key(y['m'])
    ok = all(v is not None for v in per.values())
    mu = mean(per.values()) if ok else None
    return dict(per_seed=per, mean=mu, ahead_all=ok and all(v > 0 for v in per.values()))


def judge(runs, seeds):
    a, c = diffs(runs, 'b2t', 'b2g', seeds), diffs(runs, 'b2t', 'tft', seeds)
    marks = {}
    ni = 'NOT JUDGED'
    why = lambda *need: [f'{r}_s{s}: ' + '; '.join(runs[(r, s)]['reasons']) if (r, s) in runs else f'{r}_s{s}: missing'
                        for r in need for s in seeds if not ((r, s) in runs and runs[(r, s)]['valid'])]
    marks['B1-a'] = dict(a, rule='PASS if mean >= +15 and ahead on every seed; PROVED WRONG if mean < +5; else FAIL', why_not=why('b2t', 'b2g'),
                         verdict=ni if a['mean'] is None else 'PASS' if a['mean'] >= 15 and a['ahead_all'] else 'PROVED WRONG' if a['mean'] < 5 else 'FAIL')
    marks['B1-c'] = dict(c, rule='PASS if mean >= +3 and ahead on every seed', why_not=why('b2t', 'tft'),
                         verdict=ni if c['mean'] is None else 'PASS' if c['mean'] >= 3 and c['ahead_all'] else 'FAIL')
    per = {s: g(runs.get(('b2t', s)) or {}, 'm', 'donor', 'exact') if (('b2t', s) in runs and runs[('b2t', s)]['valid']) else None for s in seeds}
    intact = {s: runs[('b2t', s)]['m']['new_pooled'] if (('b2t', s) in runs and runs[('b2t', s)]['valid']) else None for s in seeds}
    ok = all(v is not None for v in per.values())
    mu, mi = (mean(per.values()), mean(intact.values())) if ok else (None, None)
    v = ni if mu is None else 'PASS' if mu <= 10 else 'FAIL'
    if mu is not None and mi < 20:
        v = f'UNINFORMATIVE (intact new-kinds mean {mi:.2f} < 20; the rule alone would say {v})'
    marks['B1-b'] = dict(per_seed=per, mean=mu, intact_new_pooled_per_seed=intact, intact_mean=mi, rule='PASS if the mean donor exact <= 10', why_not=why('b2t'), verdict=v)
    return marks


def read_only(runs, seeds, eval_dir):
    ro = {'by_run': {}, 'mean': {}, 'atype_diffs': {}, 'always': {}, 'distance': {}}
    for (arm, s), r in sorted(runs.items()):
        if s in seeds and r['valid']:
            ro['by_run'][f'{arm}_s{s}'] = r['m']
    for arm in ARMS:
        ms = [runs[(arm, s)]['m'] for s in seeds if (arm, s) in runs and runs[(arm, s)]['valid']]
        if ms:
            ro['mean'][arm] = {k: mean(m[k] for m in ms) for k in SETS} | dict(
                n=len(ms), donor_exact=mean(g(m, 'donor', 'exact') for m in ms), loops0_exact=mean(g(m, 'loops0', 'exact') for m in ms))
    for name, (x, y) in {'B1-a (b2t - b2g)': ('b2t', 'b2g'), 'B1-c (b2t - tft)': ('b2t', 'tft')}.items():
        types = sorted({t for s in seeds for arm in (x, y) if (arm, s) in runs and runs[(arm, s)]['valid'] for t in runs[(arm, s)]['m']['by_atype'] or {}})
        ro['atype_diffs'][name] = {t: diffs(runs, x, y, seeds, lambda m, t=t: g(m, 'by_atype', t, 'exact') or 0.0) for t in types}
    sets = eval_sets(eval_dir)
    for k in ('fresh', 'new_pooled'):
        yn = [r for r in sets[k] if r['atype'] == 'yes_no']
        yes = sum(en_norm(r['canonical']) == 'yes' for r in yn)
        ro['always'][k] = dict(n_yes_no=len(yn), n=len(sets[k]), always_yes=100 * yes / max(len(yn), 1), always_no=100 * (len(yn) - yes) / max(len(yn), 1),
                               always_yes_on_all_rows=100 * yes / len(sets[k]), always_no_on_all_rows=100 * (len(yn) - yes) / len(sets[k]))
    for arm, m in ro['mean'].items():
        ro['distance'][arm] = {f'{k} - bare 8-shot': m[k] - v for k, v in BARE.items() if m[k] is not None} | {
            f'{k} - sandwich': m[k] - v for k, v in SANDWICH.items() if m[k] is not None}
    return ro


f2 = lambda x: 'n/a' if x is None else f'{x:.2f}'


def markdown(out):
    L = ['# Test B1 results (students)', '', f"Seeds: {out['seeds']}. Scores are exact match under the round-6 scorer, in percent (unrounded in B1-ANALYSIS.json).", '',
         '## Marks', '', '| mark | verdict | mean | per seed | ahead on every seed |', '|---|---|---|---|---|']
    for k, m in out['marks'].items():
        L.append(f"| {k} | **{m['verdict']}** | {f2(m['mean'])} | {', '.join(f'{s}: {f2(v)}' for s, v in m['per_seed'].items())} | {m.get('ahead_all', '')} |")
    for k, m in out['marks'].items():
        if m['why_not']:
            L += ['', f'{k} could not be fully judged:'] + [f'- {w}' for w in m['why_not']]
    L += ['', '## Runs', '', '| run | valid | FRESH | R5 | R6 | new pooled | GEN-HELDOUT (GEN arm\'s own distribution) | in-dist held-out | donor | loops:0 | size |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for name, r in out['runs'].items():
        m = r.get('m')
        if m:
            L.append(f"| {name} | {r['valid']} | " + ' | '.join(f2(m[k]) for k in SETS) + f" | {f2(g(m, 'donor', 'exact'))} | {f2(g(m, 'loops0', 'exact'))} | {m['n_params']:,} |")
        else:
            L.append(f"| {name} | {r['valid']} | {r['reasons']} |")
    for name, r in out['runs'].items():
        if r['reasons']:
            L.append(f"\n{name} invalid: " + '; '.join(r['reasons']))
    ro = out['read_only']
    L += ['', '## Read only', '', '### Means over valid seeds', '', '| arm | n | ' + ' | '.join(SETS) + ' | donor | loops:0 |', '|' + '---|' * (len(SETS) + 4)]
    for arm, m in ro['mean'].items():
        L.append(f'| {arm} | {m["n"]} | ' + ' | '.join(f2(m[k]) for k in SETS) + f' | {f2(m["donor_exact"])} | {f2(m["loops0_exact"])} |')
    L += ['', '### Difference by answer type (new kinds pooled, mean over seeds; per-seed in the JSON)', '', '| comparison | ' + 'atype | diff |', '|---|---|---|']
    for name, d in ro['atype_diffs'].items():
        for t, x in d.items():
            L.append(f'| {name} | {t} | {f2(x["mean"])} |')
    L += ['', '### Always yes / always no (the yes/no rows)', '']
    for k, a in ro['always'].items():
        L.append(f"- {k}: {a['n_yes_no']} yes/no rows of {a['n']}; always-yes scores {a['always_yes']:.2f}% of them ({a['always_yes_on_all_rows']:.2f}% of all rows), always-no {a['always_no']:.2f}% ({a['always_no_on_all_rows']:.2f}%)")
    L += ['', '### Donor and loops:0 (read only, b2t first)', '', '| run | donor exact | skipped | donor_match | donor_position_match | pos_coincide | exact given intact right | plain exact | plain pos_coincide | loops:0 exact | loops:0 modes (question-blind talker) |', '|' + '---|' * 11]
    for name, m in ro['by_run'].items():
        d, p, l = m.get('donor') or {}, (m.get('donor') or {}).get('plain') or {}, m.get('loops0') or {}
        L.append(f"| {name} | {f2(d.get('exact'))} | {d.get('skipped', 'n/a')} | {f2(d.get('donor_match'))} | {f2(d.get('donor_position_match'))} | {f2(d.get('pos_coincide'))} | "
                 f"{f2(g(d, 'exact_given_intact_right', 'exact'))} | {f2(p.get('exact'))} | {f2(p.get('pos_coincide'))} | {f2(l.get('exact'))} | {l.get('modes', 'n/a')} |")
    L += ['', '### Reachability (share of new-kinds-pooled rows the talker can emit at all)', '']
    L += [f"- {name}: {f2(g(m, 'reachable', 'new_pooled', 'share'))}%" for name, m in ro['by_run'].items()]
    L += ['', '### Distance to the references (mean over valid seeds)', '']
    for arm, d in ro['distance'].items():
        L.append(f'- {arm}: ' + ', '.join(f'{k} {v:+.2f}' for k, v in d.items()))
    L += ['', 'References: bare 1.2B 8-shot 75.0 FRESH, 67.7 R5, 77.6 R6; today\'s sandwich 92.2 FRESH, 78.2 new pooled.',
          '', 'GEN-HELDOUT-R4 is the GEN arm\'s own distribution (most of its names and nouns are in that arm\'s training pools) and is never subtracted across arms.']
    return '\n'.join(L) + '\n'


def analyze(dirs, seeds, eval_dir, passmarks, expect=None, data_check=True):
    expect = {**recorded_shas(passmarks), **{k: v for k, v in (expect or {}).items() if v}}
    if data_check and len([v for v in expect.values() if v]) < 2:
        print(f'WARNING: manifest sha256 known for only {sorted(expect)} (PASS-MARKS addendum 3 needs one line each: "- teach MANIFEST.json sha256 <hex>"); runs without one are NOT JUDGED', file=sys.stderr)
    found, dup = find_runs(dirs)
    runs = {}
    for (arm, s), p in sorted(found.items()):
        res = json.load(open(p))
        reasons = validate(arm, s, res, expect, data_check)
        if f'{arm}_s{s}' in dup:
            reasons.append(f'run name {arm}_s{s} occurs in more than one folder (screen and confirm seeds clash?); pass one queue dir')
        runs[(arm, s)] = dict(path=p, reasons=reasons, valid=not reasons, m=metrics(res) if isinstance(res.get('english'), dict) and g(res, 'english', 'intact') else None)
        if runs[(arm, s)]['m'] is None:
            runs[(arm, s)]['valid'] = False
    out = dict(seeds=seeds, expect_manifest_sha256=expect, duplicates=dup, marks=judge(runs, seeds))
    out['runs'] = {f'{a}_s{s}': {k: v for k, v in r.items()} for (a, s), r in runs.items()}
    out['read_only'] = read_only(runs, seeds, eval_dir)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', default=[os.path.join(HERE, 'results')])
    ap.add_argument('--seeds', default='300,301')
    ap.add_argument('--eval', default=os.path.join(HERE, 'english_eval'))
    ap.add_argument('--passmarks', default=os.path.join(HERE, 'PASS-MARKS.md'))
    ap.add_argument('--expect-teach')
    ap.add_argument('--expect-gen')
    ap.add_argument('--skip-data-check', action='store_true')
    ap.add_argument('--out-json', default=os.path.join(HERE, 'results', 'B1-ANALYSIS.json'))
    ap.add_argument('--out-md', default=os.path.join(HERE, 'results', 'RESULTS-B1.md'))
    a = ap.parse_args(argv)
    out = analyze(a.results, [int(x) for x in a.seeds.split(',')], a.eval, a.passmarks, dict(teach=a.expect_teach, gen=a.expect_gen), not a.skip_data_check)
    for f in (a.out_json, a.out_md):
        os.makedirs(os.path.dirname(os.path.abspath(f)), exist_ok=True)
    json.dump(out, open(a.out_json, 'w'), indent=1)
    md = markdown(out)
    open(a.out_md, 'w').write(md)
    print(md)
    return out


if __name__ == '__main__':
    main()

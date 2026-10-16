"""Scratch A/B readouts for one finished run (run card: scratch A/B screen, Oct 16). Runs on the box right after training,
on the run's own checkpoint.pt, and writes RUN/readout.json.

  python -m custom_io.scratch_readout --run DIR --data D --big-data DB [--bf16]

Eval sets: the six dev splits of --data plus the chain-5 panel of --big-data (the same rows final_eval scores), each
evaluated with evalx.evaluate at batch 128 (the same length-sorted batches as final_eval, so a row's shuffle partner is
the same in every model).

base (register_loop):
  swap      the checkpoint loaded into RegisterLoop (its own class) and into RegisterLoopScratch; answers compared
            question by question on every eval set. swap.identical = no question differs. Also recorded: whether the
            reloaded RegisterLoop reproduces the run's RESULT.json exact scores and chain-5 hits.
  lesions   intact / scratch_zero / scratch_shuffle through the swapped model, ONLY if swap.identical.
arm (register_scratch):
  lesions   intact / scratch_zero / scratch_shuffle (after round 1, the default).
  scratch   per round, % of rows whose scratch slots (decoded through the talker) equal the next worked-step value;
            values longer than the 7 slots are excluded and counted. Rows: the staircase rows (chain-5 in_dist with >= 2
            step values, big build) and every in_dist dev row.
"""
import argparse, contextlib, json, os, time
import torch
from custom_io import diag_register as dg
from custom_io.data import DEV_SPLITS, CharVocab, Dataset, collate, to_device
from custom_io.evalx import CHAIN5, _dev_rows, evaluate, is_hit
from custom_io.models.register_loop import RegisterLoop
from custom_io.models.register_scratch import RegisterLoopScratch

LESIONS = [None, 'scratch_zero', 'scratch_shuffle']


def eval_sets(data, big):
    sets = {s: _dev_rows(data, s, None) for s in DEV_SPLITS}
    sets['chain5'] = [r for r in _dev_rows(big, 'in_dist', None) if r['family'] in CHAIN5]
    return sets


def answers(model, sets, lesion, bs, device, amp):
    """{set: {'exact', 'n', 'preds': {id: answer}}}"""
    out = {}
    for k, rows in sets.items():
        with amp():
            r = evaluate(model, rows, bs, device, lesion, return_preds=True)
        assert len(r['preds']) == len(rows), f'duplicate ids in {k}'
        out[k] = {'exact': r['exact'], 'n': r['n'], 'preds': r['preds']}
    return out


def lesion_table(model, sets, bs, device, amp, intact=None):
    tab = {}
    for lesion in LESIONS:
        res = intact if lesion is None and intact is not None else answers(model, sets, lesion, bs, device, amp)
        tab[lesion or 'intact'] = {k: {'exact': v['exact'], 'n': v['n']} for k, v in res.items()}
        print(json.dumps({'event': 'readout_lesion', 'lesion': lesion or 'intact',
                          **{k: round(v['exact'], 2) for k, v in res.items()}}), flush=True)
    return tab


@torch.no_grad()
def scratch_accuracy(model, rows, bs, device, amp):
    """Per round r (1-based in the output list order): scratch readout == next worked-step value vals[min(r+1, k)-1]
    (0-based r -> vals[min(r + 2, k) - 1], exactly the training target). Values longer than n_scratch are excluded."""
    R, ns, ds = model.n_loops, model.n_scratch, Dataset(rows, model.vocab, strict=False)
    hit, n, excl = [0] * R, [0] * R, [0] * R
    for s in range(0, len(rows), bs):
        ids = list(range(s, min(s + bs, len(rows))))
        b = to_device(collate([ds[i] for i in ids]), device)
        with amp():
            ss = model.scratch_strings(b)
        for r in range(R):
            for j, i in enumerate(ids):
                v = dg.step_values(rows[i], model.use_steps)
                t = v[min(r + 2, len(v)) - 1]
                if len(t) > ns:
                    excl[r] += 1
                    continue
                n[r] += 1
                hit[r] += int(ss[r][j] == t)
    return {'n_rows': len(rows), 'by_round': [100 * h / max(k, 1) for h, k in zip(hit, n)], 'n_scored': n, 'n_excluded': excl}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True, help='run dir with checkpoint.pt and RESULT.json')
    ap.add_argument('--data', required=True)
    ap.add_argument('--big-data', required=True)
    ap.add_argument('--bf16', action='store_true')
    ap.add_argument('--eval-batch', type=int, default=128)
    ap.add_argument('--device', default='auto')
    a = ap.parse_args(argv)
    t0 = time.time()
    device = torch.device('cuda' if a.device == 'auto' and torch.cuda.is_available() else 'cpu' if a.device == 'auto' else a.device)
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if a.bf16 and device.type == 'cuda' else contextlib.nullcontext
    ck = torch.load(os.path.join(a.run, 'checkpoint.pt'), map_location=device)
    vocab, cfg = CharVocab(ck['chars']), ck['cfg']
    sets = eval_sets(a.data, a.big_data)
    out = {'run': a.run, 'model': ck['name'], 'cfg': cfg, 'step': ck['step'], 'eval_batch': a.eval_batch,
           'sets': {k: len(v) for k, v in sets.items()}}

    def load(cls):
        m = cls(vocab, **cfg)
        m.load_state_dict(ck['model'], strict=True)
        return m.to(device).eval()

    if ck['name'] == 'register_loop':
        own = answers(load(RegisterLoop), sets, None, a.eval_batch, device, amp)
        sw_model = load(RegisterLoopScratch)
        sw = answers(sw_model, sets, None, a.eval_batch, device, amp)
        diffs, first = {}, []
        for k in sets:
            d = [i for i in own[k]['preds'] if own[k]['preds'][i] != sw[k]['preds'][i]]
            diffs[k] = len(d)
            first += [{'set': k, 'id': i, 'own': own[k]['preds'][i], 'swap': sw[k]['preds'][i]} for i in d[:5]]
        swap = {'identical': not any(diffs.values()), 'n_questions': sum(len(v) for v in sets.values()),
                'n_differ': diffs, 'first_differences': first[:20]}
        # the reloaded base against what the run itself recorded at the end of training
        try:
            res = json.load(open(os.path.join(a.run, 'RESULT.json')))
            fe = res.get('final_eval') or {}
            swap['vs_result_json'] = {
                'exact_delta': {s: round(own[s]['exact'] - fe[s]['exact'], 4) for s in DEV_SPLITS if s in fe},
                'chain5_hits_differ': sum(int(is_hit(own['chain5']['preds'][r['id']], r)) != res['chain5']['intact']['hits'].get(r['id'])
                                          for r in sets['chain5']) if 'chain5' in res else None}
        except Exception as e:
            swap['vs_result_json'] = {'error': repr(e)}
        out['swap'] = swap
        print(json.dumps({'event': 'readout_swap', 'identical': swap['identical'], 'n_differ': diffs,
                          'vs_result_json': swap['vs_result_json']}), flush=True)
        if swap['identical']:
            out['lesions'] = lesion_table(sw_model, sets, a.eval_batch, device, amp, intact=sw)
            m = sw_model
        else:
            out['lesions'] = None
            out['lesions_skipped'] = 'swap check failed: the scratch class does not reproduce the base answers'
            m = None
    elif ck['name'] == 'register_scratch':
        m = load(RegisterLoopScratch)
        out['lesions'] = lesion_table(m, sets, a.eval_batch, device, amp)
    else:
        raise SystemExit(f'not a scratch A/B run: {ck["name"]}')

    if m is not None:   # for the base (through the swap) this is a reference only: its scratch slots were never taught
        sc = {'staircase_rows': scratch_accuracy(m, dg.chain5_rows(a.big_data), a.eval_batch, device, amp),
              'in_dist_rows': scratch_accuracy(m, sets['in_dist'], a.eval_batch, device, amp)}
        out['scratch_next_value'] = sc
        print(json.dumps({'event': 'readout_scratch', **{k: {'by_round': [round(x, 1) for x in v['by_round']],
                                                              'n_excluded': v['n_excluded']} for k, v in sc.items()}}), flush=True)
    out['wall_s'] = time.time() - t0
    json.dump(out, open(os.path.join(a.run, 'readout.json'), 'w'), indent=1)
    print(json.dumps({'event': 'readout_done', 'wall_s': round(out['wall_s'], 1)}), flush=True)
    return out


if __name__ == '__main__':
    main()

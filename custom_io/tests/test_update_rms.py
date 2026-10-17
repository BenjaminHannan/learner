"""train.py --log-update-rms (C8): per-module update rms + pre-clip grad-norm stats, and proof it changes nothing.
python3 -m pytest custom_io/tests/test_update_rms.py   (CPU, tiny plain_tf on a synthetic data dir, about 10 s)"""
import contextlib, io, json, os, random, tempfile
import numpy as np
import torch
from custom_io import data as D
from custom_io.data import CharVocab, Dataset, load_rows, to_device, train_batches
from custom_io.models import build
from custom_io.train import GradStats, lr_at, main, update_group

CFG = '{"d_model":32,"n_layers":2,"n_heads":2}'
STEPS, EVERY = 30, 10


def make_data():
    tmp = tempfile.mkdtemp()
    os.makedirs(tmp + '/dev')
    rows = [dict(id=f't{i}', prompt=f'Say the word number {i} twice.', answer=('abcdefghij'[i % 10] * (i % 4 + 1)), accepted=[], family='x', level=0, steps=[])
            for i in range(48)]
    for f in ('train.jsonl', 'dev/in_dist.jsonl'):
        with open(os.path.join(tmp, f), 'w') as fh:
            fh.write(''.join(json.dumps(r) + '\n' for r in rows))
    return tmp


class Rec(torch.optim.AdamW):
    made = []

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        Rec.made.append(self)


def run_main(tmp, name, *flags):
    """train.main on the synthetic data -> (result, train events, checkpoint state_dict, optimizer)."""
    Rec.made.clear()
    buf, orig = io.StringIO(), torch.optim.AdamW
    torch.optim.AdamW = Rec
    try:
        with contextlib.redirect_stdout(buf):
            res = main(['--model', 'plain_tf', '--cfg', CFG, '--data', tmp, '--steps', str(STEPS), '--batch', '8', '--lr', '3e-3', '--warmup', '5',
                        '--log-every', str(EVERY), '--out', f'{tmp}/{name}', *flags])
    finally:
        torch.optim.AdamW = orig
    ev = [json.loads(l) for l in buf.getvalue().splitlines() if l.startswith('{')]
    sd = torch.load(f'{tmp}/{name}/checkpoint.pt')['model']
    return res, [e for e in ev if e['event'] == 'train'], sd, Rec.made[0]


def reference(tmp):
    """The pre-C8 loop, copied: clip_grad_norm_ result discarded, no snapshots -> (train losses per step, state_dict, optimizer)."""
    random.seed(0); np.random.seed(0); torch.manual_seed(0); torch.cuda.manual_seed_all(0)
    D.set_max_ans(8)
    rows = load_rows(os.path.join(tmp, 'train.jsonl'))
    vocab = CharVocab.get(tmp, None, rows)
    batches = train_batches(Dataset(rows, vocab), 8, 'shuffled', 0)
    model = build('plain_tf', vocab, **json.loads(CFG))
    emb = {id(m.weight) for m in model.modules() if isinstance(m, torch.nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': no_decay, 'weight_decay': 0.0}], lr=3e-3, betas=(0.9, 0.95), fused=False)
    losses, run, n = [], 0.0, 0
    model.train()
    for step in range(STEPS):
        for g in opt.param_groups:
            g['lr'] = lr_at(step, STEPS, 5, 3e-3, 0.0, None)
        out = model.loss(to_device(next(batches), torch.device('cpu')))
        loss, aux = out if isinstance(out, tuple) else (out, {})
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        run += loss.detach(); n += 1
        if (step + 1) % EVERY == 0:
            losses.append(round(float(run) / n, 5)); run, n = 0.0, 0
    return losses, model.state_dict(), opt


def same_weights(a, b):
    assert a.keys() == b.keys()
    for k in a:
        assert torch.equal(a[k], b[k]), k


def same_opt(a, b):
    assert len(a.state) == len(b.state) > 0
    for (pa, sa), (pb, sb) in zip(a.state.items(), b.state.items()):
        assert sa.keys() == sb.keys()
        for k in sa:
            assert torch.equal(sa[k], sb[k]), k


def test_group_names():
    assert update_group('blocks.0.qkv.weight') == 'blocks.0' and update_group('blocks.1.ln2.bias') == 'blocks.1'
    assert update_group('tok.weight') == 'tok' and update_group('ln_f.bias') == 'ln_f' and update_group('scale') == 'scale'
    assert update_group('core.3.attn.q.weight') == 'core.3'


def test_gradstats():
    g = GradStats(1.0)
    for x in (0.5, 2.0, 1.0, 4.0):
        g.add(torch.tensor(x))
    assert g.pop() == dict(grad_norm_mean=1.875, grad_norm_max=4.0, clip_frac=0.5)      # 1.0 is not > clip
    g.add(torch.tensor(3.0))
    assert g.pop() == dict(grad_norm_mean=3.0, grad_norm_max=3.0, clip_frac=1.0)        # popped = reset


def test_flag_off_matches_original_loop():
    tmp = make_data()
    try:
        losses, sd, opt = reference(tmp)
        res, ev, sd_off, opt_off = run_main(tmp, 'off')
    finally:
        D.set_max_ans(8)
    assert [e['loss'] for e in ev] == losses and len(losses) == 3
    same_weights(sd, sd_off); same_opt(opt, opt_off)
    assert 'update_rms_log' not in res and all(k not in e for e in ev for k in ('grad_norm_mean', 'upd_rms', 'upd_rms_all', 'clip_frac'))


def test_flag_on_changes_nothing():
    tmp = make_data()
    r0, ev0, sd0, opt0 = run_main(tmp, 'off')
    r1, ev1, sd1, opt1 = run_main(tmp, 'on', '--log-update-rms')
    same_weights(sd0, sd1); same_opt(opt0, opt1)
    assert [e['loss'] for e in ev0] == [e['loss'] for e in ev1] and r0['final_train_loss'] == r1['final_train_loss']
    for a, b in zip(ev0, ev1):                  # the old keys are untouched; only the new ones are added
        assert {k: v for k, v in b.items() if k in a and k != 'elapsed'} == {k: v for k, v in a.items() if k != 'elapsed'}


def test_flag_on_logs_stats():
    tmp = make_data()
    res, ev, _, _ = run_main(tmp, 'on', '--log-update-rms', '--grad-clip', '0.05')
    assert [e['step'] for e in ev] == [10, 20, 30] and [h['step'] for h in res['update_rms_log']] == [10, 20, 30]
    json.dumps(res['update_rms_log'])
    for e, h in zip(ev, res['update_rms_log']):
        assert {k: e[k] for k in h if k != 'step'} == {k: h[k] for k in h if k != 'step'}
        assert e['grad_norm_mean'] > 0 and e['grad_norm_max'] >= e['grad_norm_mean'] and 0 <= e['clip_frac'] <= 1
        assert 0 < e['upd_rms_all'] < 1 and e['upd_rms_all'] == float(f'{e["upd_rms_all"]:.6g}')
        assert set(e['upd_rms']) == {'tok', 'pos', 'blocks.0', 'blocks.1', 'ln_f'}, set(e['upd_rms'])
        for g, v in e['upd_rms'].items():
            assert np.isfinite(v) and v > 0, (g, v)
        assert min(e['upd_rms'].values()) <= e['upd_rms_all'] <= max(e['upd_rms'].values())
    assert res['update_rms_log'][-1]['clip_frac'] == 1.0            # clip 0.05 is far below the gradient norm
    res, ev, _, _ = run_main(tmp, 'on2', '--log-update-rms', '--grad-clip', '1e9')
    assert all(e['clip_frac'] == 0.0 for e in ev)


def test_final_step_logs_when_not_multiple():
    tmp = make_data()
    res, ev, _, _ = run_main(tmp, 'on', '--log-update-rms', '--log-every', '12')
    assert [e['step'] for e in ev] == [12, 24, 30] and len(res['update_rms_log']) == 3 and all(e['upd_rms_all'] > 0 for e in ev)


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn(); print('ok', name)

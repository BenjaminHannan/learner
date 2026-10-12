"""python3 -m custom_io.tests.test_b3_run   (CPU, a few minutes; stub Gemma, no data files)
B3_G1 end to end, tiny width, max_prompt 2,000 (caps applied in a child process): 50 AdamW steps on a small repeated set of arithmetic questions hidden in 400-2,000
letters of prose, loss finite and falling; the free run and generate() work; the extra evals (call accuracy, tool off, opswap replay, write_copy, H1 rounds and B3's
length buckets / call rounds / tape full) run on a tiny dev set; the analyzer's b3_report reads the result; the checkpoint round trip keeps every weight."""
import json, os, subprocess, sys, tempfile, contextlib
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def child():
    from custom_io.g8a import caps as CP
    caps = CP.apply(dict(max_prompt=2000, max_ans=35, n_num=650, w_max=1485, n_res=11, n_reg=36, plain_target=109))
    from custom_io.data import CharVocab, Dataset, collate
    from custom_io.g8a.b3_cost import SW, SMALL
    from custom_io.g8a.tok_cost import synth_text
    from custom_io.models import build
    from custom_io.tests.test_b3 import StubEG
    V = CharVocab.build([])
    text = synth_text(60000)

    def row(i, letters, fam='chain_story2'):
        a, b, c = 120 + 17 * i, 340 + 29 * i, 7 + i
        q = f' Tom has {a} apples and buys {b} more, then gives {c} away. How many apples now?'
        body = text[i * 2000:i * 2000 + max(letters - len(q), 0)]
        return dict(id=f'r{i}', family=fam, prompt=(body + q)[-letters:] if body else q.strip(), answer=str(a + b - c), accepted=[str(a + b - c)], level=2, variant='v', stage=9, steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}'])
    lens = [400, 900, 1500, 1999]
    train = [row(i, lens[i % 4]) for i in range(8)]
    assert max(len(r['prompt']) for r in train) >= 1900
    ds = Dataset(train, V, strict=False)
    batches = [collate([ds[i] for i in range(s, s + 2)]) for s in range(0, 8, 2)]
    torch.manual_seed(0)
    m = build('b3', V, **dict(SMALL, n_loops=12), **SW)
    m._eg = [StubEG()]
    opt = torch.optim.AdamW(m.parameters(), lr=2e-3, betas=(0.9, 0.95), weight_decay=0.0)
    m.train()
    ls = []
    for s in range(50):
        loss, aux = m.loss(batches[s % 4])
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        ls.append(float(loss.detach()))
    assert all(map(lambda x: x == x and abs(x) < 1e9, ls)), ls
    first, last = sum(ls[:5]) / 5, sum(ls[-5:]) / 5
    assert last < first, (first, last)
    m.eval()
    with torch.no_grad():
        o = m.run(batches[0])
        ans = m.generate(batches[0])
    assert len(ans) == 2 and len(o['rounds']) == 2
    # a tiny dev set: 6 splits, rows of 100-1,999 letters
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'dev'))
    dev = [row(20 + i, [100, 300, 800, 1400, 1999][i % 5]) for i in range(60)]
    from custom_io.data import DEV_SPLITS
    for sp in DEV_SPLITS:
        with open(os.path.join(d, 'dev', f'{sp}.jsonl'), 'w') as f:
            for r in dev[:10]:
                f.write(json.dumps(r) + '\n')
    with open(os.path.join(d, 'dev', 'in_dist.jsonl'), 'w') as f:
        for r in dev:
            f.write(json.dumps(r) + '\n')
    ctx = dict(data=d, big=None, device=torch.device('cpu'), batch_size=8, amp=contextlib.nullcontext)
    ex = m.extra_evals(ctx)
    b3 = ex['b3']
    sp = b3['splits']['in_dist']
    assert set(sp['by_length']) == {'0-280', '281-700', '701-1300', '1301-2000'} and sp['n'] == 60, sp['by_length']
    assert 'h1' in ex and 'op_acc' in ex and 'write_copy' in ex and 'opswap' in ex
    # the analyzer reads it
    from custom_io import analyze_8a as AN
    res = dict(status='ok', extra=ex, lesions={}, final_eval=None)
    rep = AN.b3_report({('3M', 'B3', 400): res}, [400])
    assert rep['3M']['by_length']['in_dist']['1301-2000']['n'] > 0 and 'tape_full_rows' in rep['3M']
    # checkpoint round trip
    sd = m.state_dict()
    m2 = build('b3', V, **dict(SMALL, n_loops=12), **SW)
    m2.load_state_dict(sd)
    assert all(torch.equal(m2.state_dict()[k], v) for k, v in sd.items())
    print(json.dumps(dict(ok=True, loss_first5=round(first, 2), loss_last5=round(last, 2), steps=50, max_len=max(len(r['prompt']) for r in train), rounds=o['rounds'])))


def test_end_to_end():
    out = subprocess.run([sys.executable, '-m', 'custom_io.tests.test_b3_run', '--child'], cwd=ROOT, env=dict(os.environ, PYTHONPATH=ROOT), capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-4000:]
    res = json.loads(out.stdout.strip().splitlines()[-1])
    print('ok B3_G1 on CPU at 2,000 letters: 50 steps, loss %.1f -> %.1f, longest prompt %d letters, extra evals and the analyzer ran' % (res['loss_first5'], res['loss_last5'], res['max_len']))


if __name__ == '__main__':
    if '--child' in sys.argv:
        child()
    else:
        test_end_to_end()
        print('ALL OK')

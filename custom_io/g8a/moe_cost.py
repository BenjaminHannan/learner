"""Report-only cost check of the expert layer (design/8a-gx-experts section 6): one forward + backward of G-B2 3M vs GX-3M on CPU, micro-batch of 32 rows
(prompts ~200 letters, caps_g applied, EmbeddingGemma replaced by the test stub): bytes of tensors saved for backward (every pack call counted, weights included)
and wall time (best of 2 after a warm-up). Prints one JSON.   python3 -m custom_io.g8a.moe_cost"""
import json, os, time
import torch
from custom_io.g8a import caps as CP, configs as C
from custom_io.tests import moe_fp as FP


def rows(n=32):
    fill = 'the old fox sees a red hen by the long wall and then runs off to find some warm bread for the small boys at home '
    out = []
    for i in range(n):
        a, b = 10 + i, 3 + i % 7
        out.append(dict(id=f'cost{i}', prompt=(fill * 3)[:150 + 3 * i % 40] + f' Tom has {a} apples and gets {b} more . How many ?', answer=str(a + b), accepted=[str(a + b)],
                        family='story_addsub', level=1, stage=1, variant='v', steps=[f'{a} + {b} = {a + b}']))
    return out


def measure(m, b):
    saved = [0]

    def pack(t):
        saved[0] += t.numel() * t.element_size()
        return t
    times = []
    for rep in range(3):
        saved[0] = 0
        t0 = time.time()
        with torch.autograd.graph.saved_tensors_hooks(pack, lambda t: t):
            loss, _ = m.loss(b)
        loss.backward()
        times.append(time.time() - t0)
        m.zero_grad()
    return dict(saved_bytes=saved[0], seconds=min(times[1:]))


def main():
    CP.apply(json.load(open(os.path.join(os.path.dirname(__file__), 'caps_g.json'))))
    from custom_io.data import Dataset, collate
    rs = rows()
    b = collate([Dataset(rs, FP.vocab())[i] for i in range(len(rs))])
    ex = dict(eg_embed=True, n_loops=12)
    res = {}
    for name, e in (('G-B2 3M', ex), ('GX-3M', dict(ex, experts=52, top_k=8))):
        cfg = C.b2_cfg('3M', e)
        res[name] = dict(measure(FP.make(cfg), b), params=C.n('ledger', cfg), active=C.n_active('ledger', cfg))
    g, d = res['GX-3M'], res['G-B2 3M']
    res['ratio_GX_over_B2'] = dict(saved_bytes=g['saved_bytes'] / d['saved_bytes'], seconds=g['seconds'] / d['seconds'])
    res['note'] = dict(embeddinggemma='stub (moe_fp.StubEG), not the real model: its 271M frozen params are in neither arm here', dtype='fp32 on CPU, no autocast',
                       micro_batch=len(rs), threads=torch.get_num_threads(), prompt_chars=[min(len(r['prompt']) for r in rs), max(len(r['prompt']) for r in rs)])
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()

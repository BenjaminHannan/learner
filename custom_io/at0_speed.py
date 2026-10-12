"""python3 -m custom_io.at0_speed [--updates 100] [--batch 8] [--letters 280] [--threads 2]   (CPU; AT-0 (ix) of big-run PLAN.md's sixth Addendum: REPORTED, NOT GATED)
Speed and memory of B3AT (model b3at, arm AT) at 3M: the REAL 3M config (g8a/configs.b3at_cfg('3M', {"eg_embed": true}) under g8a/caps_b3g2.json, the config the queue file
8aAT-3M-s400-pc.txt trains: 4,023,302 trained parameters), `--updates` optimizer updates (AdamW, lr 1e-3, grad clip 1) on batches of `--batch` rows (the micro-batch of the PC job:
batch 256 / accum 32 = 8), each row a prose filler of `--letters` letters followed by a question with 0, 1 or 2 tool calls (the rows of test_b3's mix), the loss = B3AT's teacher-forced
loss over every row's turns (R drawn per batch from KS_T = 4, 8, 16, 32, row cut TOTAL_CAP 96 // (calls + 1)). The frozen Gemma is the real EmbeddingGemma if it loads offline
(from $CUSTOM_IO_EG2 or the Hugging Face cache), else test_b3's stub (deterministic noise states of the same shape: the thinker, talker and tape cost are real, the Gemma forward
pass is not); the line says which. Prints seconds per update (mean, median, the slowest, and by drawn R), the rounds each update ran, and peak memory (the process's peak resident
set, from resource.getrusage; the Gemma weights are included only if the real one loaded). The PC's GPU numbers are not these: this is the CPU cost on the code's own path, the
input to choosing the job's --accum (the queue file's guess is 32)."""
import argparse, json, os, resource, statistics, time
import torch


def load_eg():
    """The real frozen EmbeddingGemma if it loads offline, else None (the caller uses the stub)."""
    try:
        os.environ.setdefault('HF_HUB_OFFLINE', '1')
        from custom_io.models.eg import FrozenEG
        eg = FrozenEG(by_bytes=True)
        eg.load('cpu')
        return eg
    except Exception as e:      # no weights here: the stub
        return None


def make_rows(n, letters):
    from custom_io.tests.test_b3 import rows
    rs = []
    for i, r in enumerate(rows(n)):
        pad = ('The old harbour keeps its lamps lit until the last boat is in, and the clerk writes the tide down. ' * 40)[:max(0, letters - len(r['prompt']) - 1)]
        rs.append(dict(r, id=f'sp{i}', prompt=(pad + ' ' + r['prompt']).strip()))
    return rs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--updates', type=int, default=100)
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--letters', type=int, default=280)
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--stub', action='store_true', help='use the stub Gemma without trying the real one')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    from custom_io.data import ByteVocab, Dataset, collate
    from custom_io.g8a import caps as CP
    from custom_io.g8a import configs as C
    from custom_io.models import build
    here = os.path.dirname(os.path.abspath(__file__))
    caps = CP.apply(json.load(open(os.path.join(here, 'g8a', 'caps_b3g2.json'))))
    extra = {'eg_embed': True}
    if CP.n_loops_needed(caps) > 8:
        extra['n_loops'] = CP.n_loops_needed(caps)      # what job.py adds to --b2-extra
    cfg = C.b3at_cfg('3M', extra)
    V = ByteVocab()
    torch.manual_seed(0)
    m = build('b3at', V, **cfg)
    eg = None if a.stub else load_eg()
    if eg is not None:
        m._eg = [eg]
    else:
        from custom_io.tests.test_b3 import StubEG
        m._eg = [StubEG()]
    gem = 'real EmbeddingGemma' if eg is not None else 'stub Gemma'
    n_train = m.n_params()
    print(f'b3at 3M: {n_train:,} trained parameters (g2c3s {C.G2C3S:,}: {100 * (n_train / C.G2C3S - 1):+.2f}%), writer_mlp {cfg["writer_mlp"]}, n_loops {cfg["n_loops"]}; {gem}; {a.threads} threads; '
          f'batch {a.batch}, {a.letters} letters, {a.updates} updates', flush=True)
    rs = make_rows(max(a.batch, 12), a.letters)
    ds = Dataset(rs, V, strict=False)
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=1e-3)
    m.train()
    torch.manual_seed(123)
    secs, rounds, by_R = [], [], {}
    for u in range(a.updates):
        idx = [(u * a.batch + j) % len(rs) for j in range(a.batch)]
        b = collate([ds[i] for i in idx])
        t = time.perf_counter()
        loss, aux = m.loss(b)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        dt = time.perf_counter() - t
        secs.append(dt)
        rounds.append(float(aux['rounds']))
        by_R.setdefault(int(aux['R']), []).append(dt)
        assert torch.isfinite(loss.detach()), f'update {u}: non-finite loss'
        if (u + 1) % 10 == 0:
            print(f'  update {u + 1}: loss {float(loss.detach()):.3f}, last {dt:.2f}s, mean so far {statistics.mean(secs):.2f}s', flush=True)
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024      # Linux: kilobytes
    res = dict(model='b3at', rung='3M', gemma=gem, trained_params=n_train, updates=a.updates, batch=a.batch, letters=a.letters, threads=a.threads,
               s_per_update_mean=round(statistics.mean(secs), 3), s_per_update_median=round(statistics.median(secs), 3), s_per_update_max=round(max(secs), 3),
               s_by_R={k: round(statistics.mean(v), 3) for k, v in sorted(by_R.items())}, updates_by_R={k: len(v) for k, v in sorted(by_R.items())},
               mean_rounds_per_row=round(statistics.mean(rounds), 1), peak_rss_mb=round(peak_mb))
    print(json.dumps(res), flush=True)
    print(f'AT-0 (ix) (reported, not gated): {res["s_per_update_mean"]} s per update (median {res["s_per_update_median"]}, slowest {res["s_per_update_max"]}) at batch {a.batch}, '
          f'peak memory {res["peak_rss_mb"]} MB, {gem}, CPU {a.threads} threads')
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()

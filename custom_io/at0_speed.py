"""python3 -m custom_io.at0_speed [--micro-short 100] [--micro-long 20] [--letters 280] [--letters-long 2000] [--batch 8] [--accum 32] [--threads 2]   (CPU; AT-0 (ix) of big-run PLAN.md's sixth Addendum: REPORTED, NOT GATED)
Speed and memory of B3AT (model b3at, arm AT) at 3M: the REAL 3M config (g8a/configs.b3at_cfg('3M', {"eg_embed": true}) under g8a/caps_b3g2.json, the config the queue file
8aAT-3M-s400-pc.txt trains: 4,023,302 trained parameters). The config is solved in a CHILD process (b3at_cfg builds ~200 models to find writer_mlp; that would inflate this process's
peak memory), which hands the config back as JSON. Then two timed phases on micro-batches of `--batch` rows (the PC job's micro-batch: batch 256 / accum 32 = 8): `--micro-short`
micro-batches of `--letters` letters (280) and `--micro-long` micro-batches of `--letters-long` letters (2,000: the job's longest rows, which the accum=32 guess is sized for). Each row is a
prose filler of that many letters followed by a question with 0, 1 or 2 tool calls (the rows of test_b3's mix); the loss = B3AT's teacher-forced loss over every row's turns (R drawn per
batch from KS_T = 4, 8, 16, 32, row cut TOTAL_CAP 96 // (calls + 1)). Per micro-batch the forward + backward and the optimizer step (grad clip 1, AdamW lr 1e-3) are timed separately; a
real job update is `--accum` micro-batches and ONE optimizer step (train.py), so the estimate is accum x mean(forward+backward) + mean(step). The frozen Gemma is the real
EmbeddingGemma if it loads offline (from $CUSTOM_IO_EG2 or the Hugging Face cache), else test_b3's stub (deterministic noise states of the same shape: the thinker, talker and tape cost
are real, the Gemma forward pass is not); each line says which. Memory is the peak resident set of this training process (resource.getrusage ru_maxrss, high-water mark after the phase;
the cfg solve is not in it; the Gemma weights are in it only if the real one loaded; the long phase's number includes the short phase's). The PC's GPU numbers are not these: this is
the CPU cost on the code's own path, the input to choosing the job's --accum (the queue file's guess is 32)."""
import argparse, json, os, resource, statistics, subprocess, sys, time
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




def solve_cfg(threads):
    """-> the b3at 3M cfg under caps_b3g2.json, solved in a child process (its ~200 model builds stay out of this process's peak memory)."""
    out = subprocess.run([sys.executable, '-m', 'custom_io.at0_speed', '--cfg-child', '--threads', str(threads)], capture_output=True, text=True,
                         cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if out.returncode != 0:
        raise RuntimeError('cfg child failed: ' + out.stderr[-2000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def child_cfg():
    from custom_io.g8a import caps as CP
    from custom_io.g8a import configs as C
    here = os.path.dirname(os.path.abspath(__file__))
    caps = CP.apply(json.load(open(os.path.join(here, 'g8a', 'caps_b3g2.json'))))
    extra = {'eg_embed': True}
    if CP.n_loops_needed(caps) > 8:
        extra['n_loops'] = CP.n_loops_needed(caps)      # what job.py adds to --b2-extra
    print(json.dumps(C.b3at_cfg('3M', extra)))


def timed_phase(m, opt, V, Dataset, collate, letters, n_micro, batch, accum, gem, threads, tag):
    rs = make_rows(max(batch, 12), letters)
    ds = Dataset(rs, V, strict=False)
    fb, st, rounds, by_R = [], [], [], {}
    torch.manual_seed(123)
    for u in range(n_micro):
        idx = [(u * batch + j) % len(rs) for j in range(batch)]
        b = collate([ds[i] for i in idx])
        t = time.perf_counter()
        loss, aux = m.loss(b)
        loss.backward()
        t1 = time.perf_counter()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        t2 = time.perf_counter()
        fb.append(t1 - t); st.append(t2 - t1)
        rounds.append(float(aux['rounds']))
        by_R.setdefault(int(aux['R']), []).append(t1 - t)
        assert torch.isfinite(loss.detach()), f'{tag} micro-batch {u}: non-finite loss'
        if (u + 1) % 10 == 0:
            print(f'  {tag} micro-batch {u + 1}: loss {float(loss.detach()):.3f}, forward+backward {t1 - t:.2f}s, mean so far {statistics.mean(fb):.2f}s', flush=True)
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024      # Linux: kilobytes; the process high-water mark so far
    res = dict(model='b3at', rung='3M', gemma=gem, letters=letters, batch=batch, micro_batches=n_micro, accum=accum, threads=threads,
               s_per_microbatch_mean=round(statistics.mean(fb), 3), s_per_microbatch_median=round(statistics.median(fb), 3), s_per_microbatch_max=round(max(fb), 3),
               s_optimizer_step_mean=round(statistics.mean(st), 3),
               est_s_per_job_update=round(accum * statistics.mean(fb) + statistics.mean(st), 2),
               s_by_R={k: round(statistics.mean(v), 3) for k, v in sorted(by_R.items())}, microbatches_by_R={k: len(v) for k, v in sorted(by_R.items())},
               mean_rounds_per_row=round(statistics.mean(rounds), 1), peak_rss_mb=round(peak_mb))
    print(json.dumps(res), flush=True)
    gnote = 'real Gemma weights included' if gem.startswith('real') else 'stub Gemma: the real Gemma weights are NOT included'
    print(f'AT-0 (ix) (reported, not gated), {letters} letters: {res["s_per_microbatch_mean"]} s per micro-batch of {batch} (median {res["s_per_microbatch_median"]}, slowest {res["s_per_microbatch_max"]}, '
          f'{n_micro} micro-batches) forward+backward, optimizer step {res["s_optimizer_step_mean"]} s; est. {res["est_s_per_job_update"]} s per job update '
          f'(= {accum} x micro-batch forward+backward + 1 optimizer step); peak memory {res["peak_rss_mb"]} MB = peak resident set of this training process '
          f'(model, optimizer, activations; {gnote}; the cfg solve ran in a child process), {gem}, CPU {threads} threads', flush=True)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--micro-short', type=int, default=100, help='micro-batches timed at --letters')
    ap.add_argument('--micro-long', type=int, default=20, help='micro-batches timed at --letters-long')
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--letters', type=int, default=280)
    ap.add_argument('--letters-long', type=int, default=2000)
    ap.add_argument('--accum', type=int, default=32, help='micro-batches per job update (the queue file --accum AT=32)')
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--stub', action='store_true', help='use the stub Gemma without trying the real one')
    ap.add_argument('--cfg-child', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    if a.cfg_child:
        return child_cfg()
    from custom_io.data import ByteVocab, Dataset, collate
    from custom_io.g8a import caps as CP
    from custom_io.g8a import configs as C
    from custom_io.models import build
    here = os.path.dirname(os.path.abspath(__file__))
    CP.apply(json.load(open(os.path.join(here, 'g8a', 'caps_b3g2.json'))))
    cfg = solve_cfg(a.threads)
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
          f'micro-batch {a.batch}; {a.micro_short} at {a.letters} letters, {a.micro_long} at {a.letters_long} letters; accum {a.accum}; rss before training {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MB', flush=True)
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=1e-3)
    m.train()
    out = [timed_phase(m, opt, V, Dataset, collate, L_, k, a.batch, a.accum, gem, a.threads, f'{L_} letters')
           for L_, k in ((a.letters, a.micro_short), (a.letters_long, a.micro_long)) if k > 0]
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()

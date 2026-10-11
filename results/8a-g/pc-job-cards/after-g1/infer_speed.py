"""fc100 part 3 (11 Oct 2026, spec addendum T): how fast the ~100M B3 group 2 shapes of fc100 part 2 answer. Run from src-b3g2 (custom_io of claude/learner-new-g2 at
1acfde9a73) by the post-G1 chain waiter v3d right after fc100 part 2 (queue 8aFC2), alone on the GPU. Read-only: it trains nothing, writes one JSON.

For each a64 shape line of the 8aFC2 queue (as of addendum W: five 512-wide shapes, 21, 26, 30, 34 and 37 layers), a freshly started model (seed 400, eval mode, bf16 autocast on cuda as in
training's eval, the frozen EmbeddingGemma 2 front included) answers dev in_dist questions with exactly K thinking rounds (generate lesion 'loops:K'; K = 12, the
model's n_loops, and 32, the cap) at batch sizes 1, 16 and 128. A timed answer = read the question (Gemma + letter reader) + K rounds + write the answer.
Weights are untrained, so the writer's per-round notes are timed two ways:
  quiet: in each round the writer stops after one step (what a trained model does on a round where it makes no calculator call), and the answer gets
         max_ans + 1 steps (a trained model's longest answer and its end mark).
  busy:  the writer runs on in each round and for the answer until it ends or hits its cap WCAP (untrained weights rarely end it): the slow side.
A real model sits between them, near quiet when it makes few calls; ms_per_writer_step converts calls into time. Each cell: one warmup batch on other rows,
then its batches in a fixed shuffled order until done or --cell-s seconds (at least one batch). --selftest DIR: a CPU check (see --help). Gemma's per-batch memo and tokenizer cache are cleared before
every timed batch, so each question is read from scratch.
-> --out JSON (rewritten after each cell): per shape {n_params, cells: {"K12-B1-quiet": {q_per_s, s_per_q, rows, batches, seconds, prompt_bytes_mean,
writer_steps_per_round, answer_writer_steps, peak_alloc_mib, peak_reserved_mib} or {error}}}. Never exits non-zero after it starts measuring."""
import argparse, gc, json, os, random, shlex, sys, time

import torch

STARTED = time.time()


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def shapes_of(queue):
    """-> [(name, cfg)] for the 8aFC2 train lines with accumulation 64 (one line per shape)."""
    out = []
    for line in open(queue, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#') or ':' in line.split()[0]:
            continue
        tok = shlex.split(line)
        if '--model' not in tok or tok[tok.index('--model') + 1] != 'b3g2' or not tok[0].endswith('-a64'):
            continue
        out.append((tok[0], json.loads(tok[tok.index('--cfg') + 1])))
    return out


def test_rows(n):
    """The rows of custom_io/tests/test_b3g2_run.py (three families, short prompts), for --selftest."""
    rs = []
    for i in range(n):
        a, b, c = 10 + 7 * i, 100 + 13 * i, 3 + i % 5
        if i % 3 == 0:
            rs.append(dict(id=f'a{i}', family='chain_ops', prompt=f'Tom has {a} apples and buys {b} more. How many apples now?', answer=str(a + b), accepted=[str(a + b)], level=1,
                           variant='v', stage=1, steps=[f'{a} + {b} = {a + b}']))
        elif i % 3 == 1:
            rs.append(dict(id=f'a{i}', family='copy_word', prompt=f'Echo: sune{i} Give only the answer.', answer=f'sune{i}', accepted=[f'sune{i}'], level=1, variant='v', stage=1, steps=[]))
        else:
            rs.append(dict(id=f'a{i}', family='chain_story2', prompt=f'Facts: Xavi had {a} cards. Then Xavi got {b} more. After that, Xavi lost {c}. How many now?', answer=str(a + b - c),
                           accepted=[str(a + b - c)], level=2, variant='v', stage=1, steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}']))
    return rs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--pool', help='the a64-L pool (its dev/in_dist.jsonl is read)')
    ap.add_argument('--caps', help="the pool's B3G2 caps.json (written by 8aFC2-caps-3M-s400)")
    ap.add_argument('--queue', required=True, help='8aFC2-pc.txt (the shapes)')
    ap.add_argument('--out')
    ap.add_argument('--device', default='cuda')
    ap.add_argument('--loops', default='12,32')
    ap.add_argument('--batches', default='1,16,128')
    ap.add_argument('--modes', default='quiet,busy')
    ap.add_argument('--cell-s', type=float, default=30.0, help='stop a cell after this many timed seconds (at least one batch)')
    ap.add_argument('--minutes', type=float, default=75.0, help='whole-run cap: later cells are marked skipped')
    ap.add_argument('--cfg', default=None, help='JSON merged into every shape cfg (CPU dry runs only)')
    ap.add_argument('--busy', default=None, help='shared GPU-BUSY file (one line while this runs)')
    ap.add_argument('--shapes', default=None, help='comma list of shapes to run, e.g. 21x512 (default: every a64 shape in the queue)')
    ap.add_argument('--src', default=None, help='the code folder holding custom_io (default: the current folder)')
    ap.add_argument('--selftest', default=None, help='a new empty folder: CPU run of one shape at a tiny width on the b3g2 test rows (no Gemma, no GPU)')
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.abspath(a.src or os.getcwd()))
    if a.selftest:
        os.makedirs(os.path.join(a.selftest, 'pool', 'dev'))
        with open(os.path.join(a.selftest, 'pool', 'dev', 'in_dist.jsonl'), 'w') as f:
            for r in test_rows(400):
                f.write(json.dumps(r) + '\n')
        json.dump(dict(max_prompt=400, max_ans=12, n_num=16, w_max=80, n_res=11, n_reg=13, plain_target=64, le=95), open(os.path.join(a.selftest, 'caps.json'), 'w'))
        a.pool, a.caps, a.out = os.path.join(a.selftest, 'pool'), os.path.join(a.selftest, 'caps.json'), os.path.join(a.selftest, 'out.json')
        a.device, a.loops, a.batches, a.cell_s, a.minutes, a.busy, a.shapes = 'cpu', '2,3', '1,16', 0.5, 5.0, None, '21x512'
        a.cfg = json.dumps(dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0, writer_inner=24, eg_embed=False))
        torch.set_num_threads(2)
    assert a.pool and a.caps and a.out, '--pool, --caps and --out are needed (or --selftest)'

    from custom_io import data as D
    from custom_io.data import ByteVocab, Dataset, collate, load_rows, to_device
    from custom_io.g8a import caps as CP
    from custom_io.models import build

    dev = torch.device(a.device)
    cuda = dev.type == 'cuda'
    D.set_max_ans(8)                                     # train.py's order: --max-ans 8, then the caps
    caps = CP.apply(json.load(open(a.caps)))
    shapes = shapes_of(a.queue)
    assert shapes, f'no a64 b3g2 shape lines in {a.queue}'
    rows = load_rows(os.path.join(a.pool, 'dev', 'in_dist.jsonl'))
    rnd = random.Random(400)
    rnd.shuffle(rows)
    timed, warm = rows[:256], (rows[256:384] if len(rows) >= 384 else rows[:128])
    order = sorted(range(len(timed)), key=lambda i: len(timed[i]['prompt']))
    Ks = [int(x) for x in a.loops.split(',')]
    Bs = [int(x) for x in a.batches.split(',')]
    modes = a.modes.split(',')

    def plan(B):
        """-> list of row-index batches: B=1: 16 rows evenly spread over the lengths; B=16: 64 rows in length-sorted batches; else all, length-sorted."""
        if B == 1:
            pick = [order[(i * len(order)) // 16] for i in range(min(16, len(order)))]
            bs = [[i] for i in pick]
        else:
            n = min(len(order), 64 if B <= 16 else len(order))
            pick = [order[(i * len(order)) // n] for i in range(n)]
            bs = [pick[s:s + B] for s in range(0, len(pick), B)]
        random.Random(B).shuffle(bs)                     # a cell cut by --cell-s still sees short and long questions
        return bs

    res = dict(started=time.strftime('%Y-%m-%d %H:%M:%S'), device=str(dev), gpu=torch.cuda.get_device_name(0) if cuda else None, torch=torch.__version__,
               caps=caps, rows_timed=len(timed), loops=Ks, batches=Bs, modes=modes, cell_s=a.cell_s, how=__doc__.split('\n\n')[0], shapes={})

    def save():
        json.dump(res, open(a.out + '.tmp', 'w'), indent=1)
        os.replace(a.out + '.tmp', a.out)

    busy = None
    if a.busy:
        from custom_io.local_runner import Busy
        busy = Busy(a.busy, 'custom-io')
        busy.add('8aFCI/infer_speed', os.getpid())
    amp = (lambda: torch.autocast('cuda', dtype=torch.bfloat16)) if cuda else (lambda: torch.autocast('cpu', enabled=False))
    sync = torch.cuda.synchronize if cuda else (lambda: None)

    def measure(tag, sh, cfg):
        torch.manual_seed(400)
        model = build('b3g2', ByteVocab(), **cfg).to(dev).eval()
        sh['n_params'] = sum(p.numel() for p in model.parameters())
        ds_t, ds_w = Dataset(timed, model.vocab, strict=False), Dataset(warm, model.vocab, strict=False)
        eg = model._eg[0] if getattr(model, 'eg_embed', False) else None
        st = dict(in_loop=False, quiet=False, loop_steps=0, ans_steps=0)
        loop0, greedy0, run0 = model.loop, model.writer.greedy, model.writer.run

        def loop(*x, **k):
            st['in_loop'] = True
            try:
                return loop0(*x, **k)
            finally:
                st['in_loop'] = False

        def greedy(*x, **k):
            if st['quiet']:
                k['max_len'] = 1 if st['in_loop'] else D.MAX_ANS + 1
            return greedy0(*x, **k)

        def run(*x, **k):
            st['loop_steps' if st['in_loop'] else 'ans_steps'] += 1
            return run0(*x, **k)

        model.loop, model.writer.greedy, model.writer.run = loop, greedy, run

        def answer(ds, ids, K):
            if eg is not None:
                eg._last = None
                eg._align.clear()
            b = to_device(collate([ds[i] for i in ids]), dev)
            with torch.no_grad(), amp():
                out = model.generate(b, lesion=f'loops:{K}')
            assert len(out) == len(ids)

        log(f'{tag}: built, {sh["n_params"]:,} params')
        for B in Bs:
            bs = plan(B)
            wb = list(range(min(B, len(warm))))
            for K in Ks:
                for mode in modes:
                    key = f'K{K}-B{B}-{mode}'
                    if (time.time() - STARTED) / 60 > a.minutes:
                        sh['cells'][key] = dict(error='skipped (whole-run time cap)')
                        continue
                    st['quiet'] = mode == 'quiet'
                    try:
                        answer(ds_w, wb, K)                      # warmup on other rows
                        sync()
                        if cuda:
                            torch.cuda.reset_peak_memory_stats()
                        st['loop_steps'] = st['ans_steps'] = 0
                        n = nb = 0
                        pb = 0
                        secs = 0.0
                        for ids in bs:
                            sync()
                            t0 = time.perf_counter()
                            answer(ds_t, ids, K)
                            sync()
                            secs += time.perf_counter() - t0
                            n += len(ids); nb += 1
                            pb += sum(len(timed[i]['prompt'].encode('utf-8')) for i in ids)
                            if secs > a.cell_s:
                                break
                        c = dict(q_per_s=round(n / secs, 3), s_per_q=round(secs / n, 4), rows=n, batches=nb, seconds=round(secs, 2),
                                 prompt_bytes_mean=round(pb / n, 1), writer_steps_per_round=round(st['loop_steps'] / max(nb * (K - 1), 1), 2),
                                 answer_writer_steps=round(st['ans_steps'] / nb, 2))
                        if cuda:
                            c.update(peak_alloc_mib=round(torch.cuda.max_memory_allocated() / 2 ** 20), peak_reserved_mib=round(torch.cuda.max_memory_reserved() / 2 ** 20))
                        sh['cells'][key] = c
                        log(f'{tag} {key}: {c["q_per_s"]} questions/s ({c["s_per_q"]} s each, {n} rows), writer steps/round {c["writer_steps_per_round"]}')
                    except Exception as e:                       # out of memory included: the cell's error is the result
                        sh['cells'][key] = dict(error=f'{type(e).__name__}: {str(e)[:300]}')
                        log(f'{tag} {key}: {sh["cells"][key]["error"]}')
                        if cuda:
                            torch.cuda.empty_cache()
                    save()
        # ms per extra writer step (one step of a whole batch), from quiet vs busy at the same K and B: rounds and answer
        for B in Bs:
            for K in Ks:
                q, b = sh['cells'].get(f'K{K}-B{B}-quiet', {}), sh['cells'].get(f'K{K}-B{B}-busy', {})
                if 's_per_q' in q and 's_per_q' in b and b['writer_steps_per_round'] > q['writer_steps_per_round']:
                    extra = (b['writer_steps_per_round'] - q['writer_steps_per_round']) * (K - 1) + b['answer_writer_steps'] - q['answer_writer_steps']
                    sh.setdefault('ms_per_writer_step', {})[f'K{K}-B{B}'] = round(1000 * (b['s_per_q'] - q['s_per_q']) * B / extra, 3)

    try:
        for name, cfg in shapes:
            if a.cfg:
                cfg = dict(cfg, **json.loads(a.cfg))
            if a.selftest:                                   # no Gemma here: drop the no-plug front's keys (it needs Gemma's 512 width)
                cfg = {k: v for k, v in cfg.items() if k not in ('eg_pre', 'eg_adapter')}
            tag = name.split('-')[1]                        # the shape as the queue names it, e.g. 21x512
            if a.shapes and tag not in a.shapes.split(','):
                continue
            sh = res['shapes'][tag] = dict(job=name, cfg=cfg, cells={})
            try:
                measure(tag, sh, cfg)
            except Exception as e:
                sh['error'] = f'{type(e).__name__}: {str(e)[:300]}'
                log(f'{tag}: {sh["error"]}')
            gc.collect()                                         # the model (and its Gemma copy) went out of scope with measure()
            if cuda:
                torch.cuda.empty_cache()
            save()
    finally:
        if busy:
            busy.remove('8aFCI/infer_speed')
    res['minutes'] = round((time.time() - STARTED) / 60, 1)
    save()
    log(f'INFER SPEED DONE in {res["minutes"]} min -> {a.out}')
    for tag, sh in res['shapes'].items():
        for key, c in sh.get('cells', {}).items():
            log(f'  {tag} {key}: ' + (f'{c["q_per_s"]} q/s, {c["s_per_q"]} s/q' if 'q_per_s' in c else c['error']))
    if a.selftest:
        sh = res['shapes'].get('21x512', {})
        want = [f'K{K}-B{B}-{m}' for B in Bs for K in Ks for m in modes]
        bad = [k for k in want if 'q_per_s' not in sh.get('cells', {}).get(k, {})]
        ok = not bad and 'error' not in sh and len(sh.get('ms_per_writer_step', {})) == len(Bs) * len(Ks)
        print('INFER SELFTEST OK' if ok else f'INFER SELFTEST FAILED: cells {bad}, error {sh.get("error")}, ms_per_writer_step {sh.get("ms_per_writer_step")}', flush=True)
        sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()

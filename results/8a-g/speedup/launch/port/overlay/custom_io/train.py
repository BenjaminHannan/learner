"""CLI trainer.  python3 -m custom_io.train --model plain_tf --cfg '{"d_model":256}' --steps 3000 --out runs/x --final-eval"""
import argparse, contextlib, hashlib, json, math, os, random, re, sys, time
import numpy as np
import torch
from custom_io import capcount, data as D
from custom_io.data import DEFAULT_DATA, ByteVocab, CharVocab, Dataset, load_rows, to_device, train_batches
from custom_io.evalx import can_donor, chain_panel, donor_all, eval_all, evaluate, short, subsample, _dev_rows, is_hit
from custom_io.models import NAMES, build

PLAIN_TF_S = 3244544                                                     # plain_tf S, the size every 3M design is matched to
SIZE_BAND = (round(PLAIN_TF_S * 0.97), round(PLAIN_TF_S * 1.03))        # the sealed +-3% band: 3,147,208 .. 3,341,880


def lr_at(step, steps, warmup, base, elapsed=0.0, cap=None):
    """Linear warmup, then cosine to 10% of base. Progress = max(step/steps, elapsed/cap) so a --minutes
    cap still anneals the lr to its floor by the time training stops."""
    if step < warmup:
        return base * (step + 1) / warmup
    q = max(step / steps, elapsed / cap if cap else 0.0)
    p = min(1.0, max(0.0, (q - warmup / steps) / max(1 - warmup / steps, 1e-8)))
    return base * (0.1 + 0.45 * (1 + math.cos(math.pi * p)))


def split_batch(batch, k):
    """k row-slices of a collated batch (every tensor is cut along dim 0, `rows` along with it); the padded width is kept, so micro-batches line up with the full batch."""
    n = len(batch['rows'])
    cuts = [round(i * n / k) for i in range(k + 1)]
    return [{key: (v[a:b] if torch.is_tensor(v) or isinstance(v, list) else v) for key, v in batch.items()} for a, b in zip(cuts, cuts[1:]) if b > a]


_TEE = [None]      # with --ckpt-every / --resume every event line is also appended to OUT/events.jsonl (stdout.txt is rewritten by a restarted job; this file keeps every segment)


def jprint(**kw):
    line = json.dumps(kw)
    print(line, flush=True)
    if _TEE[0] is not None:
        _TEE[0].write(line + '\n')
        _TEE[0].flush()


def lesion_names(model):
    """Every generate() lesion final_eval runs: the model's own (not loops) + loops:K for K in {0,1,2,2n} (or the model's LOOP_SWEEP)."""
    names = [l for l in model.LESIONS if l.split(':')[0] != 'loops']
    if getattr(model, 'n_loops', 1) > 1:    # a 1-loop model's sweep is only a format check (loops:1 = intact); skip it
        names += [f'loops:{k}' for k in (getattr(model, 'LOOP_SWEEP', None) or sorted({0, 1, 2, 2 * model.n_loops}))]
    return names


def chain5_eval(model, args, device, amp):
    """chain-5 panel (big build) for the intact model and every lesion -> {'intact': {..., 'hits': {id: 0/1}}, lesion: {...}}."""
    rows = {r['id']: r for r in _dev_rows(args.big_data, 'in_dist', None)}
    out = {}
    for lesion in [None] + lesion_names(model):
        with amp():
            r = chain_panel(model, args.big_data, lesion, args.eval_batch, device, return_preds=lesion is None)
        if lesion is None:
            r['hits'] = {i: int(is_hit(p, rows[i])) for i, p in r.pop('preds').items()}
        out[lesion or 'intact'] = r
        jprint(event='eval', lesion=lesion, chain5=round(r['exact'], 2), n=r['n'])
    return out


def run_extra(model, args, device, amp, result):
    """model.extra_evals(ctx) -> result['extra']; a failure is recorded in result['extra_error'], never raised."""
    try:
        ctx = dict(data=args.data, big=args.big_data, device=device, batch_size=args.eval_batch, amp=amp)
        result['extra'] = model.extra_evals(ctx)
        json.dumps(result['extra'])
        jprint(event='extra', **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in result['extra'].items()
                                 if isinstance(v, (int, float, str, bool))}, keys=sorted(result['extra']))
    except Exception:
        import traceback
        result.pop('extra', None)
        result['extra_error'] = traceback.format_exc()
        jprint(event='extra_error', error=result['extra_error'].strip().splitlines()[-1])


def final_eval(model, args, device, amp):
    """Full eval_all, then every lesion the model supports (+ loops:K sweep for models with n_loops, + the donor swap
    for models with state/talk, stored under lesions['donor'] as {split: donor_eval result})."""
    names = lesion_names(model)
    runs = {}
    for lesion in [None] + names:
        with amp():
            runs[lesion] = eval_all(model, args.data, args.eval_max, lesion, args.eval_batch, device, return_preds=lesion is None and args.save_preds)
        if lesion is None and args.save_preds:      # per-row intact dev predictions of all 6 splits -> PREDS.json beside RESULT.json
            preds = {s: r.pop('preds') for s, r in runs[None].items()}
            if args.out:
                os.makedirs(args.out, exist_ok=True)
                json.dump(preds, open(os.path.join(args.out, 'PREDS.json'), 'w'))
            jprint(event='preds', n={s: len(p) for s, p in preds.items()})
        jprint(event='eval', lesion=lesion, **short(runs[lesion]))
    if can_donor(model):
        with amp():
            runs['donor'] = donor_all(model, args.data, args.eval_max, args.eval_batch, device)
        jprint(event='eval', lesion='donor', **{s: {k: round(v[k], 2) for k in ('exact', 'donor_match')} for s, v in runs['donor'].items()})
    return runs.pop(None), runs


def english_eval(model, args, device, amp):
    """english.eval_english on the held-out in-dist slice (DATA/dev/in_dist.jsonl, every key kept) + the eval dir; one event line per set and lesion."""
    from custom_io import english
    held = load_rows(os.path.join(args.data, 'dev', 'in_dist.jsonl'), keep=None)
    r = english.eval_english(model, args.english_eval, held, device, args.eval_batch, amp)
    json.dumps(r)
    for k, v in (r.get('intact') or {}).items():
        if isinstance(v, dict) and 'exact' in v:
            jprint(event='eval', set=k, exact=round(v['exact'], 2), n=v.get('n'))
    for k1, v1 in (r.get('lesions') or {}).items():
        for k2, v2 in (v1 or {}).items():
            e = v2.get('exact', (v2.get('judged') or {}).get('exact')) if isinstance(v2, dict) else None
            jprint(event='eval', lesion=f'{k1}/{k2}', exact=None if e is None else round(e, 2))
    return r


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# Periodic checkpoint + resume (--ckpt-every N / --resume). With both off none of this runs and training is exactly what it was without it.
#
# OUT/ckpt/step-<k>.pt (+ step-<k>.json, the sidecar) holds everything that decides the next update: model, optimizer, the step (lr is a function of the step and of the
# elapsed time, both restored), every random stream training draws from (python `random`, numpy, torch CPU, torch CUDA on every device, and the model's own
# random.Random streams: b3 `_gap_rng`, tool `_drill_rng`), the data-order position, the loss window of the log line, and the counters RESULT.json reports.
# The data order needs no saved generator: data.train_batches draws one RandomState(seed).permutation per epoch and takes batch after batch from it, so the position
# after k updates is "k batches in" and `batches_from` replays the permutation draws (nothing is collated) to get there.
# A checkpoint is valid only with its sidecar, whose sha256 and size match the .pt (a write is: temp file in the same folder, fsync, os.replace; then the sidecar the same way).
# What is NOT restored exactly: per-distinct-row counters of caches that start empty after a resume (capcount hits and the models' trace_stats): a row that was already
# counted before the restart is counted once more if it shows up again. A zero count stays zero. No cache changes a value, only those counters.
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
CKPT_KEEP = 2
CKPT_NAME = re.compile(r'^step-(\d+)\.pt$')
# train.py arguments that decide what is trained; --accum (memory only: the update is the same rows, the loss a mean of micro-batches), paths, evals and logging are left out
CONFIG_KEYS = ('model', 'steps', 'batch', 'lr', 'warmup', 'grad_clip', 'seed', 'order', 'bf16', 'max_ans', 'minutes')


def batches_from(ds, batch_size, order='shuffled', seed=0, skip=0):
    """data.train_batches, started `skip` batches in. Same permutation draws and the same batches; the skipped ones are not collated."""
    assert order in ('shuffled', 'curriculum')
    rng, n = np.random.RandomState(seed), len(ds)
    per_epoch = len(range(0, n - batch_size + 1, batch_size))
    assert per_epoch > 0, f'{n} rows are fewer than one batch of {batch_size}'
    epochs, pos = divmod(skip, per_epoch)
    if order == 'shuffled':
        for _ in range(epochs):
            rng.permutation(n)
    first = True
    while True:
        idx = rng.permutation(n) if order == 'shuffled' else np.arange(n)
        for i in range(pos * batch_size if first else 0, n - batch_size + 1, batch_size):
            yield D.collate([ds[j] for j in idx[i:i + batch_size]])
        first = False


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def config_id(args, cfg, vocab=None):
    """-> (hash, the dict that was hashed): what the run trains, not where it runs. The caps file counts by its content."""
    d = {k: getattr(args, k) for k in CONFIG_KEYS}
    d['cfg'] = cfg
    d['caps'] = hashlib.sha256(open(args.caps, 'rb').read()).hexdigest() if args.caps else None
    if args.speed_arms:         # numerics-changing speed arms (--speed-arms); only when on, so a flag-off hash is the one train.py had without the flag
        d['speed_arms'] = args.speed_arms
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest(), d


def data_id(args, rows, vocab):
    """The data a run reads: MANIFEST.json's sha256 when the data dir has one (the 8a pool and the English adapter do), train.jsonl's size, the row count, the vocab."""
    mf = os.path.join(args.data, 'MANIFEST.json')
    tr = os.path.join(args.data, 'train.jsonl')
    return dict(manifest_sha256=hashlib.sha256(open(mf, 'rb').read()).hexdigest() if os.path.exists(mf) else None,
                train_bytes=os.path.getsize(tr) if os.path.exists(tr) else None, rows=len(rows), vocab=len(vocab),
                vocab_sha256=hashlib.sha256(('bytes' if vocab.is_bytes else vocab.chars).encode()).hexdigest())


def code_id():
    """sha1 (10 hex) over the .py / .json files of custom_io (not tests, results, queues): the same tree gives the same id on the PC and on a rented box."""
    root = os.path.dirname(os.path.abspath(__file__))
    h = hashlib.sha1()
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(x for x in dn if x not in ('results', 'tests', '__pycache__') and not x.startswith('queue'))
        for f in sorted(fn):
            if f.endswith(('.py', '.json')):
                p = os.path.join(dp, f)
                h.update(os.path.relpath(p, root).replace(os.sep, '/').encode() + b'\0' + open(p, 'rb').read() + b'\0')
    return h.hexdigest()[:10]


def fsync_dir(d):
    try:
        fd = os.open(d, os.O_RDONLY)
    except OSError:                     # Windows cannot open a folder
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write(path, write):
    """write(fileobj) into a temp file in the same folder, flush + fsync, then os.replace onto `path`: `path` is either the old file or the whole new one, never half."""
    d = os.path.dirname(os.path.abspath(path))
    tmp = os.path.join(d, f'.{os.path.basename(path)}.tmp-{os.getpid()}')
    try:
        with open(tmp, 'wb') as f:
            write(f)
            f.flush()
            os.fsync(f.fileno())
        for k in range(5):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:     # Windows: the target is briefly held open by another process (a scanner); a few tries
                if k == 4:
                    raise
                time.sleep(1)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    fsync_dir(d)


def ckpt_files(ckdir):
    """-> [(step, pt path, sidecar path)] newest first, for every step-<k>.pt present (valid or not)."""
    out = []
    if os.path.isdir(ckdir):
        for f in os.listdir(ckdir):
            m = CKPT_NAME.match(f)
            if m:
                out.append((int(m.group(1)), os.path.join(ckdir, f), os.path.join(ckdir, f[:-3] + '.json')))
    return sorted(out, reverse=True)


def prune_ckpts(ckdir, keep=CKPT_KEEP):
    """Called after a new checkpoint is completely written: keep the newest `keep` complete ones, delete the rest (and stale temp files)."""
    found = ckpt_files(ckdir)
    complete = [c for c in found if os.path.exists(c[2])]
    keep_steps = {c[0] for c in complete[:keep]}
    for step, pt, js in found:
        if step not in keep_steps:
            for p in (js, pt):          # sidecar first: a half-deleted checkpoint then has no sidecar and is invalid, never "valid but missing"
                if os.path.exists(p):
                    os.remove(p)
    for f in os.listdir(ckdir):
        if f.startswith('.') and '.tmp-' in f:
            try:
                os.remove(os.path.join(ckdir, f))
            except OSError:
                pass


def save_ckpt(ckdir, step, payload, side):
    """Write step-<step>.pt, then its sidecar (both atomic), then drop older ones. -> (bytes, seconds)."""
    t = time.time()
    os.makedirs(ckdir, exist_ok=True)
    pt, js = os.path.join(ckdir, f'step-{step}.pt'), os.path.join(ckdir, f'step-{step}.json')
    if os.path.exists(js):              # re-making a step after a resume: the old sidecar must not vouch for the new bytes
        os.remove(js)
    atomic_write(pt, lambda f: torch.save(payload, f))
    side = dict(side, step=step, file=os.path.basename(pt), bytes=os.path.getsize(pt), sha256=sha256_file(pt))
    atomic_write(js, lambda f: f.write(json.dumps(side, indent=1, sort_keys=True).encode()))
    prune_ckpts(ckdir)
    return side['bytes'], time.time() - t


def torch_load(path):
    try:
        return torch.load(path, map_location='cpu', weights_only=False)
    except TypeError:                   # torch before 1.13
        return torch.load(path, map_location='cpu')


def read_valid_ckpt(pt, js):
    """-> sidecar dict of a checkpoint whose sidecar parses and whose .pt has the recorded size and sha256; else raises ValueError(reason)."""
    try:
        side = json.load(open(js))
    except (OSError, ValueError) as e:
        raise ValueError(f'sidecar {os.path.basename(js)} unreadable: {e}')
    if not isinstance(side, dict) or side.get('file') != os.path.basename(pt):
        raise ValueError('sidecar does not describe this file')
    if os.path.getsize(pt) != side.get('bytes'):
        raise ValueError(f'size {os.path.getsize(pt)} != recorded {side.get("bytes")} (truncated?)')
    if sha256_file(pt) != side.get('sha256'):
        raise ValueError('sha256 differs from the sidecar (corrupt)')
    return side


def model_streams(model):
    """The model's own random streams and counters, by module path: random.Random / RandomState / torch.Generator attributes and the *_stats dicts."""
    rngs, stats = {}, {}
    for name, m in model.named_modules():
        for k, v in vars(m).items():
            if isinstance(v, random.Random):
                rngs[f'{name}.{k}'] = ('py', v.getstate())
            elif isinstance(v, np.random.RandomState):
                rngs[f'{name}.{k}'] = ('np', v.get_state())
            elif isinstance(v, torch.Generator):
                rngs[f'{name}.{k}'] = ('torch', v.get_state())
            elif k.endswith('_stats') and isinstance(v, dict):
                stats[f'{name}.{k}'] = dict(v)
            elif k in ('_tk_letters', '_tk_spots') and isinstance(v, (int, float)):
                stats[f'{name}.{k}'] = v
    return rngs, stats


def restore_model_streams(model, rngs, stats):
    mods = dict(model.named_modules())
    have, _ = model_streams(model)
    if set(have) != set(rngs):
        raise ValueError(f'the model has random streams {sorted(have)} but the checkpoint has {sorted(rngs)}')
    for key, (kind, st) in rngs.items():
        name, _, k = key.rpartition('.')
        obj = getattr(mods[name], k)
        {'py': random.Random.setstate, 'np': np.random.RandomState.set_state, 'torch': torch.Generator.set_state}[kind](obj, st)
    for key, v in stats.items():
        name, _, k = key.rpartition('.')
        if isinstance(v, dict):
            getattr(mods[name], k).clear()
            getattr(mods[name], k).update(v)
        else:
            setattr(mods[name], k, v)


def global_streams(device):
    cuda = [t.clone() for t in torch.cuda.get_rng_state_all()] if device.type == 'cuda' else None
    return dict(py=random.getstate(), np=np.random.get_state(), torch=torch.get_rng_state(), cuda=cuda)


def restore_global_streams(g, device):
    random.setstate(g['py'])
    np.random.set_state(g['np'])
    torch.set_rng_state(g['torch'].cpu())
    if g['cuda'] is not None and device.type == 'cuda':
        if len(g['cuda']) != torch.cuda.device_count():
            jprint(event='resume_warning', warning=f'checkpoint has CUDA RNG states for {len(g["cuda"])} devices, this machine has {torch.cuda.device_count()}: CUDA streams not restored')
        else:
            torch.cuda.set_rng_state_all([t.cpu() for t in g['cuda']])


def load_resume(ckdir, cfg_hash, dat_id, code):
    """Newest valid checkpoint of ckdir -> (payload, sidecar), or None when ckdir has none at all. A corrupt one is skipped (event ckpt_skipped) for the one before it.
    A valid one made under another config hash or another data manifest is refused (SystemExit, rc 1); so is a folder where every checkpoint is corrupt."""
    found = ckpt_files(ckdir)
    if not found:
        return None
    for step, pt, js in found:
        try:
            side = read_valid_ckpt(pt, js)
            if side.get('config_hash') != cfg_hash:
                sys.exit(f'--resume refused: {os.path.basename(pt)} was made under config hash {side.get("config_hash")}, this run is {cfg_hash} (model / cfg / steps / batch / lr / warmup / grad-clip / seed / order / bf16 / max-ans / minutes / caps / speed-arms changed)')
            if side.get('data_id') != dat_id:
                sys.exit(f'--resume refused: {os.path.basename(pt)} was made on other data (manifest / train.jsonl / vocab): saved {side.get("data_id")}, now {dat_id}')
            payload = torch_load(pt)
            if payload.get('step') != step or payload.get('version') != 1:
                raise ValueError('payload step / version differs from the file name')
        except Exception as e:           # SystemExit (a refusal) is not an Exception: it passes
            jprint(event='ckpt_skipped', file=os.path.basename(pt), reason=str(e))
            continue
        if side.get('code_id') != code:
            jprint(event='resume_warning', warning=f'code id {side.get("code_id")} at the save, {code} now: other code can change the run')
        return payload, side
    sys.exit(f'--resume refused: {ckdir} holds {len(found)} checkpoint(s) and none is valid (see the ckpt_skipped lines); move the folder aside to start from step 0')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True, choices=NAMES)
    ap.add_argument('--cfg', default='{}', help='JSON dict of model kwargs')
    ap.add_argument('--data', default=DEFAULT_DATA, help='dir with train.jsonl and dev/')
    ap.add_argument('--big-data', default=None, help='data root with a 200-per-cell dev/ (chain-5 panel + extra_evals)')
    ap.add_argument('--vocab', help='vocab json (default: DATA/charvocab.json, built from DATA/train.jsonl if absent)')
    ap.add_argument('--steps', type=int, default=3000)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--accum', type=int, default=1, help='gradient accumulation: split every batch into this many micro-batches (same 256 rows per update; the loss is the mean of the micro-batch losses, so a token-mean loss differs slightly from the full-batch one)')
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--warmup', type=int, default=300)
    ap.add_argument('--grad-clip', type=float, default=1.0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--order', choices=['shuffled', 'curriculum'], default='shuffled')
    ap.add_argument('--device', default='auto')
    ap.add_argument('--bf16', action='store_true', help='autocast bf16 (cuda only)')
    ap.add_argument('--log-every', type=int, default=100)
    ap.add_argument('--eval-every', type=int, default=0, help='quick eval on 200 rows of dev/in_dist every N steps')
    ap.add_argument('--final-eval', action='store_true')
    ap.add_argument('--english-eval', help='dir of the four English eval sets: with --final-eval run english.eval_english (needs DATA/dev/in_dist.jsonl, vocab of 108) instead of eval_all, chain-5 and extra_evals')
    ap.add_argument('--max-ans', type=int, default=8, help='answer chars before EOS (data.set_max_ans); a model with a smaller max_ans is refused')
    ap.add_argument('--caps', help='caps.json from custom_io.g8a.caps: sizes the prompt / answer / workspace / target caps from the data (8A addendum E); applied before any data or model is built')
    ap.add_argument('--eval-max', type=int, help='cap rows per dev split in the final eval')
    ap.add_argument('--save-preds', action='store_true', help='with --final-eval: write the intact per-row dev predictions of all 6 splits to OUT/PREDS.json')
    ap.add_argument('--eval-batch', type=int, default=128)
    ap.add_argument('--minutes', type=float, help='wall-clock cap on training; still evals afterwards')
    ap.add_argument('--out', help='dir for RESULT.json and checkpoint.pt')
    ap.add_argument('--ckpt-every', type=int, default=0, help='every N updates (and after the last one) write OUT/ckpt/step-<k>.pt (+ .json): model, optimizer, every RNG, data position, counters; the newest 2 are kept. 0 = off')
    ap.add_argument('--resume', action='store_true', help='continue from the newest valid checkpoint in OUT/ckpt (refuses if the config hash or data manifest differs); with none there, start at step 0')
    ap.add_argument('--speed-arms', default='', choices=['', 'defer'], help="NUMERICS-CHANGING speed arms, fresh runs from update 0 only (the config hash includes it, so --resume refuses to cross a change of it): 'defer' = the deferred batched writer (b3g2 only; models/b3g2_defer.py). '' = off (bitwise the original)")
    args = ap.parse_args(argv)
    if (args.ckpt_every or args.resume) and not args.out:
        ap.error('--ckpt-every and --resume need --out')
    if args.ckpt_every < 0:
        ap.error('--ckpt-every must be >= 0')
    ck_on = bool(args.ckpt_every or args.resume)
    if ck_on:
        os.makedirs(args.out, exist_ok=True)
        _TEE[0] = open(os.path.join(args.out, 'events.jsonl'), 'a', encoding='utf-8')
        jprint(event='segment', ckpt_every=args.ckpt_every, resume=args.resume, unix=round(time.time()))
    cfg = json.loads(args.cfg)
    device = torch.device('cuda' if args.device == 'auto' and torch.cuda.is_available() else 'cpu' if args.device == 'auto' else args.device)
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if args.bf16 and device.type == 'cuda' else contextlib.nullcontext
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
    t_start = time.time()
    D.set_max_ans(args.max_ans)         # before any data or model is built
    if args.caps:
        from custom_io.g8a import caps as _caps
        _c = _caps.apply(json.load(open(args.caps)))
        args.max_ans = _c['max_ans']
        jprint(event='caps', **_c)

    rows = load_rows(os.path.join(args.data, 'train.jsonl'))
    if cfg.get('bytes'):                # V1: raw UTF-8 bytes (269 ids), no vocab file; the model's cfg {"bytes": true} says so
        assert not args.vocab, '--vocab and cfg bytes are exclusive'
        vocab = ByteVocab()
    else:
        vocab = CharVocab.get(args.data, args.vocab, rows)
    batches = train_batches(Dataset(rows, vocab), args.batch, args.order, args.seed)
    dev = subsample(load_rows(os.path.join(args.data, 'dev', 'in_dist.jsonl')), 200)
    model = build(args.model, vocab, **cfg).to(device)
    if args.speed_arms:
        if not hasattr(model, 'speed_defer'):
            sys.exit(f"--speed-arms {args.speed_arms} needs a model with the deferred writer (b3g2); model {args.model} has none")
        from custom_io.models import b3g2_defer
        if not b3g2_defer.applies_statically(model):       # B3G2.loss would count a fallback on every call: refuse at startup instead of silently running the original
            sys.exit(f"--speed-arms {args.speed_arms} can never take the deferred path with this model: " + (f"talk_rounds is {model.talk_rounds!r} (the deferred writer needs 'last')" if model.talk_rounds != 'last' else "the writer has a copy path (the deferred writer needs copy False)"))
        model.speed_defer = True
    if args.caps and hasattr(model, '_targets'):    # plain_tf_steps family: its answer slots are the steps+answer target (caps plain_target), not max_ans
        model.max_ans = args.max_ans
    if getattr(model, 'max_ans', args.max_ans) < args.max_ans:
        sys.exit(f'--max-ans {args.max_ans} but the model has max_ans {model.max_ans}: its answer slots cannot hold the targets')
    if args.english_eval and args.final_eval:
        assert len(vocab) == 108, f'english eval needs the 108-id vocab, got {len(vocab)}'
    # no weight decay on biases, norms or embedding tables (so ids never seen in training keep their init scale)
    emb = {id(m.weight) for m in model.modules() if isinstance(m, torch.nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': no_decay, 'weight_decay': 0.0}],
                            lr=args.lr, betas=(0.9, 0.95), fused=device.type == 'cuda')
    jprint(event='start', model=args.model, cfg=cfg, n_params=model.n_params(), device=str(device), vocab=len(vocab), rows=len(rows), **({'speed_arms': args.speed_arms} if args.speed_arms else {}))
    n, (lo, hi) = model.n_params(), SIZE_BAND
    jprint(event='cap_hits', step=0, **capcount.snapshot())
    jprint(event='size', n_params=n, band=[lo, hi], inside=lo <= n <= hi, headroom_to_top=hi - n, vs_plain_tf_pct=round(100 * (n / PLAIN_TF_S - 1), 2))

    cap = args.minutes * 60 if args.minutes else None
    t0, eval_s, step, run_loss, run_n, last_loss, status = time.time(), 0.0, 0, 0.0, 0, None, 'ok'
    resumed_from, ck_stats = [], dict(writes=0, write_s=0.0, last_bytes=0)
    if ck_on:
        ckdir = os.path.join(args.out, 'ckpt')
        cfg_hash, cfg_hashed = config_id(args, cfg)
        dat_id, code = data_id(args, rows, vocab), code_id()
    if args.resume:
        got = load_resume(ckdir, cfg_hash, dat_id, code)
        if got is not None:
            ck, side = got
            model.load_state_dict(ck['model'])
            opt.load_state_dict(ck['opt'])
            restore_global_streams(ck['rng'], device)
            restore_model_streams(model, *ck['model_streams'])
            if args.speed_arms and side.get('defer_counts') is not None:
                model.defer_counts.update(side['defer_counts'])      # flag-ON sidecar only: the defer counts stay exact across --resume (the redone updates are counted again from the saved value)
            capcount.HITS.clear(); capcount.HITS.update(ck['cap_hits'])
            lp = ck['loop']
            step, eval_s, run_n, last_loss = ck['step'], lp['eval_s'], lp['run_n'], lp['last_loss']
            run_loss = lp['run_loss'].to(device) if torch.is_tensor(lp['run_loss']) else lp['run_loss']
            t0 = time.time() - lp['elapsed']            # elapsed (lr cap, train lines) and train_s go on from where the last segment stopped; the time the box was down is not counted
            resumed_from = list(ck['resumed_from']) + [step]
            if ck['data']['n_rows'] != len(rows):
                sys.exit(f'--resume refused: checkpoint was made on {ck["data"]["n_rows"]} rows, now {len(rows)}')
            batches = batches_from(Dataset(rows, vocab), args.batch, args.order, args.seed, skip=ck['data']['batches'])
            if side.get('accum') != args.accum:
                jprint(event='resume_warning', warning=f'--accum was {side.get("accum")} at the save, now {args.accum} (same rows per update; the loss is a mean of micro-batches)')
            jprint(event='resumed', step=step, **{'from': side['file']}, msg=f'RESUMED step={step} from={side["file"]}', config_hash=cfg_hash[:12], earlier_resumes=resumed_from[:-1])
    model.train()
    while step < args.steps:
        elapsed = time.time() - t0
        if cap and elapsed >= cap:
            status = 'time_cap'
            break
        lr = lr_at(step, args.steps, args.warmup, args.lr, elapsed, cap)
        for g in opt.param_groups:
            g['lr'] = lr
        batch = to_device(next(batches), device)
        if args.accum > 1:
            parts = split_batch(batch, args.accum)
            loss, aux = 0.0, {}
            for mb in parts:
                with amp():
                    out = model.loss(mb)
                l_i, a_i = out if isinstance(out, tuple) else (out, {})
                (l_i / len(parts)).backward()
                loss = loss + l_i.detach() / len(parts)
                for k_, v_ in a_i.items():
                    aux[k_] = aux.get(k_, 0.0) + v_.detach() / len(parts) if torch.is_tensor(v_) else aux.get(k_, 0.0) + v_ / len(parts)
        else:
            with amp():
                out = model.loss(batch)
            loss, aux = out if isinstance(out, tuple) else (out, {})
            loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step(); opt.zero_grad(set_to_none=True)
        step += 1
        run_loss += loss.detach(); run_n += 1
        if step % args.log_every == 0 or step == args.steps:
            last_loss = float(run_loss) / run_n
            jprint(event='train', step=step, loss=round(last_loss, 5), lr=round(lr, 7), elapsed=round(time.time() - t0, 1), cap_hits=capcount.snapshot()['total'],
                   **{k: round(float(v), 5) for k, v in aux.items()})
            run_loss, run_n = 0.0, 0
            if not math.isfinite(last_loss):
                status = 'nonfinite_loss'
                break
        if args.eval_every and step % args.eval_every == 0:
            te = time.time()
            with amp():
                r = evaluate(model, dev, args.eval_batch, device)
            eval_s += time.time() - te
            jprint(event='quick_eval', step=step, dev_in_dist_200=round(r['exact'], 2), loss=last_loss)
        if args.ckpt_every and (step % args.ckpt_every == 0 or step == args.steps):
            ck_t = time.time()
            try:
                ms_rngs, ms_stats = model_streams(model)
                nbytes, secs = save_ckpt(ckdir, step, dict(
                    version=1, step=step, model=model.state_dict(), opt=opt.state_dict(), rng=global_streams(device), model_streams=(ms_rngs, ms_stats),
                    cap_hits=dict(capcount.HITS), resumed_from=resumed_from,
                    loop=dict(elapsed=ck_t - t0, eval_s=eval_s, run_loss=run_loss.cpu() if torch.is_tensor(run_loss) else run_loss, run_n=run_n, last_loss=last_loss),
                    data=dict(batches=step, n_rows=len(rows), order=args.order, seed=args.seed, batch=args.batch, per_epoch=len(rows) // args.batch)),
                    dict(version=1, config_hash=cfg_hash, config=cfg_hashed, data_id=dat_id, code_id=code, train_py_sha256=sha256_file(os.path.abspath(__file__)),
                         torch=torch.__version__, device=device.type, accum=args.accum, resumed_from=resumed_from, saved_unix=round(time.time()),
                         **({'defer_counts': dict(model.defer_counts)} if args.speed_arms else {})))      # flag-off sidecar: exactly the g2fa4 one
                ck_stats['writes'] += 1; ck_stats['write_s'] += secs; ck_stats['last_bytes'] = nbytes
                jprint(event='ckpt', step=step, file=f'step-{step}.pt', mib=round(nbytes / 2 ** 20, 1), write_s=round(secs, 2))
            except Exception as e:      # a full disk or a locked file must not kill a 100-hour run: say so loudly, keep training, try again at the next interval
                ck_stats['failed'] = ck_stats.get('failed', 0) + 1
                jprint(event='ckpt_failed', step=step, error=repr(e)[:300])
            t0 += time.time() - ck_t        # writing a checkpoint is not training time (train_s, steps_per_s, the lr cap and the log's elapsed leave it out)
    if device.type == 'cuda':
        torch.cuda.synchronize()
    train_s = time.time() - t0 - eval_s
    result = dict(config=dict({k: v for k, v in vars(args).items() if (ck_on or k not in ('ckpt_every', 'resume')) and (args.speed_arms or k != 'speed_arms')}, cfg=cfg), n_params=model.n_params(), steps=step, status=status, final_train_loss=last_loss,
                  train_s=train_s, steps_per_s=step / max(train_s, 1e-9), final_eval=None, lesions={}, cap_hits=capcount.snapshot())
    jprint(event='cap_hits', step=step, **result['cap_hits'])       # scorecard row 6: every count must be 0 (see custom_io/capcount.py)
    if hasattr(model, '_tk_spots'):         # tok_think: valid letters vs token spots the thinker saw in training (ratio = letters per spot)
        result['tok_think'] = dict(letters=model._tk_letters, spots=model._tk_spots, ratio=round(model._tk_letters / max(model._tk_spots, 1), 4))
    if args.speed_arms:
        result['defer_stats'] = b3g2_defer.stats(model)       # defer.py's Defer.stats(): counts and per-micro-batch means; kept across --resume through the flag-on sidecar
    if ck_on:
        result['resumed_from'] = resumed_from
        result['ckpt'] = dict(every=args.ckpt_every, config_hash=cfg_hash, code_id=code, **ck_stats)
    mf = os.path.join(args.data, 'MANIFEST.json')       # the English adapter's manifest: its sha256 travels with the result (analyze_b1 checks it)
    if os.path.exists(mf):
        import hashlib
        result['data_manifest_sha256'] = hashlib.sha256(open(mf, 'rb').read()).hexdigest()
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        torch.save(dict(model=model.state_dict(), name=args.model, cfg=cfg, chars=vocab.chars, vocab='bytes' if vocab.is_bytes else 'chars', step=step), os.path.join(args.out, 'checkpoint.pt'))
    def write():
        result['wall_s'] = time.time() - t_start
        if device.type == 'cuda':       # peaks so far (training, then evals): later queues size --par and # MEM from these
            result['peak_mem_mib'], result['peak_reserved_mib'] = (round(f(device) / 2 ** 20, 1) for f in (torch.cuda.max_memory_allocated, torch.cuda.max_memory_reserved))
        if args.out:
            json.dump(result, open(os.path.join(args.out, 'RESULT.json'), 'w'), indent=1)
    write()                                           # trained model + stats survive even if the eval below dies
    if args.final_eval and args.english_eval:
        result['english'] = english_eval(model, args, device, amp)
        write()
    elif args.final_eval:
        result['final_eval'], result['lesions'] = final_eval(model, args, device, amp)
        write()
        if args.big_data:
            result['chain5'] = chain5_eval(model, args, device, amp)
            write()
        if hasattr(model, 'extra_evals'):
            run_extra(model, args, device, amp, result)
    result['cap_hits'] = capcount.snapshot()      # again after the final evaluations
    jprint(event='cap_hits', step=step, final=True, **result['cap_hits'])
    write()
    jprint(event='done', steps=step, status=status, steps_per_s=round(result['steps_per_s'], 3), wall_s=round(result['wall_s'], 1),
           **{k: result[k] for k in ('peak_mem_mib', 'peak_reserved_mib') if k in result},
           **(short(result['final_eval']) if result['final_eval'] else {}))
    return result


if __name__ == '__main__':
    main()

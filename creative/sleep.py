"""Sleep plumbing B2 lacks (roadmap section 6): resume from a checkpoint, train on records whose targets are forced slot ids, mix in
skills replay, with the fixed recipe: fresh AdamW; a fixed number of updates with each puzzle record seen at most `max_visits` times;
every batch half puzzle rows, half replay rows. lr and updates are chosen on DEV with the PC arm only, then frozen in SleepCfg.

Optimizer groups, betas and lr schedule are copied from custom_io.train (weight decay 0.1 on matrices, none on biases / norms / embeddings).
The target cache (custom_io.models.progparse._CACHE) is keyed by row id: puzzle record ids are unique ('W:mk:practice:0001:0'), and replay
rows keep their own ids."""
import json, os, random
from dataclasses import asdict, dataclass
import numpy as np
import torch
from custom_io.data import CharVocab, Dataset, collate, load_rows, to_device
from custom_io.models import build
from custom_io.train import lr_at


@dataclass
class SleepCfg:
    updates: int = 400
    batch: int = 64                 # half puzzle records, half replay rows
    lr: float = 3e-4
    warmup: int = 20
    grad_clip: float = 1.0
    max_visits: int = 4
    seed: int = 0
    weight_decay: float = 0.1


def load_parent(path, device='cpu'):
    """Rebuild a train.py checkpoint (model, name, cfg, chars, step). Returns (model, vocab, meta); the model is left in train mode."""
    ck = torch.load(path, map_location=device)
    vocab = CharVocab(ck['chars'])
    model = build(ck['name'], vocab, **ck['cfg'])
    model.load_state_dict(ck['model'])
    return model.to(device), vocab, dict(name=ck['name'], cfg=ck['cfg'], step=ck.get('step'))


def save_parent(model, name, cfg, vocab, path, step=0, **meta):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    torch.save(dict(model=model.state_dict(), name=name, cfg=cfg, chars=vocab.chars, step=step, **meta), path)


def load_replay(train_jsonl, n=None, seed=0):
    """Skills replay rows (the 200k skills data). n = how many to keep (random, seeded)."""
    rows = load_rows(train_jsonl)
    if n and n < len(rows):
        rows = random.Random(seed).sample(rows, n)
    return rows


def _order(n, draws, rng):
    """`draws` indices into range(n), balanced (every index drawn floor or ceil of draws / n times), epoch-wise shuffles."""
    out = []
    while len(out) < draws:
        p = list(range(n))
        rng.shuffle(p)
        out += p
    return out[:draws]


def max_updates(n_records, batch, replay, max_visits=4):
    """Most updates that keep every record at <= max_visits visits."""
    return max_visits * n_records // (batch // 2 if replay else batch)


def check_visits(n_records, cfg, replay=True):
    """Raises if the fixed update count would show a puzzle record more than max_visits times (half a batch per update with replay, all of it without)."""
    per = cfg.batch // 2 if replay else cfg.batch
    draws = cfg.updates * per
    if n_records and draws > cfg.max_visits * n_records:
        raise ValueError(f'{cfg.updates} updates draw {draws} puzzle rows from {n_records} records '
                         f'(> {cfg.max_visits} visits each); at most {cfg.max_visits * n_records // per} updates fit')


def sleep(model, records, replay_rows, vocab, cfg, device='cpu', amp=None, log=None):
    """Fresh AdamW, cfg.updates updates. records = puzzle rows (targets registered); replay_rows = skills rows (may be empty: then the whole
    batch is records). No records = no sleep (arm N): returns immediately. -> dict(loss, visits, updates)."""
    import contextlib
    amp = amp or contextlib.nullcontext
    if not records:
        return dict(loss=[], visits={}, updates=0)
    if len({r['id'] for r in records}) != len(records):
        raise ValueError('puzzle record ids must be unique (the target cache is keyed by id)')
    check_visits(len(records), cfg, bool(replay_rows))
    half = cfg.batch // 2 if replay_rows else cfg.batch
    draws = cfg.updates * half
    rng = random.Random(cfg.seed)
    torch.manual_seed(cfg.seed)
    rec_order = _order(len(records), draws, rng)
    rep_order = _order(len(replay_rows), cfg.updates * (cfg.batch - half), rng) if replay_rows else []
    emb = {id(m.weight) for m in model.modules() if isinstance(m, torch.nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': cfg.weight_decay}, {'params': no_decay, 'weight_decay': 0.0}],
                            lr=cfg.lr, betas=(0.9, 0.95), fused=torch.device(device).type == 'cuda')
    visits, losses = {}, []
    model.train()
    for step in range(cfg.updates):
        rows = [records[i] for i in rec_order[step * half:(step + 1) * half]]
        rows += [replay_rows[i] for i in rep_order[step * (cfg.batch - half):(step + 1) * (cfg.batch - half)]]
        for r in rows[:half]:
            visits[r['id']] = visits.get(r['id'], 0) + 1
        ds = Dataset(rows, vocab, strict=False)
        batch = to_device(collate([ds[i] for i in range(len(rows))]), device)
        for g in opt.param_groups:
            g['lr'] = lr_at(step, cfg.updates, cfg.warmup, cfg.lr)
        with amp():
            out = model.loss(batch)
        loss, aux = out if isinstance(out, tuple) else (out, {})
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(float(loss.detach()))
        if log and (step + 1) % 50 == 0:
            log(dict(event='sleep', step=step + 1, loss=round(float(np.mean(losses[-50:])), 4)))
    assert max(visits.values()) <= cfg.max_visits, 'a record was seen too often'
    return dict(loss=losses, visits=visits, updates=cfg.updates, cfg=asdict(cfg))

"""Answer-aware selector over frozen team members (GPT's proposal, 2026-10-05; marks in SELECTOR-PASS-MARKS.md).

  python -m custom_io.selector fresh   --curriculum DIR --data DATA --out WORK          # 16k + 4k fresh practice rows
  python -m custom_io.selector answers --data DATA --work WORK --tag s100 --members B2=ck1 tfsteps=ck2 tf=ck3
  python -m custom_io.selector train   --data DATA --work WORK --tag s100 --arm aware|blind --seed 100

Members are frozen solo checkpoints (same seed per team). Each member's greedy answer is cached once for the fresh rows and
every dev split. A selector (the team coach's 0.44M char encoder) reads three member-tagged, fixed-width answer fields
(8 chars each) followed by the question, and outputs one independent right/wrong logit per member (BCE on the members'
actual exact-match results; all-right and all-wrong rows kept). The team answer is the member with the highest logit
(ties: B2, then tfsteps, then tf). arm 'blind' is identical except every answer field is a fixed mask symbol, so the only
difference between the arms is whether the selector can see the proposed answers.
"""
import argparse, json, os, random, sys, time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import DEV_SPLITS, MAX_ANS, MAX_PROMPT, PAD, Q0, CharVocab, load_rows
from custom_io.evalx import is_hit
from custom_io.train import jprint, lr_at

ORDER = ['B2', 'tfsteps', 'tf']          # also the tie-break order
FIELD = MAX_ANS                          # chars per answer field
MASK = Q0 + 7                            # <q7>: the blind arm's fixed symbol
SPLITS = [s for s in DEV_SPLITS if s != 'family']


def fresh(a):
    """16k train + 4k val rows from a new seed of the same practised families (held-out pieces are excluded by the
    curriculum's fixed split hash); drop any prompt seen in the seed-1 train file or any dev split."""
    sys.path.insert(0, a.curriculum)
    from skills_curriculum.build import iter_train
    from custom_io.data import KEEP
    seen = {r['prompt'] for r in load_rows(os.path.join(a.data, 'train.jsonl'), keep=('prompt',))}
    for s in DEV_SPLITS:
        seen |= {r['prompt'] for r in load_rows(os.path.join(a.data, 'dev', f'{s}.jsonl'), keep=('prompt',))}
    vocab = CharVocab.get(a.data)
    out, dropped = [], {'seen': 0, 'long': 0}
    for r in iter_train(a.seed):
        if r['prompt'] in seen:
            dropped['seen'] += 1
            continue
        if len(vocab.encode(r['prompt'])) > MAX_PROMPT or len(r['answer']) > MAX_ANS:
            dropped['long'] += 1
            continue
        r = {k: r[k] for k in KEEP if k in r}
        r['id'] = f"fresh-{a.seed}-{len(out)}"
        out.append(r)
        if len(out) == a.n_train + a.n_val:
            break
    os.makedirs(a.out, exist_ok=True)
    for name, part in (('fresh_train', out[:a.n_train]), ('fresh_val', out[a.n_train:])):
        with open(os.path.join(a.out, f'{name}.jsonl'), 'w') as f:
            for r in part:
                f.write(json.dumps(r) + '\n')
    jprint(event='fresh', train=a.n_train, val=a.n_val, seed=a.seed, dropped=dropped)


def all_rows(a):
    rows = {'fresh_train': load_rows(os.path.join(a.work, 'fresh_train.jsonl')),
            'fresh_val': load_rows(os.path.join(a.work, 'fresh_val.jsonl'))}
    for s in SPLITS:
        rows[s] = load_rows(os.path.join(a.data, 'dev', f'{s}.jsonl'))
    return rows


def answers(a):
    from custom_io.models import load_model
    from custom_io.models.plain_tf import PlainTF
    from custom_io.evalx import evaluate
    from custom_io import fastgen
    torch.set_num_threads(a.threads)
    rows = all_rows(a)
    for spec in a.members:
        name, ck = spec.split('=', 1)
        dst = os.path.join(a.work, f'answers_{a.tag}_{name}.json')
        if os.path.exists(dst):
            continue
        m, t, res = load_model(ck, a.device), time.time(), {}
        fast = isinstance(m, PlainTF) and m.n_loops == 1 and not m.has_place
        for split, rs in rows.items():
            res[split] = fastgen.generate(m, rs, a.device) if fast else evaluate(m, rs, 256, a.device, return_preds=True)['preds']
        json.dump(dict(checkpoint=ck, answers=res), open(dst, 'w'))
        jprint(event='answers', member=name, tag=a.tag, s=round(time.time() - t, 1),
               **{s: round(100 * np.mean([is_hit(res[s][r['id']], r) for r in rs]), 2) for s, rs in rows.items()})


class Selector(nn.Module):
    """[tag_0 field_0 tag_1 field_1 tag_2 field_2] + question -> one logit per member. Same encoder as team.Coach."""

    def __init__(self, n_vocab, n_members=3, d=128, layers=2, heads=4):
        super().__init__()
        self.tok, self.pos = nn.Embedding(n_vocab, d), nn.Embedding(n_members * (FIELD + 1) + MAX_PROMPT, d)
        layer = nn.TransformerEncoderLayer(d, heads, 4 * d, dropout=0.0, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.ln, self.head = nn.LayerNorm(d), nn.Linear(d, n_members)

    def forward(self, ids, mask):
        x = self.enc(self.tok(ids) + self.pos(torch.arange(ids.shape[1], device=ids.device)), src_key_padding_mask=~mask)
        x = (x * mask[..., None]).sum(1) / mask.sum(1, keepdim=True).clamp(min=1)
        return self.head(self.ln(x)).float()


def encode(rows, ans, vocab, blind):
    """-> ids [N, T], mask [N, T] (answer fields are always real positions; only question padding is masked), hits [N, M]."""
    head = len(ORDER) * (FIELD + 1)
    T = head + max(len(r['prompt']) for r in rows)
    ids, mask = np.zeros((len(rows), T), np.int64), np.zeros((len(rows), T), bool)
    hits = np.zeros((len(rows), len(ORDER)), np.float32)
    for i, r in enumerate(rows):
        for k, name in enumerate(ORDER):
            a = ans[name][r['id']]
            hits[i, k] = is_hit(a, r)
            f = [MASK] * FIELD if blind else (vocab.encode(a)[:FIELD] + [PAD] * FIELD)[:FIELD]
            ids[i, k * (FIELD + 1)] = Q0 + k
            ids[i, k * (FIELD + 1) + 1:(k + 1) * (FIELD + 1)] = f
        p = vocab.encode(r['prompt'])
        ids[i, head:head + len(p)] = p
        mask[i, :head + len(p)] = True
    return torch.from_numpy(ids), torch.from_numpy(mask), torch.from_numpy(hits)


@torch.no_grad()
def score(sel, enc, rows, ans, bs=512):
    """-> dict with team exact %, B2 exact %, rescues / harmful overrides vs B2 (% of rows), union %, picks per member."""
    ids, mask, hits = enc
    picks = torch.cat([sel(ids[s:s + bs], mask[s:s + bs]).argmax(-1) for s in range(0, len(rows), bs)])
    team = hits[torch.arange(len(rows)), picks]
    b2 = hits[:, 0]
    pct = lambda x: round(100 * float(x.float().mean()), 2)
    return dict(team=pct(team), B2=pct(b2), **{f'm_{n}': pct(hits[:, k]) for k, n in enumerate(ORDER)},
                union=pct(hits.max(1).values), rescues=pct((b2 == 0) & (team == 1)), harmful=pct((b2 == 1) & (team == 0)),
                picks={n: int((picks == k).sum()) for k, n in enumerate(ORDER)}), picks


def train(a):
    torch.set_num_threads(a.threads)
    random.seed(a.seed); np.random.seed(a.seed)
    rows = all_rows(a)
    vocab = CharVocab.get(a.data)
    ans = {}
    for name in ORDER:
        res = json.load(open(os.path.join(a.work, f'answers_{a.tag}_{name}.json')))['answers']
        for split in rows:
            ans.setdefault(split, {})[name] = res[split]
    blind = a.arm == 'blind'
    enc = {s: encode(rows[s], ans[s], vocab, blind) for s in rows}
    torch.manual_seed(a.seed)                        # same init in both arms
    sel = Selector(len(vocab))
    emb = {id(m.weight) for m in sel.modules() if isinstance(m, nn.Embedding)}
    decay = [p for p in sel.parameters() if p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in sel.parameters() if p.ndim < 2 or id(p) in emb]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': a.wd}, {'params': no_decay, 'weight_decay': 0.0}], lr=a.lr, betas=(0.9, 0.95))
    ids, mask, hits = enc['fresh_train']
    rng = np.random.RandomState(a.seed)              # same batch order in both arms
    order, pos = rng.permutation(len(ids)), 0
    best, best_state, curve, t0 = -1.0, None, [], time.time()
    for step in range(a.steps):
        lr = lr_at(step, a.steps, a.warmup, a.lr)
        for g in opt.param_groups:
            g['lr'] = lr
        if pos + a.batch > len(order):
            order, pos = rng.permutation(len(ids)), 0
        b = torch.from_numpy(order[pos:pos + a.batch]); pos += a.batch
        loss = F.binary_cross_entropy_with_logits(sel(ids[b], mask[b]), hits[b])
        loss.backward()
        torch.nn.utils.clip_grad_norm_(sel.parameters(), a.grad_clip)
        opt.step(); opt.zero_grad(set_to_none=True)
        if (step + 1) % a.eval_every == 0:
            sel.eval()
            v, _ = score(sel, enc['fresh_val'], rows['fresh_val'], ans['fresh_val'])
            sel.train()
            curve.append(dict(step=step + 1, loss=round(float(loss), 4), val_team=v['team']))
            jprint(event='val', step=step + 1, loss=round(float(loss), 4), val_team=v['team'], val_B2=v['B2'], elapsed=round(time.time() - t0, 1))
            if v['team'] > best:                     # ties keep the earlier checkpoint
                best, best_state = v['team'], {k: x.clone() for k, x in sel.state_dict().items()}
    sel.load_state_dict(best_state)
    sel.eval()
    result = dict(config=vars(a), selected_val_team=best, curve=curve, params=sum(p.numel() for p in sel.parameters()), eval={}, rows={})
    for s in ['fresh_val'] + SPLITS:
        r, picks = score(sel, enc[s], rows[s], ans[s])
        result['eval'][s] = r
        if s in SPLITS:
            result['rows'][s] = {row['id']: ORDER[int(k)] for row, k in zip(rows[s], picks)}
        jprint(event='eval', split=s, **{k: v for k, v in r.items() if k != 'picks'}, picks=r['picks'])
    os.makedirs(a.out, exist_ok=True)
    json.dump(result, open(os.path.join(a.out, 'RESULT.json'), 'w'))
    torch.save(dict(selector=sel.state_dict(), arm=a.arm, tag=a.tag), os.path.join(a.out, 'selector.pt'))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fresh')
    f.add_argument('--curriculum', required=True); f.add_argument('--data', required=True); f.add_argument('--out', required=True)
    f.add_argument('--seed', type=int, default=2026100502); f.add_argument('--n-train', type=int, default=16000)
    f.add_argument('--n-val', type=int, default=4000)
    g = sub.add_parser('answers')
    g.add_argument('--data', required=True); g.add_argument('--work', required=True); g.add_argument('--tag', required=True)
    g.add_argument('--members', nargs='+', required=True); g.add_argument('--device', default='cpu')
    g.add_argument('--threads', type=int, default=4)
    t = sub.add_parser('train')
    t.add_argument('--data', required=True); t.add_argument('--work', required=True); t.add_argument('--tag', required=True)
    t.add_argument('--arm', choices=['aware', 'blind'], required=True); t.add_argument('--seed', type=int, default=0)
    t.add_argument('--steps', type=int, default=2000); t.add_argument('--batch', type=int, default=256)
    t.add_argument('--lr', type=float, default=1e-3); t.add_argument('--warmup', type=int, default=100)
    t.add_argument('--wd', type=float, default=0.01); t.add_argument('--grad-clip', type=float, default=1.0)
    t.add_argument('--eval-every', type=int, default=200); t.add_argument('--threads', type=int, default=4)
    t.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    {'fresh': fresh, 'answers': answers, 'train': train}[a.cmd](a)


if __name__ == '__main__':
    main()

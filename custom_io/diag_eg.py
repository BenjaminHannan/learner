"""Why EmbeddingGemma 2 as B2's reader lost (diagnosis only: no B2 or EG arm is trained, nothing is scored on any eval set).
python3 -m custom_io.diag_eg --ckpt CK/B2_s100/checkpoint.pt [--per-family 60] [--out custom_io/results/eg-diag/DIAG.json]
Needs $CUSTOM_IO_EG2 (local EmbeddingGemma 2) and transformers >= 5.19. CPU, fp32. Rows: a fixed sample of the skills training set.
  W  wiring: EmbeddingGemma is in eval mode with no trainable parameter, and a prompt's states do not change with the batch it is padded in.
  P1 spelling: a probe trained on 75% of the rows reads the char at each position back from that position's state (held-out 25%):
     EG state alone (linear); EG state + the char's offset in its word piece + the piece's length (2-layer MLP, the generous one);
     B2's trained reader output (linear). Split by chars in 1-char pieces vs chars inside longer pieces, and on cipher_map rows.
  P2 sameness: within a prompt, is the same word at two places more alike (cosine of the mean state over its chars) than two different
     words? AUC over all word pairs, and match@1: a repeated word's nearest earlier word is the same word. EG raw states vs B2's reader.
  P3 layers (--layers): P1's linear read (alone and with the offset in the piece) and P2's AUC on EmbeddingGemma's hidden state after each
     listed layer (0 = its input embedding; 512-d inside the model, the final 768-d output is P1/P2's "eg")."""
import argparse, collections, json, os, random, re
import numpy as np
import torch
from custom_io.data import DEFAULT_DATA, collate, Dataset, load_rows
from custom_io.models import load_model
from custom_io.models.eg import FrozenEG


def sample(per_family, seed=0):
    rows = load_rows(os.path.join(DEFAULT_DATA, 'train.jsonl'), keep=('id', 'prompt', 'answer', 'family'))
    by = collections.defaultdict(list)
    for r in rows:
        by[r['family']].append(r)
    rng = random.Random(seed)
    out = []
    for f in sorted(by):
        out += rng.sample(by[f], min(per_family, len(by[f])))
    rng.shuffle(out)
    return out


@torch.no_grad()
def eg_states(eg, rows, bs=16):
    """-> list of (H [len(prompt), 768] float32, offset-in-piece [len], piece length [len]) per row."""
    out = []
    for s in range(0, len(rows), bs):
        rs = rows[s:s + bs]
        T = max(len(r['prompt']) for r in rs)
        H, _ = eg.encode([r['prompt'] for r in rs], T, torch.device('cpu'))
        for b, r in enumerate(rs):
            n = len(r['prompt'])
            c2t = eg.align(r['prompt'])[1].astype(np.int64)
            first, cnt = {}, collections.Counter(c2t.tolist())
            for i, t in enumerate(c2t.tolist()):
                first.setdefault(t, i)
            off = np.array([i - first[t] for i, t in enumerate(c2t.tolist())])
            ln = np.array([cnt[t] for t in c2t.tolist()])
            out.append((H[b, :n].float().numpy(), off, ln))
    return out


@torch.no_grad()
def b2_states(m, rows, bs=64):
    out = []
    for s in range(0, len(rows), bs):
        rs = rows[s:s + bs]
        b = collate([Dataset(rs, m.vocab, strict=False)[i] for i in range(len(rs))])
        X = m.read(b)[0]
        for k, r in enumerate(rs):
            out.append(X[k, :len(r['prompt'])].float().numpy())
    return out


@torch.no_grad()
def eg_layer_states(eg, rows, layers, bs=16):
    """-> {layer: [per-row [len(prompt), 512] float32]}: the model's hidden state after each listed layer, gathered per char like encode()."""
    out = {l: [] for l in layers}
    for s in range(0, len(rows), bs):
        rs = rows[s:s + bs]
        al = [eg.align(r['prompt']) for r in rs]
        L = max(len(a[0]) for a in al)
        ids = np.full((len(rs), L), eg.tok.pad_token_id, np.int64)
        am = np.zeros((len(rs), L), np.int64)
        for b, (t, _) in enumerate(al):
            ids[b, :len(t)], am[b, :len(t)] = t, 1
        hs = eg.m(input_ids=torch.from_numpy(ids), attention_mask=torch.from_numpy(am), output_hidden_states=True).hidden_states
        for l in layers:
            for b, (r, (_, c2t)) in enumerate(zip(rs, al)):
                out[l].append(hs[l][b, torch.from_numpy(c2t.astype(np.int64))].float().numpy())
    return out


def p3(rows, E, layer_states, train_ids):
    """per layer: linear letter read alone / with the offset in the piece, and the same-word AUC."""
    res = {}
    for l, S in layer_states.items():
        E2 = [(S[k], E[k][1], E[k][2]) for k in range(len(rows))]
        chars = sorted({c for r in rows for c in r['prompt']})
        cid = {c: i for i, c in enumerate(chars)}
        tr = [k for k in range(len(rows)) if k in train_ids]
        te = [k for k in range(len(rows)) if k not in train_ids]
        def feats(ks, off):
            X = []
            for k in ks:
                H, o, ln = E2[k]
                if off:
                    oh = np.zeros((len(o), 32), np.float32)
                    oh[np.arange(len(o)), np.minimum(o, 15)] = 1
                    oh[np.arange(len(ln)), 16 + np.minimum(ln, 16) - 1] = 1
                    H = np.concatenate([H, oh], 1)
                X.append(H)
            return np.concatenate(X).astype(np.float32)
        y = lambda ks: np.concatenate([[cid[c] for c in rows[k]['prompt']] for k in ks])
        letter = np.concatenate([[c.isalpha() for c in rows[k]['prompt']] for k in te])
        out = {}
        for name, off in (('linear', False), ('linear_plus_offset', True)):
            hit = probe(feats(tr, off), y(tr), feats(te, off), y(te), len(chars))
            out[name] = round(100 * float(hit[letter].mean()), 2)
        out['same_word_auc'] = p2(rows, S)['auc']
        res[l] = out
        print(json.dumps({l: out}), flush=True)
    return res


def wiring(eg, rows):
    m = eg.m
    short, long_ = min(rows[:50], key=lambda r: len(r['prompt'])), max(rows[:50], key=lambda r: len(r['prompt']))
    with torch.no_grad():
        a = eg.encode([short['prompt']], len(short['prompt']), torch.device('cpu'))[0][0]
        eg._last = None
        b = eg.encode([short['prompt'], long_['prompt']], len(long_['prompt']), torch.device('cpu'))[0][0, :len(short['prompt'])]
    return dict(eval_mode=not m.training, trainable_params=sum(p.numel() for p in m.parameters() if p.requires_grad),
                padding_max_abs_diff=float((a.float() - b.float()).abs().max()), state_rms=float(a.float().pow(2).mean().sqrt()))


def probe(Xtr, ytr, Xte, yte, n_cls, hidden=0, steps=400, seed=0):
    torch.manual_seed(seed)
    Xtr, Xte = torch.tensor(Xtr), torch.tensor(Xte)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-5
    Xtr, Xte = (Xtr - mu) / sd, (Xte - mu) / sd
    net = torch.nn.Linear(Xtr.shape[1], n_cls) if not hidden else torch.nn.Sequential(
        torch.nn.Linear(Xtr.shape[1], hidden), torch.nn.GELU(), torch.nn.Linear(hidden, n_cls))
    opt = torch.optim.Adam(net.parameters(), lr=3e-3 if not hidden else 1e-3)
    ytr_t = torch.tensor(ytr)
    for _ in range(steps):
        idx = torch.randint(0, len(Xtr), (8192,))
        loss = torch.nn.functional.cross_entropy(net(Xtr[idx]), ytr_t[idx])
        opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        return (net(Xte).argmax(-1).numpy() == np.asarray(yte))


def p1(rows, E, B, train_ids):
    chars = sorted({c for r in rows for c in r['prompt']})
    cid = {c: i for i, c in enumerate(chars)}
    feats = collections.defaultdict(lambda: ([], [], [], []))      # split -> (eg, eg+off, b2, y), plus tags
    tags = {'tr': [], 'te': []}
    for k, r in enumerate(rows):
        sp = 'tr' if k in train_ids else 'te'
        H, off, ln = E[k]
        oh = np.zeros((len(r['prompt']), 32), np.float32)
        oh[np.arange(len(off)), np.minimum(off, 15)] = 1
        oh[np.arange(len(ln)), 16 + np.minimum(ln, 16) - 1] = 1
        f = feats[sp]
        f[0].append(H); f[1].append(np.concatenate([H, oh], 1)); f[2].append(B[k]); f[3].append(np.array([cid[c] for c in r['prompt']]))
        tags[sp] += [(r['family'], c.isalpha(), int(l)) for c, l in zip(r['prompt'], ln)]
    cat = lambda sp, j: np.concatenate(feats[sp][j]).astype(np.float32)
    ytr, yte = np.concatenate(feats['tr'][3]), np.concatenate(feats['te'][3])
    res = {}
    for name, j, hid in (('eg_linear', 0, 0), ('eg_plus_offset_mlp', 1, 512), ('b2_reader_linear', 2, 0)):
        hit = probe(cat('tr', j), ytr, cat('te', j), yte, len(chars), hidden=hid)
        sel = lambda fn: hit[[fn(t) for t in tags['te']]]
        pc = lambda h: round(100 * float(h.mean()), 2) if len(h) else None
        res[name] = dict(all=pc(hit), letters=pc(sel(lambda t: t[1])), letters_in_1char_pieces=pc(sel(lambda t: t[1] and t[2] == 1)),
                         letters_in_longer_pieces=pc(sel(lambda t: t[1] and t[2] > 1)), cipher_map_letters=pc(sel(lambda t: t[1] and t[0] == 'cipher_map')))
    res['n_test_chars'] = int(len(yte))
    res['share_of_letters_in_longer_pieces'] = round(100 * np.mean([t[2] > 1 for t in tags['te'] if t[1]]), 2)
    return res


def auc(pos, neg):
    if not pos or not neg:
        return None
    s = np.concatenate([pos, neg]); y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    o = s.argsort(); rk = np.empty(len(s)); rk[o] = np.arange(1, len(s) + 1)
    return float((rk[y == 1].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def p2(rows, states, families=None):
    pos, neg, m1 = [], [], []
    for k, r in enumerate(rows):
        if families and r['family'] not in families:
            continue
        S = states[k]
        ws = [(mt.group(0).lower(), mt.start(), mt.end()) for mt in re.finditer(r'[A-Za-z]+', r['prompt'])]
        V = [S[a:b].mean(0) for _, a, b in ws]
        V = [v / (np.linalg.norm(v) + 1e-8) for v in V]
        for j in range(len(ws)):
            sims = [float(V[i] @ V[j]) for i in range(j)]
            for i, sm in enumerate(sims):
                (pos if ws[i][0] == ws[j][0] else neg).append(sm)
            if any(ws[i][0] == ws[j][0] for i in range(j)):
                m1.append(ws[int(np.argmax(sims))][0] == ws[j][0])
    return dict(auc=None if auc(pos, neg) is None else round(auc(pos, neg), 4), same_word_pairs=len(pos), different_word_pairs=len(neg),
                mean_cos_same=round(float(np.mean(pos)), 4) if pos else None, mean_cos_different=round(float(np.mean(neg)), 4) if neg else None,
                match_at_1=round(100 * float(np.mean(m1)), 2) if m1 else None, n_repeats=len(m1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--per-family', type=int, default=60)
    ap.add_argument('--out', default='custom_io/results/eg-diag/DIAG.json')
    ap.add_argument('--layers', default='', help='P3 only (skips P1/P2): comma list of layers, e.g. 0,3,6,9,12,15,18,21,24')
    a = ap.parse_args(argv)
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    rows = sample(a.per_family)
    eg = FrozenEG().load(torch.device('cpu'))
    out = dict(rows=len(rows), per_family=a.per_family, ckpt=a.ckpt, wiring=wiring(eg, rows))
    print(json.dumps(out), flush=True)
    E = eg_states(eg, rows)
    if a.layers:
        layers = [int(x) for x in a.layers.split(',')]
        out['P3_layers'] = p3(rows, E, eg_layer_states(eg, rows, layers), set(range(int(0.75 * len(rows)))))
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        json.dump(out, open(a.out, 'w'), indent=1)
        return
    m = load_model(a.ckpt, torch.device('cpu')).eval()
    B = b2_states(m, rows)
    train_ids = set(range(int(0.75 * len(rows))))
    out['P1_spelling'] = p1(rows, E, B, train_ids)
    print(json.dumps(out['P1_spelling']), flush=True)
    MATCH = ['rule_apply', 'object_track', 'passage_qa', 'table_lookup', 'order_chain', 'kin_chain']
    out['P2_sameness'] = {src: dict(all=p2(rows, S), matching_families=p2(rows, S, MATCH))
                          for src, S in (('eg_raw', [e[0] for e in E]), ('b2_reader', B))}
    print(json.dumps(out['P2_sameness']), flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()

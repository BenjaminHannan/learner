"""Ultracode v4 diagnostics for the learning blocker (exploratory, fast lane; no training of the real model).

Same stack and rows as the fit screens (skills_pretrain_v1.py: main2, worst-8 families, the 2,000 fixed rows of
--sample-seed S, trainfit = fixed[:320], held-out = the 320 in_dist rows of those families).

  --mode bare     what the frozen LM does alone: chat template + direct answer, chat template + worked steps,
                  and the raw copy-path format with no prefix ([question][EOS][BOS] -> greedy)
  --mode chan     channel capacity: per row (main2-wrong trainfit rows, up to 8 per family) optimise 8 free
                  vectors placed in front of the question, after it, or alone (no question), starting from main2's
                  own prefix; steps until teacher-forced exact (max --chan-steps)
  --mode direct   can reader+core learn these rows with a clean signal? main2's reader+core + a new answer-class
                  head on the core state (no LM in the loss), 6,000 updates in the fit screen's row order;
                  scored on trainfit and held-out (answers never seen in the 2,000 rows count as wrong);
                  --families/--target/--head vocab/--learner/--warmup: learning ladder (LD)
  --mode probe    eval-only: can the number tokens be read back from the LM features, the 32-wide reader, the
                  core's input and its rounds 1 and 4? (token and row probes, kNN and ridge)
Prints one line per result starting with RESULT and writes OUT/DIAG-<mode>.json.
"""
import argparse
import json
import math
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_runtime_v1 as runtime  # noqa: E402
import skills_pretrain_v1 as sp  # noqa: E402

W8 = 'chain_ops,state_update,cipher_map,chain_story2,var_chain,seq_cycle,fewshot_number_rule,group_induct'.split(',')


def emit(tag, obj):
    print('RESULT ' + json.dumps({'tag': tag, **obj}), flush=True)


def rows_for(data, seed, n_fixed=2000, dev_n=320, fams=None, passes=3):
    fs = set(fams or W8)
    rows_all = [json.loads(l) for l in (Path(data) / 'train.jsonl').read_text().splitlines()]
    rows_all = [r for r in rows_all if r['family'] in fs]
    rng = random.Random('fixed|%d' % seed)
    fixed = rng.sample(rows_all, n_fixed)
    order = []
    for _ in range(passes):
        order += rng.sample(fixed, len(fixed))
    dev = [json.loads(l) for l in (Path(data) / 'dev' / 'in_dist.jsonl').read_text().splitlines()]
    held = [r for r in dev if r['family'] in fs][:dev_n]
    return fixed, order, fixed[:dev_n], held


def target_text(row, kind):
    """answer = norm(answer); x0 = first integer in the prompt; step1 = last integer in steps[0]; None if absent"""
    if kind == 'answer':
        return sp.norm(row['answer'])
    m = re.findall(r'\d+', row['prompt']) if kind == 'x0' else re.findall(r'-?\d+', row['steps'][0] if row['steps'] else '')
    return (m[0] if kind == 'x0' else m[-1]) if m else None


def reset_fresh(parts):
    for m in (parts['core'], parts['reader']):
        for mod in m.modules():
            if hasattr(mod, 'reset_parameters') and mod is not m:
                mod.reset_parameters()


def hit(text, row):
    return sp.norm(text) in {sp.norm(a) for a in row['accepted']}


def lenient(text, row):
    t = text.strip().splitlines()[0] if text.strip() else ''
    t = re.sub(r'^(the answer is|answer:)\s*', '', t.strip(), flags=re.I).strip().rstrip('.').strip()
    return hit(t, row)


def by_family(rows, oks):
    fam = {}
    for r, ok in zip(rows, oks):
        f = fam.setdefault(r['family'], [0, 0])
        f[0] += int(ok)
        f[1] += 1
    return fam


def setup(a, need_modules=True):
    root = Path(a.root).resolve()
    cfg = json.loads((root / sp.EXP / 'TRAIN-CONFIG-v2.json').read_text())
    rt = runtime.import_runtime()
    torch = rt.torch
    dec, tok, lm = runtime.load_native_stack(rt, root, cfg)
    modules = named = None
    if need_modules:
        saved = torch.load(Path(a.parent_path).resolve(), map_location='cpu', weights_only=True)
        modules = runtime.build_modules(rt, dec, 0, cfg['device'])
        named = runtime.restore_parent_modules(rt, saved, modules, lm)
    return rt, torch, cfg, dec, tok, lm, modules, named


# ---------------------------------------------------------------- bare LM
def gen_grouped(torch, lm, seqs, max_new, eos, bs=32):
    """greedy generation, rows grouped by identical length (no padding, exact)"""
    out = [None] * len(seqs)
    groups = {}
    for i, s in enumerate(seqs):
        groups.setdefault(len(s), []).append(i)
    for n, idx in groups.items():
        for k in range(0, len(idx), bs):
            part = idx[k:k + bs]
            ids = torch.tensor([seqs[i] for i in part], device=lm.device)
            with torch.no_grad():
                g = lm.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=max_new,
                                do_sample=False, eos_token_id=eos, pad_token_id=eos)
            for j, i in enumerate(part):
                row = g[j, n:].tolist()
                out[i] = row[:row.index(eos)] if eos in row else row
    return out


def mode_bare(a):
    rt, torch, cfg, dec, tok, lm, _, _ = setup(a, need_modules=False)
    _, _, fit, held = rows_for(a.data, a.sample_seed)
    eos = common.EOS_ID
    res = {}
    for split, rows in (('trainfit', fit), ('heldout', held)):
        chat = lambda q: tok.encode(tok.apply_chat_template([{'role': 'user', 'content': q}], tokenize=False,
                                                            add_generation_prompt=True), add_special_tokens=False)
        variants = {
            'chat_direct': ([chat(r['prompt'] + '\nReply with only the final answer, nothing else.') for r in rows], 16),
            'chat_steps': ([chat(r['prompt'] + '\nWork it out step by step, then give the final answer on the last '
                                 'line as "Answer: <answer>".') for r in rows], 256),
            'raw_copy': ([list(tok.encode(r['prompt'], add_special_tokens=False)) + [eos, common.BOS_ID] for r in rows], 12),
        }
        for v, (seqs, mx) in variants.items():
            t0 = time.time()
            outs = gen_grouped(torch, lm, seqs, mx, eos)
            texts = [tok.decode(o, skip_special_tokens=True) for o in outs]
            if v == 'chat_steps':
                oks = []
                for t, r in zip(texts, rows):
                    m = re.findall(r'Answer:\s*(.+)', t)
                    oks.append(bool(m) and lenient(m[-1], r))
            else:
                oks = [lenient(t, r) for t, r in zip(texts, rows)]
            res[split + '/' + v] = {'correct': sum(oks), 'n': len(rows), 'by_family': by_family(rows, oks),
                                    'examples': [[r['prompt'][:120], r['answer'], t[-160:]] for r, t in list(zip(rows, texts))[::40]],
                                    'seconds': round(time.time() - t0, 1)}
            emit('bare', {'split': split, 'variant': v, 'correct': sum(oks), 'n': len(rows),
                          'by_family': res[split + '/' + v]['by_family']})
    return res


# ---------------------------------------------------------------- channel capacity
def mode_chan(a):
    rt, torch, cfg, dec, tok, lm, modules, named = setup(a)
    _, _, fit, _ = rows_for(a.data, a.sample_seed)
    parts = runtime.module_dict(modules)
    for _, m in modules:
        m.eval()
    emb = lm.get_input_embeddings()
    rms = float(emb.weight.detach().pow(2).mean().sqrt())
    picked, per_fam = [], {}
    for row in fit:
        enc = sp.encode(tok, row, torch, cfg['device'])
        if enc is None:
            continue
        ids, mask, labels = enc
        feats = rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch)
        with torch.no_grad():
            h, _ = runtime.english_graph(rt, parts['core'], parts['reader'], feats, mask)
            pref = dec.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), mask, (1, h.shape[1]))
            pe = emb(ids)
            x = torch.cat([pref, pe], 1)
            per, pred = rt.human_loss(lm, x, labels, dec.bos_id, dec.eos_id, True, True)
        exact = bool((pred == labels).all())
        if exact or per_fam.get(row['family'], 0) >= a.chan_per_family:
            continue
        per_fam[row['family']] = per_fam.get(row['family'], 0) + 1
        picked.append((row, ids, labels, pref.detach().clone(), pe.detach()))
    emit('chan-picked', {'n': len(picked), 'per_family': per_fam, 'emb_rms': rms,
                         'prefix_rms': float(torch.stack([p[3].pow(2).mean().sqrt() for p in picked]).mean())})
    out = {}
    for place in ('front', 'back', 'alone'):
        steps = []
        for row, ids, labels, p0, pe in picked:
            p = torch.nn.Parameter(p0.clone())
            opt = torch.optim.Adam([p], lr=a.chan_lr * float(p0.pow(2).mean().sqrt()))
            got = None
            for s in range(a.chan_steps + 1):
                x = {'front': lambda: torch.cat([p, pe], 1), 'back': lambda: torch.cat([pe, p], 1),
                     'alone': lambda: p}[place]()
                per, pred = rt.human_loss(lm, x, labels, dec.bos_id, dec.eos_id, True, True)
                if bool((pred == labels).all()):
                    got = s
                    break
                opt.zero_grad()
                per.mean().backward()
                opt.step()
            steps.append(got)
            fam = out.setdefault(place, {}).setdefault(row['family'], [])
            fam.append(got)
        ok = [s for s in steps if s is not None]
        emit('chan', {'placement': place, 'solved': len(ok), 'n': len(steps),
                      'median_steps': sorted(ok)[len(ok) // 2] if ok else None,
                      'by_family': {f: [sum(v is not None for v in vs), len(vs)] for f, vs in out[place].items()}})
    return out


# ---------------------------------------------------------------- geometry, fixed point, family-mean lesion
def tf_exact(rt, torch, dec, lm, prefix, labels):
    with torch.no_grad():
        _, pred = rt.human_loss(lm, prefix, labels, dec.bos_id, dec.eos_id, True, True)
    return bool((pred == labels).all())


def mode_geom(a):
    rt, torch, cfg, dec, tok, lm, modules, named = setup(a)
    _, _, fit, held = rows_for(a.data, a.sample_seed)
    parts = runtime.module_dict(modules)
    core, reader = parts['core'], parts['reader']
    for _, m in modules:
        m.eval()
    emb = lm.get_input_embeddings()
    recs = []
    for row in fit + held:
        ids, mask, labels = sp.encode(tok, row, torch, cfg['device'])
        f = rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch)
        with torch.no_grad(), rt.ordered_attention_math():
            query = rt.compare.project_cached_question(reader, f, mask)
            st = core.begin_latent(query, None, query_mask=mask)
            hs = []
            for _ in range(8):
                st = core.advance_latent(st)
                hs.append(st['h'][:, :st['query_n']].clone())
            e = st['e'][:, :st['query_n']]
            h4 = hs[3]
            pref = dec.adapter.project_training(h4, torch.ones_like(h4, dtype=torch.bool), mask, (1, h4.shape[1]))
            pe = emb(ids)
        rel = [float((hs[r] - hs[r - 1]).norm() / hs[r].norm()) for r in range(1, 8)]
        recs.append({'row': row, 'ids': ids, 'labels': labels, 'pref': pref, 'pe': pe, 'rel': rel,
                     'e_over_h': float(e.norm() / h4.norm()), 'held': row in held,
                     'p8': dec.adapter.project_training(hs[7], torch.ones_like(hs[7], dtype=torch.bool), mask, (1, h4.shape[1]))})
    n = len(recs)
    rel_mean = [sum(r['rel'][k] for r in recs) / n for k in range(7)]
    emit('fixed-point', {'rel_change_round2_to_8': [round(x, 5) for x in rel_mean],
                         'e_over_h': round(sum(r['e_over_h'] for r in recs) / n, 3)})
    P = torch.stack([r['pref'][0].flatten() for r in recs])
    Pn = torch.nn.functional.normalize(P, dim=1)
    cos = (Pn @ Pn.T)
    off = cos[~torch.eye(n, dtype=torch.bool, device=cos.device)]
    fams = sorted({r['row']['family'] for r in recs})
    fam_mean = {f: torch.stack([r['pref'] for r in recs if r['row']['family'] == f and not r['held']]).mean(0) for f in fams}
    spread = [float((r['pref'] - fam_mean[r['row']['family']]).norm() / r['pref'].norm()) for r in recs]
    allmean = torch.stack([r['pref'] for r in recs if not r['held']]).mean(0)
    emit('prefix-geometry', {'cos_mean': round(float(off.mean()), 4), 'cos_min': round(float(off.min()), 4),
                             'spread_vs_family_mean': round(sum(spread) / n, 4),
                             'prefix_norm': round(float(P.norm(dim=1).mean()), 2),
                             'emb_token_norm': round(float(emb.weight.norm(dim=1).mean()), 4)})
    out = {}
    for split in ('trainfit', 'heldout'):
        rs = [r for r in recs if r['held'] == (split == 'heldout')]
        res = {}
        for name, fn in (('intact', lambda r: r['pref']), ('family_mean', lambda r: fam_mean[r['row']['family']]),
                         ('global_mean', lambda r: allmean), ('rounds8', lambda r: r['p8'])):
            oks = [tf_exact(rt, torch, dec, lm, torch.cat([fn(r), r['pe']], 1), r['labels']) for r in rs]
            res[name] = {'correct': sum(oks), 'n': len(rs), 'by_family': by_family([r['row'] for r in rs], oks)}
        # shuffle within family (next row of the same family)
        oks = []
        for i, r in enumerate(rs):
            same = [x for x in rs if x['row']['family'] == r['row']['family'] and x is not r]
            oks.append(tf_exact(rt, torch, dec, lm, torch.cat([same[i % len(same)]['pref'], r['pe']], 1), r['labels']))
        res['shuffle_same_family'] = {'correct': sum(oks), 'n': len(rs), 'by_family': by_family([r['row'] for r in rs], oks)}
        out[split] = res
        emit('lesions-tf', {'split': split, **{k: v['correct'] for k, v in res.items()}, 'n': len(rs),
                            'by_family': {k: v['by_family'] for k, v in res.items()}})
    return {'rel_change': rel_mean, 'lesions': out}


# ---------------------------------------------------------------- exit expressivity
def mode_exitcap(a):
    rt, torch, cfg, dec, tok, lm, modules, named = setup(a)
    _, _, fit, _ = rows_for(a.data, a.sample_seed)
    parts = runtime.module_dict(modules)
    for _, m in modules:
        m.eval()
    emb = lm.get_input_embeddings()
    ad = dec.adapter
    picked, per_fam = [], {}
    for row in fit:
        ids, mask, labels = sp.encode(tok, row, torch, cfg['device'])
        f = rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch)
        with torch.no_grad():
            h, _ = runtime.english_graph(rt, parts['core'], parts['reader'], f, mask)
            pref = ad.project_training(h, torch.ones_like(h, dtype=torch.bool), mask, (1, h.shape[1]))
            pe = emb(ids)
        if tf_exact(rt, torch, dec, lm, torch.cat([pref, pe], 1), labels) or per_fam.get(row['family'], 0) >= a.chan_per_family:
            continue
        per_fam[row['family']] = per_fam.get(row['family'], 0) + 1
        picked.append((row, ids, mask, labels, h.detach().clone(), pe.detach()))
    out = {}
    for what in ('h', 'hidden'):
        steps = []
        for row, ids, mask, labels, h0, pe in picked:
            N = h0.shape[1]
            if what == 'h':
                v = torch.nn.Parameter(h0.clone())
                make = lambda: ad.project_training(v, torch.ones_like(v, dtype=torch.bool), mask, (1, N))
            else:
                # per-token exit hidden (after GELU, N x hidden) -> second Linear -> chunk means
                with torch.no_grad():
                    hf = h0.float()
                    mean = hf.mean(-1, keepdim=True)
                    var = (hf - mean).square().mean(-1, keepdim=True)
                    nrm = (hf - mean) * torch.rsqrt(var + 1e-5)
                    c = torch.arange(N, device=hf.device).float() / max(N - 1, 1)
                    geom = torch.stack((torch.zeros_like(c), c), -1)[None]
                    z = torch.cat((nrm * ad.scale + ad.bias, geom, torch.ones(1, N, 1, device=hf.device)), -1)
                    hid0 = ad.project[1](ad.project[0](z))
                v = torch.nn.Parameter(hid0.clone())
                make = lambda: torch.nn.functional.adaptive_avg_pool1d(ad.project[2](v)[0].T[None], 8)[0].T[None]
            opt = torch.optim.Adam([v], lr=a.chan_lr * float(v.detach().pow(2).mean().sqrt()))
            got = None
            for s_ in range(a.chan_steps + 1):
                per, pred = rt.human_loss(lm, torch.cat([make(), pe], 1), labels, dec.bos_id, dec.eos_id, True, True)
                if bool((pred == labels).all()):
                    got = s_
                    break
                opt.zero_grad()
                per.mean().backward()
                opt.step()
            steps.append(got)
            out.setdefault(what, {}).setdefault(row['family'], []).append(got)
        ok = [x for x in steps if x is not None]
        emit('exitcap', {'optimise': what, 'solved': len(ok), 'n': len(steps),
                         'median_steps': sorted(ok)[len(ok) // 2] if ok else None,
                         'by_family': {f: [sum(x is not None for x in xs), len(xs)] for f, xs in out[what].items()}})
    return out


# ---------------------------------------------------------------- direct head
def mode_direct(a):
    rt, torch, cfg, dec, tok, lm, modules, named = setup(a)
    fixed, order, fit, held = rows_for(a.data, a.sample_seed, n_fixed=a.fresh_rows or 2000, fams=a.families.split(','),
                                       passes=1 if a.fresh_rows else 3)  # --fresh-rows N: N distinct rows seen once each
    parts = runtime.module_dict(modules)
    dev = cfg['device']
    T = lambda r: target_text(r, a.target)
    ntok = lambda r: len(tok.encode(T(r), add_special_tokens=False))
    if a.head == 'vocab' or a.target != 'answer':
        ok = {id(r): T(r) is not None and (a.head != 'vocab' or ntok(r) == 1) for r in fixed + held}
        pre = {'fixed': fixed, 'order': order, 'held': held}
        fixed, order, held = [[r for r in pre[k] if ok[id(r)]] for k in ('fixed', 'order', 'held')]
        fit = fixed[:len(fit)]
        emit('direct-drop', {'target': a.target, 'head': a.head, 'dropped': {k: len(v) - len(g) for (k, v), g in zip(pre.items(), (fixed, order, held))},
                             'kept': {'fixed': len(fixed), 'order': len(order), 'fit': len(fit), 'held': len(held)},
                             'dropped_by_family': {f: {k: [sum(not ok[id(r)] for r in pre[k] if r['family'] == f), sum(r['family'] == f for r in pre[k])]
                                                             for k in ('fixed', 'held')}
                                                   for f in sorted({r['family'] for r in pre['fixed'] + pre['held']})}})
    classes = sorted({T(r) for r in fixed})
    cid = {c: i for i, c in enumerate(classes)}
    cache = {}

    def feats(row):
        k = row['id']
        if k not in cache:
            enc = sp.encode(tok, row, torch, dev)
            ids, mask, _ = enc
            cache[k] = (rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch), mask)
        return cache[k]
    t0 = time.time()
    for r in fixed + held:
        feats(r)
    emit('direct-cache', {'rows': len(cache), 'classes': len(classes), 'seconds': round(time.time() - t0, 1),
                          'held_unseen_answers': sum(T(r) not in cid for r in held)})
    if a.fresh_core:
        reset_fresh(parts)
    if a.reader_hidden:  # wider reader: function-preserving (new units' outputs start at 0), or fresh with --fresh-core
        seq = parts['reader'].proj
        l1, l2 = seq[1], seq[3]
        g = torch.Generator(device='cpu').manual_seed(1000 + a.sample_seed)
        n1, n2 = torch.nn.Linear(l1.in_features, a.reader_hidden).to(dev), torch.nn.Linear(a.reader_hidden, l2.out_features).to(dev)
        if not a.fresh_core:
            with torch.no_grad():
                bound = 1.0 / math.sqrt(l1.in_features)
                n1.weight.copy_((torch.rand(a.reader_hidden, l1.in_features, generator=g) * 2 - 1).mul_(bound))
                n1.bias.copy_((torch.rand(a.reader_hidden, generator=g) * 2 - 1).mul_(bound))
                n1.weight[:l1.out_features] = l1.weight
                n1.bias[:l1.out_features] = l1.bias
                n2.weight.zero_()
                n2.weight[:, :l1.out_features] = l2.weight
                n2.bias.copy_(l2.bias)
        seq[1], seq[3] = n1, n2
        emit('direct-reader', {'hidden': a.reader_hidden, 'fresh': a.fresh_core})
    torch.manual_seed(a.sample_seed)
    width = {'core': 8 * 256, 'lmread': 3 * 2048, 'tfm': 8 * 256}[a.learner]
    nout = 2048 if a.head == 'vocab' else len(classes)
    if a.head == 'vocab':
        class VocabHead(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.proj = torch.nn.Linear(width, 2048)
                self.E = lm.get_input_embeddings().weight.detach().float().to(dev)

            def forward(self, s):
                return self.proj(s) @ self.E.T
        head = VocabHead().to(dev)
        label = lambda r: tok.encode(T(r), add_special_tokens=False)[0]
    else:
        head = (torch.nn.Linear(width, nout) if a.head == 'linear' else
                torch.nn.Sequential(torch.nn.Linear(width, 512), torch.nn.GELU(), torch.nn.Linear(512, nout))).to(dev)
        label = lambda r: cid.get(T(r), -1)
    tfm = None
    if a.learner == 'tfm':
        class Tfm(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.inp = torch.nn.Linear(2048, 256)
                self.pos = torch.nn.Parameter(torch.randn(64, 256) * 0.02)
                self.enc = torch.nn.TransformerEncoder(torch.nn.TransformerEncoderLayer(
                    256, 8, 1024, dropout=0.0, activation='gelu', batch_first=True, norm_first=True), 4)
                self.ln = torch.nn.LayerNorm(256)

            def forward(self, f):
                x = self.inp(torch.nn.functional.layer_norm(f.float(), (2048,))) + self.pos[:f.shape[1]]
                z = self.ln(self.enc(x))
                return torch.nn.functional.adaptive_avg_pool1d(z[0].T[None], 8)[0].T.reshape(1, -1)
        tfm = Tfm().to(dev)
    learner_params = {'core': [p for n, p in named if n.startswith('core.')] + (list(parts['reader'].parameters()) if a.reader_hidden else [p for n, p in named if n.startswith('reader.')]), 'lmread': [],
                      'tfm': list(tfm.parameters()) if tfm is not None else []}[a.learner]
    train_params = learner_params + list(head.parameters())
    opt = torch.optim.AdamW(train_params, lr=a.lr, weight_decay=0)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / a.warmup)) if a.warmup > 0 else None

    def state(row):
        f, mask = feats(row)
        if a.learner == 'lmread':
            z = torch.nn.functional.layer_norm(f.float(), (2048,))
            return torch.cat([z.mean(1), z[:, -1], z[:, -2]], 1)
        if a.learner == 'tfm':
            return tfm(f)
        h, _ = runtime.english_graph(rt, parts['core'], parts['reader'], f, mask)
        z = torch.nn.functional.layer_norm(h.float(), (256,))
        return torch.nn.functional.adaptive_avg_pool1d(z[0].T[None], 8)[0].T.reshape(1, -1)

    def score(rows):
        for _, m in modules:
            m.eval()
        ok = []
        with torch.no_grad():
            for r in rows:
                ok.append(int(head(state(r)).argmax()) == label(r))
        for _, m in modules:
            m.train()
        parts['core'].halt.requires_grad_(False)
        return {'correct': sum(ok), 'n': len(rows), 'by_family': by_family(rows, ok)}
    curve = []
    curve.append({'update': 0, 'trainfit': score(fit), 'heldout': score(held)})
    emit('direct-eval', {'update': 0, 'fit': curve[-1]['trainfit']['correct'], 'held': curve[-1]['heldout']['correct']})
    n_upd = len(order) if a.fresh_rows else min(a.updates, len(order))
    bs = a.batch
    i = 0
    stream = order * (1 + (n_upd * bs) // len(order))
    for u in range(1, n_upd + 1):
        opt.zero_grad(set_to_none=True)
        loss = 0
        for r in stream[(u - 1) * bs:u * bs]:
            logit = head(state(r))
            loss = loss + torch.nn.functional.cross_entropy(logit, torch.tensor([label(r)], device=dev)) / bs
        loss.backward()
        torch.nn.utils.clip_grad_norm_(train_params, 1.0)
        opt.step()
        if sched is not None:
            sched.step()
        if u % 1500 == 0 or u == n_upd:
            curve.append({'update': u, 'trainfit': score(fit), 'heldout': score(held)})
            emit('direct-eval', {'update': u, 'fit': curve[-1]['trainfit']['correct'], 'held': curve[-1]['heldout']['correct'],
                                 'fit_by_family': curve[-1]['trainfit']['by_family'],
                                 'held_by_family': curve[-1]['heldout']['by_family'],
                                 'minutes': round((time.time() - t0) / 60, 1)})
    return {'classes': len(classes), 'curve': curve}


# ---------------------------------------------------------------- number-identity probe
STAGES = ('f', 'r32', 'e', 'h1', 'h4')
CHAIN = ('chain_ops', 'state_update', 'chain_story2', 'var_chain')


def ridge_pred(torch, Xtr, Ytr, Xte, vmask, crit):
    """ridge with lambda in {1e-2,1,1e2} x tr(X^T X)/d picked on the rows in vmask (higher crit is better), then refit on all"""
    Xtr, Ytr, Xte = Xtr.double(), Ytr.double(), Xte.double()

    def fit(X, Y, m):
        mx, my = X.mean(0), Y.mean(0)
        A = (X - mx).T @ (X - mx)
        A = A + m * A.diagonal().sum() / X.shape[1] * torch.eye(X.shape[1], device=X.device, dtype=X.dtype)
        W = torch.linalg.solve(A, (X - mx).T @ (Y - my))
        return lambda Z: (Z - mx) @ W + my
    best = 1.0
    if bool(vmask.any()) and bool((~vmask).any()):
        best = max((1e-2, 1.0, 1e2), key=lambda m: crit(fit(Xtr[~vmask], Ytr[~vmask], m)(Xtr[vmask]), vmask))
    return fit(Xtr, Ytr, best)(Xte), best


def knn_pred(torch, Xtr, Xte):
    A, B = torch.nn.functional.normalize(Xtr, dim=1), torch.nn.functional.normalize(Xte, dim=1)
    return torch.cat([(B[i:i + 512] @ A.T).argmax(1) for i in range(0, len(B), 512)])


def mode_probe(a):
    rt, torch, cfg, dec, tok, lm, modules, named = setup(a)
    fixed, _, _, held = rows_for(a.data, a.sample_seed)
    parts = runtime.module_dict(modules)
    core, reader = parts['core'], parts['reader']
    dev = cfg['device']
    if a.fresh_core:
        torch.manual_seed(a.sample_seed)
        reset_fresh(parts)
    for _, m in modules:
        m.eval()
    store = {}
    hook = reader.proj[2].register_forward_hook(lambda m, i, o: store.__setitem__('r32', o.detach()))
    recs = {'fixed': [], 'held': []}
    norms = {'q': [], 'pos': [], 'h4': []}
    t0 = time.time()
    for split, rows in (('fixed', fixed), ('held', held)):
        for ri, row in enumerate(rows):
            enc = sp.encode(tok, row, torch, dev)
            if enc is None:
                continue
            ids, mask = enc[:2]
            with torch.no_grad():
                f = rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch)
            with torch.no_grad(), rt.ordered_attention_math():
                q = rt.compare.project_cached_question(reader, f, mask)
                st = core.begin_latent(q, None, query_mask=mask)
                n = st['query_n']
                reps = {'f': f[0], 'r32': store['r32'][0], 'e': st['e'][0, :n]}
                for r in range(1, 5):
                    st = core.advance_latent(st)
                    if r in (1, 4):
                        reps['h%d' % r] = st['h'][0, :n]
            norms['q'].append(q[0, 0, :n].float().norm(dim=-1))
            norms['pos'].append((st['e'][0, :n] - q[0, 0, :n]).float().norm(dim=-1))
            norms['h4'].append(reps['h4'].float().norm(dim=-1))
            ss = [tok.decode([i]).strip() for i in ids[0].tolist()[:n]]
            toks = [t for t, s in enumerate(ss) if s.isdigit() and len(s) <= 3]
            rec = {'ri': ri, 'row': row, 'lab': [int(ss[t]) for t in toks],
                   'tok': {k: v[toks].float() for k, v in reps.items()},
                   'x': {k: torch.cat([v.mean(0), v[-1]]).float() for k, v in reps.items()} if row['family'] in CHAIN else None}
            recs[split].append(rec)
    hook.remove()
    emit('probe-cache', {'fixed': len(recs['fixed']), 'held': len(recs['held']), 'seconds': round(time.time() - t0, 1)})
    med = {k: round(float(torch.cat(v).median()), 3) for k, v in norms.items()}
    emit('probe-norms', {'q_median': med['q'], 'pos_code_median': med['pos'], 'h4_median': med['h4']})
    nval = 400
    cut = len(fixed) - nval
    out = {'norms': med, 'token': {}, 'row': {t: {} for t in ('x0', 'step1', 'answer')}}
    lab_tr = torch.tensor([l for r in recs['fixed'] for l in r['lab']], device=dev)
    lab_te = torch.tensor([l for r in recs['held'] for l in r['lab']], device=dev)
    classes = sorted(set(lab_tr.tolist()))
    cidx = {c: i for i, c in enumerate(classes)}
    seen = torch.tensor([int(l) in cidx for l in lab_te.tolist()], device=dev)
    ytr = torch.tensor([cidx[int(l)] for l in lab_tr.tolist()], device=dev)
    yte = torch.tensor([cidx.get(int(l), -1) for l in lab_te.tolist()], device=dev)
    vtok = torch.tensor([r['ri'] >= cut for r in recs['fixed'] for _ in r['lab']], device=dev)
    onehot = torch.nn.functional.one_hot(ytr, len(classes)).double()
    cov = round(float(seen.float().mean()), 4) if len(lab_te) else None
    for st_name in STAGES:
        Xtr = torch.cat([r['tok'][st_name] for r in recs['fixed']])
        Xte = torch.cat([r['tok'][st_name] for r in recs['held']])
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
        Xtr, Xte = (Xtr - mu) / sd, (Xte - mu) / sd
        knn = float((ytr[knn_pred(torch, Xtr, Xte[seen])] == yte[seen]).float().mean())
        P, lam = ridge_pred(torch, Xtr, onehot, Xte[seen], vtok, lambda P, vm: float((P.argmax(1) == ytr[vm]).float().mean()))
        ridge = float((P.argmax(1) == yte[seen]).float().mean())
        out['token'][st_name] = {'knn': round(knn, 4), 'ridge': round(ridge, 4), 'coverage': cov, 'n': int(seen.sum()), 'ridge_lambda_mult': lam}
    emit('probe-token', out['token'])
    rtr = [r for r in recs['fixed'] if r['x'] is not None]
    rte = [r for r in recs['held'] if r['x'] is not None]
    ns = {}
    for tgt in ('x0', 'step1', 'answer'):
        def val(r):
            try:
                return float(int(target_text(r['row'], tgt)))
            except (TypeError, ValueError):
                return None
        tr = [r for r in rtr if val(r) is not None]
        te = [r for r in rte if val(r) is not None]
        y = torch.tensor([val(r) for r in tr], device=dev).double()
        yt = torch.tensor([val(r) for r in te], device=dev).double()
        m, s_ = y.mean(), y.std() + 1e-6
        y, yt = ((y - m) / s_)[:, None], ((yt - m) / s_)[:, None]
        vm = torch.tensor([r['ri'] >= cut for r in tr], device=dev)
        for st_name in STAGES:
            Xtr = torch.stack([r['x'][st_name] for r in tr])
            Xte = torch.stack([r['x'][st_name] for r in te])
            mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
            P, _ = ridge_pred(torch, (Xtr - mu) / sd, y, (Xte - mu) / sd, vm, lambda P, v: -float((P - y[v]).pow(2).mean()))
            out['row'][tgt][st_name] = round(float(1 - (P - yt).pow(2).sum() / (yt - yt.mean()).pow(2).sum()), 4)
        ns[tgt] = {'train': len(tr), 'held': len(te)}
    emit('probe-row', out['row'])
    emit('probe-row-n', ns)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', required=True, choices=['bare', 'chan', 'direct', 'geom', 'exitcap', 'probe'])
    ap.add_argument('--root', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--parent-path', default='')
    ap.add_argument('--sample-seed', type=int, default=1)
    ap.add_argument('--chan-per-family', type=int, default=8)
    ap.add_argument('--chan-steps', type=int, default=150)
    ap.add_argument('--chan-lr', type=float, default=0.02, help='Adam lr as a multiple of the row prefix RMS')
    ap.add_argument('--head', default='mlp', choices=['mlp', 'linear', 'vocab'])
    ap.add_argument('--families', default=','.join(W8))
    ap.add_argument('--target', default='answer', choices=['answer', 'x0', 'step1'])
    ap.add_argument('--learner', default='core', choices=['core', 'lmread', 'tfm'])
    ap.add_argument('--warmup', type=int, default=0)
    ap.add_argument('--reader-hidden', type=int, default=0, help='direct mode: widen the reader 2048->32->256 to 2048->H->256')
    ap.add_argument('--updates', type=int, default=6000)
    ap.add_argument('--fresh-rows', type=int, default=0, help='direct mode: N distinct rows, one pass each (--updates ignored)')
    ap.add_argument('--batch', type=int, default=1)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--fresh-core', action='store_true')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    res = {'bare': mode_bare, 'chan': mode_chan, 'direct': mode_direct, 'geom': mode_geom, 'exitcap': mode_exitcap, 'probe': mode_probe}[a.mode](a)
    (out / ('DIAG-%s.json' % a.mode)).write_text(json.dumps({'args': vars(a), 'result': res,
                                                              'minutes': round((time.time() - t0) / 60, 1)}, indent=1))
    print('DIAG-DONE ' + a.mode, flush=True)


if __name__ == '__main__':
    main()

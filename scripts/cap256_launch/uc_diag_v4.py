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
                  scored on trainfit and held-out (answers never seen in the 2,000 rows count as wrong)
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


def rows_for(data, seed, n_fixed=2000, dev_n=320):
    rows_all = [json.loads(l) for l in (Path(data) / 'train.jsonl').read_text().splitlines()]
    rows_all = [r for r in rows_all if r['family'] in set(W8)]
    rng = random.Random('fixed|%d' % seed)
    fixed = rng.sample(rows_all, n_fixed)
    order = []
    for _ in range(3):
        order += rng.sample(fixed, len(fixed))
    dev = [json.loads(l) for l in (Path(data) / 'dev' / 'in_dist.jsonl').read_text().splitlines()]
    held = [r for r in dev if r['family'] in set(W8)][:dev_n]
    return fixed, order, fixed[:dev_n], held


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


# ---------------------------------------------------------------- direct head
def mode_direct(a):
    rt, torch, cfg, dec, tok, lm, modules, named = setup(a)
    fixed, order, fit, held = rows_for(a.data, a.sample_seed)
    parts = runtime.module_dict(modules)
    dev = cfg['device']
    classes = sorted({sp.norm(r['answer']) for r in fixed})
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
                          'held_unseen_answers': sum(sp.norm(r['answer']) not in cid for r in held)})
    if a.fresh_core:
        for m in (parts['core'], parts['reader']):
            for mod in m.modules():
                if hasattr(mod, 'reset_parameters') and mod is not m:
                    mod.reset_parameters()
    torch.manual_seed(a.sample_seed)
    width = 8 * 256
    head = (torch.nn.Linear(width, len(classes)) if a.head == 'linear' else
            torch.nn.Sequential(torch.nn.Linear(width, 512), torch.nn.GELU(), torch.nn.Linear(512, len(classes)))).to(dev)
    train_params = [p for n, p in named if n.startswith(('core.', 'reader.'))] + list(head.parameters())
    opt = torch.optim.AdamW(train_params, lr=a.lr, weight_decay=0)

    def state(row):
        f, mask = feats(row)
        h, _ = runtime.english_graph(rt, parts['core'], parts['reader'], f, mask)
        z = torch.nn.functional.layer_norm(h.float(), (256,))
        return torch.nn.functional.adaptive_avg_pool1d(z[0].T[None], 8)[0].T.reshape(1, -1)

    def score(rows):
        for _, m in modules:
            m.eval()
        ok = []
        with torch.no_grad():
            for r in rows:
                ok.append(classes[int(head(state(r)).argmax())] == sp.norm(r['answer']))
        for _, m in modules:
            m.train()
        parts['core'].halt.requires_grad_(False)
        return {'correct': sum(ok), 'n': len(rows), 'by_family': by_family(rows, ok)}
    curve = []
    curve.append({'update': 0, 'trainfit': score(fit), 'heldout': score(held)})
    emit('direct-eval', {'update': 0, 'fit': curve[-1]['trainfit']['correct'], 'held': curve[-1]['heldout']['correct']})
    n_upd = a.updates
    bs = a.batch
    i = 0
    stream = order * (1 + (n_upd * bs) // len(order))
    for u in range(1, n_upd + 1):
        opt.zero_grad(set_to_none=True)
        loss = 0
        for r in stream[(u - 1) * bs:u * bs]:
            logit = head(state(r))
            loss = loss + torch.nn.functional.cross_entropy(logit, torch.tensor([cid[sp.norm(r['answer'])]], device=dev)) / bs
        loss.backward()
        torch.nn.utils.clip_grad_norm_(train_params, 1.0)
        opt.step()
        if u % 1500 == 0 or u == n_upd:
            curve.append({'update': u, 'trainfit': score(fit), 'heldout': score(held)})
            emit('direct-eval', {'update': u, 'fit': curve[-1]['trainfit']['correct'], 'held': curve[-1]['heldout']['correct'],
                                 'fit_by_family': curve[-1]['trainfit']['by_family'],
                                 'held_by_family': curve[-1]['heldout']['by_family'],
                                 'minutes': round((time.time() - t0) / 60, 1)})
    return {'classes': len(classes), 'curve': curve}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', required=True, choices=['bare', 'chan', 'direct'])
    ap.add_argument('--root', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--parent-path', default='')
    ap.add_argument('--sample-seed', type=int, default=1)
    ap.add_argument('--chan-per-family', type=int, default=8)
    ap.add_argument('--chan-steps', type=int, default=150)
    ap.add_argument('--chan-lr', type=float, default=0.02, help='Adam lr as a multiple of the row prefix RMS')
    ap.add_argument('--head', default='mlp', choices=['mlp', 'linear'])
    ap.add_argument('--updates', type=int, default=6000)
    ap.add_argument('--batch', type=int, default=1)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--fresh-core', action='store_true')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    res = {'bare': mode_bare, 'chan': mode_chan, 'direct': mode_direct}[a.mode](a)
    (out / ('DIAG-%s.json' % a.mode)).write_text(json.dumps({'args': vars(a), 'result': res,
                                                              'minutes': round((time.time() - t0) / 60, 1)}, indent=1))
    print('DIAG-DONE ' + a.mode, flush=True)


if __name__ == '__main__':
    main()

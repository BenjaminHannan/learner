"""Exploratory (fast lane) pretraining of the core on the generated skills curriculum (PR #32).

Not a sealed run. Same frozen LFM, same reader + core + prefix + calculator-path modules and the same
per-update step as the English pilot (train_english_paraphrase_pilot_windows_v1.train_step), but the
input is a curriculum prompt and the target is its short answer. Starts from a pilot parent checkpoint
and continues its Adam state. Rows are read in file order (easy to hard); --updates takes an even
stride through train.jsonl so every stage is visited.

usage: skills_pretrain_v1.py --root PKG --data OUT_DIR --out REL_DIR --updates N [--parent-seed 0]
       [--eval-every 4000] [--dev-n 100] [--minutes 120] [--phase train|eval]
       [--parent-path CKPT.pt] [--eval-at-start] [--no-checkpoint]   (stiffness test, STIFFNESS-TEST-v1.md)
       [--eval-only] [--dev-kinds in_dist,family] [--sample-seed S] [--fixed-rows M --passes P]   (plateau diagnosis, PLATEAU-DIAG-v1.md)
Writes OUT/final-checkpoint.pt (parent-shaped, so the English pilot can start from it) and OUT/SKILLS-RESULT.json.
"""
import argparse
import copy
import random
import json
import math
from pathlib import Path
import sys
import time
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_runtime_v1 as runtime  # noqa: E402
import train_english_paraphrase_pilot_windows_v1 as trainer  # noqa: E402

BUSY = Path(r'C:\Users\benja\GPU-BUSY.txt')
EXP = 'artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/CONFIGS-v1/'
CP = {'ids': None}
STEPS = {'on': False}
SEP = ' # '
DEV = ('in_dist', 'answer', 'frame', 'vocab', 'variant', 'family')


def norm(s):
    return ' '.join(s.strip().lower().split())


LORA = {'on': True}
SHUF = {'prev': None}

def encode(tokenizer, row, torch, device):
    ids = list(tokenizer.encode(row['prompt'], add_special_tokens=False)) + [common.EOS_ID]
    if len(ids) > 64:
        return None
    tgt = (' ; '.join(row['steps']) + SEP + row['answer']) if STEPS['on'] else row['answer']
    labels = list(tokenizer.encode(tgt, add_special_tokens=False)) + [common.EOS_ID]
    return (torch.tensor([ids], device=device, dtype=torch.long), torch.ones((1, len(ids)), device=device, dtype=torch.bool),
            torch.tensor([labels], device=device, dtype=torch.long))


def evaluate(rt, ctx, modules, rows, tokenizer):
    torch = rt.torch
    parts = runtime.module_dict(modules)
    for _, m in modules:
        m.eval()
    ok = skipped = 0
    fam = {}
    for row in rows:
        enc = encode(tokenizer, row, torch, ctx.device)
        if enc is None:
            skipped += 1
            continue
        ids, mask, _ = enc
        CP['ids'] = ids
        feats = rt.compare.extract_question_features(ctx.lm, ids, mask, 'contextual', torch)
        obs = runtime.generate_observed(rt, ctx.dec, parts['core'], parts['reader'], feats, mask, 48 if STEPS['on'] else 12)
        out = obs['MODEL_native_decoder_return'][0] if obs['MODEL_native_decoder_return'] else []
        text = tokenizer.decode(out, skip_special_tokens=True)
        if STEPS['on']:
            text = text.rsplit('#', 1)[-1] if '#' in text else '\x00no-answer'
        hit = norm(text) in {norm(a) for a in row['accepted']}
        ok += hit
        f = fam.setdefault(row.get('family', '?'), [0, 0])
        f[0] += hit
        f[1] += 1
    for _, m in modules:
        m.train()
    parts['core'].halt.requires_grad_(False)
    return {'correct': ok, 'n': len(rows) - skipped, 'skipped': skipped, 'by_family': fam}


def load_dev(data, n):
    dev = {}
    for k in DEV:
        p = Path(data) / 'dev' / (k + '.jsonl')
        rows = [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        step = max(1, len(rows) // n)
        dev[k] = rows[::step][:n]
    return dev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--updates', type=int, required=True)
    ap.add_argument('--parent-seed', type=int, default=0)
    ap.add_argument('--eval-every', type=int, default=4000)
    ap.add_argument('--dev-n', type=int, default=100)
    ap.add_argument('--minutes', type=float, default=120)
    ap.add_argument('--lr-mult', type=float, default=1.0)
    ap.add_argument('--lr-final-mult', type=float, default=None, help='cosine-decay lr from lr-mult to this multiple over the run')
    ap.add_argument('--steps', action='store_true', help='target = worked steps + " # " + answer; scored on the text after the last #')
    ap.add_argument('--copy-path', action='store_true', help='prefix = 8 pooled vectors + the prompt token embeddings (talker can copy prompt tokens)')
    ap.add_argument('--families', default='', help='comma list: train and score only these families (diagnosis)')
    ap.add_argument('--parent-path', default='', help='start from this parent-shaped checkpoint (e.g. a skills final-checkpoint.pt) instead of the pinned seed parent; any update count accepted')
    ap.add_argument('--eval-at-start', action='store_true', help='score in_dist once before the first update (curve point at update 0)')
    ap.add_argument('--no-checkpoint', action='store_true', help='do not write final-checkpoint.pt (saves ~61 MB of disk per run)')
    ap.add_argument('--eval-only', action='store_true', help='no training: score the starting checkpoint on the dev files')
    ap.add_argument('--dev-kinds', default='', help='comma list of dev files to score (default: all six)')
    ap.add_argument('--sample-seed', type=int, default=None, help='train on a seeded random sample of the (family-filtered) rows instead of the ordered stride')
    ap.add_argument('--fixed-rows', type=int, default=0, help='with --sample-seed: draw this many rows once and repeat them --passes times (reshuffled each pass); also scores them as dev "trainfit"')
    ap.add_argument('--passes', type=int, default=1)
    ap.add_argument('--pointer', action='store_true', help='with --copy-path: add 8 pointer vectors (Linear 256->8 softmax over prompt positions, value = prompt embedding), the allptr exit; fresh params')
    ap.add_argument('--prefix-hidden', type=int, default=0, help='widen the exit StatePrefix 259->32->2048 hidden to this width; function-preserving, fresh Adam state for the widened layers')
    ap.add_argument('--zero-pool', action='store_true', help='with --copy-path: zero the 8 pooled core vectors (lesion: does the core matter?)')
    ap.add_argument('--lm-lora', type=int, default=0, help='rank-r LoRA on every Linear inside the frozen LM (not lm_head), used only when the LM talks (off during reader feature extraction); B=0 so the start is exactly the parent; kept outside lm.parameters()')
    ap.add_argument('--shuffle-pool', action='store_true', help='with --copy-path: replace the 8 pooled core vectors with the previous question\'s (lesion: does the core carry question-specific information?)')
    ap.add_argument('--rounds', type=int, default=4, help='latent loop rounds (shared weights; parent used 4)')
    ap.add_argument('--reader-hidden', type=int, default=0, help='widen the reader 2048->32->256 bottleneck to this width; function-preserving (new units feed zero weights), new weights get fresh Adam state; checkpoint then has the wider shape')
    a = ap.parse_args()
    STEPS['on'] = a.steps
    root = Path(a.root).resolve()
    out = root / a.out
    out.mkdir(parents=True, exist_ok=True)
    if BUSY.exists():
        raise SystemExit('GPU-BUSY marker present: ' + BUSY.read_text()[:200])
    BUSY.write_text('skills pretrain\n')
    try:
        cfg = json.loads((root / EXP / 'TRAIN-CONFIG-v2.json').read_text())
        rt = runtime.import_runtime()
        torch = rt.torch
        rt.compare.install_cuda_memory_budget(torch, cfg['budget']['cuda_peak_reserved_cap_bytes'])
        dec, tokenizer, lm = runtime.load_native_stack(rt, root, cfg)
        parent = next(p for p in cfg['parents'] if p['seed'] == a.parent_seed)
        if a.parent_path:
            src = Path(a.parent_path).resolve()
            saved = torch.load(src, map_location='cpu', weights_only=True)
            print(json.dumps({'event': 'parent-path', 'path': str(src), 'sha256': common.digest(src), 'update': saved.get('update')}), flush=True)
        else:
            saved = torch.load(common.pinned(root, parent['checkpoint']), map_location='cpu', weights_only=True)
        modules = runtime.build_modules(rt, dec, a.parent_seed, cfg['device'])
        named = runtime.restore_parent_modules(rt, saved, modules, lm)
        names = [n for n, _ in named]
        runtime.validate_parent_metadata(saved, names, saved['update'] if a.parent_path else runtime.PARENT_UPDATE)
        opt = runtime.make_optimizer(torch, [p for _, p in named])
        runtime.restore_adam(torch, opt, saved, named)
        participation, nonzero = Counter(saved['participation']), Counter()
        if a.lm_lora:
            r_, lora = a.lm_lora, torch.nn.ModuleDict()
            g = torch.Generator(device='cpu').manual_seed(3000 + (a.sample_seed or 0))
            LORA['on'] = True

            def hook(mod, inp, out, key=None):
                if not LORA['on']:
                    return out
                A, B = lora[key + '_A'], lora[key + '_B']
                return out + B(A(inp[0].to(A.weight.dtype))).to(out.dtype)
            for name, mod in lm.model.named_modules():
                if isinstance(mod, torch.nn.Linear):
                    key = name.replace('.', '__')
                    A = torch.nn.Linear(mod.in_features, r_, bias=False)
                    B = torch.nn.Linear(r_, mod.out_features, bias=False)
                    with torch.no_grad():
                        A.weight.copy_(torch.randn(r_, mod.in_features, generator=g) / math.sqrt(mod.in_features))
                        B.weight.zero_()
                    lora[key + '_A'], lora[key + '_B'] = A, B
                    mod.register_forward_hook(lambda m, i, o, key=key: hook(m, i, o, key))
            lora = lora.to(cfg['device'])
            o_extract = rt.compare.extract_question_features

            def extract_off(*x, **k):
                LORA['on'] = False
                try:
                    return o_extract(*x, **k)
                finally:
                    LORA['on'] = True
            rt.compare.extract_question_features = extract_off
            named = named + [('lora.' + n, p) for n, p in lora.named_parameters()]
            opt.add_param_group({'params': list(lora.parameters())})
            print(json.dumps({'event': 'lm-lora', 'rank': r_, 'linears': len(lora) // 2,
                              'params': sum(p.numel() for p in lora.parameters())}), flush=True)
        if a.rounds != 4:
            R = a.rounds

            def fixed_rounds(core, query, notebook=None, **metadata):
                state = core.begin_latent(query, notebook, **metadata)
                terms = []
                for _ in range(R):
                    state = core.advance_latent(state)
                    terms.extend(block.mlp.aux for block in core.blocks)
                h, q = core.read_latent(state)
                return h, q, torch.stack(terms).mean()
            rt.train_api.fixed4_training = fixed_rounds
        for which, H in (('reader', a.reader_hidden), ('prefix', a.prefix_hidden)):
            if not H:
                continue
            seq = runtime.module_dict(modules)['reader'].proj if which == 'reader' else dec.adapter.project
            i1, i2 = (1, 3) if which == 'reader' else (0, 2)
            l1, l2 = seq[i1], seq[i2]
            old_h = l1.out_features
            if H <= old_h:
                raise SystemExit('--%s-hidden must exceed %d' % (which, old_h))
            g = torch.Generator(device='cpu').manual_seed(1000 + (a.sample_seed or 0))
            n1 = torch.nn.Linear(l1.in_features, H).to(l1.weight.device)
            n2 = torch.nn.Linear(H, l2.out_features).to(l2.weight.device)
            with torch.no_grad():
                bound = 1.0 / math.sqrt(l1.in_features)
                n1.weight.copy_((torch.rand(H, l1.in_features, generator=g) * 2 - 1).mul_(bound))
                n1.bias.copy_((torch.rand(H, generator=g) * 2 - 1).mul_(bound))
                n1.weight[:old_h] = l1.weight
                n1.bias[:old_h] = l1.bias
                n2.weight.zero_()
                n2.weight[:, :old_h] = l2.weight
                n2.bias.copy_(l2.bias)
            swap = {id(l1.weight): n1.weight, id(l1.bias): n1.bias, id(l2.weight): n2.weight, id(l2.bias): n2.bias}
            seq[i1], seq[i2] = n1, n2
            new_named = [(n, swap.get(id(p), p)) for n, p in named]
            opt2 = runtime.make_optimizer(torch, [p for _, p in new_named])
            for (_, p_old), (_, p_new) in zip(named, new_named):
                if p_old is p_new and opt.state.get(p_old):
                    opt2.state[p_new] = opt.state[p_old]
            named, opt = new_named, opt2
            print(json.dumps({'event': which + '-widened', 'from': old_h, 'to': H,
                              'params': sum(p.numel() for p in seq.parameters())}), flush=True)
        if a.copy_path:
            ad = dec.adapter
            emb = lm.get_input_embeddings()
            o_train, o_fwd = ad.project_training, ad.forward

            ptr = None
            if a.pointer:  # allptr exit (reasoner_ptr/real/english/run_english.py): + 8 pointer vectors over prompt embeddings
                g = torch.Generator(device='cpu').manual_seed(2000 + (a.sample_seed or 0))
                ptr = torch.nn.Linear(256, 8)
                with torch.no_grad():
                    bound = 1.0 / math.sqrt(256)
                    ptr.weight.copy_((torch.rand(8, 256, generator=g) * 2 - 1).mul_(bound))
                    ptr.bias.copy_((torch.rand(8, generator=g) * 2 - 1).mul_(bound))
                ptr = ptr.to(cfg['device'])
                opt.add_param_group({'params': list(ptr.parameters())})
                named = named + [('ptr.weight', ptr.weight), ('ptr.bias', ptr.bias)]

            def with_prompt(pref, h):
                with torch.no_grad():
                    pe = emb(CP['ids']).to(pref.dtype)
                if a.shuffle_pool:
                    prev, SHUF['prev'] = SHUF['prev'], pref.detach()
                    pref = prev if prev is not None else pref * 0
                parts = [pref * 0 if a.zero_pool else pref]
                if ptr is not None:
                    pw = ptr(h.float()).softmax(1)
                    parts.append(torch.einsum('bnk,bnl->bkl', pw, pe))
                return torch.cat(parts + [pe], 1)
            ad.project_training = lambda *x, **k: with_prompt(o_train(*x, **k), x[0])
            ad.forward = lambda *x, **k: with_prompt(o_fwd(*x, **k), x[0].latent)

            def loss_fn(rt_, lm_, dec_, h, mask, target):
                prefix = dec_.adapter.project_training(h, torch.ones_like(h, dtype=torch.bool), mask, (1, h.shape[1]))
                per, pred = rt_.human_loss(lm_, prefix, target, dec_.bos_id, dec_.eos_id, True, True)
                valid = target != -100
                ok = (pred == target) & valid
                return per, pred, {'CE': float(per.detach().mean()), 'valid_target_tokens': int(valid.sum()),
                                   'first_token_CE': 0.0, 'EOS_CE': 0.0,
                                   'teacherforced_token_accuracy': float(ok.sum()) / int(valid.sum()),
                                   'teacherforced_exact': bool(ok.sum() == valid.sum())}
            runtime.english_loss = loss_fn
        ctx = type('Ctx', (), {})()
        ctx.lm, ctx.dec, ctx.device = lm, dec, cfg['device']
        dev = load_dev(a.data, a.dev_n)
        rows_all = [json.loads(l) for l in (Path(a.data) / 'train.jsonl').read_text().splitlines()]
        if a.families:
            keep = set(a.families.split(','))
            rows_all = [r for r in rows_all if r['family'] in keep]
            dev = {k: [r for r in json.loads('[' + ','.join(l for l in (Path(a.data) / 'dev' / (k + '.jsonl')).read_text().splitlines()) + ']') if r['family'] in keep][:a.dev_n] for k in DEV if (Path(a.data) / 'dev' / (k + '.jsonl')).exists()}
        if a.dev_kinds:
            dev = {k: v for k, v in dev.items() if k in a.dev_kinds.split(',')}
        stride = max(1, len(rows_all) // max(1, a.updates))
        if a.eval_only:
            rows = []
        elif a.sample_seed is not None and a.fixed_rows:
            rng = random.Random('fixed|%d' % a.sample_seed)
            fixed = rng.sample(rows_all, a.fixed_rows)
            rows = []
            for _ in range(a.passes):
                rows += rng.sample(fixed, len(fixed))
            dev['trainfit'] = fixed[:a.dev_n]
        elif a.sample_seed is not None:
            rows = random.Random('sample|%d' % a.sample_seed).sample(rows_all, min(a.updates, len(rows_all)))
        else:
            rows = rows_all[::stride][:a.updates]
        print(json.dumps({'event': 'skills-start', 'train_rows': len(rows_all), 'used': len(rows), 'stride': stride}), flush=True)
        log, curve, t0, done = [], [], time.time(), 0
        base_lr = runtime.ADAM_RECIPE['lr'] * a.lr_mult
        for g in opt.param_groups:
            g['lr'] = base_lr
        if a.eval_at_start:
            curve.append({'update': 0, **{k: evaluate(rt, ctx, modules, dev[k], tokenizer) for k in ('in_dist', 'trainfit') if k in dev}})
            print(json.dumps({'event': 'skills-eval', **curve[-1]}), flush=True)
        for i, row in enumerate(rows, 1):
            if a.lr_final_mult is not None:
                fin = runtime.ADAM_RECIPE['lr'] * a.lr_final_mult
                cur = fin + 0.5 * (base_lr - fin) * (1 + math.cos(math.pi * (i - 1) / len(rows)))
                for g in opt.param_groups:
                    g['lr'] = cur
            enc = encode(tokenizer, row, torch, ctx.device)
            if enc is None:
                continue
            ids, mask, labels = enc
            CP['ids'] = ids
            feats = rt.compare.extract_question_features(lm, ids, mask, 'contextual', torch)
            ctx.tokens, ctx.features = {0: (ids, mask, labels)}, {0: feats}
            r = trainer.train_step(rt, ctx, modules, named, opt, 0, participation, nonzero)
            if a.lm_lora and done == 0:
                lg = [(n, p.grad) for n, p in named if n.startswith('lora.') and n.endswith('_A.weight')]
                print(json.dumps({'event': 'lm-lora-first-step', 'A_with_grad': sum(1 for _, g_ in lg if g_ is not None),
                                  'A_total': len(lg)}), flush=True)
            done += 1
            log.append((row['stage'], r['CE'], r['teacherforced_exact']))
            if i % 500 == 0:
                last = log[-500:]
                print(json.dumps({'event': 'skills-progress', 'update': i, 'stage': row['stage'],
                                  'CE': round(sum(x[1] for x in last) / len(last), 4),
                                  'exact': round(sum(x[2] for x in last) / len(last), 3),
                                  'minutes': round((time.time() - t0) / 60, 1)}), flush=True)
            if i % a.eval_every == 0:
                curve.append({'update': i, **{k: evaluate(rt, ctx, modules, dev[k], tokenizer) for k in ('in_dist', 'trainfit') if k in dev}})
                print(json.dumps({'event': 'skills-eval', **curve[-1]}), flush=True)
            if (time.time() - t0) / 60 > a.minutes:
                print(json.dumps({'event': 'skills-time-cap', 'update': i}), flush=True)
                break
        final = {k: evaluate(rt, ctx, modules, v, tokenizer) for k, v in dev.items()}
        ck_sha = None
        if not a.no_checkpoint:
            payload = copy.copy(saved)
            payload.update(runtime.checkpoint_payload(modules, opt, names, participation,
                                                      {'update': runtime.PARENT_UPDATE + done}, common.rng_snapshot(torch)))
            ck = out / 'final-checkpoint.pt'
            torch.save(payload, ck)
            ck_sha = common.digest(ck)
        res = {'updates_done': done, 'rounds': a.rounds, 'pointer': a.pointer, 'reader_hidden': a.reader_hidden or None, 'prefix_hidden': a.prefix_hidden or None, 'zero_pool': a.zero_pool, 'shuffle_pool': a.shuffle_pool, 'lm_lora': a.lm_lora or None, 'sample_seed': a.sample_seed, 'fixed_rows': a.fixed_rows, 'passes': a.passes,
               'families': a.families or None, 'stride': stride, 'parent_seed': a.parent_seed, 'lr_mult': a.lr_mult,
               'dev_n': a.dev_n, 'final_dev': final, 'in_dist_curve': curve, 'parent_path': a.parent_path or None,
               'checkpoint_sha256': ck_sha, 'minutes': round((time.time() - t0) / 60, 1)}
        (out / 'SKILLS-RESULT.json').write_text(json.dumps(res, indent=1))
        print('SKILLS-RESULT ' + json.dumps(res), flush=True)
    finally:
        try:
            BUSY.unlink()
        except OSError:
            pass


if __name__ == '__main__':
    main()

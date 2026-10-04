"""Exploratory (fast lane) pretraining of the core on the generated skills curriculum (PR #32).

Not a sealed run. Same frozen LFM, same reader + core + prefix + calculator-path modules and the same
per-update step as the English pilot (train_english_paraphrase_pilot_windows_v1.train_step), but the
input is a curriculum prompt and the target is its short answer. Starts from a pilot parent checkpoint
and continues its Adam state. Rows are read in file order (easy to hard); --updates takes an even
stride through train.jsonl so every stage is visited.

usage: skills_pretrain_v1.py --root PKG --data OUT_DIR --out REL_DIR --updates N [--parent-seed 0]
       [--eval-every 4000] [--dev-n 100] [--minutes 120] [--phase train|eval]
Writes OUT/final-checkpoint.pt (parent-shaped, so the English pilot can start from it) and OUT/SKILLS-RESULT.json.
"""
import argparse
import copy
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
        ok += norm(text) in {norm(a) for a in row['accepted']}
    for _, m in modules:
        m.train()
    parts['core'].halt.requires_grad_(False)
    return {'correct': ok, 'n': len(rows) - skipped, 'skipped': skipped}


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
        saved = torch.load(common.pinned(root, parent['checkpoint']), map_location='cpu', weights_only=True)
        modules = runtime.build_modules(rt, dec, a.parent_seed, cfg['device'])
        named = runtime.restore_parent_modules(rt, saved, modules, lm)
        names = [n for n, _ in named]
        runtime.validate_parent_metadata(saved, names, runtime.PARENT_UPDATE)
        opt = runtime.make_optimizer(torch, [p for _, p in named])
        runtime.restore_adam(torch, opt, saved, named)
        participation, nonzero = Counter(saved['participation']), Counter()
        if a.copy_path:
            ad = dec.adapter
            emb = lm.get_input_embeddings()
            o_train, o_fwd = ad.project_training, ad.forward

            def with_prompt(pref):
                with torch.no_grad():
                    pe = emb(CP['ids']).to(pref.dtype)
                return torch.cat((pref, pe), 1)
            ad.project_training = lambda *x, **k: with_prompt(o_train(*x, **k))
            ad.forward = lambda *x, **k: with_prompt(o_fwd(*x, **k))

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
        stride = max(1, len(rows_all) // a.updates)
        rows = rows_all[::stride][:a.updates]
        print(json.dumps({'event': 'skills-start', 'train_rows': len(rows_all), 'used': len(rows), 'stride': stride}), flush=True)
        log, curve, t0, done = [], [], time.time(), 0
        base_lr = runtime.ADAM_RECIPE['lr'] * a.lr_mult
        for g in opt.param_groups:
            g['lr'] = base_lr
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
            done += 1
            log.append((row['stage'], r['CE'], r['teacherforced_exact']))
            if i % 500 == 0:
                last = log[-500:]
                print(json.dumps({'event': 'skills-progress', 'update': i, 'stage': row['stage'],
                                  'CE': round(sum(x[1] for x in last) / len(last), 4),
                                  'exact': round(sum(x[2] for x in last) / len(last), 3),
                                  'minutes': round((time.time() - t0) / 60, 1)}), flush=True)
            if i % a.eval_every == 0:
                curve.append({'update': i, 'in_dist': evaluate(rt, ctx, modules, dev['in_dist'], tokenizer)})
                print(json.dumps({'event': 'skills-eval', **curve[-1]}), flush=True)
            if (time.time() - t0) / 60 > a.minutes:
                print(json.dumps({'event': 'skills-time-cap', 'update': i}), flush=True)
                break
        final = {k: evaluate(rt, ctx, modules, v, tokenizer) for k, v in dev.items()}
        payload = copy.copy(saved)
        payload.update(runtime.checkpoint_payload(modules, opt, names, participation,
                                                  {'update': runtime.PARENT_UPDATE + done}, common.rng_snapshot(torch)))
        ck = out / 'final-checkpoint.pt'
        torch.save(payload, ck)
        res = {'updates_done': done, 'stride': stride, 'parent_seed': a.parent_seed, 'lr_mult': a.lr_mult,
               'dev_n': a.dev_n, 'final_dev': final, 'in_dist_curve': curve,
               'checkpoint_sha256': common.digest(ck), 'minutes': round((time.time() - t0) / 60, 1)}
        (out / 'SKILLS-RESULT.json').write_text(json.dumps(res, indent=1))
        print('SKILLS-RESULT ' + json.dumps(res), flush=True)
    finally:
        try:
            BUSY.unlink()
        except OSError:
            pass


if __name__ == '__main__':
    main()

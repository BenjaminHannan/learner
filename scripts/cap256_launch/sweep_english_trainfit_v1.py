"""Exploratory (fast lane) TRAIN-only sweep for the English pilot: lr x updates x warmup.

Not a sealed run. Reuses the pilot trainer and the pilot eval generator through
monkeypatches; it touches ONLY the TRAIN panel (the fresh eval inputs are replaced
by an empty list and no gold file is opened). Scores train fit = correct of 48 TRAIN QA.

usage: sweep_english_trainfit_v1.py --root PKG --tag T --lr-mult 3 --passes 32 --warmup 0 --seeds 0 --arms control,treatment
"""
import argparse
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_runtime_v1 as runtime  # noqa: E402
import english_full_pilot_schedule_v1 as sched  # noqa: E402
import train_english_paraphrase_pilot_windows_v1 as trainer  # noqa: E402
import eval_english_fresh_windows_v1 as ev  # noqa: E402
import score_english_free_answer_v1 as scorer  # noqa: E402

BUSY = Path(r'C:\Users\benja\GPU-BUSY.txt')
EXP = 'artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/CONFIGS-v1/'


def write_cfg(path, cfg):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=1, sort_keys=True) + '\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--lr-mult', type=float, default=1.0)
    ap.add_argument('--passes', type=int, default=32)
    ap.add_argument('--warmup', type=int, default=0)
    ap.add_argument('--seeds', default='0')
    ap.add_argument('--arms', default='control,treatment')
    ap.add_argument('--phase', default='both')
    ap.add_argument('--aux-weight', type=float, default=0.0, help='add this x router balance aux to the loss')
    ap.add_argument('--overfit-items', type=int, default=4)
    ap.add_argument('--overfit-updates', type=int, default=0, help='train only QA frames 0,1,4,5 for N updates')
    a = ap.parse_args()
    root = Path(a.root).resolve()
    seeds = [int(s) for s in a.seeds.split(',')]
    arms = a.arms.split(',')
    OVER = tuple(4 * (i // 2) + i % 2 for i in range(a.overfit_items))
    total = a.overfit_updates or a.passes * sched.PER_PASS
    base = 'artifacts/english-sweep/' + a.tag
    if a.phase != 'eval':
        if BUSY.exists():
            raise SystemExit('GPU-BUSY marker present: ' + BUSY.read_text()[:200])
        BUSY.write_text('english sweep %s\n' % a.tag)
    try:
        # ---- train
        if a.phase in ('train', 'both'):
            tcfg = json.loads((root / EXP / 'TRAIN-CONFIG-v2.json').read_text())
            tcfg['output_namespace'] = base + '/train'
            tcfg['resume_every_updates'] = 576
            tcfg['budget']['worker_seconds'] = 28800
            tpath = root / base / 'TRAIN-CONFIG.json'
            tsha = write_cfg(tpath, tcfg)
            orig_validate = runtime.validate_native_config
            orig_consts = (sched.PASSES, sched.UPDATES, sched.QA_UPDATES, sched.AUX_UPDATES)

            def validate(root_, cfg_, kind, runner):
                admitted = orig_validate(root_, cfg_, kind, runner)  # real pins and frames, 2304 schedule checked
                if kind == 'train':
                    sched.PASSES, sched.UPDATES = a.passes, total
                    sched.QA_UPDATES, sched.AUX_UPDATES = 48 * a.passes, 24 * a.passes
                    if not a.overfit_updates:
                        admitted['schedules'] = {s: sched.pilot_schedule(s) for s in (0, 1)}
                    else:
                        recs = [{'update': n + 1, 'task_role': 'QA', 'control_frame_index': OVER[n % len(OVER)],
                                 'treatment_frame_index': OVER[n % len(OVER)]} for n in range(total)]
                        admitted['schedules'] = {0: recs, 1: recs}
                return admitted
            runtime.validate_native_config = validate
            trainer.TOTAL = total
            trainer.RUN_ORDER = tuple((s, r) for s in seeds for r in arms)
            step_state = {'opt': None, 'n': 0}
            orig_step = trainer.train_step

            def step(rt, ctx, modules, named, opt, frame_index, participation, nonzero):
                if step_state['opt'] is not opt:
                    step_state['opt'], step_state['n'] = opt, 0
                step_state['n'] += 1
                lr = runtime.ADAM_RECIPE['lr'] * a.lr_mult
                if a.warmup:
                    lr *= min(1.0, step_state['n'] / a.warmup)
                for g in opt.param_groups:
                    g['lr'] = lr
                return orig_step(rt, ctx, modules, named, opt, frame_index, participation, nonzero)
            trainer.train_step = step
            if a.aux_weight:
                aux_box = {}
                orig_graph, orig_loss = runtime.english_graph, runtime.english_loss

                def graph(rt, core, reader, features, mask):
                    h, aux = orig_graph(rt, core, reader, features, mask)
                    aux_box['aux'] = aux
                    return h, aux

                def loss_fn(rt, lm, dec, h, mask, target):
                    per, prediction, stats = orig_loss(rt, lm, dec, h, mask, target)
                    return per + a.aux_weight * aux_box['aux'], prediction, stats
                runtime.english_graph, runtime.english_loss = graph, loss_fn
            targs = argparse.Namespace(root=str(root), config=str(tpath), config_sha256=tsha, require_owned_stdin=True,
                                       check=False, resume=False, segment_updates=None)
            sys.stdin = io.StringIO(trainer.GO_LINE)
            rc = trainer.run(targs)
            print(json.dumps({'event': 'sweep-train-done', 'tag': a.tag, 'rc': rc}), flush=True)
            import subprocess
            if a.phase == 'both':
                subprocess.run([sys.executable, '-B', __file__] + [x for x in sys.argv[1:] if x != 'both'] + ['--phase', 'eval'], check=True)
        if a.phase == 'both':
            return
        # ---- train-fit eval (TRAIN panel only)
        ecfg = json.loads((root / EXP / 'EVAL-CONFIG-v1.json').read_text())
        states = []
        ce = {}
        for s in seeds:
            for r in arms:
                closed = json.loads((root / base / 'train' / ('seed%d' % s) / r / 'CLOSED.json').read_text())
                ce[(s, r)] = closed['final_CE_last_pass_mean']
                states.append({'state_id': 'seed%d-%s' % (s, r), 'seed': s, 'arm': r,
                               'checkpoint': {'path': base + '/train/seed%d/%s/final-checkpoint.pt' % (s, r),
                                              'sha256': closed['checkpoint']['sha256']}})
        ecfg['states'] = states
        ecfg['output_namespace'] = base + '/eval'
        epath = root / base / 'EVAL-CONFIG.json'
        esha = write_cfg(epath, ecfg)
        ev.ENDPOINT_UPDATE = total
        ev.validate_eval_states = lambda cfg: cfg['states']
        ev.load_fresh_inputs = lambda path: ([], 'empty-train-only-sweep')
        eargs = argparse.Namespace(root=str(root), config=str(epath), config_sha256=esha, require_owned_stdin=True,
                                   check=False)
        sys.stdin = io.StringIO(ev.GO_LINE)
        ev.run(eargs)
        bank = common.read_json(root / ecfg['bank']['path'])
        out = {'tag': a.tag, 'lr_mult': a.lr_mult, 'passes': a.passes, 'warmup': a.warmup, 'updates': total, 'runs': {}}
        for st in states:
            rows = [json.loads(l) for l in (root / base / 'eval' / ('RAW-%s.jsonl' % st['state_id'])).read_text().splitlines()]
            fit = scorer.score_train_fit(rows, bank)
            out['runs'][st['state_id']] = {'train_fit': fit['correct'], 'final_CE': ce[(st['seed'], st['arm'])]}
            if a.overfit_updates:
                ex = bank['examples']
                ok = 0
                for r in rows:
                    if r['panel'] == 'TRAIN' and r['frame_index'] in OVER:
                        pp, qq = divmod(r['frame_index'], 4)
                        qu = ex[pp]['questions'][qq]
                        ok += scorer.is_correct(r['output_text'], qu['canonical_answer'], qu.get('accepted_answers', []))
                out['runs'][st['state_id']]['fit_on_the_trained_items'] = ok
        (root / base / 'SWEEP-RESULT.json').write_text(json.dumps(out, indent=1))
        print('SWEEP-RESULT ' + json.dumps(out), flush=True)
    finally:
        try:
            BUSY.unlink()
        except OSError:
            pass


if __name__ == '__main__':
    main()

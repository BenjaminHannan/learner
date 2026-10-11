"""Full domain-mode run with protected whole-model nights (main-brain thread).

  python -m mainbrain.fullrun --constants CONST.json --parent CKPT --tool sheet|rpn --out DIR --seed N [--threads 4]

Runs domain/mode.py's main loop unchanged (practice, tries, quiz, check, undo, stop), with two substitutions:
- the constants file is CONST.json (a v4-style whole-model file plus `protect` and `protect_energy`);
- before each night the model re-measures what its old answers use, on its current weights and its diary, and that
  night's optimizer steps are projected (mainbrain/kf.py or gp.py). Unprojectable parameters stay frozen.
The log gets one 'protect' line per night (written to stdout; mode's log.jsonl is untouched in format).
"""
import json
import sys
import time

from domain import mode
from mainbrain import gp, guess, kf


def install(cons_path, out=None, seed=None):
    cons = json.load(open(cons_path))
    method, energy = cons['protect'], cons['protect_energy']
    pg = cons.get('protect_g', 'empirical')
    assert pg in ('empirical', 'example'), pg
    assert method in ('kf', 'gp') and 0 < energy < 1, (method, energy)
    assert not cons.get('addon'), 'protection replaces the add-on'
    mode.CONST_PATH = cons_path
    if 'guess' in cons:   # SB-2 head: installed first, so it is the inner train_night/make_opt (K-FAC is measured on the plain loss)
        guess.install(out, cons['guess']['weight'], cons['guess']['lr'], seed)
    base_train, base_make = mode.train_night, mode.make_opt

    def train_night(m, new, diary, updates, cons, seed, fresh=False, picks=None, addon=None):
        t = time.time()
        for p in m.parameters():
            p.requires_grad_(True)
        if method == 'kf':
            F, info = kf.factors(kf.kfac_stats(m, diary, norm='example' if pg == 'example' else None), energy)
            wrap = lambda mm, base: kf.KFOptimizer(mm, base, F)
        else:
            P, info = gp.projectors(gp.covariances(m, diary), energy)
            wrap = lambda mm, base: gp.GPOptimizer(mm, base, P)
        frozen = gp.freeze_unprojected(m)
        mode.make_opt = lambda mm, lr: wrap(mm, base_make(mm, lr))
        extra = dict(g=pg) if 'protect_g' in cons else {}
        print('protect', json.dumps(dict(method=method, energy=energy, **extra, seed=seed, frozen=len(frozen), secs=round(time.time() - t, 1),
                                         free_share={n: v.get('free_share', v.get('free')) for n, v in info.items()})), flush=True)
        try:
            return base_train(m, new, diary, updates, cons, seed, fresh=fresh, picks=picks, addon=addon)
        finally:
            mode.make_opt = base_make
            for p in m.parameters():
                p.requires_grad_(True)

    mode.train_night = train_night


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    i = argv.index('--constants')
    cons_path = argv[i + 1]
    del argv[i:i + 2]
    install(cons_path, out=argv[argv.index('--out') + 1], seed=int(argv[argv.index('--seed') + 1]))
    mode.main(argv)


if __name__ == '__main__':
    main()

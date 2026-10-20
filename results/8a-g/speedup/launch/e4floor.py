"""e4floor.py: GPU-RUN-5 (PREREG-gpu-run-5.md, per the coordinator's ruling of 10-20): six fresh 300-update loss traces of B3G2 in the order B, D, B, D, B, D (B = baseline, D = defer),
the same seed, the same rows, the same pinned stochastic parts, each built exactly as prof_train's own E4 (loss_curves) builds its traces: Trainer(world, args, names, batch_seed=args.seed),
pin_stochastic(tr, K0) with K0 = rounds_needed(world, [the first batch of args.seed]), the job's real lr schedule (--curve-schedule real), one float loss per update, then close + cleanup.
It decides nothing: gpu_run_5_marks.py reads the json. Every prof_train argument is accepted (the parser is prof_train's own); --curve-updates sets the trace length (300 on the box).

  python e4floor.py --arm B3G2 --rung 3M --accum 4 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json --curve-updates 300 --out out/gr5_e4floor.json

Output: {meta, order, K0, traces: [{label, kind B|D, names, losses[300], t_start, t_end, started_utc, ended_utc, wall_s}], schedule, curve_updates}, rewritten after every trace
(a partial file still holds the finished traces), plus <out>.launch.json (host, CPU model, torch/CUDA versions) from prof_launch."""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prof_launch as pl                                                     # noqa: E402  (registers same / defer / kvcat / fastteach; --deterministic is handled there)

prof = pl.prof
ORDER = ('B', 'D', 'B', 'D', 'B', 'D')
NAMES = dict(B=[], D=['defer'])


def trace(world, args, names, k0):
    """One E4 trace, prof_train.loss_curves's recipe for one label (no cache)."""
    tr = prof.Trainer(world, args, list(names), batch_seed=args.seed)
    restore = prof.pin_stochastic(tr, k0) if k0 else (lambda: None)
    if args.curve_schedule == 'short':
        tr.lr_steps, tr.lr_warmup = args.curve_updates, max(1, args.curve_updates // 5)
    try:
        ls = []
        for i in range(args.curve_updates):
            loss, _, _ = tr.update()
            ls.append(float(loss))
            if (i + 1) % 50 == 0:
                prof.log(f'  e4floor {",".join(names) or "baseline"}: update {i + 1}/{args.curve_updates} loss {ls[-1]:.5f}')
        stats = tr.variant_stats() if hasattr(tr, 'variant_stats') else None
        return ls, stats
    finally:
        restore(); tr.close(); prof.cleanup(world.device)


def main(argv=None):
    names = pl.register_all()
    a = prof.build_parser().parse_args(argv)
    a.accum = a.accum or prof.ARM_INFO[a.arm]['accum']
    if a.equiv_pin == 0:
        raise SystemExit('e4floor: the ruling fixes the pinned stochastic parts; --equiv-pin 0 is refused')
    prof.load_pkg(a.pkg_root)
    world = prof.World(a)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    info = pl.host_info()
    json.dump(info, open(os.path.splitext(a.out)[0] + '.launch.json', 'w'), indent=1)
    first = next(world.batches(a.seed))
    k0 = prof.rounds_needed(world, [first])
    res = dict(meta=world.meta(), registered=names, order=list(ORDER), K0=k0, curve_updates=a.curve_updates, schedule=a.curve_schedule, seed=a.seed, traces=[],
               note='six fresh traces B,D,B,D,B,D (B baseline, D defer); same seed, rows and pinned stochastic parts; prof_train loss_curves recipe per trace; nothing is cached or reused')
    prof.log(f'e4floor: K0={k0}, {a.curve_updates} updates per trace, order {"".join(ORDER)}, schedule {a.curve_schedule}')
    for i, kind in enumerate(ORDER):
        t0 = time.time()
        prof.log(f'e4floor trace {i + 1}/6 ({kind}: {",".join(NAMES[kind]) or "baseline"}) start')
        ls, stats = trace(world, a, NAMES[kind], k0)
        t1 = time.time()
        res['traces'].append(dict(label=f'{kind}{i // 2 + 1}', kind=kind, names=NAMES[kind], losses=ls, t_start=t0, t_end=t1, started_utc=pl._utc(t0), ended_utc=pl._utc(t1),
                                  wall_s=round(t1 - t0, 1), variant_stats=stats))
        prof.log(f'e4floor trace {i + 1}/6 ({kind}) end: {t1 - t0:.0f} s, loss at update {len(ls)} {ls[-1]:.5f}')
        res['meta']['finished'] = pl._utc(time.time())
        json.dump(res, open(a.out, 'w'), indent=1, default=str)
    info['ended_utc'] = pl._utc(time.time())
    json.dump(info, open(os.path.splitext(a.out)[0] + '.launch.json', 'w'), indent=1)
    prof.log(f'e4floor done: {a.out}')
    return res


if __name__ == '__main__':
    main()

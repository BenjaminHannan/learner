"""DEV-only pilot of C1 (roadmap D7): warm-up, floors, gates, aim check and the PC learning-rate choice on ONE parent. No T1 / T1b / X is read.
Steps: (0) raw parent: gates + aim check; (1) shared warm-up on 2-number solver puzzles (+ skills replay if given); (2) warmed parent: DEV temperature,
signal and sameness gates, aim check, rules-only floors; (3) PC arm only: sleep on solver programs for practice puzzles over a (lr, updates) grid,
read DEV luck / reach@4 / aim after each, pick the best. Writes out_dir/pilot.json (+ warmed.pt). Without --skills-train there is no replay, so warm-up
harm on skills is NOT measured (reported as no_replay)."""
import copy, json, os, random, time
from creative import arms, puzzles, sampler, scoreboard, sleep


def dev_report(model, vocab, dev, practice, device, tries, temps):
    best, grid = scoreboard.tune_temperature(model, dev, vocab, device, temps, tries)
    tr, raw = sampler.sample_tries(model, dev, vocab, device, tries, best)
    nb, _ = sampler.sample_tries(model, dev, vocab, device, tries, best, branch=0)
    ptr, _ = sampler.sample_tries(model, practice, vocab, device, tries, best)
    gate = scoreboard.dev_gate(dev, tr, raw, nb, (practice, ptr))
    sc = scoreboard.score_puzzles(dev, tr, raw, sampler.greedy_tries(model, dev, vocab, device))
    sc.pop('per_puzzle')
    return dict(temperature=best, temp_grid={str(k): v for k, v in grid.items()}, gate=gate, scoreboard=sc,
                aim=scoreboard.aim_check(model, dev, vocab, device, tries, best))


def pilot(ckpt, out_dir, data, device='cpu', skills_train=None, replay_n=4000, warm_n=1500, warm_updates=200, warm_lr=3e-4,
          lrs=(1e-4, 3e-4, 1e-3), pc_updates=(120,), pc_per_puzzle=2, pc_puzzles=1024, tries=32, practice_limit=None, batch=64,
          temps=(0.7, 1.0, 1.3, 1.6, 2.0), seed=0, log=print, reuse_warmed=False):
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    res = dict(ckpt=ckpt, seed=seed, no_replay=skills_train is None)
    save = lambda: json.dump(res, open(os.path.join(out_dir, 'pilot.json'), 'w'), indent=1)
    model, vocab, meta = sleep.load_parent(ckpt, device)
    model.eval()
    dev = puzzles.load_split(data, 'dev')
    practice = puzzles.load_split(data, 'practice')[:practice_limit]
    res['floors'] = dict(rules_only_per_try=sum(puzzles.rules_only_floor(r['nums'], r['target']) for r in dev) / len(dev))
    replay = sleep.load_replay(skills_train, replay_n, seed) if skills_train else []
    warmed_path = os.path.join(out_dir, 'warmed.pt')
    if reuse_warmed and os.path.exists(warmed_path):
        model, vocab, meta = sleep.load_parent(warmed_path, device)
        model.eval()
        res['reused_warmed'] = warmed_path
    else:
        log(dict(event='raw parent'))
        res['raw'] = dev_report(model, vocab, dev, practice, device, tries, temps)
        save()
        log(dict(event='raw done', gate=res['raw']['gate']['verdict'], t=round(time.time() - t0)))
        wu = [arms.record(r, t, 'WU', 0) for r, t in puzzles.warmup_rows(warm_n, seed, per_pair=3)]
        cfg = sleep.SleepCfg(updates=warm_updates, batch=batch, lr=warm_lr, warmup=20, seed=seed,
                             max_visits=max(4, -(-warm_updates * (batch // 2 if replay else batch) // warm_n)))
        out = sleep.sleep(model, wu, replay, vocab, cfg, device, log=log)
        res['warmup'] = dict(n_records=len(wu), updates=out['updates'], loss_first=sum(out['loss'][:10]) / 10, loss_last=sum(out['loss'][-10:]) / 10,
                             max_visits=cfg.max_visits, replay_rows=len(replay))
        sleep.save_parent(model, meta['name'], meta['cfg'], vocab, warmed_path, step=(meta['step'] or 0) + warm_updates, warmup=True)
        model.eval()
        log(dict(event='warm-up done', **res['warmup'], t=round(time.time() - t0)))
    res['warmed'] = dev_report(model, vocab, dev, practice, device, tries, temps)
    save()
    log(dict(event='warmed done', gate=res['warmed']['gate']['verdict'], t=round(time.time() - t0)))

    rng = random.Random(seed)
    rows = puzzles.load_split(data, 'practice')[:pc_puzzles]          # the full practice split, whatever practice_limit says
    pc = [arms.record(r, t, 'PC', k) for r in rows for k, t in enumerate(puzzles.solver_records(r, pc_per_puzzle, rng))]
    res['pc_grid'], temp = [], res['warmed']['temperature']
    for upd in pc_updates:
        cap = sleep.max_updates(len(pc), batch, bool(replay), 4)
        upd = min(upd, cap)                                           # the 4-visit cap, whatever the grid asked for
        for lr in lrs:
            m = copy.deepcopy(model)
            c = sleep.SleepCfg(updates=upd, batch=batch, lr=lr, warmup=20, seed=seed)
            so = sleep.sleep(m, pc, replay, vocab, c, device)
            m.eval()
            tr, raw = sampler.sample_tries(m, dev, vocab, device, tries, temp)
            sc = scoreboard.score_puzzles(dev, tr, raw, sampler.greedy_tries(m, dev, vocab, device))
            aim = scoreboard.aim_check(m, dev, vocab, device, tries, temp)
            row = dict(updates=upd, lr=lr, n_records=len(pc), dev_luck=sc['luck'], dev_reach4=sc['reach4'], dev_reach32=sc['reach32'],
                       dev_first_try=sc['first_try'], dev_aim=sc['aim'], own_minus_rules_luck=aim['own_minus_rules_luck'],
                       loss_last=sum(so['loss'][-10:]) / 10)
            res['pc_grid'].append(row)
            save()
            log(dict(event='pc', **row, t=round(time.time() - t0)))
    best = max(res['pc_grid'], key=lambda r: (r['dev_luck'], r['dev_reach4']))
    res['pc_choice'] = dict(lr=best['lr'], updates=best['updates'], note='chosen on DEV with the PC arm only; freeze before any T1 run')
    res['wall_s'] = time.time() - t0
    json.dump(res, open(os.path.join(out_dir, 'pilot.json'), 'w'), indent=1)
    return res

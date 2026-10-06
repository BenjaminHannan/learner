"""DEV-only pilot of C1 (roadmap D7, as decided 10-06): one parent. Reads no T1 / T1b / X.
  0. raw parent: skills score (warm-up harm baseline).
  1. warm-up LADDER: every rung = the 1,500 two-number puzzles + N three-number solver puzzles (decided 10-06: N = 1,500 only; 3,000 / 6,000 are comparison runs; number sets in no sealed split),
     every record seen at most 4 times, skills replay on when given.
     Fallbacks (off unless --fallbacks) if the last rung fails (roadmap 10-06): (a) if the warmed parent does not reproduce its own warm-up puzzles (greedy < FIT_MIN = 0.9, a threshold chosen by the build thread), repeat the last rung with up to
     16 visits per warm-up record (the 4-visit cap is for sleep records only); (b) if it fits but still fails DEV, add `dreams` (random rule-following 3-number
     programs labelled with the value they make, on number sets in no sealed split); (c) otherwise stop and report. Hindsight relabelling is NOT a warm-up (arm H). After each rung: re-choose the temperature on DEV (highest reach@4 among temperatures
     passing sameness; widen on a grid edge), run the signal + aim + sameness gates at that temperature (rules share is reported, never gated). The smallest rung that passes wins; if
     none does the pilot stops and says so (C1 stops with T1 sealed).
  2. warmed parent: headroom (DEV luck, first try), skills score and harm against raw, aim check, floors.
  3. PC arm only (solver programs for practice puzzles, <= 2 per puzzle, skills replay on): lr grid with the edge rule (widen x3 on an edge, <= 2 times),
     update count at the 4-visit cap. At the re-chosen temperature: PC - N luck (gate: PC / N >= 1.6 and PC - N >= +3 points), PC's first-try gain, skills harm.
Writes out_dir/pilot.json after every stage (and warmed.pt). Without --skills-train there is no replay: flagged `no_replay`, harm unmeasured."""
import copy, json, os, random, time
from creative import arms, marks, puzzles, sampler, scoreboard, sleep
from custom_io.data import load_rows
from custom_io.evalx import CHAIN5, evaluate

LADDER = (1500,)       # decided 10-06: --warm3 1500 with max_visits 4 on both parents; 6,000 and 6,000 @ 16 visits are comparison runs only
FIT_MIN = 0.9          # fallback (a)/(b) fork: warmed parent 'fits' its own warm-up puzzles at greedy >= 0.9. Chosen by the build thread (Sonnet), not in the spec.
NOTES = ('Gates rewritten 10-06 AFTER seeing DEV numbers from the second pilot (feasibility check, not a claim): signal = accepted try on >= 100 practice puzzles; '
         'aim = luck / rules_share >= 0.082 (2x the value-blind follower); sameness >= 4; rules_share reported, never gated. Marks re-scaled to ratio + guard '
         '(L1 1.6x and +3, L2 1.4x and +2.5, G0 1.5x and +3, PC 1.6x and +3). PC gave +2 points on the first (failed) warm-up and that was known when the marks '
         'were re-scaled. T1 and T1b stay sealed.')
LRS = (3e-4, 1e-3, 3e-3, 1e-2)
TEMPS = (0.7, 1.0, 1.5, 2.0)


def skills_eval(model, skills_data, device, bs=128):
    """Practised skills: exact % on the five chain families (pooled-5) of skills_data/dev/in_dist.jsonl, plus all of in_dist. None without data."""
    if not skills_data:
        return None
    rows = load_rows(os.path.join(skills_data, 'dev', 'in_dist.jsonl'))
    was = model.training
    model.eval()
    r5 = evaluate(model, [r for r in rows if r['family'] in CHAIN5], bs, device)
    ra = evaluate(model, rows, bs, device)
    model.train(was)
    return dict(pooled5=r5['exact'] / 100, n5=r5['n'], in_dist=ra['exact'] / 100, n_in_dist=ra['n'])


def scored(model, dev, vocab, device, T, tries):
    tr, raw = sampler.sample_tries(model, dev, vocab, device, tries, T)
    s = scoreboard.score_puzzles(dev, tr, raw, sampler.greedy_tries(model, dev, vocab, device))
    s.pop('per_puzzle')
    return s, tr, raw


def pilot(ckpt, out_dir, data, device='cpu', skills_train=None, skills_data=None, replay_n=None, ladder=LADDER, warm_n=1500, warm_lr=3e-4,
          lrs=LRS, pc_per_puzzle=2, tries=32, practice_limit=None, batch=64, temps=TEMPS, seed=0, log=print, fallbacks=False, dreams_n=3000):
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    res = dict(ckpt=ckpt, seed=seed, no_replay=skills_train is None, notes=NOTES, ladder_rungs=[])
    save = lambda: json.dump(res, open(os.path.join(out_dir, 'pilot.json'), 'w'), indent=1)
    raw_model, vocab, meta = sleep.load_parent(ckpt, device)
    raw_model.eval()
    dev = puzzles.load_split(data, 'dev')
    practice_all = puzzles.load_split(data, 'practice')
    practice = practice_all[:practice_limit]
    res['floors'] = dict(rules_only_per_try=sum(puzzles.rules_only_floor(r['nums'], r['target']) for r in dev) / len(dev))
    replay = sleep.load_replay(skills_train, replay_n, seed) if skills_train else []
    res['replay_rows'] = len(replay)
    res['skills_raw'] = skills_eval(raw_model, skills_data, device)
    save()
    log(dict(event='raw skills', skills=res['skills_raw'], t=round(time.time() - t0)))

    def rung_run(N, dreams=0, visits=4, tag=''):
        """One warm-up rung: 1,500 two-number puzzles + N three-number solver puzzles (+ dreams); <= `visits` visits per record. Returns (model, rung)."""
        m = copy.deepcopy(raw_model)
        wu = [arms.record(r, t, 'WU', 0) for r, t in puzzles.warmup_rows(warm_n, seed, per_pair=3)]
        wu += [arms.record(r, t, 'WU3', 0) for r, t in puzzles.warmup3_rows(N, seed)]
        wu += [arms.record(r, t, 'DREAM', 0) for r, t in puzzles.dream_rows(dreams, seed)] if dreams else []
        updates = sleep.max_updates(len(wu), batch, bool(replay), visits)
        cfg = sleep.SleepCfg(updates=updates, batch=batch, lr=warm_lr, warmup=20, seed=seed, max_visits=visits)
        out = sleep.sleep(m, wu, replay, vocab, cfg, device, log=log)
        m.eval()
        T = scoreboard.choose_temperature(m, dev, vocab, device, temps, tries, seed, log=log)
        rung = dict(warm3=N, dreams=dreams, max_visits=visits, tag=tag, n_records=len(wu), updates=out['updates'],
                    loss_last=sum(out['loss'][-10:]) / 10, temperature=T)
        if T['best'] is None:
            rung['gate'] = 'no temperature passes the sameness gate'
        else:
            tr, raw = sampler.sample_tries(m, dev, vocab, device, tries, T['best'])
            nb, _ = sampler.sample_tries(m, dev, vocab, device, tries, T['best'], branch=0)
            ptr, _ = sampler.sample_tries(m, practice, vocab, device, tries, T['best'])
            rung['gate'] = scoreboard.dev_gate(dev, tr, raw, nb, (practice, ptr))
        res['ladder_rungs'].append(rung)
        save()
        g = rung['gate']
        log(dict(event='rung', warm3=N, dreams=dreams, visits=visits, verdict=g if isinstance(g, str) else g['verdict'], t=round(time.time() - t0)))
        return m, rung

    def passes(rung):
        return not isinstance(rung['gate'], str) and rung['gate']['signal_ok'] and rung['gate']['aim_ok']

    def fits_own_warmup(m, n=256):
        """Fallback (a): does the warmed parent reproduce its own warm-up puzzles? Greedy first try on a sample of the 3-number warm-up puzzles (T from the pilot, not used)."""
        w = [r for r, _ in puzzles.warmup3_rows(max(ladder), seed)][:n]
        gr = sampler.greedy_tries(m, w, vocab, device)
        return sum(scoreboard.judge_try(r, g) == 'accept' for r, g in zip(w, gr)) / len(w)

    warmed, chosen = None, None
    for N in ladder:
        m, rung = rung_run(N)
        if passes(rung):
            warmed, chosen = m, rung
            break
    if warmed is None and fallbacks:
        fit = fits_own_warmup(m)                                   # m = the last rung's model (N = ladder[-1])
        res['fallback_a_fit_own_warmup_greedy'] = fit
        save()
        log(dict(event='fallback a: fit on own warm-up puzzles', greedy_accepted=fit))
        if fit < FIT_MIN:                                          # (a) it does not fit: up to 16 visits per warm-up record
            m, rung = rung_run(ladder[-1], 0, 16, 'fallback a: 16 visits')
            if passes(rung):
                warmed, chosen = m, rung
            else:
                fit = fits_own_warmup(m)
                res['fallback_a_fit_after_16_visits'] = fit
        if warmed is None and fit >= FIT_MIN:                      # (b) it fits but fails DEV: dreams
            m, rung = rung_run(ladder[-1], dreams_n, 4, 'fallback b: dreams')
            if passes(rung):
                warmed, chosen = m, rung
    if warmed is None:
        ran = [x['tag'] for x in res['ladder_rungs'] if x['tag']]
        res['result'] = ('LADDER FAILED: no rung passed the gates (fallbacks run: %s); C1 stops with T1 sealed. Send the numbers to the coordinator.' % (', '.join(ran) or 'none'))
        res['wall_s'] = time.time() - t0
        save()
        return res
    N, T = chosen['warm3'], chosen['temperature']['best']
    sleep.save_parent(warmed, meta['name'], meta['cfg'], vocab, os.path.join(out_dir, 'warmed.pt'), step=(meta['step'] or 0) + chosen['updates'], warmup=True, warm3=N)
    s0, _, _ = scored(warmed, dev, vocab, device, T, tries)
    res['warmed'] = dict(warm3=N, temperature=T, gate=chosen['gate'], headroom=dict(dev_luck=s0['luck'], dev_first_try=s0['first_try'], dev_reach4=s0['reach4']),
                         scoreboard=s0, aim=scoreboard.aim_check(warmed, dev, vocab, device, tries, T), skills=skills_eval(warmed, skills_data, device))
    if res['skills_raw'] and res['warmed']['skills']:
        res['warmed']['harm_pooled5_points'] = 100 * (res['skills_raw']['pooled5'] - res['warmed']['skills']['pooled5'])
    save()
    log(dict(event='warmed', warm3=N, T=T, **res['warmed']['headroom'], t=round(time.time() - t0)))

    rng = random.Random(seed)
    pc = [arms.record(r, t, 'PC', k) for r in practice_all for k, t in enumerate(puzzles.solver_records(r, pc_per_puzzle, rng))]
    upd = sleep.max_updates(len(pc), batch, bool(replay), 4)
    grid, rows_, widen = list(lrs), {}, 0

    def run_lr(lr):
        if lr in rows_:
            return
        m = copy.deepcopy(warmed)
        so = sleep.sleep(m, pc, replay, vocab, sleep.SleepCfg(updates=upd, batch=batch, lr=lr, warmup=20, seed=seed), device)
        m.eval()
        sc, _, _ = scored(m, dev, vocab, device, T, tries)
        rows_[lr] = dict(lr=lr, updates=upd, n_records=len(pc), dev_luck=sc['luck'], dev_reach4=sc['reach4'], dev_reach32=sc['reach32'],
                         dev_first_try=sc['first_try'], dev_aim=sc['aim'], luck_gain=100 * (sc['luck'] - s0['luck']), first_try_gain=100 * (sc['first_try'] - s0['first_try']),
                         loss_last=sum(so['loss'][-10:]) / 10, skills=skills_eval(m, skills_data, device))
        res['pc_grid'] = [rows_[k] for k in sorted(rows_)]
        save()
        log(dict(event='pc', **{k: v for k, v in rows_[lr].items() if k != 'skills'}, t=round(time.time() - t0)))

    for lr in grid:
        run_lr(lr)
    while widen < 2:
        best = max(rows_, key=lambda k: (rows_[k]['dev_luck'], rows_[k]['dev_reach4']))
        if best not in (min(rows_), max(rows_)):
            break
        widen += 1
        run_lr(best * 3 if best == max(rows_) else best / 3)
    best = max(rows_, key=lambda k: (rows_[k]['dev_luck'], rows_[k]['dev_reach4']))
    b = rows_[best]
    res['pc_choice'] = dict(lr=best, updates=upd, widened=widen, on_edge=best in (min(rows_), max(rows_)),
                            note='chosen on DEV with the PC arm only; freeze before any T1 run')
    pc_over_n = b['dev_luck'] / s0['luck'] if s0['luck'] > 0 else (float('inf') if b['dev_luck'] > 0 else 0.0)
    res['pc_gate'] = dict(pc_minus_n_luck_points=b['luck_gain'], pc_over_n_luck=pc_over_n, first_try_gain_points=b['first_try_gain'], needed_points=3.0, needed_ratio=1.6,
                          passes=marks.pc_gate(b['luck_gain'], pc_over_n), temperature=T, with_replay=bool(replay))
    if res['skills_raw'] and b['skills']:
        res['pc_gate']['harm_pooled5_points_vs_warmed'] = 100 * (res['warmed']['skills']['pooled5'] - b['skills']['pooled5']) if res['warmed']['skills'] else None
    res['wall_s'] = time.time() - t0
    save()
    log(dict(event='done', pc_gate=res['pc_gate'], wall_s=round(res['wall_s'])))
    return res

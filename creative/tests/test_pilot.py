"""python3 -m creative.tests.test_pilot   (CPU, about a minute; tiny random B2, synthetic skills data)
The pilot's control flow: ladder, fallbacks a and b, re-chosen temperature with the edge rule, PC lr edge rule, PC gate, warm-up harm."""
import json, os, tempfile
import torch
from custom_io.data import CharVocab
from custom_io.models.ledger import Ledger
from creative import pilot, puzzles, scoreboard, sleep

SMALL = dict(copy=True, d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)


def setup(d):
    v = CharVocab.build([])
    torch.manual_seed(0)
    ck = os.path.join(d, 'tiny.pt')
    sleep.save_parent(Ledger(v, **SMALL), 'ledger', SMALL, v, ck)
    data = os.path.join(d, 'skills')
    os.makedirs(os.path.join(data, 'dev'))
    rows = [dict(id=f'sk{i}', prompt=f'Ida has {10 + i} keys, loses 3, picks up {i}. end?', answer=str(7 + 2 * i), accepted=[str(7 + 2 * i)], family='chain_ops',
                 level=6, stage=6, variant='', steps=[f'{10 + i} - 3 = {7 + i}', f'{7 + i} + {i} = {7 + 2 * i}']) for i in range(1, 40)]
    for name in ('train.jsonl', os.path.join('dev', 'in_dist.jsonl')):
        with open(os.path.join(data, name), 'w') as f:
            f.write('\n'.join(json.dumps(r) for r in rows) + '\n')
    return ck, data


def test_default_is_one_rung_without_fallbacks():
    import inspect
    sig = inspect.signature(pilot.pilot)
    assert sig.parameters['ladder'].default == (1500,) and sig.parameters['fallbacks'].default is False
    print('ok default_is_one_rung_without_fallbacks')


def test_ladder_fails_and_fallbacks_run():
    with tempfile.TemporaryDirectory() as d:
        ck, data = setup(d)
        out = os.path.join(d, 'out')
        r = pilot.pilot(ck, out, os.path.join('creative', 'data', 'c1'), skills_train=os.path.join(data, 'train.jsonl'), skills_data=data, ladder=(32, 64),
                        warm_n=32, tries=4, practice_limit=24, batch=16, temps=(1.0,), dreams_n=32, fallbacks=True, log=lambda x: None)
        assert r['result'].startswith('LADDER FAILED') and not r['no_replay'] and r['replay_rows'] == 39
        tags = [x['tag'] for x in r['ladder_rungs']]
        assert [x['warm3'] for x in r['ladder_rungs'][:2]] == [32, 64] and 'fallback_a_fit_own_warmup_greedy' in r
        assert any('fallback a' in t for t in tags) or any('fallback b' in t for t in tags), tags
        assert r['skills_raw']['pooled5'] >= 0 and json.load(open(os.path.join(out, 'pilot.json')))['result'] == r['result']
    print('ok ladder_fails_and_fallbacks_run')


def test_pc_stage_with_forced_gate():
    """Force the signal gate and the temperature so the PC stage runs: lr grid with the edge rule, the PC gate, harm vs the warmed parent."""
    real_gate, real_temp = scoreboard.dev_gate, scoreboard.choose_temperature
    scoreboard.dev_gate = lambda *a, **k: dict(real_gate(*a, **k), signal_ok=True, aim_ok=True, verdict='pass')
    scoreboard.choose_temperature = lambda *a, **k: dict(best=1.0, evaluated={}, widened=0, edge_note=None)
    try:
        with tempfile.TemporaryDirectory() as d:
            ck, data = setup(d)
            out = os.path.join(d, 'out')
            r = pilot.pilot(ck, out, os.path.join('creative', 'data', 'c1'), skills_train=os.path.join(data, 'train.jsonl'), skills_data=data, ladder=(32,),
                            warm_n=32, lrs=(1e-3, 3e-3), visits=(1, 2), extra_visits=4, tries=4, practice_limit=24, batch=16, temps=(1.0,), log=lambda x: None)
            assert r['warmed']['warm3'] == 32 and 'headroom' in r['warmed'] and 'harm_pooled5_points' in r['warmed']
            keys = [(x['lr'], x['visits']) for x in r['pc_grid']]
            assert len(keys) >= 4 and len(set(keys)) == len(keys) and {k[0] for k in keys} >= {1e-3, 3e-3} and {k[1] for k in keys} >= {1, 2}
            assert r['pc_choice']['visits'] in (1, 2, 4) and 'dose_extended' in r['pc_choice'] and 'dose grid' in r['notes'].lower()
            assert all(x['within_skills_limit'] == (x['skills_harm_points'] is None or x['skills_harm_points'] <= pilot.SKILLS_HARM_MAX) for x in r['pc_grid'])
            assert all(set(x['loss_split_after']) == {'puzzle_rows', 'replay_rows'} and x['dev_twin_luck'] is not None and x['dev_plain_hit_given_legal'] is not None for x in r['pc_grid'])
            assert set(r['pc_n']) >= {'dev_luck', 'dev_twin_luck', 'dev_first_try', 'dev_first_try_masked', 'dev_plain_luck', 'loss_split'} and 'stop_rule' in r['pc_gate']
            assert set(r['pc_gate']) >= {'pc_minus_n_luck_points', 'pc_over_n_luck', 'first_try_gain_points', 'needed_points', 'needed_ratio', 'passes', 'with_replay'} and r['pc_gate']['with_replay']
            assert r['sampler'] == 'masked level 4' and 'used-number' in r['notes'] and r['floors']['exact_legal_per_try'] > r['floors']['rules_only_per_try']
            assert r['warmed']['headroom']['dev_first_try_masked'] is not None and r['warmed']['headroom']['dev_plain_rules_share'] is not None
            assert all(x['dev_plain_rules_share'] is not None and x['dev_first_try_masked'] is not None for x in r['pc_grid'])
            assert (r['pc_gate'].get('needed_points'), r['pc_gate'].get('needed_ratio')) == (3.0, 1.6) and 'Gates rewritten' in r['notes']
            assert all(x['updates'] == sleep.max_updates(x['n_records'], 16, True, x['visits']) for x in r['pc_grid'])
            assert (pilot.LRS, pilot.VISITS) == ((3e-4, 1e-3), (4, 8, 16))
    finally:
        scoreboard.dev_gate, scoreboard.choose_temperature = real_gate, real_temp
    print('ok pc_stage_with_forced_gate')


def test_pc_stop_when_no_setting_within_skills_limit():
    real_gate, real_temp, real_max = scoreboard.dev_gate, scoreboard.choose_temperature, pilot.SKILLS_HARM_MAX
    scoreboard.dev_gate = lambda *a, **k: dict(real_gate(*a, **k), signal_ok=True, aim_ok=True, verdict='pass')
    scoreboard.choose_temperature = lambda *a, **k: dict(best=1.0, evaluated={}, widened=0, edge_note=None)
    pilot.SKILLS_HARM_MAX = -1e9
    try:
        with tempfile.TemporaryDirectory() as d:
            ck, data = setup(d)
            r = pilot.pilot(ck, os.path.join(d, 'out'), os.path.join('creative', 'data', 'c1'), skills_train=os.path.join(data, 'train.jsonl'), skills_data=data, ladder=(32,),
                            warm_n=32, lrs=(1e-3,), visits=(1,), extra_visits=None, tries=4, practice_limit=24, batch=16, temps=(1.0,), log=lambda x: None)
            assert r['pc_gate']['passes'] is False and 'skills limit' in r['pc_gate']['reason'] and 'stop_rule' in r['pc_gate'] and len(r['pc_grid']) == 1
    finally:
        scoreboard.dev_gate, scoreboard.choose_temperature, pilot.SKILLS_HARM_MAX = real_gate, real_temp, real_max
    print('ok pc_stop_when_no_setting_within_skills_limit')


def test_temperature_rule():
    import creative.sampler as S
    calls = []

    def fake(model, rows, vocab, device, n_tries=32, temperature=1.0, seed=0, **k):
        calls.append(temperature)
        return [[] for _ in rows], [0] * len(rows)
    real_s, real_score = S.sample_tries, scoreboard.score_puzzles
    # reach@4 peaks at 2.25 but only grid points count; sameness holds only for T >= 1.0
    f = lambda T: dict(reach4=max(0.0, 0.1 - abs(T - 2.25) * 0.01), reach32=0.5, distinct_rules=5.0 if T >= 1.0 else 3.0, rules_share=0.6)
    S.sample_tries = fake
    scoreboard.score_puzzles = lambda rows, tr, raw=None, greedy=None: f(calls[-1])
    try:
        r = scoreboard.choose_temperature(None, [], None, 'cpu', grid=(0.7, 1.0, 1.5, 2.0))
    finally:
        S.sample_tries, scoreboard.score_puzzles = real_s, real_score
    assert r['best'] == 2.0 and r['widened'] == 1 and '3.0' in r['evaluated'] and r['evaluated']['0.7']['eligible'] is False and r['edge_note'] is None, r   # 3.0 was tried, 2.0 stays best (interior)
    print('ok temperature_rule')


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()

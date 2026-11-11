"""Independent saved TRAIN-only continuation audit; no model imports or calls."""
import argparse
from collections import Counter
import datetime
import json
import math
from pathlib import Path

from recount_final import read, sha, score


def recount(root, config, original_hashes):
    cfg = read(config)
    old = read(root / cfg['source_plan']['path'])
    config_hash = sha(config)
    for name in ('source_plan', 'source_seal', 'source_release', 'source_runner'):
        pin = cfg[name]
        assert sha(root / pin['path']) == pin['sha256']
    matrix = root / cfg['output_namespace']
    source = root / cfg['input_namespace']
    assert cfg['additional_updates'] == 5120 and cfg['additional_visits'] == 20
    assert cfg['lr'] == .001 and cfg['fixed_rounds'] == 4
    preserved = {}
    for rel, digest in original_hashes.items():
        actual = sha(source / rel)
        assert actual == digest, 'original artifact changed: ' + rel
        preserved[rel] = actual
    summaries = []
    predictions = {}
    new_hashes = {}
    for entry in cfg['sources']:
        seed, arm = entry['seed'], entry['arm']
        for key in ('checkpoint', 'closed'):
            pin = entry[key]
            assert sha(root / pin['path']) == pin['sha256'], 'source pin changed'
        original_closed = read(root / entry['closed']['path'])
        frame_path = (root / entry['checkpoint']['path']).parent / 'INPUT-FRAMES.json'
        assert sha(frame_path) == original_closed['input_frames_sha256']
        frames = read(frame_path)
        byid = {f['id']: f for f in frames['rows']}
        assert set(byid) == set(old['selected_ids'])
        schedule = read(root / old['schedules'][str(seed)]['path'])
        assert sha(root / old['schedules'][str(seed)]['path']) == old['schedules'][str(seed)]['sha256']
        out = matrix / ('seed%d' % seed) / arm
        closed = read(out / 'CLOSED.json')
        resume = read(out / 'RESUME.json')
        def identity_check(record):
            assert record['seed'] == seed and record['arm'] == arm
            assert record['config_sha256'] == config_hash
            assert record['source_checkpoint_sha256'] == entry['checkpoint']['sha256']
            assert record['source_plan_sha256'] == cfg['source_plan']['sha256']
            assert record['source_runner_sha256'] == cfg['source_runner']['sha256']
            assert record['TRAIN_only'] is True and record['optimizer_reset'] is False
        identity_check(closed)
        identity_check(resume)
        assert closed['closed'] is True
        assert closed['optimizer_updates'] == 10240 and closed['additional_optimizer_updates'] == 5120
        assert closed['source_checkpoint_sha256'] == entry['checkpoint']['sha256']
        assert closed['durable_model_and_Adam_reload_equal'] is True
        assert closed['LM_unchanged'] is True
        assert closed['model_call_account'] == {'TRAIN_optimizer_teacherforcing': 5120,
                                               'TRAIN_generation': 768,
                                               'TRAIN_diagnostic_teacherforcing': 768}
        assert resume['parameter_order_matches_source'] is True
        assert resume['Adam_steps_match_source_participation'] is True
        assert resume['source_input_frames_sha256'] == original_closed['input_frames_sha256']
        visits = Counter({i: 20 for i in byid})
        train = []
        for add, line in enumerate((out / 'TRAIN-RAW.jsonl').open(encoding='utf8'), 1):
            r = json.loads(line)
            identity_check(r)
            identity = schedule[add - 1]
            visits[identity] += 1
            assert r['id'] == identity and r['additional_update'] == add and r['update'] == 5120 + add
            assert r['visit_for_row'] == visits[identity]
            f = byid[identity]
            assert r['labels'] == f['labels'] and r['label_mask'] == f['label_mask']
            assert r['input_frame_sha256'] == f['frame_sha256']
            assert r['lr'] == .001 and r['auxiliary_weight'] == 0 and r['objective'] == 'numeric-answer-CE-only'
            assert math.isfinite(r['numeric_CE']) and math.isfinite(r['preclip_norm'])
            train.append(r)
        assert len(train) == 5120 and visits == Counter({i: 40 for i in byid})
        assert closed['visits'] == dict(visits)
        diagnostics = {step: {} for step in (5888, 7680, 10240)}
        ce = {step: [] for step in diagnostics}
        eos = Counter()
        for line in (out / 'DIAGNOSTIC-RAW.jsonl').open(encoding='utf8'):
            r = json.loads(line)
            identity_check(r)
            step, identity = r['update'], r['id']
            assert step in diagnostics and identity in byid and identity not in diagnostics[step]
            target = byid[identity]['labels'][0]
            assert r['canonical_target_ids_with_EOS'] == target and r['labels'] == byid[identity]['labels']
            assert r['label_mask'] == byid[identity]['label_mask']
            correct = score(r, target)
            diagnostics[step][identity] = correct
            assert math.isfinite(r['numeric_CE'])
            ce[step].append(r['numeric_CE'])
            eos[step] += bool(r['observed_EOS'])
        snapshots = []
        for step, records in diagnostics.items():
            assert records.keys() == byid.keys()
            saved = read(out / ('TRAIN-DIAGNOSTIC-%d.json' % step))
            identity_check(saved)
            correct = sum(records.values())
            assert correct == saved['strict_correct'] and saved['rows'] == 256
            snapshots.append({'visits': step // 256, 'update': step, 'strict_correct': correct,
                              'mean_numeric_CE': sum(ce[step]) / 256, 'emitted_EOS': eos[step]})
        endpoint = snapshots[-1]['strict_correct']
        assert endpoint == closed['strict_TRAIN_correct']
        assert closed['TRAIN_marks_met'] is (endpoint >= 244)
        for name, key in (('TRAIN-RAW.jsonl', 'TRAIN_raw_sha256'), ('DIAGNOSTIC-RAW.jsonl', 'DIAGNOSTIC_raw_sha256')):
            assert sha(out / name) == closed[key]
        assert sha(root / closed['checkpoint']['path']) == closed['checkpoint']['sha256']
        for name in ('CLOSED.json', 'RESUME.json', 'TRAIN-RAW.jsonl', 'DIAGNOSTIC-RAW.jsonl', 'final-resume.pt'):
            new_hashes['seed%d/%s/%s' % (seed, arm, name)] = sha(out / name)
        summaries.append({'seed': seed, 'arm': arm, 'additional_updates_recounted': len(train),
                          'all_256_rows_40_visits': True, 'full_checkpoint_sha256': closed['checkpoint']['sha256'],
                          'checkpoint_hash_matches_CLOSED': True, 'snapshots': snapshots,
                          'strict_TRAIN_correct': endpoint, 'TRAIN_marks_met': endpoint >= 244,
                          'first_additional_update_CE': train[0]['numeric_CE'], 'last_additional_update_CE': train[-1]['numeric_CE'],
                          'preclip_norm_gt1_count': sum(r['preclip_norm'] > 1 for r in train),
                          'nonfinite_count': 0, 'wall_seconds': closed['wall_seconds'],
                          'optimizer_runtime_seconds': closed['optimizer_runtime_seconds'],
                          'model_call_account': closed['model_call_account']})
        predictions[(seed, arm)] = diagnostics[10240]
    paired = []
    for seed in (0, 1):
        counts = Counter(both_correct=0, loop_only=0, plain_only=0, neither=0)
        for identity, left in predictions[(seed, 'loop')].items():
            right = predictions[(seed, 'plain')][identity]
            counts['both_correct' if left and right else 'loop_only' if left else 'plain_only' if right else 'neither'] += 1
        paired.append({'seed': seed, **dict(counts)})
    passed = all(s['TRAIN_marks_met'] for s in summaries if s['arm'] == 'loop')
    return {'schema': 'cap256.independent-continuation40-recount.v1',
            'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'saved_record_recount_pass': True, 'model_calls_by_verifier': 0, 'optimizer_calls_by_verifier': 0,
            'both_loop_seeds_TRAIN_gate_pass': passed, 'unfamiliar_questions_reused': False,
            'matrix': summaries, 'paired_TRAIN_loop_plain': paired,
            'original_artifact_hashes_unchanged': preserved, 'new_file_sha256': new_hashes}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--original-hashes', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = recount(args.root, args.config, read(args.original_hashes))
    with args.output.open('x', encoding='utf8') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')

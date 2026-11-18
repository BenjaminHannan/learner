"""Analyze existing TRAIN-side receipts only; emit no questions/labels/token IDs."""
import argparse
from collections import Counter
import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics


def read(path): return json.loads(path.read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical(record): return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def analyze(root, strict_score):
    own = root / 'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1'
    plan = read(own / 'PLAN-v3.json'); matrix = own / plan['run_namespace']
    audit_path = root / plan['token_audit']['path']; assert sha(audit_path) == plan['token_audit']['sha256']
    audits = {a['id']: a for a in read(audit_path)['selected_rows']}
    target_path = root / plan['source']['target']['path']; assert sha(target_path) == plan['source']['target']['sha256']
    targets = {a['id']: a for a in read(target_path)['rows']}
    result = {'schema': 'cap256.saved-TRAIN-analysis.v1', 'verified_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'model_calls': 0, 'optimizer_calls': 0, 'evaluation_items_accessed': False,
              'token_audit_sha256': sha(audit_path), 'TRAIN_target_packet_sha256': sha(target_path), 'matrix': []}
    for seed, arm in ((0, 'loop'), (0, 'plain'), (1, 'loop'), (1, 'plain')):
        out = matrix / ('seed%d' % seed) / arm; frame_packet = read(out / 'INPUT-FRAMES.json'); frames = {a['id']: a for a in frame_packet['rows']}
        closed = read(out / 'CLOSED.json'); assert sha(out / 'INPUT-FRAMES.json') == closed['input_frames_sha256']
        checks = {'question_ids_match_presealed_token_audit': True, 'question_hashes_match_audit_and_verified_TRAIN_targets': True,
                  'canonical_TRAIN_targets_match_presealed_verified_packet': True, 'empty_notebook': True, 'no_truncation': frame_packet['truncation'] is False,
                  'frame_canonical_hashes_valid': True, 'all_training_records_bind_intended_frames_labels_masks': True}
        for identity, frame in frames.items():
            audit = audits[identity]; target = targets[identity]
            checks['question_ids_match_presealed_token_audit'] &= frame['input_ids'] == [audit['question_token_ids_with_EOS']]
            checks['question_hashes_match_audit_and_verified_TRAIN_targets'] &= frame['question_sha256'] == audit['question_sha256'] == target['question_sha256']
            checks['canonical_TRAIN_targets_match_presealed_verified_packet'] &= frame['canonical_numeric_target'] == audit['numeric_target'] == target['numeric_target'] and target['independently_verified'] is True
            checks['empty_notebook'] &= frame['notebook_ids'] == [[]] and frame['notebook_mask'] == [[]]
            checks['frame_canonical_hashes_valid'] &= canonical({k: v for k, v in frame.items() if k != 'frame_sha256'}) == frame['frame_sha256']
        training = []; nonfinite = 0; zero_grad = 0; clipped = 0
        for line in (out / 'TRAIN-RAW.jsonl').open(encoding='utf8'):
            record = json.loads(line); frame = frames[record['id']]
            checks['all_training_records_bind_intended_frames_labels_masks'] &= record['input_frame_sha256'] == frame['frame_sha256'] and record['source_question_sha256'] == frame['question_sha256'] and record['labels'] == frame['labels'] and record['label_mask'] == frame['label_mask']
            if not math.isfinite(record['numeric_CE']) or not math.isfinite(record['preclip_norm']): nonfinite += 1
            zero_grad += record['preclip_norm'] == 0; clipped += record['preclip_norm'] > 1
            training.append(record)
        assert len(training) == 5120 and set(frames) == set(plan['selected_ids']) and all(checks.values())
        diags = {}; diagnostic_ids = {}; diagnostic_stops = {}; diagnostic_teacherforced = {}
        for step in plan['diagnostic_updates']:
            diags[step] = []; diagnostic_ids[step] = set(); diagnostic_stops[step] = Counter(); diagnostic_teacherforced[step] = 0
        for line in (out / 'DIAGNOSTIC-RAW.jsonl').open(encoding='utf8'):
            record = json.loads(line); step = record['update']; identity = record['id']; frame = frames[identity]
            assert identity not in diagnostic_ids[step]; diagnostic_ids[step].add(identity)
            assert record['labels'] == frame['labels'] and record['canonical_numeric_target'] == frame['canonical_numeric_target']
            assert record['canonical_target_ids_with_EOS'] == frame['labels'][0]
            primary = strict_score(record, record['canonical_target_ids_with_EOS'])
            diags[step].append((record['numeric_CE'], primary)); diagnostic_stops[step][record['termination_reason']] += 1
            diagnostic_teacherforced[step] += record['teacherforced_argmax'] == record['labels']
        boundaries = []
        for visit, step in ((3, 768), (10, 2560), (20, 5120)):
            assert diagnostic_ids[step] == set(plan['selected_ids'])
            online = [r for r in training if r['visit_for_row'] == visit]
            assert len(online) == 256
            boundaries.append({'visits': visit, 'update': step, 'online_visit_mean_numeric_CE': statistics.mean(r['numeric_CE'] for r in online),
                'diagnostic_mean_numeric_CE': statistics.mean(c for c, _ in diags[step]), 'TRAIN_strict_correct': sum(p for _, p in diags[step]),
                'TRAIN_teacherforced_sequence_exact': diagnostic_teacherforced[step], 'termination_reasons': dict(diagnostic_stops[step])})
        result['matrix'].append({'seed': seed, 'arm': arm, 'first_update_numeric_CE': training[0]['numeric_CE'], 'last_update_numeric_CE': training[-1]['numeric_CE'],
            'first_visit_mean_numeric_CE': statistics.mean(r['numeric_CE'] for r in training if r['visit_for_row'] == 1),
            'last_visit_mean_numeric_CE': statistics.mean(r['numeric_CE'] for r in training if r['visit_for_row'] == 20),
            'min_numeric_CE': min(r['numeric_CE'] for r in training), 'max_numeric_CE': max(r['numeric_CE'] for r in training),
            'preclip_norm_min': min(r['preclip_norm'] for r in training), 'preclip_norm_max': max(r['preclip_norm'] for r in training),
            'preclip_norm_mean': statistics.mean(r['preclip_norm'] for r in training), 'updates_above_clip_threshold_1': clipped,
            'zero_gradient_norm_updates': zero_grad, 'nonfinite_CE_or_norm_records': nonfinite,
            'boundaries': boundaries, 'saved_input_target_checks': checks,
            'diagnostic_raw_sha256': sha(out / 'DIAGNOSTIC-RAW.jsonl'), 'TRAIN_raw_sha256': sha(out / 'TRAIN-RAW.jsonl')})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', required=True)
    parser.add_argument('--recount-source', required=True)
    args = parser.parse_args()
    import importlib.util
    spec = importlib.util.spec_from_file_location('_saved_token_recount', args.recount_source)
    scorer = importlib.util.module_from_spec(spec); spec.loader.exec_module(scorer)
    print(json.dumps(analyze(Path(args.root), scorer.score), indent=2, sort_keys=True))

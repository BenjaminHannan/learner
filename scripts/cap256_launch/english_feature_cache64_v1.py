"""G4: contextual frozen-feature cache for English inputs up to 64 tokens (incl. EOS).

English-scoped wrapper around the unchanged contextual compare worker: the same
feature identity validator, the same frozen extraction (final-layer LFM2
last_hidden_state, no past, no cache, detached FP32) and the same manifest +
payload {'cache_key_sha256','features'} layout. The only changes are the input
cap (64 instead of 49), a bounded row count instead of exactly 32, and that the
key is built from input token IDs/mask/learner text only (never targets).
Import is stdlib-only; Torch is passed in.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402

KEY_SCHEMA = 'premonition.English-input-feature-key.v1'
CACHE_SCHEMA = 'premonition.English-input-feature-cache.v1'
ARM = 'contextual'
INPUT_CAP_WITH_EOS = 64
MAX_ROWS = 512
COMPARE_WORKER = HERE / 'train_contextual_input_compare_windows_v1.py'
COMPARE_WORKER_SHA256 = '155f7256c183880f6b52cad4bd97fe2085de7110da4195d749f7775d2f2c3a42'


def load_compare_worker():
    if common.digest(COMPARE_WORKER) != COMPARE_WORKER_SHA256:
        raise ValueError('pinned contextual compare worker bytes differ')
    name = '_english_cache_compare_worker'
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, COMPARE_WORKER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def english_input_feature_key(record, feature_identity):
    """Only learner input enters the key: text digest, token IDs, mask, positions."""
    load_compare_worker().validate_feature_identity(feature_identity)
    allowed = {'input_id', 'learner_text', 'input_ids', 'input_mask'}
    if type(record) is not dict or not set(record) >= allowed:
        raise ValueError('input record with input_id/learner_text/input_ids/input_mask required')
    ids, mask, text = record['input_ids'], record['input_mask'], record['learner_text']
    if (type(ids) is not list or len(ids) != 1 or type(ids[0]) is not list
            or not 2 <= len(ids[0]) <= INPUT_CAP_WITH_EOS
            or any(type(v) is not int or not 0 <= v < 65536 for v in ids[0])
            or any(v in (common.PAD_ID, common.BOS_ID) for v in ids[0])
            or ids[0][-1] != common.EOS_ID or common.EOS_ID in ids[0][:-1]
            or type(mask) is not list or len(mask) != 1 or mask[0] != [True] * len(ids[0])
            or type(text) is not str or not text or type(record['input_id']) is not str):
        raise ValueError('complete English input IDs (<=64 incl. one terminal EOS) and all-true mask required')
    return {'schema': KEY_SCHEMA, 'arm': ARM, 'feature_identity': feature_identity,
            'learner_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'input_ids_sha256': common.canonical(ids), 'input_ids': ids, 'input_mask': mask,
            'position_ids': [list(range(len(ids[0])))], 'past_key_values': None, 'use_cache': False,
            'output_hidden_states': False, 'output_attentions': False, 'return_dict': True,
            'layer': feature_identity['contextual_layer']}


def tensor_digest(tensor):
    return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def _rows(records):
    if type(records) is not list or not 1 <= len(records) <= MAX_ROWS:
        raise ValueError('bounded 1..512 English input records required')
    ids = [r.get('input_id') for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('unique input_id per record required')


def build_english_feature_cache(lm, records, identity, torch, *, device, guard, gpu_guard,
                                max_seconds, max_bytes):
    _rows(records)
    worker = load_compare_worker()
    started = time.monotonic()
    features, manifest_rows, used = [], [], 0
    for record in records:
        key = english_input_feature_key(record, identity)
        guard()
        gpu_guard()
        ids = torch.tensor(key['input_ids'], device=device, dtype=torch.long)
        mask = torch.tensor(key['input_mask'], device=device, dtype=torch.bool)
        feature, seconds = common.timed_call(
            lambda: worker.extract_question_features(lm, ids, mask, ARM, torch), torch)
        used += feature.numel() * feature.element_size()
        if used > max_bytes or time.monotonic() - started > max_seconds:
            raise RuntimeError('English input cache byte/wall cap exceeded')
        manifest_rows.append({'input_id': record['input_id'], 'key_sha256': common.canonical(key),
                              'features_sha256': tensor_digest(feature), 'shape': list(feature.shape),
                              'bytes': feature.numel() * feature.element_size(),
                              'encoding_seconds': seconds, 'backbone_forward_calls': 1})
        features.append(feature)
    return features, {'schema': CACHE_SCHEMA, 'arm': ARM, 'rows': len(records), 'records': manifest_rows,
                      'feature_identity': identity, 'cache_bytes': used,
                      'cache_seconds': time.monotonic() - started, 'pre_reader_only': True,
                      'input_only': True, 'gold_accessed': False,
                      'backbone_forward_calls': len(records), 'reused': False}


def prepare_english_feature_cache(lm, records, identity, torch, *, device, directory, guard,
                                  gpu_guard, max_seconds, max_bytes):
    """Build once, then reuse the exact saved frozen features (verified by digest)."""
    _rows(records)
    keys = [english_input_feature_key(r, identity) for r in records]
    key_digest = common.canonical(keys)
    directory = Path(directory)
    path = directory / ('english-%s-%s.pt' % (ARM, key_digest))
    manifest = directory / ('english-%s-%s.json' % (ARM, key_digest))
    started = time.monotonic()
    if path.exists() or manifest.exists():
        if not path.is_file() or not manifest.is_file():
            raise RuntimeError('partial English feature cache preserved; explicit recovery required')
        receipt = json.loads(manifest.read_bytes())
        if (receipt.get('cache_key_sha256') != key_digest or receipt.get('feature_identity') != identity
                or receipt.get('rows') != len(records) or receipt.get('cache_file_sha256') != common.digest(path)):
            raise ValueError('saved English cache identity/file digest differs')
        guard()
        gpu_guard()
        payload = torch.load(path, map_location=device, weights_only=True)
        if (type(payload) is not dict or set(payload) != {'cache_key_sha256', 'features'}
                or payload['cache_key_sha256'] != key_digest or type(payload['features']) is not list
                or len(payload['features']) != len(records)):
            raise ValueError('saved English cache payload differs')
        total = 0
        for record, key, feature, row in zip(records, keys, payload['features'], receipt['records']):
            if (tuple(feature.shape) != (1, len(record['input_ids'][0]), 2048)
                    or feature.dtype != torch.float32 or feature.requires_grad
                    or not bool(torch.isfinite(feature).all()) or row.get('input_id') != record['input_id']
                    or row.get('key_sha256') != common.canonical(key)
                    or row.get('features_sha256') != tensor_digest(feature)):
                raise ValueError('saved English frozen feature values differ')
            total += feature.numel() * feature.element_size()
        if total != receipt['cache_bytes'] or total > max_bytes:
            raise RuntimeError('saved English cache byte accounting differs')
        if time.monotonic() - started > max_seconds:
            raise RuntimeError('English cache reload wall cap exceeded')
        return payload['features'], {**receipt, 'reused': True, 'backbone_forward_calls': 0,
                                     'cache_load_seconds': time.monotonic() - started}
    features, receipt = build_english_feature_cache(lm, records, identity, torch, device=device,
        guard=guard, gpu_guard=gpu_guard, max_seconds=max_seconds, max_bytes=max_bytes)
    guard(receipt['cache_bytes'] + common.MIB)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {'cache_key_sha256': key_digest, 'features': [f.detach().cpu() for f in features]}
    with path.open('xb') as stream:
        torch.save(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())
    receipt = {**receipt, 'cache_key_sha256': key_digest, 'cache_file': path.name,
               'cache_file_sha256': common.digest(path), 'cache_file_bytes': path.stat().st_size}
    common.write_new_json(manifest, receipt)
    return features, receipt


def frame_input_record(frame):
    """TRAIN frame -> input-only record (targets are dropped before keying)."""
    return {'input_id': 'TRAIN-frame-%02d' % frame['frame_index'], 'learner_text': frame['learner_text'],
            'input_ids': frame['input_ids'], 'input_mask': frame['input_mask']}
